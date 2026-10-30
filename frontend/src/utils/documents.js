export const DOCUMENT_STATES = [
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'procesando', label: 'Procesando' },
  { value: 'listo', label: 'Listo' },
  { value: 'error', label: 'Error' },
]

export function getDocumentStateLabel(estado) {
  return DOCUMENT_STATES.find((state) => state.value === estado)?.label ?? estado
}

export function getDocumentPagesLabel(document) {
  const pages = Number(document?.num_paginas)

  if (!Number.isInteger(pages) || pages < 1) {
    return '— páginas'
  }

  return `${pages.toLocaleString('es-ES')} ${
    pages === 1 ? 'página' : 'páginas'
  }`
}

export function getDocumentSecondaryText(document) {
  switch (document.estado) {
    case 'pendiente':
      return 'En cola'
    case 'procesando':
      return `Indexando ${document.progreso ?? 0}%`
    case 'listo':
    case 'error':
      return getDocumentPagesLabel(document)
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
      return 'Páginas'
    default:
      return 'Información'
  }
}
