import { mapMessage } from '../utils/conversations.js'
import { apiFetch } from './http.js'

// Punto único de acceso a consultas RAG (FRONTEND_SPEC §9.2).
const queriesService = {
  async createConversation(usuarioId) {
    return apiFetch('/v1/models/conversations/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario_id: usuarioId }),
    })
  },

  async ask(question, conversationId, options = {}) {
    const { documentIds = [], usuarioId } = options

    if (!usuarioId) {
      throw new Error('No hay un perfil activo.')
    }

    const payload = {
      usuario_id: usuarioId,
      contenido: question,
    }

    if (conversationId) {
      payload.conversacion_id = conversationId
    }

    // Sin documentos seleccionados no se envía `filtros`: el backend busca
    // entonces en todos los documentos del usuario en lugar de filtrar por una
    // lista vacía, que no devolvería evidencia (RF6, RF9).
    if (documentIds.length > 0) {
      payload.filtros = { documento_ids: documentIds }
    }

    const data = await apiFetch('/v1/queries/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!data?.mensaje) {
      throw new Error('El servidor no devolvió una respuesta.')
    }

    return {
      conversationId: data.mensaje.conversacion_id ?? conversationId,
      message: mapMessage(data.mensaje, data.referencias ?? []),
    }
  },
}

export default queriesService
