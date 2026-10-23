import { useEffect, useRef, useState } from 'react'
import './ChatInput.css'

const MAX_TEXTAREA_HEIGHT = 132

function ChatInput({
  disabled = false,
  isAttaching = false,
  isSending = false,
  onAttachFile,
  onSend,
}) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)
  const canSend = value.trim().length > 0 && !disabled && !isSending
  const attachLabel = isAttaching ? 'Adjuntando documento' : 'Adjuntar documento'

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

  const handleFileChange = (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''

    if (file) {
      void onAttachFile(file)
    }
  }

  return (
    <div className="chat-input">
      <button
        className="chat-input__icon-button"
        type="button"
        aria-label={attachLabel}
        title={attachLabel}
        disabled={isAttaching}
        onClick={() => fileInputRef.current?.click()}
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

      <input
        className="chat-input__file"
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={handleFileChange}
      />

      <textarea
        className="chat-input__field"
        ref={textareaRef}
        rows="1"
        value={value}
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
    </div>
  )
}

export default ChatInput
