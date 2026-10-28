import { useEffect, useRef, useState } from 'react'
import EvidenceViewer from '../components/evidence/EvidenceViewer.jsx'
import evidenceService from '../services/evidenceService.js'
import './EvidencePage.css'

function EvidencePage({
  onBackToChat = () => {},
  onOpenDocument = () => {},
  selectedEvidenceId = null,
}) {
  const [evidence, setEvidence] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const requestRef = useRef(0)

  const loadEvidence = async () => {
    const requestId = ++requestRef.current
    setIsLoading(true)
    setError('')

    try {
      const nextEvidence = selectedEvidenceId
        ? await evidenceService.getById(selectedEvidenceId)
        : await evidenceService.getDefault()

      if (requestId !== requestRef.current) return

      setEvidence(nextEvidence)
    } catch {
      if (requestId === requestRef.current) {
        setEvidence(null)
        setError('No se pudo cargar la evidencia seleccionada.')
      }
    } finally {
      if (requestId === requestRef.current) {
        setIsLoading(false)
      }
    }
  }

  useEffect(() => {
    void loadEvidence()
  }, [selectedEvidenceId])

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
        {isLoading && (
          <div className="evidence-page__state" role="status">
            <span className="evidence-page__spinner" aria-hidden="true" />
            <p>Cargando evidencia…</p>
          </div>
        )}

        {!isLoading && error && (
          <div className="evidence-page__state evidence-page__state--error" role="alert">
            <p>{error}</p>
            <button className="evidence-page__retry" type="button" onClick={loadEvidence}>
              Reintentar
            </button>
          </div>
        )}

        {!isLoading && !error && !evidence && (
          <div className="evidence-page__state">
            <p>Aún no hay evidencia disponible.</p>
          </div>
        )}

        {!isLoading && !error && evidence && (
          <div className="evidence-page__card">
            <EvidenceViewer source={evidence} />

            <div className="evidence-page__actions">
              <button
                className="evidence-page__button evidence-page__button--primary"
                type="button"
                disabled={!evidence.documentId}
                onClick={() => onOpenDocument(evidence.documentId)}
              >
                Abrir documento
              </button>
              <button
                className="evidence-page__button evidence-page__button--secondary"
                type="button"
                onClick={onBackToChat}
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
