import { getDocumentStateLabel } from '../../utils/documents.js'
import './DocumentStatusBadge.css'

function DocumentStatusBadge({ estado }) {
  return (
    <span className={`document-status-badge document-status-badge--${estado}`}>
      {getDocumentStateLabel(estado)}
    </span>
  )
}

export default DocumentStatusBadge
