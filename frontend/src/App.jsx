import { useCallback, useState } from 'react'
import AppLayout from './layout/AppLayout.jsx'
import FloatingUserButton from './layout/FloatingUserButton.jsx'
import ChatPage from './pages/ChatPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import DocumentsPage from './pages/DocumentsPage.jsx'
import EvidencePage from './pages/EvidencePage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import LandingPage from './pages/LandingPage.jsx'
import VoicePage from './pages/VoicePage.jsx'

function App() {
  const [activeView, setActiveView] = useState('landing')
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [selectedConversationId, setSelectedConversationId] = useState(null)
  const [selectedDocumentId, setSelectedDocumentId] = useState(null)
  const [selectedEvidenceId, setSelectedEvidenceId] = useState(null)

  const handleNavigate = (view, conversationId = null, documentId = null) => {
    setActiveView(view)
    setSelectedConversationId(conversationId)
    setSelectedDocumentId(documentId)
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
        return <VoicePage />
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
        <LandingPage onNavigate={handleNavigate} />
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

      <FloatingUserButton />
    </>
  )
}

export default App
