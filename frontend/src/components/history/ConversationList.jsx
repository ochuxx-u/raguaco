import ConversationItem from './ConversationItem.jsx'
import './ConversationList.css'

function ConversationList({
  conversations,
  emptyMessage,
  error,
  isLoading,
  onRetry,
  onSelect,
}) {
  return (
    <div className="conversation-list">
      {isLoading && (
        <div className="conversation-list__state" role="status">
          <span className="conversation-list__spinner" aria-hidden="true" />
          <p>Cargando conversaciones…</p>
        </div>
      )}

      {!isLoading && error && (
        <div className="conversation-list__state conversation-list__state--error" role="alert">
          <p>{error}</p>
          <button className="conversation-list__retry" type="button" onClick={onRetry}>
            Reintentar
          </button>
        </div>
      )}

      {!isLoading && !error && conversations.length === 0 && (
        <div className="conversation-list__state">
          <p>{emptyMessage}</p>
        </div>
      )}

      {!isLoading && !error && conversations.length > 0 && (
        <ul className="conversation-list__items" aria-label="Conversaciones">
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <ConversationItem conversation={conversation} onSelect={onSelect} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default ConversationList
