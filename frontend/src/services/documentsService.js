import { apiFetch } from './http.js'

const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

function formatDate(value) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return `${String(date.getDate()).padStart(2, '0')} ${
    MONTHS[date.getMonth()]
  } ${date.getFullYear()}`
}

function formatType(formato) {
  const value = String(formato ?? '').toLowerCase()

  if (value === 'pdf') return 'PDF'
  if (value === 'docx') return 'DOC'
  if (value === 'txt') return 'TXT'
  if (value === 'md') return 'MD'

  return value ? value.toUpperCase() : 'DOC'
}

function mapDocument(document) {
  return {
    ...document,
    tipo: formatType(document.formato),
    fecha: formatDate(document.fecha_carga),
    categoria: document.categoria ?? '',
    chunks: document.num_chunks ?? 0,
  }
}

// Punto único de acceso a Documentos (FRONTEND_SPEC §9.2).
const documentsService = {
  async list(usuarioId) {
    const query = usuarioId
      ? `?usuario_id=${encodeURIComponent(usuarioId)}`
      : ''
    const data = await apiFetch(`/v1/models/documents/${query}`)
    return (data ?? []).map(mapDocument)
  },

  async getById(id) {
    return mapDocument(await apiFetch(`/v1/models/documents/${id}`))
  },

  async upload(file, metadata = {}, usuarioId) {
    if (!usuarioId) {
      throw new Error('No hay un perfil activo.')
    }

    const formData = new FormData()
    formData.append('archivo', file, file.name)
    formData.append('usuario_id', usuarioId)

    const categoria = String(metadata.categoria ?? '').trim()
    if (categoria) {
      formData.append('categoria', categoria)
    }

    const data = await apiFetch('/v1/models/documents/upload', {
      method: 'POST',
      body: formData,
    })

    return mapDocument(data)
  },

  async remove(id) {
    return apiFetch(`/v1/models/documents/${id}`, { method: 'DELETE' })
  },
}

export default documentsService
