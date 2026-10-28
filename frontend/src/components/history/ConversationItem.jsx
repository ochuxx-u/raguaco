import './ConversationItem.css'

function ConversationItem({ conversation, onSelect }) {
  return (
    <button
      className="conversation-item"
      type="button"
      onClick={() => onSelect(conversation)}
    >
      <span className="conversation-item__dot" aria-hidden="true" />

      <span className="conversation-item__content">
        <span className="conversation-item__title" title={conversation.titulo}>
          {conversation.titulo}
        </span>
        <span className="conversation-item__excerpt">
          {conversation.ultimaPregunta}
        </span>
      </span>

      <span className="conversation-item__meta">
        {conversation.fecha ? `${conversation.fecha} · ` : ''}
        {conversation.mensajeCount}{' '}
        {conversation.mensajeCount === 1 ? 'mensaje' : 'mensajes'}
      </span>
    </button>
  )
}

export default ConversationItem
