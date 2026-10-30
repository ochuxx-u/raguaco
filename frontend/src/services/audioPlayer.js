/**
 * Cola secuencial de fragmentos WAV del TTS.
 *
 * El backend entrega cada fragmento como una URL independiente. Esta clase
 * mantiene una única reproducción activa, encola los fragmentos que llegan
 * mientras suena el anterior y avisa a la página de los cambios de estado.
 */
export default class AudioPlayer {
  constructor() {
    this._queue = []
    this._current = null
    this._playing = false
    this._blocked = false
    this._generation = 0
    this._handlers = {}
  }

  setHandlers(handlers = {}) {
    this._handlers = handlers || {}
  }

  get isPlaying() {
    return this._playing
  }

  get isBlocked() {
    return this._blocked
  }

  enqueue(url) {
    if (!url) {
      return
    }

    this._queue.push(url)

    if (!this._playing && !this._blocked) {
      void this._playNext()
    }
  }

  /**
   * Reintenta la reproducción después de que el navegador bloqueara el
   * autoplay. Debe llamarse desde un gesto del usuario (clic en «Reproducir»).
   */
  retry() {
    if (!this._blocked) {
      return
    }

    this._blocked = false
    const audio = this._current

    if (!audio) {
      void this._playNext()
      return
    }

    const generation = this._generation
    this._playing = true
    this._emit('onPlayingChange', true)

    audio.play().catch((error) => {
      if (generation !== this._generation) {
        return
      }

      this._playing = false
      this._blocked = true
      this._emit('onPlayingChange', false)
      this._emit('onBlocked', error)
    })
  }

  /**
   * Detiene el audio actual y descarta todo lo pendiente. Se usa al iniciar
   * otra consulta o al desmontar VoicePage.
   */
  stop() {
    this._generation += 1
    this._queue = []
    this._blocked = false

    const audio = this._current
    this._current = null
    this._playing = false

    if (audio) {
      try {
        audio.pause()
      } catch {
        // El audio pudo haber terminado ya.
      }

      audio.removeAttribute('src')

      try {
        audio.load()
      } catch {
        // Algunos navegadores no permiten recargar tras removeAttribute.
      }
    }

    this._emit('onPlayingChange', false)
  }

  async _playNext() {
    if (this._playing || this._blocked) {
      return
    }

    const url = this._queue.shift()

    if (!url) {
      this._current = null
      this._playing = false
      this._emit('onPlayingChange', false)
      return
    }

    const generation = this._generation
    const audio = new Audio(url)
    audio.preload = 'auto'
    this._current = audio
    this._playing = true
    this._emit('onPlayingChange', true)

    const avanzar = () => {
      if (generation !== this._generation) {
        return
      }

      this._playing = false
      this._current = null
      this._emit('onPlayingChange', false)

      if (this._queue.length > 0) {
        void this._playNext()
      }
    }

    audio.addEventListener('ended', avanzar)
    audio.addEventListener('error', () => {
      if (generation !== this._generation) {
        return
      }

      this._playing = false
      this._current = null
      this._emit('onPlayingChange', false)
      this._emit('onError', 'No se pudo reproducir un fragmento de audio.')

      if (this._queue.length > 0) {
        void this._playNext()
      }
    })

    try {
      await audio.play()
    } catch (error) {
      if (generation !== this._generation) {
        return
      }

      this._playing = false
      this._blocked = true
      this._emit('onPlayingChange', false)
      this._emit('onBlocked', error)
    }
  }

  _emit(name, value) {
    const handler = this._handlers?.[name]

    if (typeof handler === 'function') {
      handler(value)
    }
  }
}
