import { getDocumentSecondaryText } from '../../utils/documents.js'
import DocumentStatusBadge from './DocumentStatusBadge.jsx'
import './DocumentRow.css'

function DocumentRow({ document, isHighlighted = false, onAsk, onViewDetail, onDelete }) {
  return (
    <article className={`document-row${isHighlighted ? ' document-row--highlighted' : ''}`}>
      <div className="document-row__type">
        {document.tipo}
      </div>

      <div className="document-row__info">
        <p className="document-row__name" title={document.nombre}>
          {document.nombre}
        </p>
        <p className="document-row__meta">
          {document.categoria} · {document.fecha}
        </p>
      </div>

      <p className="document-row__progress">{getDocumentSecondaryText(document)}</p>

      <div className="document-row__badge">
        <DocumentStatusBadge estado={document.estado} />
      </div>

      <div className="document-row__actions">
        <button
          className="document-row__ask"
          type="button"
          aria-label={`Preguntar sobre ${document.nombre}`}
          onClick={() => onAsk(document)}
        >
          Preguntar
        </button>
        <button
          className="document-row__link"
          type="button"
          aria-label={`Ver detalle de ${document.nombre}`}
          onClick={() => onViewDetail(document)}
        >
          Ver detalle
        </button>
        <button
          className="document-row__link document-row__link--danger"
          type="button"
          aria-label={`Eliminar ${document.nombre}`}
          onClick={() => onDelete(document)}
        >
          Eliminar
        </button>
      </div>
    </article>
  )
}

export default DocumentRow
