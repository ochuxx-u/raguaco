import { useState } from 'react'
import './EvidenceCard.css'

function EvidenceCard({ source, isActive }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <article className={`evidence-card${isActive ? ' evidence-card--active' : ''}`}>
      <p className="evidence-card__header">
        {source.documento} · pág. {source.pagina}
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
        aria-expanded={isExpanded}
        onClick={() => setIsExpanded((expanded) => !expanded)}
      >
        {isExpanded ? 'Ver menos' : 'Ver más'}
      </button>
    </article>
  )
}

export default EvidenceCard
