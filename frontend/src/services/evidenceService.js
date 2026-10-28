// Punto único de acceso a la evidencia (FRONTEND_SPEC §9.2).
// Sin mocks: no hay fuentes hasta conectar la API. `getDefault` devuelve null
// para que la pantalla muestre su estado vacío en lugar de un error.
const NOT_CONNECTED = 'La conexión con el backend todavía no está disponible.'

const evidenceService = {
  async getById() {
    throw new Error(NOT_CONNECTED)
  },

  async getDefault() {
    return null
  },
}

export default evidenceService
