import { apiFetch } from './http.js'

const numberFormatter = new Intl.NumberFormat('es-CO')

function formatDocumentState(item) {
  if (item.estado === 'listo') {
    return 'vectorización completada'
  }

  if (item.estado === 'procesando') {
    return `procesando ${item.progreso ?? 0}%`
  }

  if (item.estado === 'pendiente') {
    return 'en cola'
  }

  if (item.estado === 'error') {
    return 'error de procesamiento'
  }

  return item.estado ?? 'sin estado'
}

function formatActivity(item) {
  if (item.tipo === 'documento') {
    return `${item.titulo} — ${formatDocumentState(item)}`
  }

  const mensajes = item.mensajes ?? 0
  return `Conversación “${item.titulo}” — ${mensajes} ${
    mensajes === 1 ? 'mensaje' : 'mensajes'
  }`
}

// Resumen del Dashboard para el usuario activo. El backend agrega los totales
// de documentos, conversaciones y chunks, y devuelve la actividad reciente.
const dashboardService = {
  async getSummary(usuarioId) {
    const data = await apiFetch(
      `/v1/dashboard/?usuario_id=${encodeURIComponent(usuarioId)}`,
    )

    return {
      stats: {
        documents: numberFormatter.format(data.documentos ?? 0),
        conversations: numberFormatter.format(data.conversaciones ?? 0),
        chunks: numberFormatter.format(data.chunks ?? 0),
      },
      recentActivity: (data.actividad ?? []).map((item) => ({
        id: `${item.tipo}-${item.id}`,
        message: formatActivity(item),
      })),
    }
  },
}

export default dashboardService
