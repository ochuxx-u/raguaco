import NoEvidenceNotice from './NoEvidenceNotice.jsx'
import SourceChip from './SourceChip.jsx'
import './MessageBubble.css'

function MessageBubble({ message, activeMessageId, activeSourceId, onSourceClick }) {
  if (message.role === 'user') {
    return (
      <div className="message-bubble message-bubble--user">
        <p>{message.content}</p>
      </div>
    )
  }

  const hasSources = message.sources?.length > 0

  return (
    <article className="message-bubble message-bubble--assistant">
      {message.hasEvidence === false ? (
        <NoEvidenceNotice />
      ) : (
        <p className="message-bubble__content">{message.content}</p>
      )}

      {hasSources && (
        <div className="message-bubble__sources" aria-label="Fuentes de la respuesta">
          {message.sources.map((source, index) => (
            <SourceChip
              key={source.id}
              source={source}
              index={index}
              isActive={activeMessageId === message.id && activeSourceId === source.id}
              onClick={() => onSourceClick(message.id, source.id)}
            />
          ))}
        </div>
      )}
    </article>
  )
}

export default MessageBubble
