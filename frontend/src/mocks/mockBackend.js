import { documentSeeds } from './documentSeeds.js'

const LATENCY_MIN = 300
const LATENCY_MAX = 800
const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

const documents = documentSeeds.map((document) => ({ ...document }))
const processingTimers = new Map()
let sequence = 0

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

function getLatency() {
  return LATENCY_MIN + Math.round(Math.random() * (LATENCY_MAX - LATENCY_MIN))
}

function cloneDocument(document) {
  return { ...document }
}

function formatDate(date) {
  const day = String(date.getDate()).padStart(2, '0')
  const month = MONTHS[date.getMonth()]
  return `${day} ${month} ${date.getFullYear()}`
}

function getFileType(fileName) {
  const extension = fileName.split('.').pop()?.toLowerCase()

  if (extension === 'pdf') return 'PDF'
  if (extension === 'docx') return 'DOC'
  if (extension === 'txt') return 'TXT'
  return null
}

function estimateChunks(file) {
  const size = Number(file?.size) || 0
  return Math.max(24, Math.min(360, Math.round(size / 1024) || 48))
}

function stopProcessingSimulation(id) {
  const timers = processingTimers.get(id)

  if (!timers) return

  clearTimeout(timers.startTimer)
  clearInterval(timers.progressTimer)
  processingTimers.delete(id)
}

function startProcessingSimulation(id, file) {
  const startTimer = setTimeout(() => {
    const document = documents.find((item) => item.id === id)

    if (!document) return

    document.estado = 'procesando'
    document.progreso = 15
  }, 800)

  const progressTimer = setInterval(() => {
    const document = documents.find((item) => item.id === id)

    if (!document) {
      stopProcessingSimulation(id)
      return
    }

    if (document.estado !== 'procesando') return

    const nextProgress = Math.min(100, (document.progreso ?? 0) + 14)

    if (nextProgress >= 100) {
      document.estado = 'listo'
      document.progreso = null
      document.chunks = estimateChunks(file)
      stopProcessingSimulation(id)
      return
    }

    document.progreso = nextProgress
  }, 650)

  processingTimers.set(id, { startTimer, progressTimer })
}

export async function listDocuments() {
  await wait(getLatency())
  return documents.map(cloneDocument)
}

export async function getDocumentById(id) {
  await wait(getLatency())

  const document = documents.find((item) => item.id === id)

  if (!document) {
    throw new Error('Documento no encontrado.')
  }

  return cloneDocument(document)
}

export async function uploadDocument(file, metadata = {}) {
  await wait(getLatency())

  const tipo = getFileType(file.name)

  if (!tipo) {
    throw new Error('Formato de archivo no permitido.')
  }

  const categoria = String(metadata.categoria ?? '').trim() || 'Sin categoría'
  const id = `doc-${Date.now()}-${sequence++}`
  const document = {
    id,
    nombre: file.name,
    tipo,
    categoria,
    fecha: formatDate(new Date()),
    estado: 'pendiente',
    progreso: null,
    chunks: null,
  }

  documents.unshift(document)
  startProcessingSimulation(id, file)

  return cloneDocument(document)
}

export async function removeDocument(id) {
  await wait(getLatency())

  const index = documents.findIndex((document) => document.id === id)

  if (index === -1) {
    throw new Error('Documento no encontrado.')
  }

  stopProcessingSimulation(id)
  const [removedDocument] = documents.splice(index, 1)

  return cloneDocument(removedDocument)
}
