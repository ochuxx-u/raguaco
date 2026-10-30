"""Servicio de voz: secuencia completa voz → STT → RAG → TTS (RF12).

Implementa el `VoiceService` del diagrama de secuencia
(`Docs/UML/imagenes/DIA-SECUENCIA_Voice-Interact.png`):

1. `procesar_audio(audio)` transcribe la pregunta con `WhisperSTT` (STT).
2. `procesar_texto(transcripcion)` abre o valida la conversación y llama a
   `RAGService.responder` para obtener la respuesta textual con sus fuentes
   (RF5, RF8, RF9).
3. `preparar(respuesta)` + `sintetizar(plan)` convierten esa respuesta en WAV
   progresivos, para que el cliente empiece a escucharla antes de que termine
   toda la síntesis.

La detección de fin de voz (silencio) vive en
`infrastructure.stt.vad.DetectorVoz`, porque depende de cómo se captura el
audio (micrófono del navegador o del script de prueba); la API recibe el audio
ya cerrado y procesa la consulta en cuanto llega.

La optimización del TTS tiene dos piezas:

1. `tts_text.segmentar_para_voz` corta el texto en frases: el primer fragmento
   es corto (latencia percibida baja) y los siguientes se mantienen acotados
   para que cada WAV esté listo antes de que termine de sonar el anterior.
2. `VoiceService.sintetizar` es un generador asíncrono: escribe cada WAV en
   `{TTS_OUTPUT_DIR}/{job_id}/{indice}.wav` y lo entrega en cuanto está listo.
   Las rutas `POST /v1/voice/tts` y `POST /v1/voice/consultar` lo serializan
   como NDJSON; el cliente puede pedir y reproducir el fragmento 0 mientras el
   servidor sintetiza el 1.

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
from typing import TYPE_CHECKING, Any
from uuid import UUID

import numpy as np

from core.config import settings
from domain.models.base import ModeloBase
from domain.models.mensaje import MAX_LONGITUD_CONSULTA, Mensaje
from domain.models.referencia_fuente import FuenteDetalle
from infrastructure.tts.kokoro_tts import KokoroTTS, TTSError
from infrastructure.tts.tts_text import limpiar_para_voz, segmentar_para_voz

if TYPE_CHECKING:
    from domain.services.conversation_service import ConversationService
    from domain.services.rag_service import RAGService
    from infrastructure.stt.whisper_stt import WhisperSTT

# Identificadores que llegan por URL: solo se aceptan los que genera el
# servicio, para que un `../` no pueda salir del directorio de audio.
_JOB_ID = re.compile(r'^[0-9a-f]{32}$')
_NOMBRE_WAV = re.compile(r'^\d{3,4}\.wav$')

# Longitud máxima del título de una conversación creada desde voz.
MAX_TITULO = 30


def _titulo_desde_texto(texto: str) -> str:
    """Título corto de la conversación a partir de la transcripción."""
    limpio = ' '.join(texto.split())
    if len(limpio) <= MAX_TITULO:
        return limpio
    corte = limpio[:MAX_TITULO]
    ultimo_espacio = corte.rfind(' ')
    return corte[:ultimo_espacio] if ultimo_espacio > 0 else corte


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


class RespuestaVoz(ModeloBase):
    """Resultado de la secuencia voz → texto → RAG → respuesta textual.

    El audio se genera después con `preparar` + `sintetizar`; este modelo
    conserva la transcripción y la respuesta con sus fuentes (RF8, RNF7).
    """

    transcripcion: str
    respuesta: str
    conversacion_id: UUID
    mensaje: Mensaje
    referencias: list[FuenteDetalle]


class VozError(RuntimeError):
    """El flujo de voz no pudo completarse."""


class SinTranscripcion(VozError):
    """El audio no produjo texto utilizable."""


class ConversacionNoEncontrada(VozError):
    """El `conversacion_id` recibido no existe."""


class ConversacionAjena(VozError):
    """La conversación pertenece a otro usuario."""


class VoiceService:
    """Orquesta STT, RAG, segmentación y síntesis con entrega incremental."""

    def __init__(
        self,
        tts: KokoroTTS,
        *,
        stt: 'WhisperSTT | None' = None,
        rag: 'RAGService | None' = None,
        conversations: 'ConversationService | None' = None,
        directorio: str | Path | None = None,
        retencion_minutos: int | None = None,
        primer_max: int | None = None,
        resto_max: int | None = None,
    ) -> None:
        self._tts = tts
        self._stt = stt
        self._rag = rag
        self._conversations = conversations
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
    def disponible_stt(self) -> bool:
        """True si el modelo STT está descargado y el flujo puede transcribir."""
        return self._stt is not None and self._stt.configured

    @property
    def puede_consultar(self) -> bool:
        """True si STT, RAG y conversaciones están ensamblados."""
        return (
            self._stt is not None
            and self._rag is not None
            and self._conversations is not None
        )

    @property
    def directorio(self) -> Path:
        """Directorio raíz de los WAV generados."""
        return self._dir

    async def transcribir_audio(self, audio: bytes | np.ndarray) -> str:
        """Convierte el audio de la pregunta en texto (STT).

        Acepta bytes en cualquier formato que decodifique `WhisperSTT` o un
        array mono float32 a 16 kHz.
        """
        if self._stt is None:
            raise VozError(
                'El flujo de voz no tiene STT configurado (falta WhisperSTT en '
                'VoiceService).'
            )
        if isinstance(audio, (bytes, bytearray, memoryview)):
            return await self._stt.transcribir_bytes(bytes(audio))
        return await self._stt.transcribir(audio)

    async def procesar_audio(
        self,
        audio: bytes | np.ndarray,
        usuario_id: UUID,
        conversacion_id: UUID | None = None,
        *,
        opciones: dict[str, Any] | None = None,
    ) -> RespuestaVoz:
        """Secuencia completa para una pregunta hablada: STT → RAG.

        El TTS se genera después con `preparar` + `sintetizar` para poder
        entregar el audio por fragmentos (RF12). `opciones` se reenvía al RAG
        (por ejemplo, los filtros de documentos del panel de Voz).
        """
        transcripcion = await self.transcribir_audio(audio)
        return await self.procesar_texto(
            transcripcion,
            usuario_id,
            conversacion_id=conversacion_id,
            opciones=opciones,
        )

    async def procesar_texto(
        self,
        texto: str,
        usuario_id: UUID,
        conversacion_id: UUID | None = None,
        *,
        opciones: dict[str, Any] | None = None,
    ) -> RespuestaVoz:
        """Responde una consulta de voz ya transcrita (o escrita).

        Si no llega `conversacion_id`, abre una conversación nueva con las
        primeras palabras de la consulta como título. Si llega, comprueba que
        exista y sea del usuario antes de invocar al RAG (RF6). `opciones`
        mantiene el mismo contrato que `RAGService.responder` (filtros incluidos).
        """
        if self._rag is None or self._conversations is None:
            raise VozError(
                'El flujo de voz no tiene RAG o ConversationService '
                'configurados.'
            )

        consulta = ' '.join((texto or '').split())
        if not consulta:
            raise SinTranscripcion(
                'No se entendió ninguna palabra en la pregunta.'
            )
        if len(consulta) > MAX_LONGITUD_CONSULTA:
            raise VozError(
                f'La pregunta transcrita tiene {len(consulta)} caracteres y el '
                f'máximo es {MAX_LONGITUD_CONSULTA}. Intenta ser más breve.'
            )

        await self.validar_conversacion(usuario_id, conversacion_id)
        if conversacion_id is None:
            conversacion = await self._conversations.crear_conversacion(
                usuario_id,
                titulo=_titulo_desde_texto(consulta),
            )
            conversacion_id = conversacion.id

        respuesta = await self._rag.responder(
            consulta,
            conversacion_id,
            usuario_id=usuario_id,
            opciones=opciones,
        )
        return RespuestaVoz(
            transcripcion=consulta,
            respuesta=respuesta.mensaje.contenido,
            conversacion_id=conversacion_id,
            mensaje=respuesta.mensaje,
            referencias=respuesta.referencias,
        )

    async def validar_conversacion(
        self,
        usuario_id: UUID,
        conversacion_id: UUID | None,
    ) -> None:
        """Comprueba que la conversación exista y sea del usuario.

        Se puede llamar antes de abrir el stream para responder 404/403 sin
        haber empezado a generar audio.
        """
        if conversacion_id is None:
            return
        if self._conversations is None:
            raise VozError('El flujo de voz no tiene ConversationService.')
        conversacion = await self._conversations.obtener(conversacion_id)
        if conversacion is None:
            raise ConversacionNoEncontrada(
                f'No existe una conversación con el id {conversacion_id}'
            )
        if conversacion.usuario_id != usuario_id:
            raise ConversacionAjena(
                f'La conversación {conversacion_id} no pertenece '
                f'al usuario {usuario_id}'
            )

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
