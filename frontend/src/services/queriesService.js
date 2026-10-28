// Punto único de acceso a consultas RAG (FRONTEND_SPEC §9.2).
// Sin mocks: no hay evidencia que recuperar hasta conectar la API. Se devuelve
// una respuesta vacía para que el chat muestre el aviso explícito de RF9 en
// lugar de inventar contenido.
const NOT_CONNECTED = 'La conexión con el backend todavía no está disponible.'

const queriesService = {
  async createConversation() {
    throw new Error(NOT_CONNECTED)
  },

  async getConversationMessages(conversationId) {
    return []
  },

  async ask() {
    return { respuesta: null, fuentes: [] }
  },
}

export default queriesService
