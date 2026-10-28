import { useEffect, useRef, useState } from 'react'
import './FloatingUserButton.css'

// Iniciales del nombre: primera letra de las dos primeras palabras.
function getInitials(nombre) {
  const words = String(nombre ?? '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)

  if (words.length === 0) {
    return '?'
  }

  return words
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase()
}

function FloatingUserButton({
  user = null,
  onLogout = () => {},
  onOpenProfileSelector = () => {},
}) {
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

  // Al cerrar el menú desde una acción, el foco vuelve al botón flotante
  // (el botón de la acción desaparece y perdería el foco).
  const closeMenuAndFocus = () => {
    closeMenu()
    buttonRef.current?.focus()
  }

  const handleLogout = () => {
    closeMenuAndFocus()
    onLogout()
  }

  const handleOpenProfileSelector = () => {
    closeMenuAndFocus()
    onOpenProfileSelector()
  }

  const menuLabel = isOpen ? 'Cerrar menú de usuario' : 'Abrir menú de usuario'
  const initials = user ? getInitials(user.nombre) : '?'
  const displayName = user?.nombre || 'Invitado'
  const displayEmail = user?.email || 'Sin perfil seleccionado'

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
              {initials}
            </span>
            <div className="floating-user__identity">
              <p className="floating-user__name">{displayName}</p>
              <p className="floating-user__email">{displayEmail}</p>
            </div>
          </div>

          <div className="floating-user__actions">
            {user ? (
              <button
                className="floating-user__action"
                type="button"
                onClick={handleLogout}
              >
                Cerrar sesión
              </button>
            ) : (
              <button
                className="floating-user__action"
                type="button"
                onClick={handleOpenProfileSelector}
              >
                Elegir perfil
              </button>
            )}
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
        <span
          className={`floating-user__button-initials${
            user ? '' : ' floating-user__button-initials--guest'
          }`}
          aria-hidden="true"
        >
          {initials}
        </span>
      </button>
    </div>
  )
}

export default FloatingUserButton
