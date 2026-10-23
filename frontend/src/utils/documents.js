export const DOCUMENT_STATES = [
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'procesando', label: 'Procesando' },
  { value: 'listo', label: 'Listo' },
  { value: 'error', label: 'Error' },
]

export function getDocumentStateLabel(estado) {
  return DOCUMENT_STATES.find((state) => state.value === estado)?.label ?? estado
}

export function getDocumentSecondaryText(document) {
  switch (document.estado) {
    case 'pendiente':
      return 'En cola'
    case 'procesando':
      return `Indexando ${document.progreso ?? 0}%`
    case 'listo':
      return `${(document.chunks ?? 0).toLocaleString('es-ES')} chunks`
    case 'error':
      return 'Sin chunks'
    default:
      return ''
  }
}

export function getDocumentMetricLabel(estado) {
  switch (estado) {
    case 'pendiente':
      return 'Estado de procesamiento'
    case 'procesando':
      return 'Progreso'
    case 'listo':
    case 'error':
      return 'Chunks generados'
    default:
      return 'Información'
  }
}
