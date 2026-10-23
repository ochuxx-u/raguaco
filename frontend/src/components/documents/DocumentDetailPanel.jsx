import { useEffect } from 'react'
import {
  getDocumentMetricLabel,
  getDocumentSecondaryText,
  getDocumentStateLabel,
} from '../../utils/documents.js'
import DocumentStatusBadge from './DocumentStatusBadge.jsx'
import './DocumentDetailPanel.css'

function DocumentDetailPanel({ document, error, onAsk, onClose }) {
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!document) {
    return null
  }

  return (
    <div
      className="document-detail"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose()
        }
      }}
    >
      <section
        className="document-detail__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="document-detail-title"
      >
        <header className="document-detail__header">
          <h2 className="document-detail__title" id="document-detail-title">
            Detalle del documento
          </h2>
          <button
            className="document-detail__close"
            type="button"
            aria-label="Cerrar detalle del documento"
            title="Cerrar detalle"
            autoFocus
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
        </header>

        {error && (
          <p className="document-detail__error" role="alert">
            {error}
          </p>
        )}

        <div className="document-detail__file">
          <div className="document-detail__type">{document.tipo}</div>
          <div className="document-detail__file-info">
            <p className="document-detail__name" title={document.nombre}>
              {document.nombre}
            </p>
            <DocumentStatusBadge estado={document.estado} />
          </div>
        </div>

        <dl className="document-detail__metadata">
          <div className="document-detail__metadata-row">
            <dt>Nombre</dt>
            <dd>{document.nombre}</dd>
          </div>
          <div className="document-detail__metadata-row">
            <dt>Tipo</dt>
            <dd>{document.tipo}</dd>
          </div>
          <div className="document-detail__metadata-row">
            <dt>Categoría</dt>
            <dd>{document.categoria}</dd>
          </div>
          <div className="document-detail__metadata-row">
            <dt>Fecha</dt>
            <dd>{document.fecha}</dd>
          </div>
          <div className="document-detail__metadata-row">
            <dt>Estado</dt>
            <dd>{getDocumentStateLabel(document.estado)}</dd>
          </div>
          <div className="document-detail__metadata-row">
            <dt>{getDocumentMetricLabel(document.estado)}</dt>
            <dd>{getDocumentSecondaryText(document)}</dd>
          </div>
        </dl>

        <footer className="document-detail__actions">
          <button
            className="document-detail__ask"
            type="button"
            onClick={() => onAsk(document)}
          >
            Preguntar
          </button>
          <button
            className="document-detail__close-button"
            type="button"
            onClick={onClose}
          >
            Cerrar
          </button>
        </footer>
      </section>
    </div>
  )
}

export default DocumentDetailPanel
