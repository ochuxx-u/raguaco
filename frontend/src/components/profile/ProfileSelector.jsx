import { useEffect, useRef, useState } from 'react'
import usersService from '../../services/usersService.js'
import './ProfileSelector.css'

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

function ProfileSelector({ onSelect = () => {}, onClose = () => {} }) {
  const [users, setUsers] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const dialogRef = useRef(null)
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  const loadUsers = async () => {
    setIsLoading(true)
    setError('')

    try {
      const data = await usersService.list()
      setUsers(Array.isArray(data) ? data : [])
    } catch {
      setUsers([])
      setError('No se pudieron cargar los perfiles.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadUsers()
  }, [])

  // Diálogo modal: foco inicial, cierre con Escape y foco atrapado dentro.
  useEffect(() => {
    const dialog = dialogRef.current

    if (!dialog) {
      return undefined
    }

    const previouslyFocused = document.activeElement
    dialog.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onCloseRef.current()
        return
      }

      if (event.key !== 'Tab') {
        return
      }

      const focusableElements = Array.from(
        dialog.querySelectorAll(
          'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      )

      if (focusableElements.length === 0) {
        event.preventDefault()
        return
      }

      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]

      if (
        event.shiftKey &&
        (document.activeElement === firstElement || document.activeElement === dialog)
      ) {
        event.preventDefault()
        lastElement.focus()
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault()
        firstElement.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)

      if (previouslyFocused instanceof HTMLElement) {
        previouslyFocused.focus()
      }
    }
  }, [])

  // Evita el scroll del fondo mientras el diálogo está abierto.
  useEffect(() => {
    const { overflow } = document.body.style
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.overflow = overflow
    }
  }, [])

  const handleOverlayMouseDown = (event) => {
    if (event.target === event.currentTarget) {
      onClose()
    }
  }

  return (
    <div
      className="profile-selector"
      role="presentation"
      onMouseDown={handleOverlayMouseDown}
    >
      <section
        className="profile-selector__dialog"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="profile-selector-title"
        aria-describedby="profile-selector-description"
        tabIndex={-1}
      >
        <header className="profile-selector__header">
          <div className="profile-selector__heading">
            <h2 className="profile-selector__title" id="profile-selector-title">
              Elegir perfil
            </h2>
            <p className="profile-selector__subtitle" id="profile-selector-description">
              Selecciona el perfil con el que quieres entrar.
            </p>
          </div>

          <button
            className="profile-selector__close"
            type="button"
            aria-label="Cerrar selección de perfil"
            title="Cerrar selección de perfil"
            onClick={onClose}
          >
            <svg
              viewBox="0 0 24 24"
              width="16"
              height="16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
            >
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </header>

        <div className="profile-selector__body">
          {isLoading && (
            <div className="profile-selector__state" role="status">
              <span className="profile-selector__spinner" aria-hidden="true" />
              <p>Cargando perfiles…</p>
            </div>
          )}

          {!isLoading && error && (
            <div className="profile-selector__state profile-selector__state--error" role="alert">
              <p>{error}</p>
              <button
                className="profile-selector__retry"
                type="button"
                onClick={loadUsers}
              >
                Reintentar
              </button>
            </div>
          )}

          {!isLoading && !error && users.length === 0 && (
            <div className="profile-selector__state">
              <p>No hay perfiles creados todavía.</p>
            </div>
          )}

          {!isLoading && !error && users.length > 0 && (
            <ul className="profile-selector__list">
              {users.map((user, index) => (
                <li key={user.id}>
                  <button
                    className="profile-selector__row"
                    type="button"
                    style={{ '--profile-index': index }}
                    onClick={() => onSelect(user)}
                  >
                    <span className="profile-selector__avatar" aria-hidden="true">
                      {getInitials(user.nombre)}
                    </span>

                    <span className="profile-selector__identity">
                      <span className="profile-selector__name">{user.nombre}</span>
                      <span className="profile-selector__email">{user.email}</span>
                    </span>

                    <svg
                      className="profile-selector__chevron"
                      viewBox="0 0 24 24"
                      width="18"
                      height="18"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      aria-hidden="true"
                    >
                      <path d="m9 6 6 6-6 6" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  )
}

export default ProfileSelector
