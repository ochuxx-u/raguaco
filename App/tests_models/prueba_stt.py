"""Transcripción de voz local con `faster-whisper` (STT, RF12).
 
Uso rápido (micrófono, escucha continua):
 
    cd App && python tests/testing_stt.py
 
Transcripción de un archivo de audio:
 
    cd App && python tests/testing_stt.py --file mi_audio.mp3
 
El modelo se carga **en local** desde `App/ai-models/faster-whisper-<tamaño>/`

(rutas relativas a `App/`, que es la raíz de la aplicación). Si no existe, el

script indica el comando de HuggingFace para descargarlo.
 
Variables de entorno opcionales (ver `.env.example`):
 
    STT_MODEL=ai-models/faster-whisper-small

    STT_LANGUAGE=es

    STT_DEVICE=cpu

    STT_COMPUTE_TYPE=int8

"""
 
from __future__ import annotations
 
import argparse

import os

import queue

import sys

import threading

from pathlib import Path
 
import numpy as np

from faster_whisper import WhisperModel
 
APP_DIR = Path(__file__).resolve().parents[1]
 
# Lee `App/.env` (o el de la raíz del repositorio) si está disponible.

try:  # pragma: no cover - opcional

    from dotenv import load_dotenv
 
    for _candidate in (APP_DIR / '.env', APP_DIR.parent / '.env'):

        if _candidate.is_file():

            load_dotenv(_candidate)

            break

except ImportError:  # pragma: no cover - opcional

    pass
 
SAMPLE_RATE = 16_000

# Tamaño de bloque que se analiza del micrófono (detección rápida de pausas).

CHUNK_SECONDS = 0.5

# Pausa que marca el final de una frase y dispara la transcripción.

PAUSE_SECONDS = 0.8

# Frases más cortas que esto se descartan (ruidos, toses).

MIN_UTTERANCE_SECONDS = 0.35

# Tope de audio que se acumula antes de transcribir aunque no haya pausa.

MAX_UTTERANCE_SECONDS = 20.0

# Umbral de energía (RMS) por debajo del cual el bloque se considera silencio.

SILENCE_RMS = 0.004

# Tamaño de lote para transcribir archivos (no aplica al micrófono).

FILE_BATCH_SIZE = 8
 
HF_REPOS = {

    'tiny': 'Systran/faster-whisper-tiny',

    'base': 'Systran/faster-whisper-base',

    'small': 'Systran/faster-whisper-small',

    'medium': 'Systran/faster-whisper-medium',

    'large-v3': 'Systran/faster-whisper-large-v3',

    'large-v3-turbo': 'Systran/faster-whisper-large-v3-turbo',

    'distil-large-v3': 'Systran/faster-whisper-distil-large-v3',

}
 
 
def resolve_model_path(size_or_path: str) -> Path:

    """Devuelve la ruta local del modelo, o indica cómo obtenerla."""

    candidate = Path(size_or_path)

    if candidate.is_dir():

        return candidate
 
    # Las rutas relativas se resuelven contra `App/` (raíz de la aplicación).

    relative = APP_DIR / candidate

    if relative.is_dir():

        return relative
 
    model_dir = APP_DIR / 'ai-models' / f'faster-whisper-{size_or_path}'

    if model_dir.is_dir():

        return model_dir
 
    repo = HF_REPOS.get(size_or_path)

    if repo:

        print(

            f'No se encontró el modelo local en {model_dir}.\n'

            f'Descárgalo con:\n'

            f'  hf download {repo} --local-dir ai-models/faster-whisper-{size_or_path}\n',

            file=sys.stderr,

        )

    else:

        print(

            f'No se encontró el modelo local en {model_dir}.\n'

            f'Indica un tamaño válido ({", ".join(HF_REPOS)}) o una ruta local.',

            file=sys.stderr,

        )

    raise SystemExit(1)
 
 
def load_model(args: argparse.Namespace) -> WhisperModel:

    model_path = resolve_model_path(args.model)

    print(f'Cargando modelo desde {model_path} ...')

    model = WhisperModel(

        str(model_path),

        device=args.device,

        compute_type=args.compute_type,

        cpu_threads=args.threads,

    )

    print('¡Modelo cargado!')

    return model
 
 
def transcribe(

    model: WhisperModel,

    audio: np.ndarray,

    language: str | None,

    beam_size: int = 1,

    vad_filter: bool = True,

    word_timestamps: bool = False,

):

    """Transcribe un array float32 a 16 kHz.
 
    `beam_size=1` (greedy) es varias veces más rápido que el valor por

    defecto 5 y en frases cortas apenas cambia el resultado.

    """

    segments, info = model.transcribe(

        audio,

        language=language,

        beam_size=beam_size,

        vad_filter=vad_filter,

        vad_parameters={'min_silence_duration_ms': 500},

        condition_on_previous_text=False,

        word_timestamps=word_timestamps,

    )

    return segments, info
 
 
def rms(audio: np.ndarray) -> float:

    """Energía media del audio, para detectar silencio."""

    return float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0
 
 
def load_audio(path: str) -> np.ndarray:

    """Lee un archivo de audio y lo devuelve como mono float32 a 16 kHz.
 
    Se usa `soundfile` (no PyAV) para no depender de la versión de `av` que

    tenga instalada el entorno.

    """

    try:

        import soundfile as sf

    except ImportError as exc:  # pragma: no cover - depende del entorno

        raise SystemExit(

            'Falta `soundfile`. Instálalo con: pip install soundfile'

        ) from exc
 
    data, samplerate = sf.read(path, dtype='float32', always_2d=True)

    audio = data.mean(axis=1)
 
    if samplerate != SAMPLE_RATE:

        duration = audio.size / samplerate

        target = int(duration * SAMPLE_RATE)

        audio = np.interp(

            np.linspace(0.0, duration, target, endpoint=False),

            np.linspace(0.0, duration, audio.size, endpoint=False),

            audio,

        ).astype(np.float32)
 
    return audio
 
 
def transcribe_file(

    model: WhisperModel,

    path: str,

    language: str | None,

    beam_size: int = 1,

    batch_size: int = FILE_BATCH_SIZE,

) -> None:

    audio = load_audio(path)
 
    # `BatchedInferencePipeline` procesa varios fragmentos a la vez: mucho más

    # rápido en archivos largos. Si la versión instalada no lo tiene, se usa

    # la transcripción normal.

    segments = None

    info = None

    if batch_size > 1:

        try:

            from faster_whisper import BatchedInferencePipeline
 
            pipeline = BatchedInferencePipeline(model=model)

            segments, info = pipeline.transcribe(

                audio,

                language=language,

                batch_size=batch_size,

                vad_filter=True,

                vad_parameters={'min_silence_duration_ms': 500},

            )

        except (ImportError, TypeError):  # pragma: no cover - según versión

            segments = None
 
    if segments is None:

        segments, info = transcribe(model, audio, language, beam_size=beam_size)
 
    print(f"Idioma detectado: '{info.language}' (confianza: {info.language_probability:.2f})")

    print('--- Transcripción ---')

    for segment in segments:

        print(f'[{segment.start:.2f}s --> {segment.end:.2f}s] {segment.text.strip()}')
 
 
def _soundcard():

    """Importa `soundcard` con un mensaje claro si falta."""

    try:

        import soundcard as sc

    except ImportError as exc:  # pragma: no cover - depende del entorno

        raise SystemExit(

            'Falta `soundcard`. Instálalo con:\n'

            '  pip install soundcard\n'

        ) from exc

    return sc
 
 
class MicRecorder(threading.Thread):

    """Graba el micrófono en un hilo aparte.
 
    Así no se pierde audio mientras el hilo principal transcribe (antes, los

    segundos que tardaba la transcripción se quedaban sin grabar).

    """
 
    def __init__(self, sc, device_name: str | None, seconds: float) -> None:

        super().__init__(daemon=True)

        self._sc = sc

        self._device_name = device_name

        self._frames = int(SAMPLE_RATE * seconds)

        self._chunks: queue.Queue = queue.Queue()

        self._stop = threading.Event()

        self._error: Exception | None = None
 
    def run(self) -> None:

        try:

            mic = (

                self._sc.get_microphone(self._device_name)

                if self._device_name

                else self._sc.default_microphone()

            )

            with mic.recorder(samplerate=SAMPLE_RATE, channels=1) as recorder:

                while not self._stop.is_set():

                    data = recorder.record(numframes=self._frames)

                    self._chunks.put(np.squeeze(data).astype(np.float32))

        except Exception as exc:  # pragma: no cover - depende del entorno

            # Se avisa al hilo principal para que no se quede esperando audio.

            self._error = exc

            self._chunks.put(None)
 
    def read(self) -> np.ndarray:

        """Bloquea hasta que haya un trozo de audio grabado."""

        chunk = self._chunks.get()

        if chunk is None:

            raise SystemExit(

                f'No se pudo grabar del micrófono: {self._error}\n'

                'Comprueba el dispositivo con: python -m soundcard'

            )

        return chunk
 
    def stop(self) -> None:

        self._stop.set()
 
 
def listen(

    model: WhisperModel,

    language: str | None,

    device_name: str | None,

    beam_size: int = 1,

) -> None:

    """Escucha el micrófono y transcribe cada frase al terminar.
 
    Se acumula el audio mientras hay voz y, al detectar una pausa, se manda al

    modelo **una sola vez**. Antes se re-transcribía una ventana de 30 s cada

    5 s (6 veces el mismo audio) y la respuesta se atrasaba; así el costo es

    proporcional a lo que dura la frase.

    """

    print('🎤 Escuchando... habla en español (Ctrl+C para salir).\n')
 
    recorder = MicRecorder(_soundcard(), device_name, CHUNK_SECONDS)

    recorder.start()
 
    utterance = np.zeros(0, dtype=np.float32)

    silence = 0.0  # segundos seguidos de silencio al final de `utterance`
 
    def flush() -> None:

        """Transcribe lo acumulado (si es voz) y reinicia el buffer."""

        nonlocal utterance, silence

        if utterance.size / SAMPLE_RATE >= MIN_UTTERANCE_SECONDS:

            segments, _ = transcribe(

                model, utterance, language, beam_size=beam_size

            )

            text = ' '.join(s.text.strip() for s in segments).strip()

            if text:

                print(text, flush=True)

        utterance = np.zeros(0, dtype=np.float32)

        silence = 0.0
 
    try:

        while True:

            chunk = recorder.read()

            utterance = np.concatenate([utterance, chunk])

            duration = utterance.size / SAMPLE_RATE
 
            if rms(chunk) < SILENCE_RMS:

                silence += chunk.size / SAMPLE_RATE

            else:

                silence = 0.0
 
            # Pausa tras haber hablado (fin de frase), silencio prolongado sin

            # voz, o frase demasiado larga.

            if silence >= PAUSE_SECONDS or duration >= MAX_UTTERANCE_SECONDS:

                flush()

    except KeyboardInterrupt:

        flush()

        print('\n👋 Fin de la escucha.')

    finally:

        recorder.stop()
 
 
def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(description='STT local con faster-whisper')

    parser.add_argument(

        '--model',

        default=os.getenv('STT_MODEL', 'ai-models/faster-whisper-small'),

        help='Tamaño del modelo (small, base, ...) o ruta local.',

    )

    parser.add_argument(

        '--file',

        default=None,

        help='Transcribe un archivo de audio en vez de usar el micrófono.',

    )

    parser.add_argument(

        '--language',

        default=os.getenv('STT_LANGUAGE', 'es'),

        help='Idioma forzado (es). Usa "auto" para detección automática.',

    )

    parser.add_argument('--device', default=os.getenv('STT_DEVICE', 'cpu'))

    parser.add_argument('--compute-type', default=os.getenv('STT_COMPUTE_TYPE', 'int8'))

    parser.add_argument(

        '--threads',

        type=int,

        default=int(os.getenv('STT_THREADS', str(os.cpu_count() or 4))),

        help='Hilos de CPU para la inferencia (por defecto, todos los núcleos).',

    )

    parser.add_argument(

        '--beam-size',

        type=int,

        default=int(os.getenv('STT_BEAM_SIZE', '1')),

        help='1 = más rápido (greedy); 5 = más preciso y más lento.',

    )

    parser.add_argument(

        '--chunk-seconds',

        type=float,

        default=float(os.getenv('STT_CHUNK_SECONDS', str(CHUNK_SECONDS))),

        help='Bloque de audio del micrófono que se analiza en cada vuelta.',

    )

    parser.add_argument(

        '--batch-size',

        type=int,

        default=FILE_BATCH_SIZE,

        help='Lote para transcribir archivos (1 desactiva el modo por lotes).',

    )

    parser.add_argument(

        '--input-device',

        type=str,

        default=None,

        help='Nombre del dispositivo de entrada (por defecto usa el predeterminado).',

    )

    return parser.parse_args()
 
 
def main() -> None:

    global CHUNK_SECONDS
 
    args = parse_args()

    CHUNK_SECONDS = args.chunk_seconds

    language = None if args.language in ('', 'auto', 'none') else args.language

    model = load_model(args)
 
    if args.file:

        transcribe_file(

            model, args.file, language, args.beam_size, args.batch_size

        )

    else:

        listen(model, language, args.input_device, args.beam_size)
 
 
if __name__ == '__main__':

    main()
 