import { useEffect, useRef, useState } from 'react'
import './FloatingUserButton.css'

const mockUser = {
  name: 'Ana Torres',
  email: 'ana.torres@raguaco.ai',
  initials: 'AT',
}

function FloatingUserButton() {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef(null)
  const buttonRef = useRef(null)

  useEffect(() => {
    if (!isOpen) {
      return undefined
    }

    const handlePointerDown = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
        buttonRef.current?.focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  const closeMenu = () => setIsOpen(false)
  const menuLabel = isOpen ? 'Cerrar menú de usuario' : 'Abrir menú de usuario'

  return (
    <div className="floating-user" ref={containerRef}>
      {isOpen && (
        <div
          className="floating-user__menu"
          id="floating-user-menu"
          role="group"
          aria-label="Menú de usuario"
        >
          <div className="floating-user__header">
            <span className="floating-user__avatar" aria-hidden="true">
              {mockUser.initials}
            </span>
            <div className="floating-user__identity">
              <p className="floating-user__name">{mockUser.name}</p>
              <p className="floating-user__email">{mockUser.email}</p>
            </div>
          </div>

          <div className="floating-user__actions">
            <button
              className="floating-user__action"
              type="button"
              onClick={closeMenu}
            >
              Mi perfil
            </button>
            <button
              className="floating-user__action"
              type="button"
              onClick={closeMenu}
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      )}

      <button
        className="floating-user__button"
        ref={buttonRef}
        type="button"
        aria-label={menuLabel}
        title={menuLabel}
        aria-expanded={isOpen}
        aria-controls="floating-user-menu"
        onClick={() => setIsOpen((open) => !open)}
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
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21a8 8 0 0 1 16 0" />
        </svg>
      </button>
    </div>
  )
}

export default FloatingUserButton
