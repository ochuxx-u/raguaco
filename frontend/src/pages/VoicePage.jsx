import { useEffect, useRef, useState } from 'react'
import ChatDocumentsPanel from '../components/chat/ChatDocumentsPanel.jsx'
import NoEvidenceNotice from '../components/chat/NoEvidenceNotice.jsx'
import EvidencePanel from '../components/evidence/EvidencePanel.jsx'
import useDocumentSelection from '../hooks/useDocumentSelection.js'
import useVoiceRecorder from '../hooks/useVoiceRecorder.js'
import AudioPlayer from '../services/audioPlayer.js'
import voiceService from '../services/voiceService.js'
import { deriveConversationTitle, mapMessage } from '../utils/conversations.js'
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
  recording: {
    title: 'Estoy escuchando…',
    hint: 'Pulsa Detener cuando termines.',
  },
  processing: {
    title: 'Procesando…',
    hint: 'Transcribiendo tu pregunta.',
  },
  transcribing: {
    title: 'Transcripción lista',
    hint: 'Consultando tus documentos…',
  },
  answering: {
    title: 'Respuesta lista',
    hint: 'Preparando el audio de la respuesta.',
  },
  speaking: {
    title: 'Raguaco está respondiendo',
    hint: 'Puedes leer la respuesta mientras suena el audio.',
  },
  result: {
    title: 'Consulta completada',
    hint: 'Revisa la transcripción, la respuesta y sus fuentes.',
  },
  error: {
    title: 'No se pudo completar la consulta',
    hint: 'Revisa el mensaje y vuelve a intentarlo.',
  },
}

const EMPTY_RESULT = {
  transcripcion: '',
  respuesta: '',
  conversationId: null,
  message: null,
  sources: [],
}

function VoicePage({
  conversationId = null,
  currentUser = null,
  onConversationCreated = () => {},
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

  const {
    startRecording,
    stopRecording,
    cancelRecording,
    error: recorderError,
  } = useVoiceRecorder()

  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [isAutoplayBlocked, setIsAutoplayBlocked] = useState(false)

  const requestRef = useRef(0)
  const abortRef = useRef(null)
  const playerRef = useRef(null)
  const transcriptionRef = useRef('')
  const reportedConversationRef = useRef(null)

  const content = STATUS_CONTENT[status] ?? STATUS_CONTENT.idle
  const isListening = status === 'recording'
  const isBusy = ['processing', 'transcribing', 'answering'].includes(status)
  const isWaveActive = status === 'recording' || status === 'speaking'
  const canStart =
    status === 'idle' ||
    status === 'result' ||
    status === 'error' ||
    status === 'speaking'
  const showResults = Boolean(
    result && (result.transcripcion || result.respuesta),
  )
  const visibleError = error || recorderError

  const updateResult = (patch) => {
    setResult((current) => ({ ...(current ?? EMPTY_RESULT), ...patch }))
  }

  const reportConversation = (id) => {
    if (!id || reportedConversationRef.current === id) {
      return
    }

    reportedConversationRef.current = id

    if (id !== conversationId) {
      onConversationCreated(
        id,
        deriveConversationTitle(transcriptionRef.current),
      )
    }
  }

  useEffect(() => {
    if (recorderError && status === 'recording') {
      setError(recorderError)
      setStatus('error')
    }
  }, [recorderError, status])

  useEffect(() => {
    const player = new AudioPlayer()
    playerRef.current = player
    player.setHandlers({
      onPlayingChange: (playing) => {
        if (playing) {
          setStatus((current) =>
            ['answering', 'speaking', 'result'].includes(current)
              ? 'speaking'
              : current,
          )
          return
        }

        setStatus((current) => (current === 'speaking' ? 'result' : current))
      },
      onBlocked: () => {
        setIsAutoplayBlocked(true)
        setStatus((current) =>
          current === 'speaking' || current === 'answering'
            ? 'result'
            : current,
        )
      },
      onError: (message) => {
        setIsAutoplayBlocked(false)
        setError(message)
        setStatus((current) =>
          current === 'speaking' || current === 'answering'
            ? 'result'
            : current,
        )
      },
    })

    return () => {
      abortRef.current?.abort()
      player.setHandlers({})
      player.stop()
      playerRef.current = null
      cancelRecording()
    }
  }, [cancelRecording])

  const applyVoiceEvent = (event) => {
    switch (event.tipo) {
      case 'procesando':
        setStatus('processing')
        break

      case 'transcripcion':
        transcriptionRef.current = event.texto ?? ''
        updateResult({ transcripcion: transcriptionRef.current })
        setStatus('transcribing')
        break

      case 'respuesta': {
        const message = event.mensaje
          ? mapMessage(event.mensaje, event.referencias ?? [])
          : null

        updateResult({
          respuesta: event.texto ?? message?.content ?? '',
          message,
          sources: message?.sources ?? [],
          conversationId:
            event.conversacion_id ??
            message?.conversationId ??
            conversationId ??
            null,
        })
        reportConversation(event.conversacion_id ?? message?.conversationId)
        setStatus('answering')
        break
      }

      case 'fragmento':
        if (event.url) {
          playerRef.current?.enqueue(event.url)
        }
        break

      case 'fin':
        if (event.conversacion_id) {
          updateResult({ conversationId: event.conversacion_id })
        }
        reportConversation(event.conversacion_id)
        break

      case 'error':
        playerRef.current?.stop()
        setError(event.detalle || 'El servicio de voz devolvió un error.')
        setStatus('error')
        break

      default:
        break
    }
  }

  const handleStart = async () => {
    if (!currentUser?.id) {
      setError('Selecciona un perfil antes de usar el micrófono.')
      setStatus('error')
      return
    }

    const requestId = ++requestRef.current

    abortRef.current?.abort()
    abortRef.current = null
    playerRef.current?.stop()
    cancelRecording()

    setIsAutoplayBlocked(false)
    setResult(null)
    setError('')
    transcriptionRef.current = ''
    reportedConversationRef.current = null

    try {
      await startRecording()

      if (requestRef.current !== requestId) {
        return
      }

      setStatus('recording')
    } catch (startError) {
      if (requestRef.current !== requestId) {
        return
      }

      setError(startError?.message || 'No se pudo acceder al micrófono.')
      setStatus('error')
    }
  }

  const handleStop = async () => {
    if (status !== 'recording') {
      return
    }

    const requestId = ++requestRef.current
    setStatus('processing')
    setError('')

    let audioBlob

    try {
      audioBlob = await stopRecording()
    } catch (stopError) {
      if (stopError?.name === 'AbortError') {
        return
      }

      if (requestRef.current !== requestId) {
        return
      }

      setError(stopError?.message || 'No se pudo detener la grabación.')
      setStatus('error')
      return
    }

    if (requestRef.current !== requestId) {
      return
    }

    if (!audioBlob || audioBlob.size === 0) {
      setError('No se grabó audio. Inténtalo de nuevo.')
      setStatus('error')
      return
    }

    if (!currentUser?.id) {
      setError('No hay un perfil activo.')
      setStatus('error')
      return
    }

    const controller = new AbortController()
    abortRef.current = controller
    playerRef.current?.stop()

    try {
      const voiceResult = await voiceService.consult({
        audioBlob,
        usuarioId: currentUser.id,
        conversacionId: conversationId,
        documentIds: selectedDocumentIds,
        signal: controller.signal,
        onEvent: (event) => {
          if (requestRef.current !== requestId) {
            return
          }

          applyVoiceEvent(event)
        },
      })

      if (requestRef.current !== requestId) {
        return
      }

      setResult((current) => ({
        ...(current ?? EMPTY_RESULT),
        ...voiceResult,
      }))
      reportConversation(voiceResult.conversationId)
      setStatus(() => (playerRef.current?.isPlaying ? 'speaking' : 'result'))
    } catch (consultError) {
      if (consultError?.name === 'AbortError') {
        return
      }

      if (requestRef.current !== requestId) {
        return
      }

      setError(
        consultError?.message || 'No se pudo procesar la consulta de voz.',
      )
      setStatus('error')
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
      }
    }
  }

  const handleStartNewConversation = () => {
    requestRef.current += 1
    abortRef.current?.abort()
    abortRef.current = null
    playerRef.current?.stop()
    cancelRecording()

    setStatus('idle')
    setResult(null)
    setError('')
    setIsAutoplayBlocked(false)
    transcriptionRef.current = ''
    reportedConversationRef.current = null
    onStartNewConversation()
  }

  const handleReplay = () => {
    setIsAutoplayBlocked(false)
    setError('')
    playerRef.current?.retry()
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
          <div className="voice-page__orb-wrap">
            {isBusy && (
              <>
                <span
                  className="voice-page__halo voice-page__halo--one"
                  aria-hidden="true"
                />
                <span
                  className="voice-page__halo voice-page__halo--two"
                  aria-hidden="true"
                />
              </>
            )}
            <div
              className={`voice-page__orb voice-page__orb--${status}`}
              aria-hidden="true"
            />
          </div>

          <p className="voice-page__status" role="status" aria-live="polite">
            {content.title}
          </p>
          <p className="voice-page__hint">{content.hint}</p>

          {status !== 'result' && status !== 'error' && (
            <svg
              className={`voice-page__waveform${
                isWaveActive ? ' voice-page__waveform--active' : ''
              }`}
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

          {isBusy && (
            <span className="voice-page__spinner" aria-hidden="true" />
          )}

          <div className="voice-page__controls">
            {canStart && (
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
                {result ? 'Nueva consulta' : 'Iniciar'}
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

            {status === 'speaking' && (
              <button
                className="voice-page__control voice-page__control--secondary"
                type="button"
                aria-label="Detener la reproducción de la respuesta"
                onClick={() => playerRef.current?.stop()}
              >
                Detener audio
              </button>
            )}

            {isAutoplayBlocked && result && (
              <button
                className="voice-page__control voice-page__control--secondary"
                type="button"
                onClick={handleReplay}
              >
                Reproducir respuesta
              </button>
            )}
          </div>

          {visibleError && (
            <p className="voice-page__error" role="alert">
              {visibleError}
            </p>
          )}
        </div>

        {showResults && (
          <div className="voice-page__results">
            <div className="voice-page__cards">
              {result.transcripcion && (
                <article
                  className="voice-page__card voice-page__card--transcription"
                  aria-labelledby="voice-transcription-title"
                >
                  <h2
                    className="voice-page__card-title"
                    id="voice-transcription-title"
                  >
                    Transcripción
                  </h2>
                  <p className="voice-page__transcription">
                    {result.transcripcion}
                  </p>
                </article>
              )}

              {result.respuesta && (
                <article
                  className="voice-page__card voice-page__card--response"
                  aria-labelledby="voice-response-title"
                >
                  <h2
                    className="voice-page__card-title"
                    id="voice-response-title"
                  >
                    Respuesta
                  </h2>
                  <p className="voice-page__response">{result.respuesta}</p>
                </article>
              )}
            </div>

            {result.sources?.length > 0 ? (
              <div className="voice-page__evidence">
                <EvidencePanel
                  activeSourceId={result.sources[0]?.id ?? null}
                  onViewMore={handleOpenEvidence}
                  sources={result.sources}
                />
              </div>
            ) : (
              result.respuesta && (
                <div className="voice-page__notice">
                  <NoEvidenceNotice />
                </div>
              )
            )}
          </div>
        )}
      </div>
    </section>
  )
}

export default VoicePage
