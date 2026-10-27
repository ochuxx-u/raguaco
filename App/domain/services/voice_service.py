"""Servicio de voz: síntesis de texto a voz en fragmentos progresivos (RF12).

Es la mitad TTS del flujo `VoiceService` del diagrama de secuencia
(`Docs/UML/imagenes/DIA-SECUENCIA_Voice-Interact.png`): recibe una respuesta
textual y la convierte en audio *mientras se reproduce*, no después de
generarla completa.

La optimización tiene dos piezas:

1. `tts_text.segmentar_para_voz` corta el texto en frases: el primer fragmento
   es corto (latencia percibida baja) y los siguientes se mantienen acotados
   para que cada WAV esté listo antes de que termine de sonar el anterior.
2. `VoiceService.sintetizar` es un generador asíncrono: escribe cada WAV en
   `{TTS_OUTPUT_DIR}/{job_id}/{indice}.wav` y lo entrega en cuanto está listo.
   La ruta `POST /v1/voice/tts` lo serializa como NDJSON; el cliente puede
   pedir y reproducir el fragmento 0 mientras el servidor sintetiza el 1.

Los WAV se borran al preparar una síntesis nueva pasado
`TTS_RETENTION_MINUTES`; así el disco no crece sin límite.
"""

import asyncio
import re
import shutil
import time
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import numpy as np

from core.config import settings
from domain.models.base import ModeloBase
from infrastructure.tts.kokoro_tts import KokoroTTS, TTSError
from infrastructure.tts.tts_text import limpiar_para_voz, segmentar_para_voz

# Identificadores que llegan por URL: solo se aceptan los que genera el
# servicio, para que un `../` no pueda salir del directorio de audio.
_JOB_ID = re.compile(r'^[0-9a-f]{32}$')
_NOMBRE_WAV = re.compile(r'^\d{3,4}\.wav$')


class PlanVoz(ModeloBase):
    """Texto ya limpio y fragmentado, con el job donde se escribirán los WAV."""

    job_id: str
    texto: str
    fragmentos: list[str]


class FragmentoVoz(ModeloBase):
    """Un WAV terminado, listo para que el cliente lo descargue y reproduzca.

    `ms_sintesis` mide solo la inferencia; `ms_desde_inicio` incluye la espera
    desde que se preparó el plan (es la latencia real de disponibilidad).
    """

    indice: int
    nombre: str
    texto: str
    duracion: float
    muestras: int
    ms_sintesis: int
    ms_desde_inicio: int


class VoiceService:
    """Orquesta limpieza, segmentación, síntesis y entrega incremental de audio."""

    def __init__(
        self,
        tts: KokoroTTS,
        *,
        directorio: str | Path | None = None,
        retencion_minutos: int | None = None,
        primer_max: int | None = None,
        resto_max: int | None = None,
    ) -> None:
        self._tts = tts
        self._app_dir = Path(__file__).resolve().parents[2]
        crudo = str(directorio if directorio is not None else settings.tts_output_dir).strip()
        self._dir = self._resolver(crudo)
        self._retencion = int(
            retencion_minutos
            if retencion_minutos is not None
            else settings.tts_retention_minutes
        )
        self._primer_max = int(
            primer_max if primer_max is not None else settings.tts_first_chunk_chars
        )
        self._resto_max = int(
            resto_max if resto_max is not None else settings.tts_chunk_chars
        )
        if self._resto_max < self._primer_max:
            self._resto_max = self._primer_max
        self._dir.mkdir(parents=True, exist_ok=True)

    def _resolver(self, ruta: str | Path | None) -> Path:
        crudo = str(ruta or '').strip()
        if not crudo:
            return self._app_dir
        camino = Path(crudo).expanduser()
        return camino if camino.is_absolute() else self._app_dir / camino

    @property
    def disponible(self) -> bool:
        """True si el modelo TTS y la voz están descargados."""
        return self._tts.configured

    @property
    def directorio(self) -> Path:
        """Directorio raíz de los WAV generados."""
        return self._dir

    def preparar(self, texto: str) -> PlanVoz:
        """Limpia y segmenta `texto`; crea el directorio del job.

        Se llama antes de abrir el stream para poder validar la entrada y
        anunciar `total_fragmentos` en el primer evento NDJSON.
        """
        limpio = limpiar_para_voz(texto)
        if not limpio:
            raise TTSError(
                'El texto no tiene contenido pronunciable después de quitar '
                'citas, Markdown y emojis.'
            )

        fragmentos = segmentar_para_voz(
            limpio,
            primer_max=self._primer_max,
            resto_max=self._resto_max,
        )
        if not fragmentos:
            raise TTSError('No se pudo dividir el texto en fragmentos de voz.')

        self.limpiar_antiguos()
        job_id = uuid.uuid4().hex
        try:
            self.ruta_job(job_id).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TTSError(
                f'No se pudo crear el directorio de audio {self._dir}: {exc}'
            ) from exc
        return PlanVoz(job_id=job_id, texto=limpio, fragmentos=fragmentos)

    async def sintetizar(self, plan: PlanVoz) -> AsyncIterator[FragmentoVoz]:
        """Sintetiza el plan fragmento a fragmento y entrega cada WAV terminado.

        Es un generador asíncrono: quien lo consume (la ruta o el script de
        prueba) recibe el fragmento 0 en cuanto está en disco, sin esperar al
        resto. Si se cancela (cliente desconectado), deja de sintetizar.
        """
        inicio = time.perf_counter()
        job_dir = self.ruta_job(plan.job_id)

        for indice, texto in enumerate(plan.fragmentos):
            t0 = time.perf_counter()
            audio = await self._tts.sintetizar(texto)
            ms_sintesis = int(round((time.perf_counter() - t0) * 1000))

            nombre = f'{indice:03d}.wav'
            ruta = job_dir / nombre
            try:
                await asyncio.to_thread(
                    self._escribir_wav,
                    ruta,
                    audio,
                    self._tts.sample_rate,
                )
            except Exception as exc:
                raise TTSError(f'No se pudo escribir {ruta}: {exc}') from exc

            yield FragmentoVoz(
                indice=indice,
                nombre=nombre,
                texto=texto,
                duracion=round(len(audio) / self._tts.sample_rate, 3),
                muestras=int(len(audio)),
                ms_sintesis=ms_sintesis,
                ms_desde_inicio=int(round((time.perf_counter() - inicio) * 1000)),
            )

    def ruta_job(self, job_id: str) -> Path:
        """Directorio del job, validando que el id tenga el formato esperado."""
        if not _JOB_ID.match(job_id):
            raise ValueError(f'job_id inválido: {job_id!r}')
        return self._dir / job_id

    def ruta_fragmento(self, job_id: str, nombre: str) -> Path:
        """Ruta de un WAV concreto, sin permitir salir del job.

        Lanza `ValueError` si el id o el nombre no tienen el formato que genera
        este servicio (la ruta los traduce a 404).
        """
        if not _NOMBRE_WAV.match(nombre):
            raise ValueError(f'nombre de audio inválido: {nombre!r}')
        job_dir = self.ruta_job(job_id).resolve()
        ruta = (job_dir / nombre).resolve()
        if ruta.parent != job_dir:
            raise ValueError(f'ruta de audio inválida: {job_id}/{nombre}')
        return ruta

    def limpiar_antiguos(self) -> int:
        """Borra los jobs completos más viejos que la retención configurada.

        Devuelve cuántos directorios eliminó. `TTS_RETENTION_MINUTES=0`
        desactiva la limpieza.
        """
        if self._retencion <= 0:
            return 0
        limite = time.time() - self._retencion * 60
        borrados = 0
        for camino in self._dir.iterdir():
            if not camino.is_dir() or not _JOB_ID.match(camino.name):
                continue
            try:
                if camino.stat().st_mtime >= limite:
                    continue
                shutil.rmtree(camino)
                borrados += 1
            except OSError:
                # Un job que se está sirviendo puede desaparecer a mitad de
                # borrado: se ignora y se reintenta en la próxima síntesis.
                continue
        return borrados

    @staticmethod
    def _escribir_wav(ruta: Path, audio: np.ndarray, sample_rate: int) -> None:
        """Escribe PCM 16 bits (mitad de tamaño que float32, sin pérdida audible)."""
        import soundfile as sf

        sf.write(str(ruta), audio, sample_rate, subtype='PCM_16')
