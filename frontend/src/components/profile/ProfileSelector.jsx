import { useEffect, useRef, useState } from 'react'
import usersService from '../../services/usersService.js'
import './ProfileSelector.css'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const EMAIL_MAX_LENGTH = 254
const NAME_MIN_LENGTH = 2
const NAME_MAX_LENGTH = 50

// El backend valida con EmailStr (email-validator): además del formato, rechaza
// los TLD reservados. Se replican aquí para dar el error antes de enviar; el 422
// del backend sigue siendo la red de seguridad.
const RESERVED_TLDS = new Set([
  'test',
  'invalid',
  'local',
  'localhost',
  'example',
  'internal',
  'onion',
])

const EMPTY_FIELD_ERRORS = { nombre: '', email: '' }

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

function validateName(nombre) {
  const trimmedName = nombre.trim()

  if (trimmedName.length < NAME_MIN_LENGTH || trimmedName.length > NAME_MAX_LENGTH) {
    return 'El nombre debe tener entre 2 y 50 caracteres.'
  }

  return ''
}

function validateEmail(email) {
  const trimmedEmail = email.trim()

  if (
    trimmedEmail.length === 0 ||
    trimmedEmail.length > EMAIL_MAX_LENGTH ||
    !EMAIL_PATTERN.test(trimmedEmail)
  ) {
    return 'Introduce un email válido.'
  }

  const domain = trimmedEmail.slice(trimmedEmail.lastIndexOf('@') + 1).toLowerCase()
  const tld = domain.slice(domain.lastIndexOf('.') + 1)

  if (RESERVED_TLDS.has(tld)) {
    return 'Introduce un email válido.'
  }

  return ''
}

function ProfileSelector({ onSelect = () => {}, onClose = () => {} }) {
  const [users, setUsers] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [view, setView] = useState('list')
  const [nombre, setNombre] = useState('')
  const [email, setEmail] = useState('')
  const [fieldErrors, setFieldErrors] = useState(EMPTY_FIELD_ERRORS)
  const [submitError, setSubmitError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [focusTarget, setFocusTarget] = useState(null)
  const dialogRef = useRef(null)
  const nameInputRef = useRef(null)
  const emailInputRef = useRef(null)
  const registerButtonRef = useRef(null)
  const onCloseRef = useRef(onClose)
  const isSubmittingRef = useRef(false)
  const previousViewRef = useRef(view)

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

        if (!isSubmittingRef.current) {
          onCloseRef.current()
        }

        return
      }

      if (event.key !== 'Tab') {
        return
      }

      const focusableElements = Array.from(
        dialog.querySelectorAll(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
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

  // Al cambiar de vista, el foco acompaña: nombre al registrar y botón de
  // registro al volver a la lista (el control anterior desaparece).
  useEffect(() => {
    if (previousViewRef.current === view) {
      return
    }

    previousViewRef.current = view

    if (view === 'register') {
      nameInputRef.current?.focus()
    } else {
      registerButtonRef.current?.focus()
    }
  }, [view])

  // Al enviar, el botón se deshabilita y el foco se quedaría en el vacío:
  // se mantiene en el diálogo mientras dura la petición.
  useEffect(() => {
    if (isSubmitting) {
      dialogRef.current?.focus()
    }
  }, [isSubmitting])

  // El foco a un campo con error se aplica después de que React rehabilite
  // los inputs (durante el envío están deshabilitados).
  useEffect(() => {
    if (isSubmitting || !focusTarget) {
      return
    }

    if (focusTarget === 'nombre') {
      nameInputRef.current?.focus()
    } else {
      emailInputRef.current?.focus()
    }

    setFocusTarget(null)
  }, [focusTarget, isSubmitting])

  const handleOverlayMouseDown = (event) => {
    if (event.target === event.currentTarget && !isSubmittingRef.current) {
      onClose()
    }
  }

  const openRegister = () => {
    setFieldErrors(EMPTY_FIELD_ERRORS)
    setSubmitError('')
    setView('register')
  }

  const backToList = () => {
    if (isSubmittingRef.current) {
      return
    }

    setNombre('')
    setEmail('')
    setFieldErrors(EMPTY_FIELD_ERRORS)
    setSubmitError('')
    setFocusTarget(null)
    setView('list')
  }

  const handleNameChange = (event) => {
    const value = event.target.value
    setNombre(value)

    if (fieldErrors.nombre) {
      setFieldErrors((current) => ({ ...current, nombre: validateName(value) }))
    }

    if (submitError) {
      setSubmitError('')
    }
  }

  const handleEmailChange = (event) => {
    const value = event.target.value
    setEmail(value)

    if (fieldErrors.email) {
      setFieldErrors((current) => ({ ...current, email: validateEmail(value) }))
    }

    if (submitError) {
      setSubmitError('')
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (isSubmittingRef.current) {
      return
    }

    const nextErrors = {
      nombre: validateName(nombre),
      email: validateEmail(email),
    }

    setFieldErrors(nextErrors)
    setSubmitError('')

    if (nextErrors.nombre) {
      setFocusTarget('nombre')
      return
    }

    if (nextErrors.email) {
      setFocusTarget('email')
      return
    }

    isSubmittingRef.current = true
    setIsSubmitting(true)

    try {
      const createdUser = await usersService.create({
        nombre: nombre.trim(),
        email: email.trim().toLowerCase(),
      })

      onSelect(createdUser)
    } catch (createError) {
      if (createError?.status === 409) {
        setFieldErrors((current) => ({
          ...current,
          email: 'Ese email ya está registrado.',
        }))
        setFocusTarget('email')
      } else if (createError?.status === 0) {
        setSubmitError('No se pudo conectar con el servidor.')
      } else if (createError?.status === 422) {
        setSubmitError('Revisa los datos del formulario.')
      } else {
        setSubmitError('No se pudo registrar el usuario. Inténtalo de nuevo.')
      }
    } finally {
      isSubmittingRef.current = false
      setIsSubmitting(false)
    }
  }

  const isRegistering = view === 'register'

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
              {isRegistering ? 'Registrar nuevo usuario' : 'Elegir perfil'}
            </h2>
            <p className="profile-selector__subtitle" id="profile-selector-description">
              {isRegistering
                ? 'Completa tus datos para crear un perfil.'
                : 'Selecciona el perfil con el que quieres entrar.'}
            </p>
          </div>

          <button
            className="profile-selector__close"
            type="button"
            aria-label="Cerrar selección de perfil"
            title="Cerrar selección de perfil"
            disabled={isSubmitting}
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

        {isRegistering ? (
          <form
            className="profile-selector__form"
            noValidate
            aria-busy={isSubmitting}
            onSubmit={handleSubmit}
          >
            <div className="profile-selector__body">
              <div className="profile-selector__fields">
                <div className="profile-selector__field">
                  <label className="profile-selector__label" htmlFor="profile-selector-name">
                    Nombre
                  </label>
                  <input
                    className={`profile-selector__input${
                      fieldErrors.nombre ? ' profile-selector__input--invalid' : ''
                    }`}
                    id="profile-selector-name"
                    ref={nameInputRef}
                    type="text"
                    value={nombre}
                    minLength={NAME_MIN_LENGTH}
                    maxLength={NAME_MAX_LENGTH}
                    placeholder="Tu nombre"
                    autoComplete="name"
                    required
                    disabled={isSubmitting}
                    aria-invalid={fieldErrors.nombre ? 'true' : undefined}
                    aria-describedby={
                      fieldErrors.nombre ? 'profile-selector-name-error' : undefined
                    }
                    onChange={handleNameChange}
                  />
                  {fieldErrors.nombre && (
                    <p
                      className="profile-selector__field-error"
                      id="profile-selector-name-error"
                      role="alert"
                    >
                      {fieldErrors.nombre}
                    </p>
                  )}
                </div>

                <div className="profile-selector__field">
                  <label className="profile-selector__label" htmlFor="profile-selector-email">
                    Email
                  </label>
                  <input
                    className={`profile-selector__input${
                      fieldErrors.email ? ' profile-selector__input--invalid' : ''
                    }`}
                    id="profile-selector-email"
                    ref={emailInputRef}
                    type="email"
                    value={email}
                    maxLength={EMAIL_MAX_LENGTH}
                    placeholder="nombre@dominio.com"
                    autoComplete="email"
                    required
                    disabled={isSubmitting}
                    aria-invalid={fieldErrors.email ? 'true' : undefined}
                    aria-describedby={
                      fieldErrors.email ? 'profile-selector-email-error' : undefined
                    }
                    onChange={handleEmailChange}
                  />
                  {fieldErrors.email && (
                    <p
                      className="profile-selector__field-error"
                      id="profile-selector-email-error"
                      role="alert"
                    >
                      {fieldErrors.email}
                    </p>
                  )}
                </div>
              </div>

              {submitError && (
                <p className="profile-selector__form-error" role="alert">
                  {submitError}
                </p>
              )}

              <p className="profile-selector__sr-only" role="status">
                {isSubmitting ? 'Registrando usuario…' : ''}
              </p>
            </div>

            <footer className="profile-selector__footer">
              <div className="profile-selector__form-actions">
                <button
                  className="profile-selector__back"
                  type="button"
                  disabled={isSubmitting}
                  onClick={backToList}
                >
                  Volver
                </button>
                <button
                  className="profile-selector__submit"
                  type="submit"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Registrando…' : 'Registrar usuario'}
                </button>
              </div>
            </footer>
          </form>
        ) : (
          <>
            <div className="profile-selector__body">
              {isLoading && (
                <div className="profile-selector__state" role="status">
                  <span className="profile-selector__spinner" aria-hidden="true" />
                  <p>Cargando perfiles…</p>
                </div>
              )}

              {!isLoading && error && (
                <div
                  className="profile-selector__state profile-selector__state--error"
                  role="alert"
                >
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

            <footer className="profile-selector__footer">
              <button
                className="profile-selector__register"
                ref={registerButtonRef}
                type="button"
                onClick={openRegister}
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
                  <path d="M12 5v14M5 12h14" />
                </svg>
                Registrar nuevo usuario
              </button>
            </footer>
          </>
        )}
      </section>
    </div>
  )
}

export default ProfileSelector
