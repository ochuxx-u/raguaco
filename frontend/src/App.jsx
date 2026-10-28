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
  const [selectedConversationId, setSelectedConversationId] = useState(null)
  const [selectedDocumentId, setSelectedDocumentId] = useState(null)
  const [selectedEvidenceId, setSelectedEvidenceId] = useState(null)
  const [isProfileSelectorOpen, setIsProfileSelectorOpen] = useState(false)
  const [pendingView, setPendingView] = useState(null)

  const handleNavigate = (view, conversationId = null, documentId = null) => {
    if (view !== 'landing' && !currentUser) {
      setPendingView(view)
      setIsProfileSelectorOpen(true)
      return
    }

    setActiveView(view)
    setSelectedConversationId(conversationId)
    setSelectedDocumentId(documentId)
  }

  const handleStart = () => {
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
    setSelectedDocumentId(null)
    setSelectedEvidenceId(null)
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
    setSelectedDocumentId(null)
    setSelectedEvidenceId(null)
    setActiveView('landing')
  }

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed((isCollapsed) => !isCollapsed)
  }

  const handleSelectedDocumentChange = useCallback((documentId) => {
    setSelectedDocumentId(documentId)
  }, [])

  const handleOpenConversation = (conversationId, documentId = null) => {
    handleNavigate('chat', conversationId, documentId)
  }

  const handleOpenEvidence = useCallback((evidenceId) => {
    setSelectedEvidenceId(evidenceId)
    setActiveView('evidence')
  }, [])

  const handleBackToChat = () => {
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
        return <DashboardPage onNavigate={handleNavigate} />
      case 'documents':
        return (
          <DocumentsPage
            onNavigate={handleNavigate}
            selectedDocumentId={selectedDocumentId}
          />
        )
      case 'chat':
        return (
          <ChatPage
            conversationId={selectedConversationId}
            onOpenEvidencePage={handleOpenEvidence}
            onSelectedDocumentChange={handleSelectedDocumentChange}
            selectedDocumentId={selectedDocumentId}
          />
        )
      case 'history':
        return <HistoryPage onOpenConversation={handleOpenConversation} />
      case 'voice':
        return <VoicePage onOpenEvidencePage={handleOpenEvidence} />
      case 'evidence':
        return (
          <EvidencePage
            onBackToChat={handleBackToChat}
            onOpenDocument={handleOpenEvidenceDocument}
            selectedEvidenceId={selectedEvidenceId}
          />
        )
      default:
        return <DashboardPage onNavigate={handleNavigate} />
    }
  }

  return (
    <>
      {activeView === 'landing' ? (
        <LandingPage onNavigate={handleNavigate} onStart={handleStart} />
      ) : (
        <AppLayout
          activeView={activeView}
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
