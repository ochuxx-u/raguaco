import { useEffect, useRef } from 'react'
import EvidenceCard from './EvidenceCard.jsx'
import './EvidencePanel.css'

function EvidencePanel({ activeSourceId, focusToken = 0, onClose, onViewMore, sources = [] }) {
  const activeCardRef = useRef(null)

  useEffect(() => {
    if (!focusToken) return

    const activeCard = activeCardRef.current

    if (!activeCard) return

    activeCard.focus({ preventScroll: true })
    activeCard.scrollIntoView({ block: 'nearest' })
  }, [activeSourceId, focusToken])

  return (
    <section className="evidence-panel" aria-labelledby="evidence-panel-title">
      <header className="evidence-panel__header">
        <h2 className="evidence-panel__title" id="evidence-panel-title">
          Fuentes
        </h2>

        {onClose && (
          <button
            className="evidence-panel__close"
            type="button"
            aria-label="Cerrar panel de fuentes y evidencia"
            title="Cerrar panel de fuentes y evidencia"
            onClick={onClose}
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
            >
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        )}
      </header>

      <div className="evidence-panel__content">
        {sources.length === 0 ? (
          <p className="evidence-panel__empty">
            Aún no hay fuentes para esta respuesta.
          </p>
        ) : (
          sources.map((source) => {
            const isActive = source.id === activeSourceId

            return (
              <div
                className={`evidence-panel__item${
                  isActive ? ' evidence-panel__item--active' : ''
                }`}
                key={source.id}
                ref={isActive ? activeCardRef : null}
                tabIndex={-1}
              >
                <EvidenceCard
                  source={source}
                  isActive={isActive}
                  onViewMore={onViewMore}
                />
              </div>
            )
          })
        )}
      </div>
    </section>
  )
}

export default EvidencePanel
