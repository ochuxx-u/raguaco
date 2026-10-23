import { useState } from 'react'
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

  const handleNavigate = (view, conversationId = null) => {
    setActiveView(view)
    setSelectedConversationId(conversationId)
  }

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed((isCollapsed) => !isCollapsed)
  }

  const renderActivePage = () => {
    switch (activeView) {
      case 'dashboard':
        return <DashboardPage onNavigate={handleNavigate} />
      case 'documents':
        return <DocumentsPage onNavigate={handleNavigate} />
      case 'chat':
        return <ChatPage conversationId={selectedConversationId} />
      case 'history':
        return <HistoryPage />
      case 'voice':
        return <VoicePage />
      case 'evidence':
        return <EvidencePage />
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
