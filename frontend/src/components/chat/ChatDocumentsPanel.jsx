import './ChatDocumentsPanel.css'

function ChatDocumentsPanel({
  categories,
  categoryFilter,
  documents,
  error,
  isLoading,
  onCategoryChange,
  onClose,
  onRetry,
  onSelectDocument,
  selectedDocumentId,
}) {
  return (
    <section className="chat-documents" aria-labelledby="chat-documents-title">
      <header className="chat-documents__header">
        <h2 className="chat-documents__title" id="chat-documents-title">
          Documentos
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
                  const isSelected = document.id === selectedDocumentId

                  return (
                    <li key={document.id}>
                      <button
                        className={`chat-documents__item${
                          isSelected ? ' chat-documents__item--active' : ''
                        }`}
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => onSelectDocument(document)}
                      >
                        <span className="chat-documents__name" title={document.nombre}>
                          {document.nombre}
                        </span>
                        <span className="chat-documents__meta">{document.categoria}</span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            ) : (
              <p className="chat-documents__empty">
                {categories.length === 0
                  ? 'Aún no hay documentos cargados.'
                  : 'No hay documentos en esta categoría.'}
              </p>
            )}
          </>
        )}
      </div>

      <div className="chat-documents__filters">
        <p className="chat-documents__filters-label">Filtros</p>
        <div className="chat-documents__chips">
          <button
            className={`chat-documents__chip${
              categoryFilter === 'all' ? ' chat-documents__chip--active' : ''
            }`}
            type="button"
            aria-pressed={categoryFilter === 'all'}
            onClick={() => onCategoryChange('all')}
          >
            Todas
          </button>

          {categories.map((category) => (
            <button
              className={`chat-documents__chip${
                categoryFilter === category ? ' chat-documents__chip--active' : ''
              }`}
              type="button"
              key={category}
              aria-pressed={categoryFilter === category}
              onClick={() => onCategoryChange(category)}
            >
              {category}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}

export default ChatDocumentsPanel
