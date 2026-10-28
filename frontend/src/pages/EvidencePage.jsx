import EvidenceViewer from '../components/evidence/EvidenceViewer.jsx'
import './EvidencePage.css'

function EvidencePage({
  onBackToChat = () => {},
  onOpenDocument = () => {},
  selectedEvidence = null,
}) {
  return (
    <section className="evidence-page" aria-labelledby="evidence-title">
      <header className="evidence-page__header">
        <h1 className="evidence-page__title" id="evidence-title">
          Evidencia
        </h1>
        <p className="evidence-page__intro">
          Consulta la fuente y el fragmento que respaldan una respuesta del asistente.
        </p>
      </header>

      <div className="evidence-page__content">
        {!selectedEvidence && (
          <div className="evidence-page__notice" role="status">
            <svg
              viewBox="0 0 24 24"
              width="20"
              height="20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M12 11v5" />
              <path d="M12 8h.01" />
            </svg>
            <p>
              Selecciona los detalles de una evidencia desde Chat → Fuentes y
              evidencia → Ver más.
            </p>
          </div>
        )}

        {selectedEvidence && (
          <div className="evidence-page__card">
            <EvidenceViewer source={selectedEvidence} />

            <div className="evidence-page__actions">
              <button
                className="evidence-page__button evidence-page__button--primary"
                type="button"
                disabled={!selectedEvidence.documentId}
                onClick={() => onOpenDocument(selectedEvidence.documentId)}
              >
                Ver documento
              </button>
              <button
                className="evidence-page__button evidence-page__button--secondary"
                type="button"
                onClick={() => onBackToChat(selectedEvidence.conversationId ?? null)}
              >
                Volver al chat
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

export default EvidencePage
