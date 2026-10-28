import { useCallback, useState } from 'react'
import ProfileSelector from './components/profile/ProfileSelector.jsx'
import AppLayout from './layout/AppLayout.jsx'
import FloatingUserButton from './layout/FloatingUserButton.jsx'
import ChatPage from './pages/ChatPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import DocumentsPage from './pages/DocumentsPage.jsx'
import EvidencePage from './pages/EvidencePage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import LandingPage from './pages/LandingPage.jsx'
import VoicePage from './pages/VoicePage.jsx'
import { clearStoredUser, readStoredUser, saveStoredUser } from './utils/session.js'

function App() {
  const [currentUser, setCurrentUser] = useState(readStoredUser)
  const [activeView, setActiveView] = useState(() =>
    currentUser ? 'dashboard' : 'landing',
  )
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  // Conversación activa en caché: se conserva al navegar entre pestañas hasta
  // que el usuario crea una nueva desde el chat.
  const [selectedConversationId, setSelectedConversationId] = useState(null)
  const [selectedConversationTitle, setSelectedConversationTitle] = useState('')
  const [selectedDocumentId, setSelectedDocumentId] = useState(null)
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([])
  const [selectedEvidence, setSelectedEvidence] = useState(null)
  const [isProfileSelectorOpen, setIsProfileSelectorOpen] = useState(false)
  const [pendingView, setPendingView] = useState(null)

  const handleNavigate = (view, conversationId = null, documentId = null) => {
    if (view !== 'landing' && !currentUser) {
      setPendingView(view)
      setIsProfileSelectorOpen(true)
      return
    }

    setActiveView(view)

    // La conversación activa se conserva al navegar entre pestañas (Chat, Voz,
    // Historial…). Solo se cambia al abrir una conversación del Historial o al
    // iniciar una nueva desde el botón «Nueva conversación».
    if (conversationId) {
      setSelectedConversationId(conversationId)
    }

    // «Preguntar» desde un documento abre un chat nuevo enfocado en ese archivo.
    if (view === 'chat' && !conversationId && documentId) {
      setSelectedConversationId(null)
      setSelectedConversationTitle('')
      setSelectedEvidence(null)
    }

    setSelectedDocumentId(documentId)

    // Al cambiar de conversación, la evidencia anterior deja de estar
    // seleccionada: Evidencia debe mostrar su aviso, no una fuente de una
    // conversación que ya no está abierta.
    if (
      conversationId &&
      selectedEvidence &&
      conversationId !== selectedEvidence.conversationId
    ) {
      setSelectedEvidence(null)
    }

    if (view === 'chat' && documentId) {
      setSelectedDocumentIds([documentId])
    }
  }

  const handleStart = () => {
    if (currentUser) {
      handleNavigate('dashboard')
      return
    }

    setPendingView('dashboard')
    setIsProfileSelectorOpen(true)
  }

  const handleSelectProfile = (user) => {
    setCurrentUser(user)
    saveStoredUser(user)
    setIsProfileSelectorOpen(false)
    setActiveView(pendingView ?? 'dashboard')
    setPendingView(null)
    setSelectedConversationId(null)
    setSelectedConversationTitle('')
    setSelectedDocumentId(null)
    setSelectedDocumentIds([])
    setSelectedEvidence(null)
  }

  const handleCloseProfileSelector = () => {
    setIsProfileSelectorOpen(false)
    setPendingView(null)
  }

  const handleOpenProfileSelector = () => {
    setPendingView('dashboard')
    setIsProfileSelectorOpen(true)
  }

  const handleLogout = () => {
    clearStoredUser()
    setCurrentUser(null)
    setIsProfileSelectorOpen(false)
    setPendingView(null)
    setSelectedConversationId(null)
    setSelectedConversationTitle('')
    setSelectedDocumentId(null)
    setSelectedDocumentIds([])
    setSelectedEvidence(null)
    setActiveView('landing')
  }

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed((isCollapsed) => !isCollapsed)
  }

  const handleSelectedDocumentsChange = useCallback((documentIds) => {
    setSelectedDocumentIds(documentIds)
    setSelectedDocumentId(documentIds[0] ?? null)
  }, [])

  const handleOpenConversation = (
    conversationId,
    documentId = null,
    conversationTitle = '',
  ) => {
    handleNavigate('chat', conversationId, documentId)
    setSelectedConversationTitle(conversationTitle ?? '')
  }

  const handleOpenEvidence = useCallback((evidence) => {
    if (!evidence) return

    setSelectedEvidence(evidence)
    setActiveView('evidence')
  }, [])

  const handleConversationCreated = useCallback(
    (conversationId, conversationTitle = '') => {
      setSelectedConversationId(conversationId)
      setSelectedConversationTitle(conversationTitle ?? '')
    },
    [],
  )

  const handleConversationTitleChange = (conversationId, conversationTitle) => {
    if (conversationId === selectedConversationId) {
      setSelectedConversationTitle(conversationTitle ?? '')
    }
  }

  const handleNewConversation = () => {
    setSelectedConversationId(null)
    setSelectedConversationTitle('')
    setSelectedEvidence(null)
    setActiveView('chat')
  }

  const handleBackToChat = (conversationId = null) => {
    if (conversationId) {
      setSelectedConversationId(conversationId)
    }

    setActiveView('chat')
  }

  const handleOpenEvidenceDocument = (documentId) => {
    if (documentId) {
      setSelectedDocumentId(documentId)
    }

    setActiveView('documents')
  }

  const renderActivePage = () => {
    switch (activeView) {
      case 'dashboard':
        return (
          <DashboardPage currentUser={currentUser} onNavigate={handleNavigate} />
        )
      case 'documents':
        return (
          <DocumentsPage
            currentUser={currentUser}
            onNavigate={handleNavigate}
            selectedDocumentId={selectedDocumentId}
          />
        )
      case 'chat':
        return (
          <ChatPage
            conversationId={selectedConversationId}
            currentUser={currentUser}
            onConversationCreated={handleConversationCreated}
            onConversationTitleChange={handleConversationTitleChange}
            onNavigateToDocuments={() => handleNavigate('documents')}
            onNavigateToVoice={() => handleNavigate('voice')}
            onOpenEvidencePage={handleOpenEvidence}
            onSelectedDocumentsChange={handleSelectedDocumentsChange}
            onStartNewConversation={handleNewConversation}
            selectedDocumentIds={selectedDocumentIds}
          />
        )
      case 'history':
        return (
          <HistoryPage
            currentUser={currentUser}
            onOpenConversation={handleOpenConversation}
          />
        )
      case 'voice':
        return <VoicePage onOpenEvidencePage={handleOpenEvidence} />
      case 'evidence':
        return (
          <EvidencePage
            onBackToChat={handleBackToChat}
            onOpenDocument={handleOpenEvidenceDocument}
            selectedEvidence={selectedEvidence}
          />
        )
      default:
        return (
          <DashboardPage currentUser={currentUser} onNavigate={handleNavigate} />
        )
    }
  }

  return (
    <>
      {activeView === 'landing' ? (
        <LandingPage onNavigate={handleNavigate} onStart={handleStart} />
      ) : (
        <AppLayout
          activeView={activeView}
          conversationTitle={
            selectedConversationId ? selectedConversationTitle : ''
          }
          isSidebarCollapsed={isSidebarCollapsed}
          onNavigate={handleNavigate}
          onToggleSidebar={handleToggleSidebar}
        >
          {renderActivePage()}
        </AppLayout>
      )}

      <FloatingUserButton
        onLogout={handleLogout}
        onOpenProfileSelector={handleOpenProfileSelector}
        user={currentUser}
      />

      {isProfileSelectorOpen && (
        <ProfileSelector
          onClose={handleCloseProfileSelector}
          onSelect={handleSelectProfile}
        />
      )}
    </>
  )
}

export default App
