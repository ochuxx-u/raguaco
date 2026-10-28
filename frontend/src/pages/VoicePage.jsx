import { useRef, useState } from 'react'
import ChatDocumentsPanel from '../components/chat/ChatDocumentsPanel.jsx'
import EvidencePanel from '../components/evidence/EvidencePanel.jsx'
import useDocumentSelection from '../hooks/useDocumentSelection.js'
import voiceService from '../services/voiceService.js'
import './VoicePage.css'

const waveBars = [
  { x: 0, y: 16, height: 12 },
  { x: 30, y: 8, height: 28 },
  { x: 60, y: 2, height: 40 },
  { x: 90, y: 12, height: 20 },
  { x: 120, y: 6, height: 32 },
  { x: 150, y: 0, height: 44 },
  { x: 180, y: 10, height: 24 },
  { x: 210, y: 4, height: 36 },
  { x: 240, y: 14, height: 16 },
  { x: 270, y: 6, height: 32 },
  { x: 300, y: 12, height: 20 },
  { x: 330, y: 18, height: 8 },
]

const STATUS_CONTENT = {
  idle: {
    title: 'Habla con tu base de conocimiento',
    hint: 'Presiona Iniciar y haz tu pregunta en voz alta.',
  },
  listening: {
    title: 'Estoy escuchando…',
    hint: 'Pulsa Detener cuando termines.',
  },
  processing: {
    title: 'Procesando…',
    hint: 'Preparando la transcripción y la respuesta.',
  },
  result: {
    title: 'Consulta completada',
    hint: 'Revisa la transcripción, la respuesta y su fuente.',
  },
}

function VoicePage({
  currentUser = null,
  onOpenEvidencePage = () => {},
  onSelectedDocumentsChange = () => {},
  onStartNewConversation = () => {},
  selectedDocumentIds: initialSelectedDocumentIds = [],
}) {
  const {
    documents,
    documentsError,
    isDocumentsLoading,
    loadDocuments,
    selectedDocumentIds,
    toggleDocument,
  } = useDocumentSelection({
    currentUser,
    initialSelectedDocumentIds,
    onSelectedDocumentsChange,
  })

  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const requestRef = useRef(0)

  const isListening = status === 'listening'
  const isProcessing = status === 'processing'
  const content = STATUS_CONTENT[status]

  const handleStart = () => {
    requestRef.current += 1
    setResult(null)
    setError('')
    setStatus('listening')
  }

  const handleStop = async () => {
    if (!isListening) return

    const requestId = ++requestRef.current
    setStatus('processing')
    setError('')

    try {
      const voiceResult = await voiceService.process()

      if (requestRef.current !== requestId) return

      setResult(voiceResult)
      setStatus('result')
    } catch {
      if (requestRef.current === requestId) {
        setError('No se pudo procesar la consulta de voz. Inténtalo de nuevo.')
        setStatus('idle')
      }
    }
  }

  const handleStartNewConversation = () => {
    // Invalida cualquier consulta de voz en curso y deja esta pestaña lista
    // para la conversación nueva, sin salir de Voz.
    requestRef.current += 1
    setStatus('idle')
    setResult(null)
    setError('')
    onStartNewConversation()
  }

  const handleOpenEvidence = (source) => {
    if (source?.id) {
      onOpenEvidencePage(source)
    }
  }

  return (
    <section
      className={`voice-page voice-page--${status}`}
      aria-labelledby="voice-title"
    >
      <aside
        className="voice-page__documents"
        aria-label="Panel de selección de documentos"
      >
        <ChatDocumentsPanel
          documents={documents}
          error={documentsError}
          isLoading={isDocumentsLoading}
          onRetry={loadDocuments}
          onStartNewConversation={handleStartNewConversation}
          onToggleDocument={toggleDocument}
          selectedDocumentIds={selectedDocumentIds}
        />
      </aside>

      <div className="voice-page__main">
        <h1 className="voice-page__title" id="voice-title">
          Voz
        </h1>

        <div className="voice-page__stage">
          <div className={`voice-page__orb voice-page__orb--${status}`} aria-hidden="true" />

          <p className="voice-page__status" role="status" aria-live="polite">
            {content.title}
          </p>
          <p className="voice-page__hint">{content.hint}</p>

          {status !== 'result' && (
            <svg
              className={`voice-page__waveform${isListening ? ' voice-page__waveform--active' : ''}`}
              viewBox="0 0 360 44"
              fill="currentColor"
              aria-hidden="true"
              focusable="false"
            >
              {waveBars.map((bar) => (
                <rect
                  key={bar.x}
                  x={bar.x}
                  y={bar.y}
                  width="6"
                  height={bar.height}
                  rx="3"
                />
              ))}
            </svg>
          )}

          {isProcessing && <span className="voice-page__spinner" aria-hidden="true" />}

          <div className="voice-page__controls">
            {(status === 'idle' || status === 'result') && (
              <button
                className="voice-page__control voice-page__control--primary"
                type="button"
                aria-label="Iniciar reconocimiento de voz"
                onClick={handleStart}
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
                  <rect x="9" y="3" width="6" height="11" rx="3" />
                  <path d="M5 11a7 7 0 0 0 14 0" />
                  <path d="M12 18v3M9 21h6" />
                </svg>
                {status === 'result' ? 'Nueva consulta' : 'Iniciar'}
              </button>
            )}

            {isListening && (
              <button
                className="voice-page__control voice-page__control--secondary"
                type="button"
                aria-label="Detener reconocimiento de voz"
                onClick={handleStop}
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
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
                Detener
              </button>
            )}
          </div>

          {error && (
            <p className="voice-page__error" role="alert">
              {error}
            </p>
          )}
        </div>

        {status === 'result' && result && (
          <div className="voice-page__results">
            <div className="voice-page__cards">
              <article
                className="voice-page__card voice-page__card--transcription"
                aria-labelledby="voice-transcription-title"
              >
                <h2 className="voice-page__card-title" id="voice-transcription-title">
                  Transcripción
                </h2>
                <p className="voice-page__transcription">{result.transcripcion}</p>
              </article>

              <article
                className="voice-page__card voice-page__card--response"
                aria-labelledby="voice-response-title"
              >
                <h2 className="voice-page__card-title" id="voice-response-title">
                  Respuesta
                </h2>
                <p className="voice-page__response">{result.respuesta}</p>
              </article>
            </div>

            {result.fuente && (
              <div className="voice-page__evidence">
                <EvidencePanel
                  activeSourceId={result.fuente.id}
                  onViewMore={handleOpenEvidence}
                  sources={[result.fuente]}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

export default VoicePage
