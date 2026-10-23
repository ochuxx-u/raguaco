import {
  askQuestion,
  createChatConversation,
  getChatMessages,
} from '../mocks/mockBackend.js'

const queriesService = {
  createConversation(documentId) {
    return createChatConversation(documentId)
  },

  getConversationMessages(conversationId) {
    return getChatMessages(conversationId)
  },

  ask(question, conversationId, options) {
    return askQuestion(question, conversationId, options)
  },
}

export default queriesService
