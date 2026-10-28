// Punto único de acceso a la voz (FRONTEND_SPEC §9.2).
// Sin mocks: el flujo de voz queda pendiente de conectar la API.
const NOT_CONNECTED = 'La conexión con el backend todavía no está disponible.'

const voiceService = {
  async process() {
    throw new Error(NOT_CONNECTED)
  },
}

export default voiceService
