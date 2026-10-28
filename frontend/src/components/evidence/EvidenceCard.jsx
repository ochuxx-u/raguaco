import { useState } from 'react'
import './EvidenceCard.css'

function EvidenceCard({ source, isActive, onViewMore }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const hasExternalAction = typeof onViewMore === 'function'

  const handleToggle = () => {
    if (hasExternalAction) {
      onViewMore(source)
      return
    }

    setIsExpanded((expanded) => !expanded)
  }

  return (
    <article className={`evidence-card${isActive ? ' evidence-card--active' : ''}`}>
      <p className="evidence-card__header">
        {source.documento}
        {source.pagina != null ? ` · pág. ${source.pagina}` : ''}
      </p>

      <p
        className={`evidence-card__fragment${
          isExpanded ? ' evidence-card__fragment--expanded' : ''
        }`}
      >
        {source.fragmento}
      </p>

      <button
        className="evidence-card__toggle"
        type="button"
        aria-expanded={hasExternalAction ? undefined : isExpanded}
        onClick={handleToggle}
      >
        {hasExternalAction ? 'Ver más' : isExpanded ? 'Ver menos' : 'Ver más'}
      </button>
    </article>
  )
}

export default EvidenceCard
