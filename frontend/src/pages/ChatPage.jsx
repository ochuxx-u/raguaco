import { useEffect, useMemo, useRef, useState } from 'react'
import ChatDocumentsPanel from '../components/chat/ChatDocumentsPanel.jsx'
import ChatWindow from '../components/chat/ChatWindow.jsx'
import EvidencePanel from '../components/evidence/EvidencePanel.jsx'
import documentsService from '../services/documentsService.js'
import queriesService from '../services/queriesService.js'
import './ChatPage.css'

const INITIAL_EVIDENCE = {
  messageId: null,
  sourceId: null,
}

function ChatPage({
  conversationId,
  onSelectedDocumentChange = () => {},
  selectedDocumentId = null,
}) {
  const [documents, setDocuments] = useState([])
  const [isDocumentsLoading, setIsDocumentsLoading] = useState(true)
  const [documentsError, setDocumentsError] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')

  const [messages, setMessages] = useState([])
  const [isMessagesLoading, setIsMessagesLoading] = useState(true)
  const [messagesError, setMessagesError] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [sendError, setSendError] = useState('')
  const [attachment, setAttachment] = useState(null)
  const [attachmentError, setAttachmentError] = useState('')
  const [isAttaching, setIsAttaching] = useState(false)

  const [activeEvidence, setActiveEvidence] = useState(INITIAL_EVIDENCE)
  const [evidenceFocusToken, setEvidenceFocusToken] = useState(0)
  const [isDocumentsOpen, setIsDocumentsOpen] = useState(false)
  const [isEvidenceOpen, setIsEvidenceOpen] = useState(false)

  const messageSequence = useRef(0)
  const documentsRequestRef = useRef(0)
  const messagesRequestRef = useRef(0)

  const loadDocuments = async () => {
    const requestId = ++documentsRequestRef.current
    setIsDocumentsLoading(true)
    setDocumentsError('')

    try {
      const nextDocuments = await documentsService.list()

      if (requestId !== documentsRequestRef.current) return

      setDocuments(nextDocuments)
    } catch {
      if (requestId === documentsRequestRef.current) {
        setDocumentsError('No se pudieron cargar los documentos.')
      }
    } finally {
      if (requestId === documentsRequestRef.current) {
        setIsDocumentsLoading(false)
      }
    }
  }

  const loadConversationMessages = async () => {
    const requestId = ++messagesRequestRef.current
    setMessages([])
    setActiveEvidence(INITIAL_EVIDENCE)
    setIsMessagesLoading(true)
    setMessagesError('')

    try {
      const conversationMessages =
        await queriesService.getConversationMessages(conversationId)

      if (requestId !== messagesRequestRef.current) return

      const latestAssistant = [...conversationMessages]
        .reverse()
        .find((message) => message.role === 'assistant')

      setMessages(conversationMessages)
      setActiveEvidence({
        messageId: latestAssistant?.id ?? null,
        sourceId: latestAssistant?.sources?.[0]?.id ?? null,
      })
    } catch {
      if (requestId === messagesRequestRef.current) {
        setMessagesError('No se pudo cargar la conversación.')
      }
    } finally {
      if (requestId === messagesRequestRef.current) {
        setIsMessagesLoading(false)
      }
    }
  }

  useEffect(() => {
    void loadDocuments()
  }, [])

  useEffect(() => {
    void loadConversationMessages()
  }, [conversationId])

  useEffect(() => {
    if (documents.length === 0) return

    const hasSelectedDocument =
      selectedDocumentId &&
      documents.some((document) => document.id === selectedDocumentId)

    if (!hasSelectedDocument) {
      if (typeof onSelectedDocumentChange === 'function') {
        onSelectedDocumentChange(documents[0].id)
      }
    }
  }, [documents, selectedDocumentId, onSelectedDocumentChange])

  const categories = useMemo(() => {
    const result = []

    for (const document of documents) {
      if (!result.includes(document.categoria)) {
        result.push(document.categoria)
      }
    }

    return result
  }, [documents])

  useEffect(() => {
    if (categoryFilter !== 'all' && !categories.includes(categoryFilter)) {
      setCategoryFilter('all')
    }
  }, [categories, categoryFilter])

  const filteredDocuments = useMemo(() => {
    if (categoryFilter === 'all') return documents
    return documents.filter((document) => document.categoria === categoryFilter)
  }, [documents, categoryFilter])

  const activeDocumentId = selectedDocumentId ?? null
  const selectedDocument =
    documents.find((document) => document.id === activeDocumentId) ?? null

  const activeEvidenceMessage = messages.find(
    (message) => message.id === activeEvidence.messageId,
  )
  const evidenceSources = activeEvidenceMessage?.sources ?? []

  useEffect(() => {
    if (!isDocumentsOpen && !isEvidenceOpen) {
      return undefined
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsDocumentsOpen(false)
        setIsEvidenceOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isDocumentsOpen, isEvidenceOpen])

  const handleSelectDocument = (document) => {
    if (!document?.id) return

    if (typeof onSelectedDocumentChange === 'function') {
      onSelectedDocumentChange(document.id)
    }

    setIsDocumentsOpen(false)
  }

  const handleSourceClick = (messageId, sourceId) => {
    setActiveEvidence({ messageId, sourceId })
    setEvidenceFocusToken((token) => token + 1)
    setIsDocumentsOpen(false)
    setIsEvidenceOpen(true)
  }

  const handleOpenDocuments = () => {
    setIsDocumentsOpen(true)
    setIsEvidenceOpen(false)
  }

  const handleOpenEvidence = () => {
    setIsEvidenceOpen(true)
    setIsDocumentsOpen(false)
  }

  const closePanels = () => {
    setIsDocumentsOpen(false)
    setIsEvidenceOpen(false)
  }

  const createMessageId = (role) => {
    const id = `${role}-${Date.now()}-${messageSequence.current}`
    messageSequence.current += 1
    return id
  }

  const handleSend = async (question) => {
    const trimmedQuestion = question.trim()

    if (!trimmedQuestion || isThinking) return

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: createMessageId('user'),
        role: 'user',
        content: trimmedQuestion,
        sources: [],
      },
    ])
    setIsThinking(true)
    setSendError('')

    try {
      const result = await queriesService.ask(trimmedQuestion, conversationId, {
        documentId: activeDocumentId,
      })
      const sources = Array.isArray(result.fuentes) ? result.fuentes : []
      const hasEvidence = sources.length > 0 && Boolean(result.respuesta)
      const assistantMessage = {
        id: createMessageId('assistant'),
        role: 'assistant',
        content: hasEvidence ? result.respuesta : null,
        sources: hasEvidence ? sources : [],
        hasEvidence,
      }

      setMessages((currentMessages) => [...currentMessages, assistantMessage])
      setActiveEvidence({
        messageId: assistantMessage.id,
        sourceId: hasEvidence ? assistantMessage.sources[0]?.id ?? null : null,
      })
    } catch {
      setSendError('No se pudo obtener una respuesta. Inténtalo de nuevo.')
    } finally {
      setIsThinking(false)
    }
  }

  const handleAttachFile = async (file) => {
    if (!file || isAttaching) return

    setAttachment({ name: file.name })
    setAttachmentError('')
    setIsAttaching(true)

    try {
      const uploadedDocument = await documentsService.upload(file)

      setAttachment({ name: uploadedDocument.nombre })
      setDocuments((currentDocuments) => {
        if (currentDocuments.some((document) => document.id === uploadedDocument.id)) {
          return currentDocuments
        }

        return [uploadedDocument, ...currentDocuments]
      })
    } catch {
      setAttachment(null)
      setAttachmentError(
        'No se pudo adjuntar el archivo. Solo se permiten PDF, DOCX o TXT.',
      )
    } finally {
      setIsAttaching(false)
    }
  }

  return (
    <div className="chat-page">
      <aside
        className={`chat-page__sidebar chat-page__sidebar--documents${
          isDocumentsOpen ? ' chat-page__sidebar--open' : ''
        }`}
        id="chat-documents-panel"
        aria-label="Panel de documentos"
      >
        <ChatDocumentsPanel
          categories={categories}
          categoryFilter={categoryFilter}
          documents={filteredDocuments}
          error={documentsError}
          isLoading={isDocumentsLoading}
          onCategoryChange={setCategoryFilter}
          onClose={() => setIsDocumentsOpen(false)}
          onRetry={loadDocuments}
          onSelectDocument={handleSelectDocument}
          selectedDocumentId={activeDocumentId}
        />
      </aside>

      <div className="chat-page__conversation">
        <ChatWindow
          activeEvidence={activeEvidence}
          attachment={attachment}
          attachmentError={attachmentError}
          error={messagesError}
          isAttaching={isAttaching}
          isDocumentsOpen={isDocumentsOpen}
          isEvidenceOpen={isEvidenceOpen}
          isLoading={isMessagesLoading}
          isThinking={isThinking}
          messages={messages}
          onAttachFile={handleAttachFile}
          onOpenDocuments={handleOpenDocuments}
          onOpenEvidence={handleOpenEvidence}
          onRetry={loadConversationMessages}
          onSend={handleSend}
          onSourceClick={handleSourceClick}
          selectedDocument={selectedDocument}
          sendError={sendError}
        />
      </div>

      <aside
        className={`chat-page__sidebar chat-page__sidebar--evidence${
          isEvidenceOpen ? ' chat-page__sidebar--open' : ''
        }`}
        id="chat-evidence-panel"
        aria-label="Panel de fuentes y evidencia"
      >
        <EvidencePanel
          activeSourceId={activeEvidence.sourceId}
          focusToken={evidenceFocusToken}
          onClose={() => setIsEvidenceOpen(false)}
          sources={evidenceSources}
        />
      </aside>

      {(isDocumentsOpen || isEvidenceOpen) && (
        <button
          className="chat-page__backdrop"
          type="button"
          aria-label="Cerrar panel lateral"
          onClick={closePanels}
        />
      )}
    </div>
  )
}

export default ChatPage
