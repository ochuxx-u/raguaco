import {
  getChatConversationById,
  getChatMessages,
  listChatConversations,
} from '../mocks/mockBackend.js'

// Punto único de acceso a conversaciones e historial. Las firmas se mantienen
// preparadas para sustituir la implementación mock por la API de FastAPI.
const conversationsService = {
  list() {
    return listChatConversations()
  },

  getById(id) {
    return getChatConversationById(id)
  },

  getMessages(id) {
    return getChatMessages(id)
  },
}

export default conversationsService
