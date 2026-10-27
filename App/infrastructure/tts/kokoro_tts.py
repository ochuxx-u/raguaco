"""Motor TTS local: Kokoro-82M sobre ONNX, sin servicios externos.

La carga de los pesos es **perezosa** (la API arranca aunque el modelo no esté
descargado) y se hace una sola vez por proceso: `KokoroTTS` se comparte entre
peticiones desde `api/deps.py`. La inferencia corre en un hilo de trabajo
(`asyncio.to_thread`) para no bloquear el loop de eventos.

Kokoro acepta como máximo `MAX_FONEMAS` fonemas por inferencia, así que un
fragmento de texto que los supere se parte en sub-trozos y se concatenan con
una pausa breve. Los fragmentos normales (los que produce
`infrastructure.tts.tts_text`) quedan muy por debajo del límite.

La fonemización usa espeak-ng (vía `kokoro_onnx.tokenizer.Tokenizer`), que
mantiene estado global: se serializa con un lock. La sesión ONNX sí es segura
para usarse desde varios hilos.
"""

import asyncio
import re
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from core.config import settings

if TYPE_CHECKING:
    import onnxruntime as rt
    from kokoro_onnx.tokenizer import Tokenizer

# Kokoro genera audio mono a 24 kHz.
SAMPLE_RATE = 24_000

# Contexto máximo del modelo: 510 fonemas + tokens de padding.
MAX_FONEMAS = 510

# Silencio entre sub-trozos cuando un fragmento supera MAX_FONEMAS.
PAUSA_TROZOS_SEGUNDOS = 0.05

# Nombres de voz válidos (`ef_dora`, `em_alex`, ...): evita rutas hostiles.
_VOZ_VALIDA = re.compile(r'^[A-Za-z0-9_-]+$')

_INSTRUCCION_DESCARGA = (
    'Descárgalo según el README: hf download onnx-community/Kokoro-82M-v1.0-ONNX '
    '--local-dir App/ai-models/kokoro-82m'
)


class TTSError(RuntimeError):
    """El motor TTS no pudo cargar o sintetizar el texto."""


class KokoroTTS:
    """Cliente del modelo Kokoro-82M para convertir texto en audio.

    Se instancia una sola vez por proceso (ver `get_tts_engine` en
    `api/deps.py`): los pesos ONNX pesan cientos de MB y la carga tarda
    ~0,7 s en la variante cuantizada.
    """

    def __init__(
        self,
        model_dir: str | Path | None = None,
        model_file: str | None = None,
        voice: str | None = None,
        language: str | None = None,
        speed: float | None = None,
    ) -> None:
        # `App/` es la raíz de ejecución; resolver contra el paquete ancla las
        # rutas relativas sin depender del cwd (igual que EmbeddingService).
        self._app_dir = Path(__file__).resolve().parents[2]
        crudo = str(model_dir if model_dir is not None else settings.tts_model).strip()
        self._ruta_configurada = bool(crudo)
        self._dir = self._resolver(crudo)
        self._model_file = str(
            model_file if model_file is not None else settings.tts_model_file
        ).strip()
        self._voz = str(voice if voice is not None else settings.tts_voice).strip()
        self._language = str(
            language if language is not None else settings.tts_language
        ).strip()
        self._speed = float(speed if speed is not None else settings.tts_speed)

        self._sesion: 'rt.InferenceSession | None' = None
        self._tokenizador: 'Tokenizer | None' = None
        self._voces: np.ndarray | None = None

        self._carga = threading.Lock()
        self._espeak = threading.Lock()

    def _resolver(self, ruta: str | Path | None) -> Path:
        crudo = str(ruta or '').strip()
        if not crudo:
            return self._app_dir
        camino = Path(crudo).expanduser()
        return camino if camino.is_absolute() else self._app_dir / camino

    @property
    def configured(self) -> bool:
        """True si el modelo y la voz configurados existen en disco.

        Es una comprobación barata (sin cargar los pesos) para que la ruta
        pueda responder 503 en lugar de abrir un stream condenado a fallar
        (RNF6).
        """
        return (
            self._ruta_configurada
            and self._ruta_modelo().is_file()
            and self._ruta_voz().is_file()
        )

    @property
    def sample_rate(self) -> int:
        """Frecuencia de muestreo del audio generado (24 kHz)."""
        return SAMPLE_RATE

    @property
    def voice(self) -> str:
        """Nombre de la voz cargada (p. ej. `ef_dora`)."""
        return self._voz

    def _ruta_modelo(self) -> Path:
        # `TTS_MODEL_FILE` es relativo al directorio del modelo
        # (`onnx/model_quantized.onnx` por defecto).
        return self._dir / self._model_file

    def _ruta_voz(self) -> Path:
        return self._dir / 'voices' / f'{self._voz}.bin'

    def precargar(self) -> bool:
        """Carga los pesos en el hilo actual; `True` si quedaron listos.

        Se llama desde el hilo de calentamiento del lifespan. No propaga el
        error: un TTS no disponible no debe impedir que arranque la API
        (RNF6); la ruta responderá 503 cuando se use.
        """
        try:
            self._cargar()
            # Una inferencia corta de calentamiento: reserva los buffers de
            # ONNX y comprueba espeak-ng antes de la primera petición real.
            self.sintetizar_sync('Hola.')
        except Exception as exc:  # noqa: BLE001 - la API debe arrancar igual
            print(f'[tts] precarga omitida: {exc}', flush=True)
            return False
        print(
            f'[tts] modelo listo: {self._ruta_modelo().name} '
            f'(voz {self._voz}, {self._language})',
            flush=True,
        )
        return True

    async def sintetizar(self, texto: str) -> np.ndarray:
        """Convierte `texto` en audio mono float32 a 24 kHz.

        La inferencia es intensiva en CPU y va en un hilo aparte para no
        bloquear el loop de eventos mientras se sirven otras peticiones.
        """
        return await asyncio.to_thread(self.sintetizar_sync, texto)

    def sintetizar_sync(self, texto: str) -> np.ndarray:
        """Versión síncrona de `sintetizar` (usada por el hilo de trabajo)."""
        if not texto or not texto.strip():
            return np.zeros(0, dtype=np.float32)

        sesion, tokenizador, voces = self._cargar()

        # espeak-ng mantiene estado global: una fonemización a la vez.
        with self._espeak:
            try:
                fonemas = tokenizador.phonemize(texto, self._language)
            except Exception as exc:  # espeak-ng puede fallar por la voz/idioma
                raise TTSError(
                    f'No se pudo fonemizar el texto con espeak-ng '
                    f'(idioma {self._language}): {exc}'
                ) from exc

        if not fonemas:
            raise TTSError(
                f'espeak-ng no produjo fonemas para el texto: {texto[:120]!r}'
            )

        piezas: list[np.ndarray] = []
        for trozo in self._trocear_fonemas(fonemas):
            tokens = tokenizador.tokenize(trozo)
            if not tokens:
                continue
            # La voz se elige por longitud: es el estilo que Kokoro espera.
            estilo = voces[min(len(tokens), len(voces) - 1)]
            salida = sesion.run(
                None,
                {
                    'input_ids': [[0, *tokens, 0]],
                    'style': estilo,
                    'speed': np.full(1, self._speed, dtype=np.float32),
                },
            )[0]
            audio = np.asarray(salida, dtype=np.float32).reshape(-1)
            if piezas:
                piezas.append(
                    np.zeros(int(SAMPLE_RATE * PAUSA_TROZOS_SEGUNDOS), dtype=np.float32)
                )
            piezas.append(audio)

        if not piezas:
            raise TTSError('Kokoro no devolvió audio para el texto recibido.')
        return np.concatenate(piezas)

    def _cargar(self) -> tuple['rt.InferenceSession', 'Tokenizer', np.ndarray]:
        """Carga perezosa con doble chequeo: los pesos se leen una sola vez."""
        if self._sesion is not None and self._tokenizador is not None and self._voces is not None:
            return self._sesion, self._tokenizador, self._voces

        with self._carga:
            if (
                self._sesion is not None
                and self._tokenizador is not None
                and self._voces is not None
            ):
                return self._sesion, self._tokenizador, self._voces

            if not self._ruta_configurada:
                raise TTSError(
                    'TTS sin configurar: define TTS_MODEL en .env '
                    '(p. ej. ai-models/kokoro-82m).'
                )
            if not _VOZ_VALIDA.match(self._voz):
                raise TTSError(
                    f'Nombre de voz inválido: {self._voz!r}. Debe ser el nombre '
                    'de un archivo .bin de `voices/` (p. ej. ef_dora).'
                )

            ruta_modelo = self._ruta_modelo()
            if not ruta_modelo.is_file():
                raise TTSError(
                    f'No encuentro el modelo ONNX en {ruta_modelo}. '
                    + _INSTRUCCION_DESCARGA
                )
            ruta_voz = self._ruta_voz()
            if not ruta_voz.is_file():
                raise TTSError(
                    f'No encuentro la voz {self._voz!r} en {ruta_voz}. '
                    'Revisa TTS_VOICE o vuelve a descargar el modelo. '
                    + _INSTRUCCION_DESCARGA
                )

            import onnxruntime as rt
            from kokoro_onnx.tokenizer import Tokenizer

            # Primero el tokenizador: es rápido y detecta la falta de
            # espeak-ng antes de abrir cientos de MB de pesos.
            try:
                tokenizador = Tokenizer()
            except Exception as exc:
                raise TTSError(
                    'No se pudo iniciar espeak-ng (lo usa Kokoro para la '
                    'fonética en español). Instálalo con '
                    '`sudo apt install espeak-ng` (Linux) y reintenta. '
                    f'Detalle: {exc}'
                ) from exc

            try:
                voces = np.fromfile(ruta_voz, dtype=np.float32).reshape(-1, 1, 256)
            except Exception as exc:
                raise TTSError(f'No se pudo leer la voz {ruta_voz}: {exc}') from exc
            if voces.size == 0:
                raise TTSError(f'La voz {ruta_voz} está vacía o incompleta.')

            try:
                sesion = rt.InferenceSession(
                    str(ruta_modelo), providers=['CPUExecutionProvider']
                )
            except Exception as exc:
                raise TTSError(
                    f'No se pudo cargar el modelo ONNX {ruta_modelo}: {exc}'
                ) from exc

            self._tokenizador = tokenizador
            self._voces = voces
            self._sesion = sesion
            return sesion, tokenizador, voces

    @staticmethod
    def _trocear_fonemas(fonemas: str) -> list[str]:
        """Parte la cadena de fonemas en trozos de hasta `MAX_FONEMAS`.

        Se corta por espacios (límites entre palabras) y, si una palabra
        aislada supera el límite, se corta a la fuerza.
        """
        if len(fonemas) <= MAX_FONEMAS:
            return [fonemas]

        trozos: list[str] = []
        actual = ''
        for palabra in fonemas.split(' '):
            while len(palabra) > MAX_FONEMAS:
                if actual:
                    trozos.append(actual)
                    actual = ''
                trozos.append(palabra[:MAX_FONEMAS])
                palabra = palabra[MAX_FONEMAS:]
            candidato = f'{actual} {palabra}'.strip()
            if len(candidato) <= MAX_FONEMAS:
                actual = candidato
            else:
                if actual:
                    trozos.append(actual)
                actual = palabra
        if actual:
            trozos.append(actual)
        return trozos
