import { useCallback, useEffect, useRef, useState } from 'react'

// Formatos que se prueban en orden. Si ninguno está disponible, se deja que el
// navegador elija su formato por defecto.
const PREFERRED_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/mp4',
]

function chooseMimeType() {
  if (
    typeof MediaRecorder === 'undefined' ||
    typeof MediaRecorder.isTypeSupported !== 'function'
  ) {
    return ''
  }

  try {
    return (
      PREFERRED_MIME_TYPES.find((mimeType) =>
        MediaRecorder.isTypeSupported(mimeType),
      ) ?? ''
    )
  } catch {
    return ''
  }
}

function messageForGetUserMediaError(error) {
  switch (error?.name) {
    case 'NotAllowedError':
      return 'No se permitió el acceso al micrófono. Revisa los permisos del navegador.'
    case 'NotFoundError':
      return 'No se encontró ningún micrófono disponible.'
    case 'NotReadableError':
      return 'El micrófono está en uso o no se puede leer. Cierra otras aplicaciones y reintenta.'
    case 'SecurityError':
      return 'El micrófono requiere HTTPS o ejecutarse desde localhost.'
    default:
      return 'No se pudo acceder al micrófono.'
  }
}

/**
 * Grabación de voz con MediaRecorder.
 *
 * `stopRecording()` devuelve una Promise con el Blob de audio. Siempre detiene
 * las pistas del MediaStream, incluso cuando falla la grabación o se cancela.
 */
export default function useVoiceRecorder() {
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError] = useState('')

  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])
  const stopResolveRef = useRef(null)
  const stopRejectRef = useRef(null)

  const stopTracks = useCallback(() => {
    const stream = streamRef.current
    streamRef.current = null

    if (!stream) {
      return
    }

    for (const track of stream.getTracks()) {
      try {
        track.stop()
      } catch {
        // La pista pudo haberse detenido antes.
      }
    }
  }, [])

  const startRecording = useCallback(async () => {
    setError('')

    if (!navigator.mediaDevices?.getUserMedia) {
      const message = 'Este navegador no permite acceder al micrófono.'
      setError(message)
      throw new Error(message)
    }

    if (typeof MediaRecorder === 'undefined') {
      const message = 'Este navegador no soporta la grabación de audio.'
      setError(message)
      throw new Error(message)
    }

    let stream

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (getUserMediaError) {
      const message = messageForGetUserMediaError(getUserMediaError)
      setError(message)
      throw new Error(message)
    }

    streamRef.current = stream

    try {
      const mimeType = chooseMimeType()
      let recorder

      try {
        recorder = mimeType
          ? new MediaRecorder(stream, { mimeType })
          : new MediaRecorder(stream)
      } catch {
        // Si el navegador rechaza el MIME elegido, usa su formato por defecto.
        recorder = new MediaRecorder(stream)
      }

      chunksRef.current = []

      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || mimeType || 'audio/webm',
        })

        chunksRef.current = []
        recorderRef.current = null
        stopTracks()
        setIsRecording(false)

        const resolve = stopResolveRef.current
        stopResolveRef.current = null
        stopRejectRef.current = null
        resolve?.(blob)
      }

      recorder.onerror = () => {
        const message = 'La grabación de audio falló. Inténtalo de nuevo.'
        setError(message)

        const reject = stopRejectRef.current
        stopRejectRef.current = null
        stopResolveRef.current = null
        recorderRef.current = null
        stopTracks()
        setIsRecording(false)
        reject?.(new Error(message))
      }

      recorder.start()
      recorderRef.current = recorder
      setIsRecording(true)
    } catch {
      stopTracks()
      const message = 'No se pudo iniciar la grabación de audio.'
      setError(message)
      throw new Error(message)
    }
  }, [stopTracks])

  const stopRecording = useCallback(
    () =>
      new Promise((resolve, reject) => {
        const recorder = recorderRef.current

        if (!recorder || recorder.state === 'inactive') {
          stopTracks()
          setIsRecording(false)
          resolve(null)
          return
        }

        stopResolveRef.current = resolve
        stopRejectRef.current = reject

        try {
          recorder.stop()
        } catch (stopError) {
          stopResolveRef.current = null
          stopRejectRef.current = null
          recorderRef.current = null
          stopTracks()
          setIsRecording(false)
          reject(stopError)
        }
      }),
    [stopTracks],
  )

  const cancelRecording = useCallback(() => {
    const recorder = recorderRef.current
    recorderRef.current = null

    if (recorder && recorder.state !== 'inactive') {
      try {
        recorder.onstop = null
        recorder.stop()
      } catch {
        // El grabador pudo haberse detenido ya.
      }
    }

    chunksRef.current = []
    stopTracks()
    setIsRecording(false)

    const reject = stopRejectRef.current
    stopRejectRef.current = null
    stopResolveRef.current = null

    if (reject) {
      reject(new DOMException('Grabación cancelada', 'AbortError'))
    }
  }, [stopTracks])

  useEffect(
    () => () => {
      cancelRecording()
    },
    [cancelRecording],
  )

  return {
    startRecording,
    stopRecording,
    cancelRecording,
    isRecording,
    error,
  }
}
