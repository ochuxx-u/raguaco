import DocumentRow from './DocumentRow.jsx'
import './DocumentList.css'

function DocumentList({
  documents,
  emptyMessage,
  error,
  highlightedDocumentId,
  isLoading,
  onAsk,
  onDelete,
  onRetry,
  onViewDetail,
}) {
  if (isLoading) {
    return (
      <div className="document-list__state" role="status">
        <span className="document-list__spinner" aria-hidden="true" />
        <p>Cargando documentos…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="document-list__state document-list__state--error" role="alert">
        <p>{error}</p>
        <button className="document-list__retry" type="button" onClick={onRetry}>
          Reintentar
        </button>
      </div>
    )
  }

  if (!documents.length) {
    return (
      <div className="document-list__state">
        <p>{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="document-list">
      {documents.map((document) => (
        <DocumentRow
          key={document.id}
          document={document}
          isHighlighted={document.id === highlightedDocumentId}
          onAsk={onAsk}
          onDelete={onDelete}
          onViewDetail={onViewDetail}
        />
      ))}
    </div>
  )
}

export default DocumentList
