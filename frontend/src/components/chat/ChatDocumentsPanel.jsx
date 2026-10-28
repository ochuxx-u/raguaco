import './ChatDocumentsPanel.css'

function ChatDocumentsPanel({
  documents,
  error,
  isLoading,
  onClose,
  onRetry,
  onStartNewConversation = () => {},
  onToggleDocument,
  selectedDocumentIds = [],
}) {
  return (
    <section className="chat-documents" aria-labelledby="chat-documents-title">
      <header className="chat-documents__header">
        <h2 className="chat-documents__title" id="chat-documents-title">
          Seleccionar documentos
        </h2>

        {onClose && (
          <button
            className="chat-documents__close"
            type="button"
            aria-label="Cerrar panel de documentos"
            title="Cerrar panel de documentos"
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

      <div className="chat-documents__body">
        {isLoading && (
          <div className="chat-documents__state" role="status">
            <span className="chat-documents__spinner" aria-hidden="true" />
            <p>Cargando documentos…</p>
          </div>
        )}

        {!isLoading && error && (
          <div className="chat-documents__state chat-documents__state--error" role="alert">
            <p>{error}</p>
            <button className="chat-documents__retry" type="button" onClick={onRetry}>
              Reintentar
            </button>
          </div>
        )}

        {!isLoading && !error && (
          <>
            {documents.length > 0 ? (
              <ul className="chat-documents__list">
                {documents.map((document) => {
                  const isSelected = selectedDocumentIds.includes(document.id)

                  return (
                    <li key={document.id}>
                      <button
                        className={`chat-documents__item${
                          isSelected ? ' chat-documents__item--active' : ''
                        }`}
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => onToggleDocument(document)}
                      >
                        <span className="chat-documents__name" title={document.nombre}>
                          {document.nombre}
                        </span>
                        <span className="chat-documents__meta">
                          {document.categoria || 'Sin categoría'}
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            ) : (
              <p className="chat-documents__empty">
                Aún no hay documentos cargados.
              </p>
            )}
          </>
        )}
      </div>

      <footer className="chat-documents__footer">
        <button
          className="chat-documents__new"
          type="button"
          onClick={onStartNewConversation}
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
            <path d="M12 5v14M5 12h14" />
          </svg>
          Nueva conversación
        </button>
      </footer>
    </section>
  )
}

export default ChatDocumentsPanel
