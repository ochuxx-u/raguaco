import { API_BASE_URL } from '../config.js'

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readErrorMessage(response) {
  try {
    const body = await response.json()

    if (typeof body?.detail === 'string') {
      return body.detail
    }

    if (Array.isArray(body?.detail)) {
      return body.detail.map((item) => item?.msg ?? String(item)).join(' ')
    }
  } catch {
    // Respuesta sin JSON: se usa el mensaje genérico.
  }

  return `El servidor respondió con un error ${response.status}.`
}

export async function apiFetch(path, options = {}) {
  const { headers, ...rest } = options
  let response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      headers: { Accept: 'application/json', ...headers },
    })
  } catch {
    throw new ApiError('No se pudo conectar con el servidor.')
  }

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status)
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

/**
 * Consume una respuesta NDJSON (una línea JSON por evento).
 *
 * Se usa para los endpoints de voz, que devuelven el resultado por partes:
 * `response.json()` no sirve porque el cuerpo llega como un stream.
 *
 * `onEvent` recibe cada evento ya parseado. Si el servidor emite un evento
 * `tipo: "error"` (incluso con HTTP 200), se notifica y después se lanza un
 * `ApiError` para que la página pueda detener su estado de carga.
 */
export async function apiStream(path, options = {}) {
  const { body, headers, method = 'POST', onEvent, signal } = options

  let response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      body,
      signal,
      // No se define Content-Type: con FormData lo pone el navegador con su
      // boundary. El Accept sí debe pedir el stream NDJSON.
      headers: { Accept: 'application/x-ndjson', ...headers },
    })
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw error
    }

    throw new ApiError('No se pudo conectar con el servidor.')
  }

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status)
  }

  if (!response.body) {
    throw new ApiError('El servidor no devolvió un flujo de datos.', response.status)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const emit = (line) => {
    const trimmed = line.trim()

    if (!trimmed) {
      return
    }

    let event

    try {
      event = JSON.parse(trimmed)
    } catch {
      throw new ApiError('El servidor devolvió una línea de voz inválida.')
    }

    onEvent?.(event)

    if (event?.tipo === 'error') {
      const error = new ApiError(
        event.detalle ?? 'El servicio de voz devolvió un error.',
        200,
      )
      error.code = event.codigo ?? 'voz'
      throw error
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()

      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })

      let newlineIndex = buffer.indexOf('\n')

      while (newlineIndex !== -1) {
        emit(buffer.slice(0, newlineIndex))
        buffer = buffer.slice(newlineIndex + 1)
        newlineIndex = buffer.indexOf('\n')
      }
    }

    // Última línea sin salto final (el backend normalmente ya añade \n).
    buffer += decoder.decode()
    emit(buffer)
  } catch (error) {
    try {
      await reader.cancel()
    } catch {
      // El stream ya estaba cerrado.
    }

    throw error
  } finally {
    reader.releaseLock()
  }
}
