import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble.jsx'
import './MessageList.css'

function MessageList({
  activeEvidence,
  error,
  isLoading,
  isThinking,
  messages,
  onRetry,
  onSourceClick,
}) {
  const listRef = useRef(null)

  useEffect(() => {
    const list = listRef.current

    if (list) {
      list.scrollTop = list.scrollHeight
    }
  }, [messages, isThinking, isLoading, error])

  if (isLoading) {
    return (
      <div className="message-list__state" role="status">
        <span className="message-list__spinner" aria-hidden="true" />
        <p>Cargando conversación…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="message-list__state message-list__state--error" role="alert">
        <p>{error}</p>
        <button className="message-list__retry" type="button" onClick={onRetry}>
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div
      className="message-list"
      ref={listRef}
      role="log"
      aria-label="Conversación"
      aria-live="polite"
    >
      {messages.length === 0 && !isThinking && (
        <p className="message-list__empty">
          Pregunta algo sobre tus documentos para comenzar.
        </p>
      )}

      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          activeMessageId={activeEvidence.messageId}
          activeSourceId={activeEvidence.sourceId}
          onSourceClick={onSourceClick}
        />
      ))}

      {isThinking && (
        <div
          className="message-list__typing"
          role="status"
          aria-label="RAGUACO está pensando"
        >
          <span />
          <span />
          <span />
        </div>
      )}
    </div>
  )
}

export default MessageList
