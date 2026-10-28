import { useEffect, useRef, useState } from 'react'
import './ChatInput.css'

const MAX_TEXTAREA_HEIGHT = 132

// Máximo de caracteres de una consulta (RF5). Debe coincidir con
// `MAX_LONGITUD_CONSULTA` en `App/domain/models/mensaje.py` y con el
// `max_length` de `PublicarMensajePeticion` en `App/api/routes/queries.py`.
const MAX_MESSAGE_LENGTH = 512

// A partir de cuántos caracteres restantes se muestra el contador.
const COUNTER_REMAINING_THRESHOLD = 100

function ChatInput({
  disabled = false,
  isSending = false,
  onGoToDocuments = () => {},
  onSend,
}) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)
  const canSend = value.trim().length > 0 && !disabled && !isSending
  const remaining = MAX_MESSAGE_LENGTH - value.length
  const showCounter = remaining <= COUNTER_REMAINING_THRESHOLD
  const isAtLimit = remaining <= 0

  useEffect(() => {
    const textarea = textareaRef.current

    if (!textarea) return

    textarea.style.height = 'auto'
    const nextHeight = Math.min(textarea.scrollHeight, MAX_TEXTAREA_HEIGHT)
    textarea.style.height = `${nextHeight}px`
    textarea.style.overflowY =
      textarea.scrollHeight > MAX_TEXTAREA_HEIGHT ? 'auto' : 'hidden'
  }, [value])

  const submitQuestion = () => {
    if (!canSend) return

    const question = value.trim()
    setValue('')
    onSend(question)
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submitQuestion()
    }
  }

  return (
    <div className="chat-input">
      <button
        className="chat-input__icon-button"
        type="button"
        aria-label="Ir a Documentos para subir un archivo"
        title="Subir documento desde Documentos"
        onClick={onGoToDocuments}
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
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>

      <textarea
        className="chat-input__field"
        ref={textareaRef}
        rows="1"
        value={value}
        maxLength={MAX_MESSAGE_LENGTH}
        placeholder="Pregunta algo sobre tus documentos…"
        aria-label="Escribe tu pregunta"
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
      />

      <button
        className="chat-input__icon-button chat-input__voice"
        type="button"
        aria-label="Hablar con RAGUACO"
        title="Hablar con RAGUACO"
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
          <rect x="9" y="3" width="6" height="11" rx="3" />
          <path d="M5 11a7 7 0 0 0 14 0" />
          <path d="M12 18v3M9 21h6" />
        </svg>
      </button>

      <button
        className="chat-input__send"
        type="button"
        aria-label="Enviar pregunta"
        title="Enviar pregunta"
        disabled={!canSend}
        onClick={submitQuestion}
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
          <path d="M22 2 11 13" />
          <path d="m22 2-7 20-4-9-9-4z" />
        </svg>
      </button>

      {showCounter && (
        <span
          className={
            isAtLimit
              ? 'chat-input__counter chat-input__counter--limit'
              : 'chat-input__counter'
          }
        >
          {value.length}/{MAX_MESSAGE_LENGTH}
        </span>
      )}
    </div>
  )
}

export default ChatInput
