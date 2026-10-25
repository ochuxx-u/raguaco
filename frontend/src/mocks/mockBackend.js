import { chatSeedMessages, vacationSources } from './chatSeeds.js'
import { conversationSeeds } from './conversationSeeds.js'
import { documentSeeds } from './documentSeeds.js'

const LATENCY_MIN = 300
const LATENCY_MAX = 800
const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

const documents = documentSeeds.map((document) => ({ ...document }))
const processingTimers = new Map()
const conversations = new Map()
const demoMessages = []
let sequence = 0
let conversationSequence = 0
let chatMessageSequence = 0

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

function getLatency() {
  return LATENCY_MIN + Math.round(Math.random() * (LATENCY_MAX - LATENCY_MIN))
}

function cloneDocument(document) {
  return { ...document }
}

function cloneSource(source) {
  return { ...source }
}

function cloneChatMessage(message) {
  return {
    ...message,
    sources: (message.sources ?? []).map(cloneSource),
  }
}

function cloneConversation(conversation) {
  return {
    ...conversation,
    messages: conversation.messages.map(cloneChatMessage),
  }
}

for (const conversation of conversationSeeds) {
  conversations.set(conversation.id, cloneConversation(conversation))
}

demoMessages.push(...chatSeedMessages.map(cloneChatMessage))

function appendChatMessages(conversationId, messages) {
  const targetMessages = conversationId
    ? conversations.get(conversationId)?.messages
    : demoMessages

  if (!targetMessages) return

  targetMessages.push(...messages.map(cloneChatMessage))
}

function getAllEvidenceSources() {
  const sourcesById = new Map()

  const collectSources = (messages) => {
    for (const message of messages) {
      for (const source of message.sources ?? []) {
        sourcesById.set(source.id, source)
      }
    }
  }

  collectSources(chatSeedMessages)
  collectSources(demoMessages)

  for (const conversation of conversations.values()) {
    collectSources(conversation.messages)
  }

  return [...sourcesById.values()]
}

function getLastUserQuestion(messages) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === 'user') {
      return messages[index].content ?? ''
    }
  }

  return ''
}

function normalizeText(value) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
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

export async function createChatConversation(documentId = null) {
  const id = `conversation-${Date.now()}-${conversationSequence++}`
  const conversation = {
    id,
    documentId: documentId ?? null,
    messages: [],
  }

  conversations.set(id, conversation)

  return cloneConversation(conversation)
}

export async function getChatMessages(conversationId) {
  await wait(getLatency())

  if (!conversationId) {
    const seedDocumentExists = documents.some(
      (document) => document.id === 'doc-manual-politicas',
    )

    return seedDocumentExists ? demoMessages.map(cloneChatMessage) : []
  }

  const conversation = conversations.get(conversationId)

  return conversation ? conversation.messages.map(cloneChatMessage) : []
}

export async function listChatConversations() {
  await wait(getLatency())

  return [...conversations.values()]
    .filter((conversation) => conversation.titulo && conversation.messages.length > 0)
    .map((conversation) => ({
      id: conversation.id,
      titulo: conversation.titulo,
      fecha: conversation.fecha,
      mensajeCount: conversation.messages.length,
      ultimaPregunta: getLastUserQuestion(conversation.messages),
      documentId: conversation.documentId ?? null,
    }))
}

export async function getChatConversationById(id) {
  await wait(getLatency())

  const conversation = conversations.get(id)

  if (!conversation) {
    throw new Error('Conversación no encontrada.')
  }

  return cloneConversation(conversation)
}

export async function getEvidenceById(id) {
  await wait(getLatency())

  const source = getAllEvidenceSources().find((item) => item.id === id)

  if (!source) {
    throw new Error('Evidencia no encontrada.')
  }

  return cloneSource(source)
}

export async function getDefaultEvidence() {
  await wait(getLatency())

  const source = getAllEvidenceSources()[0]

  if (!source) {
    throw new Error('Evidencia no disponible.')
  }

  return cloneSource(source)
}

export async function askQuestion(question, conversationId, options = {}) {
  await wait(getLatency())

  const normalizedQuestion = normalizeText(question)
  const seedDocumentExists = documents.some(
    (document) => document.id === 'doc-manual-politicas',
  )
  const requestedDocumentId = options.documentId ?? null
  const hasVacationEvidence =
    normalizedQuestion.includes('vacacion') &&
    seedDocumentExists &&
    (!requestedDocumentId || requestedDocumentId === 'doc-manual-politicas')
  const respuesta = hasVacationEvidence
    ? 'Corresponden 15 días hábiles después de completar un año de servicio.'
    : null
  const fuentes = hasVacationEvidence ? vacationSources.map(cloneSource) : []

  appendChatMessages(conversationId, [
    {
      id: `chat-message-${Date.now()}-${chatMessageSequence++}`,
      role: 'user',
      content: question,
      sources: [],
    },
    {
      id: `chat-message-${Date.now()}-${chatMessageSequence++}`,
      role: 'assistant',
      content: respuesta,
      sources: fuentes,
      hasEvidence: hasVacationEvidence,
    },
  ])

  return {
    respuesta,
    fuentes,
  }
}
