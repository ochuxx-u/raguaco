import { useEffect, useState } from 'react'
import Sidebar from './Sidebar.jsx'
import './AppLayout.css'

function getViewport() {
  if (typeof window === 'undefined') {
    return 'desktop'
  }

  if (window.matchMedia('(max-width: 767px)').matches) {
    return 'mobile'
  }

  if (window.matchMedia('(max-width: 1023px)').matches) {
    return 'tablet'
  }

  return 'desktop'
}

function AppLayout({
  activeView,
  children,
  isSidebarCollapsed,
  onNavigate,
  onToggleSidebar,
}) {
  const [viewport, setViewport] = useState(getViewport)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  const isDesktop = viewport === 'desktop'
  const isOverlayMode = !isDesktop
  const isOverlayOpen = isOverlayMode && isSidebarOpen

  const isSidebarCollapsedForViewport = isDesktop
    ? isSidebarCollapsed
    : viewport === 'tablet'
      ? !isSidebarOpen
      : false

  useEffect(() => {
    const mobileQuery = window.matchMedia('(max-width: 767px)')
    const tabletQuery = window.matchMedia('(max-width: 1023px)')
    const handleViewportChange = () => setViewport(getViewport())

    mobileQuery.addEventListener('change', handleViewportChange)
    tabletQuery.addEventListener('change', handleViewportChange)

    return () => {
      mobileQuery.removeEventListener('change', handleViewportChange)
      tabletQuery.removeEventListener('change', handleViewportChange)
    }
  }, [])

  useEffect(() => {
    if (isDesktop) {
      setIsSidebarOpen(false)
    }
  }, [isDesktop])

  useEffect(() => {
    if (!isOverlayOpen) {
      return undefined
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsSidebarOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOverlayOpen])

  const handleToggleSidebar = () => {
    if (isDesktop) {
      onToggleSidebar()
      return
    }

    setIsSidebarOpen((isOpen) => !isOpen)
  }

  const handleNavigateFromSidebar = (view, conversationId = null) => {
    onNavigate(view, conversationId)
    setIsSidebarOpen(false)
  }

  const closeSidebar = () => setIsSidebarOpen(false)
  const menuLabel = isSidebarOpen ? 'Cerrar menú lateral' : 'Abrir menú lateral'

  return (
    <div className="app-layout">
      <Sidebar
        activeView={activeView}
        collapsed={isSidebarCollapsedForViewport}
        overlayOpen={isOverlayOpen}
        onNavigate={handleNavigateFromSidebar}
        onToggle={handleToggleSidebar}
      />

      {isOverlayOpen && (
        <button
          className="app-layout__backdrop"
          type="button"
          aria-label="Cerrar menú lateral"
          onClick={closeSidebar}
        />
      )}

      <div className="app-layout__main" inert={isOverlayOpen || undefined}>
        <header className="app-layout__mobile-bar">
          <button
            className="app-layout__menu-button"
            type="button"
            aria-label={menuLabel}
            title={menuLabel}
            aria-controls="app-sidebar"
            aria-expanded={isSidebarOpen}
            onClick={() => setIsSidebarOpen((isOpen) => !isOpen)}
          >
            <svg
              viewBox="0 0 24 24"
              width="20"
              height="20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
            >
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <span className="app-layout__mobile-brand">
            <span className="app-layout__mobile-logo" aria-hidden="true" />
            RAGUACO <span className="app-layout__mobile-accent">AI</span>
          </span>
        </header>

        <div className="app-layout__content" id="main-content">
          {children}
        </div>
      </div>
    </div>
  )
}

export default AppLayout
