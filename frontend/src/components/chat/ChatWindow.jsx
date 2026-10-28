import ChatInput from './ChatInput.jsx'
import MessageList from './MessageList.jsx'
import './ChatWindow.css'

function ChatWindow({
  activeEvidence,
  error,
  hasSelectedDocuments = true,
  isDocumentsOpen,
  isEvidenceOpen,
  isLoading,
  isThinking,
  messages,
  onGoToDocuments,
  onOpenDocuments,
  onOpenEvidence,
  onRetry,
  onSend,
  onSourceClick,
  selectedDocuments = [],
  sendError,
}) {
  const selectedCount = selectedDocuments.length
  const contextLabel =
    selectedCount === 0
      ? 'Sin documento seleccionado'
      : selectedCount === 1
        ? `Documento: ${selectedDocuments[0].nombre}`
        : `${selectedCount} documentos seleccionados`
  const contextTitle =
    selectedCount > 1
      ? selectedDocuments.map((document) => document.nombre).join(', ')
      : selectedDocuments[0]?.nombre

  return (
    <section className="chat-window" aria-labelledby="chat-title">
      <header className="chat-window__header">
        <div className="chat-window__heading">
          <h1 className="chat-window__title" id="chat-title">
            Chat RAG
          </h1>
          <p className="chat-window__context" title={contextTitle}>
            {contextLabel}
          </p>
        </div>

        <div className="chat-window__panel-actions">
          <button
            className={`chat-window__panel-button${
              isDocumentsOpen ? ' chat-window__panel-button--active' : ''
            }`}
            type="button"
            aria-label="Abrir panel de documentos"
            title="Abrir panel de documentos"
            aria-controls="chat-documents-panel"
            aria-expanded={isDocumentsOpen}
            onClick={onOpenDocuments}
          >
            <svg
              viewBox="0 0 24 24"
              width="20"
              height="20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
            >
              <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
              <path d="M14 3v5h5" />
              <path d="M9 13h6M9 17h4" />
            </svg>
          </button>

          <button
            className={`chat-window__panel-button${
              isEvidenceOpen ? ' chat-window__panel-button--active' : ''
            }`}
            type="button"
            aria-label="Abrir panel de fuentes y evidencia"
            title="Abrir panel de fuentes y evidencia"
            aria-controls="chat-evidence-panel"
            aria-expanded={isEvidenceOpen}
            onClick={onOpenEvidence}
          >
            <svg
              viewBox="0 0 24 24"
              width="20"
              height="20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
            >
              <path d="M12 6.5C10.7 5.3 8.8 4.8 6.5 4.8H3v12.7h3.5c2.3 0 4.2.5 5.5 1.7 1.3-1.2 3.2-1.7 5.5-1.7H21V4.8h-3.5c-2.3 0-4.2.5-5.5 1.7z" />
              <path d="M12 6.5v12.7" />
            </svg>
          </button>
        </div>
      </header>

      <MessageList
        activeEvidence={activeEvidence}
        error={error}
        isLoading={isLoading}
        isThinking={isThinking}
        messages={messages}
        onRetry={onRetry}
        onSourceClick={onSourceClick}
      />

      <div className="chat-window__composer">
        {sendError && (
          <p className="chat-window__error" role="alert">
            {sendError}
          </p>
        )}

        <ChatInput
          disabled={isLoading || Boolean(error)}
          hasSelectedDocuments={hasSelectedDocuments}
          isSending={isThinking}
          onGoToDocuments={onGoToDocuments}
          onSend={onSend}
        />
      </div>
    </section>
  )
}

export default ChatWindow
