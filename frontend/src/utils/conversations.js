const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

const ROLE_MAP = {
  usuario: 'user',
  asistente: 'assistant',
  sistema: 'assistant',
}

const MAX_TITLE_LENGTH = 30

// Fecha corta del Historial: «02 oct 2026».
export function formatConversationDate(value) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return `${String(date.getDate()).padStart(2, '0')} ${
    MONTHS[date.getMonth()]
  } ${date.getFullYear()}`
}

export function formatFileType(formato) {
  const value = String(formato ?? '').toLowerCase()

  if (value === 'pdf') return 'PDF'
  if (value === 'docx') return 'DOC'
  if (value === 'txt') return 'TXT'
  if (value === 'md') return 'MD'

  return value ? value.toUpperCase() : 'DOC'
}

// El backend guarda los primeros 30 caracteres de la pregunta como título
// (`_titulo_desde_pregunta` en App/api/routes/queries.py). Se replica para
// mostrar el título al instante mientras llega la conversación recién creada.
export function deriveConversationTitle(question) {
  const text = String(question ?? '').split(/\s+/).filter(Boolean).join(' ')

  if (text.length <= MAX_TITLE_LENGTH) {
    return text
  }

  const cut = text.slice(0, MAX_TITLE_LENGTH)
  const lastSpace = cut.lastIndexOf(' ')

  return lastSpace > 0 ? cut.slice(0, lastSpace) : cut
}

export function mapSource(fuente) {
  return {
    id: fuente.id,
    mensajeId: fuente.mensaje_id,
    chunkId: fuente.chunk_id,
    documentId: fuente.documento_id,
    documento: fuente.documento ?? 'Documento',
    tipo: formatFileType(fuente.formato),
    categoria: fuente.categoria ?? '',
    pagina: fuente.pagina ?? null,
    chunk: fuente.indice ?? null,
    fragmento: fuente.fragmento ?? '',
    similitud: fuente.similitud ?? null,
  }
}

export function mapMessage(mensaje, fuentes = mensaje?.fuentes ?? []) {
  const conversationId = mensaje.conversacion_id ?? null
  // Cada fuente conserva la conversación de su mensaje: así «Volver al chat»
  // desde Evidencia reabre la conversación a la que pertenece la evidencia.
  const sources = (fuentes ?? []).map((fuente) => ({
    ...mapSource(fuente),
    conversationId,
  }))

  return {
    id: mensaje.id,
    conversationId,
    role: ROLE_MAP[mensaje.rol] ?? mensaje.rol,
    content: mensaje.contenido,
    sources,
    hasEvidence: sources.length > 0,
  }
}

export function mapConversation(conversation) {
  const mensajeCount = conversation.mensaje_count ?? 0

  return {
    ...conversation,
    titulo: conversation.titulo || 'Conversación sin título',
    ultimaPregunta: conversation.ultima_pregunta || 'Sin mensajes todavía',
    mensajeCount,
    fecha: formatConversationDate(
      conversation.fecha_actualizacion ?? conversation.fecha_creacion,
    ),
    documentId: null,
  }
}
