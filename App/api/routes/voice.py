"""Rutas del servicio de voz (RF12).

Esta primera entrega implementa el Text-to-Speech del diagrama de secuencia
(`Docs/UML/imagenes/DIA-SECUENCIA_Voice-Interact.png`). El flujo completo
(STT → RAG → TTS) se montará encima de `POST /v1/voice/tts`, que ya devuelve
audio incremental.

`POST /v1/voice/tts` responde **NDJSON** (`application/x-ndjson`), una línea
JSON por evento:

- `inicio`: `job_id`, `total_fragmentos`, texto limpio y fragmentos.
- `fragmento`: `indice`, `texto`, `url` del WAV, `duracion` y tiempos.
- `fin`: duración total y latencias agregadas.

El cliente puede reproducir el WAV del evento `fragmento` en cuanto llega,
mientras el servidor sigue sintetizando los siguientes. Los archivos se
sirven en `GET /v1/voice/tts/{job_id}/{nombre}.wav`.

La síntesis se apoya en `VoiceService` (dominio) y `KokoroTTS`
(infraestructura); aquí solo se valida la petición y se serializa el stream.
"""

import json
import time
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import Field

from api.deps import VoiceServiceDep
from domain.models.base import ModeloBase
from infrastructure.tts.kokoro_tts import TTSError

router = APIRouter(prefix='/v1/voice', tags=['voice'])

# Tope de entrada: una respuesta RAG se recorta a 1000 caracteres, pero el
# endpoint también se usa para probar textos más largos.
MAX_TEXTO_TTS = 5000


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
