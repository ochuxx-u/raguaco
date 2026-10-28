import './Sidebar.css'

const navigationItems = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    id: 'documents',
    label: 'Documentos',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
        <path d="M14 3v5h5" />
        <path d="M9 13h6M9 17h4" />
      </svg>
    ),
  },
  {
    id: 'chat',
    label: 'Chat',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <path d="M21 12a8.5 8.5 0 0 1-8.5 8.5 9 9 0 0 1-4-.9L3 21l1.4-4.6A8.5 8.5 0 1 1 21 12z" />
        <path d="M8 11h8M8 15h5" />
      </svg>
    ),
  },
  {
    id: 'history',
    label: 'Historial',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <path d="M3 12a9 9 0 1 0 2.6-6.4L3 8" />
        <path d="M3 3v5h5" />
        <path d="M12 7v5l3 2" />
      </svg>
    ),
  },
  {
    id: 'voice',
    label: 'Voz',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <rect x="9" y="3" width="6" height="11" rx="3" />
        <path d="M5 11a7 7 0 0 0 14 0" />
        <path d="M12 18v3M9 21h6" />
      </svg>
    ),
  },
  {
    id: 'evidence',
    label: 'Evidencia',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <path d="M12 6.5C10.7 5.3 8.8 4.8 6.5 4.8H3v12.7h3.5c2.3 0 4.2.5 5.5 1.7 1.3-1.2 3.2-1.7 5.5-1.7H21V4.8h-3.5c-2.3 0-4.2.5-5.5 1.7z" />
        <path d="M12 6.5v12.7" />
      </svg>
    ),
  },
]

function Sidebar({ activeView, collapsed, overlayOpen, onNavigate, onToggle }) {
  const toggleLabel = collapsed ? 'Expandir menú lateral' : 'Colapsar menú lateral'

  return (
    <aside
      className={`sidebar${collapsed ? ' sidebar--collapsed' : ''}${
        overlayOpen ? ' sidebar--overlay-open' : ''
      }`}
      id="app-sidebar"
      aria-label="Navegación lateral"
    >
      <div className="sidebar__header">
        <button
          className="sidebar__brand"
          type="button"
          aria-label="RAGUACO AI — Ir a la página de inicio"
          title="Ir a la página de inicio"
          onClick={() => onNavigate('landing')}
        >
          <span className="sidebar__logo" aria-hidden="true" />
          <span className="sidebar__brand-text">
            RAGUACO <span className="sidebar__brand-accent">AI</span>
          </span>
        </button>
      </div>

      <nav className="sidebar__nav" aria-label="Navegación principal">
        <ul className="sidebar__nav-list">
          {navigationItems.map(({ id, label, icon }) => {
            const isActive = activeView === id

            return (
              <li key={id}>
                <button
                  className={`sidebar__nav-item${
                    isActive ? ' sidebar__nav-item--active' : ''
                  }`}
                  type="button"
                  aria-current={isActive ? 'page' : undefined}
                  aria-label={label}
                  title={collapsed ? label : undefined}
                  onClick={() => onNavigate(id)}
                >
                  <span className="sidebar__nav-icon" aria-hidden="true">
                    {icon}
                  </span>
                  <span className="sidebar__nav-label">{label}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="sidebar__footer">
        <button
          className="sidebar__toggle"
          type="button"
          aria-label={toggleLabel}
          title={toggleLabel}
          aria-controls="app-sidebar"
          aria-expanded={!collapsed}
          onClick={onToggle}
        >
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            aria-hidden="true"
          >
            <path d={collapsed ? 'M9 18l6-6-6-6' : 'M15 18l-6-6 6-6'} />
          </svg>
          <span className="sidebar__toggle-label">
            {collapsed ? 'Expandir menú' : 'Colapsar menú'}
          </span>
        </button>

      </div>
    </aside>
  )
}

export default Sidebar
