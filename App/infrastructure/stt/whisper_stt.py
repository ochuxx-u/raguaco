"""Reconocimiento de voz local con `faster-whisper` (STT, RF12).

Convierte el audio de la pregunta en texto antes de consultar el RAG. Corre
**en local**, sin API externa, con el modelo `faster-whisper-small` descargado
en `App/ai-models/faster-whisper-small/` (ver README).

Acepta audio ya decodificado (`np.ndarray` mono float32) o bytes en cualquier
formato que entienda `soundfile` (WAV, FLAC, OGG) o `ffmpeg` (WebM/Opus, MP3,
M4A…). El audio se normaliza a mono 16 kHz, que es lo que espera Whisper.

La carga del modelo es perezosa y única por proceso: `WhisperSTT` se comparte
entre peticiones desde `api/deps.py`. La transcripción se serializa con un lock
porque el modelo de faster-whisper mantiene estado interno durante `transcribe`.
"""

import asyncio
import io
import re
import subprocess
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from core.config import settings

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

# Whisper trabaja internamente a 16 kHz mono.
SAMPLE_RATE = 16_000

# Tope de audio aceptado (una pregunta de voz no debería durar más).
MAX_AUDIO_SECONDS = 60.0

# Archivos que debe contener el directorio de un modelo faster-whisper.
_ARCHIVOS_MODELO = ('model.bin', 'config.json', 'tokenizer.json', 'vocabulary.txt')

_INSTRUCCION_DESCARGA = (
    'Descárgalo según el README: hf download Systran/faster-whisper-small '
    '--local-dir App/ai-models/faster-whisper-small'
)

_ESPACIOS = re.compile(r'\s+')


class STTError(RuntimeError):
    """El modelo STT no pudo cargar o transcribir el audio."""


class WhisperSTT:
    """Cliente local de faster-whisper para pasar voz a texto.

    Se instancia una sola vez por proceso (`get_stt_service` en `api/deps.py`):
    el modelo `small` pesa ~480 MB y cargarlo en cada petición arruinaría la
    latencia.
    """

    def __init__(
        self,
        model_dir: str | Path | None = None,
        language: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        beam_size: int | None = None,
        cpu_threads: int | None = None,
    ) -> None:
        self._app_dir = Path(__file__).resolve().parents[2]
        crudo = str(model_dir if model_dir is not None else settings.stt_model).strip()
        self._ruta_configurada = bool(crudo)
        self._dir = self._resolver(crudo)
        self._language = str(
            language if language is not None else settings.stt_language
        ).strip()
        self._device = str(device if device is not None else settings.stt_device).strip()
        self._compute_type = str(
            compute_type if compute_type is not None else settings.stt_compute_type
        ).strip()
        self._beam_size = int(
            beam_size if beam_size is not None else settings.stt_beam_size
        )
        self._cpu_threads = int(
            cpu_threads if cpu_threads is not None else settings.stt_threads
        )

        self._modelo: 'WhisperModel | None' = None
        self._carga = threading.Lock()
        self._inferencia = threading.Lock()

    def _resolver(self, ruta: str | Path | None) -> Path:
        crudo = str(ruta or '').strip()
        if not crudo:
            return self._app_dir
        camino = Path(crudo).expanduser()
        return camino if camino.is_absolute() else self._app_dir / camino

    @property
    def configured(self) -> bool:
        """True si el directorio del modelo está completo en disco."""
        return self._ruta_configurada and all(
            (self._dir / archivo).is_file() for archivo in _ARCHIVOS_MODELO
        )

    @property
    def language(self) -> str | None:
        """Idioma forzado, o `None` para detección automática."""
        return None if self._language.lower() in ('', 'auto', 'none') else self._language

    def precargar(self) -> bool:
        """Carga el modelo en el hilo actual; `True` si quedó listo.

        Se llama desde el hilo de calentamiento del lifespan. No propaga el
        error: un STT no disponible no debe impedir que arranque la API (RNF6).
        """
        try:
            self._cargar()
        except Exception as exc:  # noqa: BLE001 - la API debe arrancar igual
            print(f'[stt] precarga omitida: {exc}', flush=True)
            return False
        print(
            f'[stt] modelo listo: {self._dir.name} '
            f'(idioma {self.language or "auto"}, {self._compute_type})',
            flush=True,
        )
        return True

    async def transcribir(self, audio: np.ndarray) -> str:
        """Transcribe un array mono float32 a 16 kHz."""
        return await asyncio.to_thread(self.transcribir_sync, audio)

    async def transcribir_bytes(self, data: bytes) -> str:
        """Decodifica `data` (WAV/WebM/OGG/MP3…) y lo transcribe."""
        return await asyncio.to_thread(self._transcribir_bytes_sync, data)

    def _transcribir_bytes_sync(self, data: bytes) -> str:
        audio = self.decodificar(data)
        return self.transcribir_sync(audio)

    def transcribir_sync(self, audio: np.ndarray) -> str:
        """Versión síncrona de `transcribir` (usada por el hilo de trabajo)."""
        if audio is None or audio.size == 0:
            raise STTError('El audio de la pregunta está vacío.')

        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        if audio.size > int(MAX_AUDIO_SECONDS * SAMPLE_RATE):
            audio = audio[: int(MAX_AUDIO_SECONDS * SAMPLE_RATE)]

        modelo = self._cargar()
        # El modelo no es seguro para transcribir en paralelo: se serializa.
        with self._inferencia:
            segmentos, _info = modelo.transcribe(
                audio,
                language=self.language,
                beam_size=max(1, self._beam_size),
                vad_filter=True,
                vad_parameters={'min_silence_duration_ms': 500},
                condition_on_previous_text=False,
                word_timestamps=False,
            )
            texto = ' '.join(segmento.text.strip() for segmento in segmentos)

        texto = _ESPACIOS.sub(' ', texto).strip()
        if not texto:
            raise STTError(
                'No se entendió ninguna palabra en el audio. Habla más cerca '
                'del micrófono o revisa el nivel de entrada.'
            )
        return texto

    def decodificar(self, data: bytes) -> np.ndarray:
        """Convierte bytes de audio en mono float32 a 16 kHz.

        Primero intenta `soundfile` (rápido y sin procesos); si el contenedor
        no es compatible (p. ej. WebM de MediaRecorder), delega en `ffmpeg`.
        """
        if not data:
            raise STTError('No llegó audio en la petición de voz.')

        audio, samplerate = self._leer_con_soundfile(data)
        if audio is None:
            audio, samplerate = self._leer_con_ffmpeg(data)

        if audio.size == 0:
            raise STTError('El audio decodificado no contiene muestras.')
        return self._remuestrear(audio, samplerate)

    @staticmethod
    def _leer_con_soundfile(data: bytes) -> tuple[np.ndarray | None, int]:
        try:
            import soundfile as sf

            audio, samplerate = sf.read(
                io.BytesIO(data), dtype='float32', always_2d=True
            )
        except Exception:  # formato no soportado por libsndfile
            return None, 0
        if audio.size == 0:
            return None, 0
        return audio.mean(axis=1).astype(np.float32), int(samplerate)

    @staticmethod
    def _leer_con_ffmpeg(data: bytes) -> tuple[np.ndarray, int]:
        comando = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel',
            'error',
            '-i',
            'pipe:0',
            '-vn',
            '-ac',
            '1',
            '-ar',
            str(SAMPLE_RATE),
            '-t',
            str(MAX_AUDIO_SECONDS),
            '-f',
            'f32le',
            'pipe:1',
        ]
        try:
            proceso = subprocess.run(
                comando,
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except FileNotFoundError as exc:
            raise STTError(
                'No pude decodificar el audio: falta ffmpeg. Instálalo con '
                '`sudo apt install ffmpeg` (Linux) o usa un WAV.'
            ) from exc

        if proceso.returncode != 0:
            detalle = proceso.stderr.decode('utf-8', errors='replace').strip()
            raise STTError(
                'No pude decodificar el audio de la pregunta. Envía un WAV, '
                f'OGG o WebM válido. Detalle de ffmpeg: {detalle[-300:]}'
            )
        audio = np.frombuffer(proceso.stdout, dtype='<f4').astype(np.float32)
        return audio, SAMPLE_RATE

    @staticmethod
    def _remuestrear(audio: np.ndarray, samplerate: int) -> np.ndarray:
        """Convierte a mono 16 kHz con interpolación lineal (suficiente para STT)."""
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        if samplerate == SAMPLE_RATE or audio.size == 0:
            return audio

        duracion = audio.size / samplerate
        objetivo = max(1, int(duracion * SAMPLE_RATE))
        return np.interp(
            np.linspace(0.0, duracion, objetivo, endpoint=False),
            np.linspace(0.0, duracion, audio.size, endpoint=False),
            audio,
        ).astype(np.float32)

    def _cargar(self) -> 'WhisperModel':
        """Carga perezosa con doble chequeo del modelo faster-whisper."""
        if self._modelo is not None:
            return self._modelo

        with self._carga:
            if self._modelo is not None:
                return self._modelo

            if not self._ruta_configurada:
                raise STTError(
                    'STT sin configurar: define STT_MODEL en .env '
                    '(p. ej. ai-models/faster-whisper-small).'
                )
            faltantes = [
                archivo
                for archivo in _ARCHIVOS_MODELO
                if not (self._dir / archivo).is_file()
            ]
            if faltantes:
                raise STTError(
                    f'El modelo STT de {self._dir} está incompleto (faltan '
                    f'{", ".join(faltantes)}). ' + _INSTRUCCION_DESCARGA
                )

            from faster_whisper import WhisperModel

            try:
                modelo = WhisperModel(
                    str(self._dir),
                    device=self._device,
                    compute_type=self._compute_type,
                    cpu_threads=self._cpu_threads,
                    local_files_only=True,
                )
            except Exception as exc:
                raise STTError(
                    f'No se pudo cargar el modelo STT de {self._dir}: {exc}'
                ) from exc

            self._modelo = modelo
            return modelo
