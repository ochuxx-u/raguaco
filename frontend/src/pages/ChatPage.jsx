import { useEffect, useRef, useState } from 'react'
import ChatDocumentsPanel from '../components/chat/ChatDocumentsPanel.jsx'
import ChatWindow from '../components/chat/ChatWindow.jsx'
import EvidencePanel from '../components/evidence/EvidencePanel.jsx'
import conversationsService from '../services/conversationsService.js'
import documentsService from '../services/documentsService.js'
import queriesService from '../services/queriesService.js'
import { deriveConversationTitle } from '../utils/conversations.js'
import './ChatPage.css'

const INITIAL_EVIDENCE = {
  messageId: null,
  sourceId: null,
}

function ChatPage({
  conversationId,
  currentUser = null,
  onConversationCreated = () => {},
  onConversationTitleChange = () => {},
  onNavigateToDocuments = () => {},
  onNavigateToVoice = () => {},
  onOpenEvidencePage = () => {},
  onSelectedDocumentsChange = () => {},
  onStartNewConversation = () => {},
  selectedDocumentIds: initialSelectedDocumentIds = [],
}) {
  const [documents, setDocuments] = useState([])
  const [isDocumentsLoading, setIsDocumentsLoading] = useState(true)
  const [documentsError, setDocumentsError] = useState('')
  const [selectedDocumentIds, setSelectedDocumentIds] = useState(() =>
    initialSelectedDocumentIds.filter(Boolean),
  )

  const [conversationTitle, setConversationTitle] = useState('')
  const [messages, setMessages] = useState([])
  const [isMessagesLoading, setIsMessagesLoading] = useState(true)
  const [messagesError, setMessagesError] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [sendError, setSendError] = useState('')

  const [activeEvidence, setActiveEvidence] = useState(INITIAL_EVIDENCE)
  const [evidenceFocusToken, setEvidenceFocusToken] = useState(0)
  const [isDocumentsOpen, setIsDocumentsOpen] = useState(false)
  const [isEvidenceOpen, setIsEvidenceOpen] = useState(false)

  const messageSequence = useRef(0)
  const documentsRequestRef = useRef(0)
  const messagesRequestRef = useRef(0)
  const titleRequestRef = useRef(0)
  const sendRequestRef = useRef(0)
  // Conversación cuyo historial ya está en pantalla. Tras crear una
  // conversación se marca su id para no recargar los mensajes que el backend
  // acaba de guardar y que ya se muestran.
  const loadedConversationIdRef = useRef(undefined)
  // Distingue la selección inicial (primer documento por defecto) de una
  // selección vacía elegida por el usuario: si ya ha tocado el panel, no se
  // vuelve a marcar nada automáticamente.
  const hasUserChosenSelection = useRef(false)

  const loadDocuments = async () => {
    const requestId = ++documentsRequestRef.current
    setIsDocumentsLoading(true)
    setDocumentsError('')

    if (!currentUser?.id) {
      setDocuments([])
      setIsDocumentsLoading(false)
      return
    }

    try {
      const nextDocuments = await documentsService.list(currentUser.id)

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

  const loadConversationTitle = async (id) => {
    const requestId = ++titleRequestRef.current

    if (!id) {
      setConversationTitle('')
      return
    }

    try {
      const conversation = await conversationsService.getById(id)
      const title = conversation?.titulo ?? ''

      if (requestId === titleRequestRef.current) {
        setConversationTitle(title)
        onConversationTitleChange(id, title)
      }
    } catch {
      // El título es contexto, no bloquea el chat: se mantiene «Chat».
    }
  }

  const loadConversationMessages = async () => {
    const requestId = ++messagesRequestRef.current
    setMessages([])
    setActiveEvidence(INITIAL_EVIDENCE)
    setMessagesError('')

    if (!conversationId) {
      setIsMessagesLoading(false)
      return
    }

    setIsMessagesLoading(true)

    try {
      const conversationMessages =
        await conversationsService.getMessages(conversationId)

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
    return () => {
      // Una respuesta que llegue después de salir del chat no debe cambiar la
      // conversación activa ni poblar otra vista.
      sendRequestRef.current += 1
    }
  }, [])

  useEffect(() => {
    void loadDocuments()
  }, [currentUser?.id])

  useEffect(() => {
    void loadConversationTitle(conversationId)
  }, [conversationId])

  useEffect(() => {
    if (loadedConversationIdRef.current === conversationId) {
      return
    }

    loadedConversationIdRef.current = conversationId
    void loadConversationMessages()
  }, [conversationId])

  useEffect(() => {
    if (isDocumentsLoading) return

    setSelectedDocumentIds((current) => {
      const validIds = current.filter((id) =>
        documents.some((document) => document.id === id),
      )

      if (validIds.length > 0) return validIds
      if (documents.length === 0 || hasUserChosenSelection.current) return []

      return [documents[0].id]
    })
  }, [documents, isDocumentsLoading])

  useEffect(() => {
    // Al cambiar de usuario la selección vuelve a su valor por defecto.
    hasUserChosenSelection.current = false
  }, [currentUser?.id])

  useEffect(() => {
    onSelectedDocumentsChange(selectedDocumentIds)
  }, [selectedDocumentIds, onSelectedDocumentsChange])

  const selectedDocuments = documents.filter((document) =>
    selectedDocumentIds.includes(document.id),
  )

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

  const handleToggleDocument = (document) => {
    if (!document?.id) return

    hasUserChosenSelection.current = true

    setSelectedDocumentIds((current) => {
      const isSelected = current.includes(document.id)

      // Se permite quedarse sin documentos: el chat bloquea la pregunta hasta
      // que se seleccione al menos uno y, sin filtro, el backend busca en todos
      // los documentos del usuario.
      return isSelected
        ? current.filter((id) => id !== document.id)
        : [...current, document.id]
    })
  }

  const handleSourceClick = (messageId, sourceId) => {
    setActiveEvidence({ messageId, sourceId })
    setEvidenceFocusToken((token) => token + 1)
    setIsDocumentsOpen(false)
    setIsEvidenceOpen(true)
  }

  const handleOpenEvidenceFromChat = (source) => {
    if (source?.id) {
      onOpenEvidencePage(source)
    }
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

  const handleStartNewConversation = () => {
    // Se invalida cualquier respuesta en curso para que no vuelva a poblar el
    // chat que el usuario acaba de reiniciar.
    sendRequestRef.current += 1
    messagesRequestRef.current += 1
    titleRequestRef.current += 1
    loadedConversationIdRef.current = null
    setMessages([])
    setMessagesError('')
    setIsMessagesLoading(false)
    setActiveEvidence(INITIAL_EVIDENCE)
    setConversationTitle('')
    setIsThinking(false)
    setSendError('')
    setIsDocumentsOpen(false)
    setIsEvidenceOpen(false)
    onStartNewConversation()
  }

  const createMessageId = (role) => {
    const id = `${role}-${Date.now()}-${messageSequence.current}`
    messageSequence.current += 1
    return id
  }

  const handleSend = async (question) => {
    const trimmedQuestion = question.trim()

    if (!trimmedQuestion || isThinking || selectedDocumentIds.length === 0) return

    const requestId = ++sendRequestRef.current

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
        documentIds: selectedDocumentIds,
        usuarioId: currentUser?.id,
      })

      if (requestId !== sendRequestRef.current) return

      const assistantMessage = result.message

      setMessages((currentMessages) => [...currentMessages, assistantMessage])
      setActiveEvidence({
        messageId: assistantMessage.id,
        sourceId: assistantMessage.sources[0]?.id ?? null,
      })

      if (!conversationId && result.conversationId) {
        const title = deriveConversationTitle(trimmedQuestion)

        loadedConversationIdRef.current = result.conversationId
        setConversationTitle(title)
        onConversationCreated(result.conversationId, title)
      }
    } catch {
      if (requestId === sendRequestRef.current) {
        setSendError('No se pudo obtener una respuesta. Inténtalo de nuevo.')
      }
    } finally {
      if (requestId === sendRequestRef.current) {
        setIsThinking(false)
      }
    }
  }

  return (
    <div className="chat-page">
      <aside
        className={`chat-page__sidebar chat-page__sidebar--documents${
          isDocumentsOpen ? ' chat-page__sidebar--open' : ''
        }`}
        id="chat-documents-panel"
        aria-label="Panel de selección de documentos"
      >
        <ChatDocumentsPanel
          documents={documents}
          error={documentsError}
          isLoading={isDocumentsLoading}
          onClose={() => setIsDocumentsOpen(false)}
          onRetry={loadDocuments}
          onStartNewConversation={handleStartNewConversation}
          onToggleDocument={handleToggleDocument}
          selectedDocumentIds={selectedDocumentIds}
        />
      </aside>

      <div className="chat-page__conversation">
        <ChatWindow
          activeEvidence={activeEvidence}
          conversationTitle={conversationTitle}
          error={messagesError}
          hasSelectedDocuments={selectedDocumentIds.length > 0}
          isDocumentsOpen={isDocumentsOpen}
          isEvidenceOpen={isEvidenceOpen}
          isLoading={isMessagesLoading}
          isThinking={isThinking}
          messages={messages}
          onGoToDocuments={onNavigateToDocuments}
          onGoToVoice={onNavigateToVoice}
          onOpenDocuments={handleOpenDocuments}
          onOpenEvidence={handleOpenEvidence}
          onRetry={loadConversationMessages}
          onSend={handleSend}
          onSourceClick={handleSourceClick}
          selectedDocuments={selectedDocuments}
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
          onViewMore={handleOpenEvidenceFromChat}
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
