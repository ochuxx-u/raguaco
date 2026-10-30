import { API_BASE_URL } from '../config.js'
import { mapMessage } from '../utils/conversations.js'
import { apiStream } from './http.js'

// Punto único de acceso a la voz (FRONTEND_SPEC §9.2).

function audioFilename(blob) {
  const type = String(blob?.type ?? '').toLowerCase()

  if (type.includes('mp4')) return 'pregunta.m4a'
  if (type.includes('ogg')) return 'pregunta.ogg'
  if (type.includes('wav')) return 'pregunta.wav'

  return 'pregunta.webm'
}

/**
 * Convierte una URL absoluta del backend (`http://127.0.0.1:8000/...`) en una
 * ruta que pasa por el proxy `/v1` de Vite. No se hardcodea el host.
 */
export function normalizeAudioUrl(url) {
  if (!url) {
    return ''
  }

  try {
    const origin =
      typeof window !== 'undefined' ? window.location.origin : 'http://localhost'
    const parsed = new URL(url, origin)

    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return url
    }

    return `${API_BASE_URL}${parsed.pathname}${parsed.search}`
  } catch {
    return url
  }
}

const voiceService = {
  /**
   * Envía el audio al flujo completo STT → RAG → TTS.
   *
   * Devuelve el resultado acumulado y notifica cada evento NDJSON mediante
   * `onEvent`. Los eventos `fragmento` llegan con `url` normalizada para que
   * `audioPlayer` la reproduzca a través del proxy.
   */
  async consult({
    audioBlob,
    usuarioId,
    conversacionId = null,
    documentIds = [],
    signal,
    onEvent,
  } = {}) {
    if (!audioBlob) {
      throw new Error('No se recibió audio de la pregunta.')
    }

    if (!usuarioId) {
      throw new Error('No hay un perfil activo.')
    }

    const formData = new FormData()
    formData.append('audio', audioBlob, audioFilename(audioBlob))
    formData.append('usuario_id', usuarioId)

    if (conversacionId) {
      formData.append('conversacion_id', conversacionId)
    }

    // El backend acepta `documento_ids` repetido en el multipart, con el mismo
    // concepto de filtro que POST /v1/queries/.
    const ids = Array.isArray(documentIds) ? documentIds : []

    for (const documentoId of ids) {
      if (documentoId) {
        formData.append('documento_ids', documentoId)
      }
    }

    const resultado = {
      transcripcion: '',
      respuesta: '',
      conversationId: conversacionId ?? null,
      message: null,
      sources: [],
      audioUrls: [],
      jobId: null,
    }

    await apiStream('/v1/voice/consultar', {
      method: 'POST',
      body: formData,
      signal,
      onEvent: (event) => {
        switch (event.tipo) {
          case 'transcripcion':
            resultado.transcripcion = event.texto ?? ''
            break

          case 'respuesta': {
            const message = event.mensaje
              ? mapMessage(event.mensaje, event.referencias ?? [])
              : null

            resultado.respuesta = event.texto ?? message?.content ?? ''
            resultado.conversationId =
              event.conversacion_id ??
              message?.conversationId ??
              resultado.conversationId
            resultado.message = message
            resultado.sources = message?.sources ?? []
            break
          }

          case 'inicio':
            resultado.jobId = event.job_id ?? null
            break

          case 'fragmento': {
            const url = normalizeAudioUrl(event.url)

            if (url) {
              resultado.audioUrls.push(url)
            }

            onEvent?.({ ...event, url })
            return
          }

          case 'fin':
            if (event.conversacion_id) {
              resultado.conversationId = event.conversacion_id
            }
            break

          default:
            break
        }

        onEvent?.(event)
      },
    })

    return resultado
  },
}

export default voiceService
