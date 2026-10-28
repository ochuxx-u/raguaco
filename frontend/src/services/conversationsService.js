import { mapConversation, mapMessage } from '../utils/conversations.js'
import { apiFetch } from './http.js'

// Punto único de acceso a conversaciones e historial (FRONTEND_SPEC §9.2).
const conversationsService = {
  async list(usuarioId) {
    if (!usuarioId) return []

    const data = await apiFetch(
      `/v1/models/conversations/?usuario_id=${encodeURIComponent(usuarioId)}`,
    )

    return (data ?? []).map(mapConversation)
  },

  getById(id) {
    return apiFetch(`/v1/models/conversations/${id}`)
  },

  async getMessages(id) {
    if (!id) return []

    const data = await apiFetch(`/v1/models/conversations/${id}/messages`)

    return (data ?? []).map((message) => mapMessage(message))
  },
}

export default conversationsService
