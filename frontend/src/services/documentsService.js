// Punto único de acceso a Documentos (FRONTEND_SPEC §9.2).
// Los mocks se eliminaron al iniciar la conexión con el backend: por ahora la
// aplicación arranca sin datos hasta sustituir estas funciones por la API.
const NOT_CONNECTED = 'La conexión con el backend todavía no está disponible.'

const documentsService = {
  async list() {
    return []
  },

  async getById() {
    throw new Error(NOT_CONNECTED)
  },

  async upload() {
    throw new Error(NOT_CONNECTED)
  },

  async remove() {
    throw new Error(NOT_CONNECTED)
  },
}

export default documentsService
