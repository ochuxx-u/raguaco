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
