"""Detección de fin de voz: cuándo se deja de hablar y hay que procesar.

El servicio de voz no espera a que el usuario pulse "Detener": acumula bloques
de micrófono y, cuando detecta voz seguida de `VOICE_SILENCE_SECONDS` segundos
de silencio, cierra la pregunta y devuelve el audio completo. Ese audio es el
que se manda a `WhisperSTT` (RF12).

La señal de voz se mide con el **pico** de cada bloque (amplitud máxima), no
con la energía media: un ventilador o un micrófono con ganancia alta elevan la
energía de fondo y nunca dejarían detectar el silencio, mientras que la voz
tiene picos claramente mayores. El umbral se puede calibrar con el ruido de la
sala (`pico` de los primeros bloques) antes de empezar a escuchar.

También cierra la pregunta si supera `VOICE_MAX_UTTERANCE_SECONDS`, para que
una frase larga no deje el buffer creciendo sin límite.

Los umbrales viven en `core/config.py` y se pueden ajustar por entorno:
`VOICE_SILENCE_SECONDS`, `VOICE_SILENCE_PEAK`, `VOICE_MIN_UTTERANCE_SECONDS`
y `VOICE_MAX_UTTERANCE_SECONDS`.
"""

import numpy as np

from core.config import settings

# Whisper y el flujo de voz trabajan a 16 kHz mono.
SAMPLE_RATE = 16_000

# Silencio que se conserva al final del recorte para no cortar la última sílaba.
COLA_SILENCIO_SEGUNDOS = 0.15


def pico(audio: np.ndarray) -> float:
    """Amplitud máxima de un bloque (0..1 en audio normalizado)."""
    if audio is None or audio.size == 0:
        return 0.0
    return float(np.max(np.abs(np.asarray(audio, dtype=np.float32))))


class DetectorVoz:
    """Acumula audio y avisa cuándo termina una pregunta.

    Uso típico con un grabador de micrófono:

    ```python
    detector = DetectorVoz()
    while True:
        audio = detector.agregar(chunk)
        if audio is not None:
            procesar(audio)  # fin de la pregunta
    ```

    El detector solo cierra una locución si antes detectó voz; un silencio
    prolongado sin hablar no dispara consultas vacías.
    """

    def __init__(
        self,
        *,
        silence_seconds: float | None = None,
        min_utterance_seconds: float | None = None,
        max_utterance_seconds: float | None = None,
        silence_peak: float | None = None,
    ) -> None:
        self._silencio_objetivo = float(
            silence_seconds
            if silence_seconds is not None
            else settings.voice_silence_seconds
        )
        self._minimo = float(
            min_utterance_seconds
            if min_utterance_seconds is not None
            else settings.voice_min_utterance_seconds
        )
        self._maximo = float(
            max_utterance_seconds
            if max_utterance_seconds is not None
            else settings.voice_max_utterance_seconds
        )
        self._pico_silencio = float(
            silence_peak if silence_peak is not None else settings.voice_silence_peak
        )
        self.reiniciar()

    def reiniciar(self) -> None:
        """Descarta lo acumulado y empieza a escuchar una pregunta nueva."""
        self._audio = np.zeros(0, dtype=np.float32)
        self._silencio = 0.0
        self._hablado = False

    @property
    def hablado(self) -> bool:
        """True si en la locución actual ya se detectó voz."""
        return self._hablado

    @property
    def silencio(self) -> float:
        """Segundos de silencio consecutivos al final de lo acumulado."""
        return self._silencio

    def agregar(self, chunk: np.ndarray) -> np.ndarray | None:
        """Añade un bloque de audio y devuelve la pregunta si ya terminó.

        El audio devuelto es mono float32 a 16 kHz, sin el silencio final
        (salvo una cola mínima para no cortar la última sílaba).
        """
        if chunk is None or chunk.size == 0:
            return None

        bloque = np.asarray(chunk, dtype=np.float32)
        if bloque.ndim > 1:
            bloque = bloque.mean(axis=1)
        bloque = bloque.reshape(-1)

        self._audio = np.concatenate([self._audio, bloque])
        duracion = bloque.size / SAMPLE_RATE

        if pico(bloque) < self._pico_silencio:
            self._silencio += duracion
        else:
            self._silencio = 0.0
            self._hablado = True

        duracion_total = self._audio.size / SAMPLE_RATE
        cerrada_por_silencio = (
            self._hablado and self._silencio >= self._silencio_objetivo
        )
        cerrada_por_limite = duracion_total >= self._maximo

        if not cerrada_por_silencio and not cerrada_por_limite:
            return None

        audio = self._recortar_cola()
        hablado = self._hablado
        self.reiniciar()

        # Un ruido corto (tos, golpe) no debe convertirse en una consulta.
        if not hablado or audio.size / SAMPLE_RATE < self._minimo:
            return None
        return audio

    def _recortar_cola(self) -> np.ndarray:
        """Quita el silencio final dejando una cola mínima audible."""
        if self._silencio <= COLA_SILENCIO_SEGUNDOS:
            return self._audio
        recorte = int((self._silencio - COLA_SILENCIO_SEGUNDOS) * SAMPLE_RATE)
        if recorte <= 0:
            return self._audio
        if recorte >= self._audio.size:
            return np.zeros(0, dtype=np.float32)
        return self._audio[:-recorte]
