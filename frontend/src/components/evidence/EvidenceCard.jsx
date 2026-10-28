import { useState } from 'react'
import './EvidenceCard.css'

function EvidenceCard({
  source,
  isActive,
  isViewMoreDisabled = false,
  onSelect,
  onViewMore,
}) {
  const [isExpanded, setIsExpanded] = useState(false)
  const hasExternalAction = typeof onViewMore === 'function'
  const hasSelectionAction = typeof onSelect === 'function'

  const handleToggle = () => {
    if (hasExternalAction) {
      onViewMore(source)
      return
    }

    setIsExpanded((expanded) => !expanded)
  }

  const content = (
    <>
      <span className="evidence-card__header">
        {source.documento}
        {source.pagina != null ? ` · pág. ${source.pagina}` : ''}
      </span>

      <span
        className={`evidence-card__fragment${
          isExpanded ? ' evidence-card__fragment--expanded' : ''
        }`}
      >
        {source.fragmento}
      </span>
    </>
  )

  return (
    <article
      className={`evidence-card${isActive ? ' evidence-card--active' : ''}${
        hasSelectionAction ? ' evidence-card--selectable' : ''
      }`}
    >
      {hasSelectionAction ? (
        <button
          className="evidence-card__select"
          type="button"
          aria-pressed={isActive}
          onClick={() => onSelect(source)}
        >
          {content}
        </button>
      ) : (
        <div className="evidence-card__select">{content}</div>
      )}

      <button
        className="evidence-card__toggle"
        type="button"
        aria-expanded={hasExternalAction ? undefined : isExpanded}
        disabled={isViewMoreDisabled}
        onClick={handleToggle}
      >
        {hasExternalAction ? 'Ver más' : isExpanded ? 'Ver menos' : 'Ver más'}
      </button>
    </article>
  )
}

export default EvidenceCard
