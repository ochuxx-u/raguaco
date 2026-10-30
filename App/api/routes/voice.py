"""Rutas del servicio de voz (RF12).

Implementa la secuencia completa del diagrama
(`Docs/UML/imagenes/DIA-SECUENCIA_Voice-Interact.png`):

- `POST /v1/voice/consultar`: audio → STT → RAG → TTS. Responde NDJSON con
  `procesando`, `transcripcion`, `respuesta` (texto + fuentes) y los eventos
  de audio (`inicio`, `fragmento`, `fin`). El cliente cierra la grabación al
  detectar silencio (o usa `DetectorVoz`); la API procesa el audio completo.
- `POST /v1/voice/tts`: solo texto → audio, para el chat o pruebas.
- `GET /v1/voice/tts/{job_id}/{nombre}`: sirve cada WAV generado.

El TTS se entrega por fragmentos para que el cliente pueda reproducir el
primero mientras el servidor sintetiza el siguiente (optimización de latencia).
"""

import json
import time
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from psycopg.errors import ForeignKeyViolation
from pydantic import Field

from api.deps import (
    DocumentoRepositoryDep,
    VoiceFlowServiceDep,
    VoiceServiceDep,
)
from api.routes.queries import FiltrosBusqueda, _validar_documentos_filtrados
from domain.models.base import ModeloBase
from domain.services.voice_service import (
    ConversacionAjena,
    ConversacionNoEncontrada,
    SinTranscripcion,
    VozError,
)
from infrastructure.embeddings.embedding_service import EmbeddingError
from infrastructure.llm.llm_service import LLMError
from infrastructure.stt.whisper_stt import STTError
from infrastructure.tts.kokoro_tts import TTSError

router = APIRouter(prefix='/v1/voice', tags=['voice'])

# Tope de entrada: una respuesta RAG se recorta a 1000 caracteres, pero el
# endpoint también se usa para probar textos más largos.
MAX_TEXTO_TTS = 5000

# Tope del audio subido (un minuto de WAV 16 kHz mono ronda 2 MB).
MAX_AUDIO_BYTES = 25 * 1024 * 1024


class TextoVozPeticion(ModeloBase):
    """Cuerpo de la síntesis: solo el texto que se debe pronunciar."""

    texto: str = Field(
        min_length=1,
        max_length=MAX_TEXTO_TTS,
        description=(
            'Texto a narrar. Puede venir con Markdown o citas [n]: se limpian '
            'antes de fonemizar.'
        ),
    )


def _linea(evento: dict) -> str:
    """Serializa un evento NDJSON conservando los acentos y saltos de línea."""
    return json.dumps(evento, ensure_ascii=False) + '\n'


@router.get('/')
async def voice():
    """Información básica del servicio de voz."""
    return {
        'message': 'Servicio de voz de Raguaco',
        'tts': '/v1/voice/tts',
    }


@router.post(
    '/tts',
    response_class=StreamingResponse,
    summary='Sintetizar texto a voz por fragmentos',
    description=(
        'Limpia el texto (Markdown, citas [n], emojis; las URLs se sustituyen '
        'por «el enlace»), lo parte en frases y sintetiza cada una como un WAV '
        'independiente. Responde NDJSON: el evento `fragmento` trae la URL del '
        'WAV en cuanto está listo, de modo que el cliente puede empezar a '
        'reproducir sin esperar a que termine toda la síntesis. El primer '
        'fragmento es más corto para reducir la latencia percibida.'
    ),
    responses={
        200: {
            'description': 'Stream NDJSON de eventos de síntesis',
            'content': {
                'application/x-ndjson': {
                    'example': (
                        '{"tipo":"inicio","job_id":"...","total_fragmentos":2,...}\n'
                        '{"tipo":"fragmento","indice":0,"nombre":"000.wav",...}\n'
                        '{"tipo":"fin","duracion_total":7.4,...}\n'
                    )
                }
            },
        },
        422: {'description': 'El texto está vacío o no tiene contenido pronunciable'},
        503: {'description': 'El modelo TTS o espeak-ng no están disponibles'},
    },
)
async def text_to_speech(
    request: Request,
    voz: VoiceServiceDep,
    payload: Annotated[
        TextoVozPeticion,
        Body(
            openapi_examples={
                'corta': {
                    'summary': 'Texto de prueba',
                    'value': {
                        'texto': (
                            'Raguaco responde con fuentes verificables. '
                            'Si no encuentra evidencia, lo dice explícitamente [1].'
                        )
                    },
                }
            }
        ),
    ],
) -> StreamingResponse:
    # RNF6: sin modelo no se abre un stream condenado a fallar.
    if not voz.disponible:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                'El TTS no está disponible: falta el modelo Kokoro o la voz en '
                'App/ai-models/kokoro-82m. Descárgalo según el README '
                '(hf download onnx-community/Kokoro-82M-v1.0-ONNX).'
            ),
        )

    try:
        plan = voz.preparar(payload.texto)
    except TTSError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    async def eventos():
        """Genera el NDJSON a medida que cada WAV queda en disco."""
        inicio = time.perf_counter()
        primera_ms: int | None = None
        duracion_total = 0.0
        try:
            yield _linea(
                {
                    'tipo': 'inicio',
                    'job_id': plan.job_id,
                    'total_fragmentos': len(plan.fragmentos),
                    'texto': plan.texto,
                    'fragmentos': plan.fragmentos,
                }
            )
            async for fragmento in voz.sintetizar(plan):
                if primera_ms is None:
                    primera_ms = fragmento.ms_desde_inicio
                duracion_total += fragmento.duracion
                url = str(
                    request.url_for(
                        'tts_fragmento',
                        job_id=plan.job_id,
                        nombre=fragmento.nombre,
                    )
                )
                yield _linea(
                    {
                        'tipo': 'fragmento',
                        **fragmento.model_dump(),
                        'url': url,
                    }
                )
            yield _linea(
                {
                    'tipo': 'fin',
                    'job_id': plan.job_id,
                    'total_fragmentos': len(plan.fragmentos),
                    'duracion_total': round(duracion_total, 3),
                    'ms_primera': primera_ms,
                    'ms_total': int(round((time.perf_counter() - inicio) * 1000)),
                }
            )
        except TTSError as exc:
            # El stream ya empezó (200): el error viaja como evento.
            print(f'[tts] error al sintetizar: {exc}', flush=True)
            yield _linea({'tipo': 'error', 'detalle': str(exc)})
        except Exception as exc:  # noqa: BLE001 - el stream no puede cambiar de estado
            print(f'[tts] error inesperado al sintetizar: {exc}', flush=True)
            yield _linea(
                {
                    'tipo': 'error',
                    'detalle': f'Error inesperado en el servicio de voz: {exc}',
                }
            )

    return StreamingResponse(
        eventos(),
        media_type='application/x-ndjson',
        headers={
            'Cache-Control': 'no-store',
            # Evita que un proxy (nginx) acumule el stream completo.
            'X-Accel-Buffering': 'no',
        },
    )


@router.post(
    '/consultar',
    response_class=StreamingResponse,
    summary='Preguntar por voz (STT → RAG → TTS)',
    description=(
        'Recibe el audio de una pregunta, lo transcribe con faster-whisper, '
        'consulta el RAG con el texto y devuelve la respuesta con sus fuentes '
        'y el audio por fragmentos. El cliente puede cerrar la grabación al '
        'detectar silencio (o usar `DetectorVoz`); la API procesa el audio '
        'completo y responde NDJSON con los eventos: `procesando`, '
        '`transcripcion`, `respuesta`, `inicio`, `fragmento`, `fin`. Si no hay '
        'evidencia documental, la respuesta es el rechazo explícito de RF9 y '
        '`referencias` viene vacío. `documento_ids` restringe la recuperación '
        'a esos documentos, igual que `filtros.documento_ids` en '
        '`POST /v1/queries/`; si se omite, se busca en todos los documentos del '
        'usuario. Para preguntas escritas usa `POST /v1/queries/`.'
    ),
    responses={
        200: {
            'description': 'Stream NDJSON con la transcripción, la respuesta y sus WAV',
            'content': {'application/x-ndjson': {}},
        },
        403: {'description': 'La conversación o algún documento no pertenecen al usuario'},
        404: {'description': 'No existe la conversación o algún documento indicado'},
        413: {'description': 'El audio supera el tamaño máximo'},
        422: {'description': 'Audio vacío o pregunta sin texto reconocible'},
        503: {'description': 'STT, TTS o modelos locales no disponibles'},
    },
)
async def consultar_voz(
    request: Request,
    voz: VoiceFlowServiceDep,
    documentos: DocumentoRepositoryDep,
    audio: Annotated[
        UploadFile,
        File(description='Audio de la pregunta (WAV, OGG, WebM, MP3…)'),
    ],
    usuario_id: Annotated[UUID, Form(description='Usuario que hace la pregunta')],
    conversacion_id: Annotated[
        UUID | None,
        Form(description='Conversación existente; si se omite, se crea una nueva'),
    ] = None,
    documento_ids: Annotated[
        list[UUID] | None,
        Form(
            description=(
                'Documentos concretos en los que buscar; si se omite, todos '
                'los del usuario'
            )
        ),
    ] = None,
) -> StreamingResponse:
    # RNF6: sin modelos no se abre un stream condenado a fallar.
    if not voz.puede_consultar:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='El flujo de voz no tiene STT/RAG configurados.',
        )
    if not voz.disponible_stt:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                'El STT no está disponible: falta el modelo faster-whisper en '
                'App/ai-models/faster-whisper-small. Descárgalo según el README.'
            ),
        )
    if not voz.disponible:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                'El TTS no está disponible: falta el modelo Kokoro o la voz en '
                'App/ai-models/kokoro-82m.'
            ),
        )

    filtros = None
    if documento_ids:
        # Mismo filtro que POST /v1/queries/: se valida antes de abrir el
        # stream para responder 404/403 sin empezar a transcribir.
        filtros = FiltrosBusqueda(documento_ids=list(dict.fromkeys(documento_ids)))
        await _validar_documentos_filtrados(
            documentos,
            filtros.documento_ids,
            usuario_id,
        )
    opciones = (
        {'filtros': filtros.model_dump(exclude_none=True)} if filtros else None
    )

    try:
        await voz.validar_conversacion(usuario_id, conversacion_id)
    except ConversacionNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConversacionAjena as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    data = await audio.read()
    await audio.close()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='El archivo de audio está vacío.',
        )
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f'El audio supera el máximo de '
                f'{MAX_AUDIO_BYTES // (1024 * 1024)} MB.'
            ),
        )

    async def eventos():
        """Transcribe, consulta el RAG y transmite el audio de la respuesta."""
        inicio = time.perf_counter()
        ms_stt: int | None = None
        ms_rag: int | None = None
        primera_ms: int | None = None
        duracion_total = 0.0

        def error(codigo: str, detalle: str) -> str:
            return _linea({'tipo': 'error', 'codigo': codigo, 'detalle': detalle})

        try:
            yield _linea({'tipo': 'procesando'})

            t0 = time.perf_counter()
            transcripcion = await voz.transcribir_audio(data)
            ms_stt = int(round((time.perf_counter() - t0) * 1000))
            yield _linea(
                {
                    'tipo': 'transcripcion',
                    'texto': transcripcion,
                    'ms_stt': ms_stt,
                }
            )

            t0 = time.perf_counter()
            resultado = await voz.procesar_texto(
                transcripcion,
                usuario_id,
                conversacion_id=conversacion_id,
                opciones=opciones,
            )
            ms_rag = int(round((time.perf_counter() - t0) * 1000))
            yield _linea(
                {
                    'tipo': 'respuesta',
                    'texto': resultado.respuesta,
                    'conversacion_id': str(resultado.conversacion_id),
                    'mensaje': resultado.mensaje.model_dump(mode='json'),
                    'referencias': [
                        referencia.model_dump(mode='json')
                        for referencia in resultado.referencias
                    ],
                    'ms_rag': ms_rag,
                }
            )

            plan = voz.preparar(resultado.respuesta)
            yield _linea(
                {
                    'tipo': 'inicio',
                    'job_id': plan.job_id,
                    'total_fragmentos': len(plan.fragmentos),
                    'texto': plan.texto,
                    'fragmentos': plan.fragmentos,
                }
            )
            async for fragmento in voz.sintetizar(plan):
                if primera_ms is None:
                    primera_ms = fragmento.ms_desde_inicio
                duracion_total += fragmento.duracion
                url = str(
                    request.url_for(
                        'tts_fragmento',
                        job_id=plan.job_id,
                        nombre=fragmento.nombre,
                    )
                )
                yield _linea(
                    {
                        'tipo': 'fragmento',
                        **fragmento.model_dump(),
                        'url': url,
                    }
                )
            ms_total = int(round((time.perf_counter() - inicio) * 1000))
            yield _linea(
                {
                    'tipo': 'fin',
                    'job_id': plan.job_id,
                    'conversacion_id': str(resultado.conversacion_id),
                    'total_fragmentos': len(plan.fragmentos),
                    'duracion_total': round(duracion_total, 3),
                    'ms_primera': primera_ms,
                    'ms_stt': ms_stt,
                    'ms_rag': ms_rag,
                    'ms_total': ms_total,
                }
            )
        except SinTranscripcion as exc:
            yield error('sin_transcripcion', str(exc))
        except STTError as exc:
            yield error('stt', str(exc))
        except (ConversacionNoEncontrada, ConversacionAjena, VozError) as exc:
            yield error('voz', str(exc))
        except EmbeddingError as exc:
            yield error('rag_no_disponible', str(exc))
        except LLMError as exc:
            yield error('llm', str(exc))
        except TTSError as exc:
            yield error('tts', str(exc))
        except ForeignKeyViolation:
            yield error(
                'usuario_no_existe',
                f'No existe un usuario con el id {usuario_id}.',
            )
        except Exception as exc:  # noqa: BLE001 - el stream no puede cambiar de estado
            print(f'[voz] error inesperado: {exc}', flush=True)
            yield error('interno', f'Error inesperado en el flujo de voz: {exc}')

    return StreamingResponse(
        eventos(),
        media_type='application/x-ndjson',
        headers={
            'Cache-Control': 'no-store',
            'X-Accel-Buffering': 'no',
        },
    )


@router.get(
    '/tts/{job_id}/{nombre}',
    name='tts_fragmento',
    response_class=FileResponse,
    summary='Descargar un fragmento WAV',
    description='Sirve uno de los WAV generados por `POST /v1/voice/tts`.',
    responses={
        200: {'description': 'Audio WAV mono a 24 kHz', 'content': {'audio/wav': {}}},
        404: {'description': 'El job o el fragmento no existen'},
    },
)
async def tts_fragmento(
    job_id: str,
    nombre: str,
    voz: VoiceServiceDep,
) -> FileResponse:
    try:
        ruta = voz.ruta_fragmento(job_id, nombre)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Fragmento de audio no encontrado',
        ) from exc
    if not ruta.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Fragmento de audio no encontrado',
        )
    return FileResponse(
        ruta,
        media_type='audio/wav',
        filename=nombre,
        content_disposition_type='inline',
        headers={'Cache-Control': 'private, max-age=600'},
    )
