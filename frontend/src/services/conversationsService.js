// Punto único de acceso a conversaciones e historial (FRONTEND_SPEC §9.2).
// Sin mocks: el historial arranca vacío hasta conectar la API de FastAPI.
const NOT_CONNECTED = 'La conexión con el backend todavía no está disponible.'

const conversationsService = {
  async list() {
    return []
  },

  async getById() {
    throw new Error(NOT_CONNECTED)
  },

  async getMessages(id) {
    return []
  },
}

export default conversationsService
