"""Rutas de consultas al asistente.

Secuencia *Ask with PNL*
(`Docs/UML/imagenes/DIA-SECUENCIA_Ask-With-PNL.png`):

`POST /` es el único punto de entrada: recibe el mensaje del usuario
(`{usuario_id, conversacion_id?, contenido, filtros?}`) y lo resuelve de
principio a fin.
`RAGService.responder` guarda el mensaje del usuario, recupera la evidencia de
los documentos del usuario, genera la respuesta con el LLM y guarda la respuesta
con sus fuentes; la ruta devuelve respuesta + fuentes (RF5, RF8, RF9).

El historial de una conversación se lee en
`GET /v1/models/conversations/{conversacion_id}/messages`.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, status
from psycopg.errors import ForeignKeyViolation
from pydantic import ConfigDict, Field

from api.deps import ConversacionRepositoryDep, ConversationServiceDep, RAGServiceDep
from domain.models.base import ModeloBase
from domain.models.mensaje import MAX_LONGITUD_CONSULTA
from domain.services.rag_service import RespuestaRAG
from infrastructure.embeddings.embedding_service import EmbeddingError
from infrastructure.llm.llm_service import LLMError

router = APIRouter(prefix='/v1/queries', tags=['queries'])

# Longitud máxima del título de una conversación nueva: los primeros 30
# caracteres de la pregunta (o menos si la pregunta es más corta o el corte
# cae a mitad de palabra).
MAX_LONGITUD_TITULO = 30


def _titulo_desde_pregunta(contenido: str) -> str:
    """Deriva el título de la conversación nueva a partir de la pregunta.

    Normaliza espacios y toma como máximo los primeros
    `MAX_LONGITUD_TITULO` caracteres, retrocediendo al último espacio si el
    corte cae a mitad de palabra.
    """
    texto = ' '.join(contenido.split())
    if len(texto) <= MAX_LONGITUD_TITULO:
        return texto
    corte = texto[:MAX_LONGITUD_TITULO]
    ultimo_espacio = corte.rfind(' ')
    return corte[:ultimo_espacio] if ultimo_espacio > 0 else corte


class FiltrosBusqueda(ModeloBase):
    """Filtros opcionales de la recuperación (RF6).

    Restringen la búsqueda a ciertos documentos (`documento_ids`), a una
    `categoria` del documento o a `metadatos` del fragmento (contención JSONB).
    Se combinan entre sí y todos son opcionales: sin `filtros` se busca en todos
    los documentos del usuario. El scope por usuario se aplica siempre en la
    consulta SQL, así que un id de otro usuario no devuelve nada.
    """

    # `forbid`: una clave mal escrita falla con 422 en vez de buscar sin filtro.
    model_config = ConfigDict(extra='forbid')

    documento_ids: list[UUID] | None = Field(
        default=None,
        description='Documentos concretos en los que buscar; si se omite, todos los del usuario',
    )
    categoria: str | None = Field(
        default=None,
        description='Categoría del documento (p. ej. "rrhh")',
    )
    metadatos: dict[str, Any] | None = Field(
        default=None,
        description='Metadatos del fragmento que debe contener (contención JSONB)',
    )


class ConsultaPeticion(ModeloBase):
    """Cuerpo de la consulta: el mensaje que envía el usuario (Ask with PNL).

    `conversacion_id` es opcional, como el `conversacionId?` del diagrama: sin
    él se abre una conversación nueva. `contenido` es el texto del mensaje
    (RF5) y se acota a `MAX_LONGITUD_CONSULTA`, el mismo límite que el campo de
    texto del chat en el frontend. `filtros` restringe opcionalmente la
    recuperación (documentos, categoría o metadatos del fragmento) sin salir de
    los documentos del usuario.
    """

    usuario_id: UUID = Field(description='Usuario que envía la consulta')
    contenido: str = Field(
        min_length=1,
        max_length=MAX_LONGITUD_CONSULTA,
        description=f'Texto del mensaje (máximo {MAX_LONGITUD_CONSULTA} caracteres)',
    )
    conversacion_id: UUID | None = Field(
        default=None,
        description='Conversación donde se pregunta; si se omite, se crea una nueva',
    )
    filtros: FiltrosBusqueda | None = Field(
        default=None,
        description='Restringe la búsqueda a ciertos documentos, categoría o metadatos (RF6)',
    )


@router.post(
    '/',
    response_model=RespuestaRAG,
    summary='Preguntar al asistente',
    description=(
        'Recibe el mensaje del usuario, lo guarda en la conversación y responde '
        'con fuentes documentales (RF5, RF8). Si no se indica `conversacion_id`, '
        'se crea una conversación nueva. `filtros` restringe opcionalmente la '
        'recuperación a ciertos documentos (`documento_ids`), a una `categoria` o '
        'a `metadatos` del fragmento (RF6); la búsqueda nunca sale de los '
        'documentos del usuario. Sin evidencia relevante en los documentos del '
        'usuario, el sistema se niega explícitamente, sin invocar al LLM y sin '
        'referencias (RF9).'
    ),
    responses={
        403: {'description': 'La conversación no pertenece al usuario indicado'},
        404: {'description': 'No existe la conversación o el usuario indicado'},
        422: {'description': 'Faltan datos o no son válidos'},
        502: {'description': 'El LLM no pudo generar la respuesta'},
        503: {'description': 'El modelo de embeddings no está disponible'},
    },
)
async def ask(
    rag: RAGServiceDep,
    conversaciones: ConversacionRepositoryDep,
    conversation_service: ConversationServiceDep,
    payload: Annotated[
        ConsultaPeticion,
        Body(
            openapi_examples={
                'nueva': {
                    'summary': 'Consulta en conversación nueva',
                    'value': {
                        'usuario_id': '00000000-0000-4000-8000-000000000001',
                        'contenido': '¿Cuántos días de vacaciones me corresponden?',
                    },
                },
                'existente': {
                    'summary': 'Consulta en una conversación abierta',
                    'value': {
                        'usuario_id': '00000000-0000-4000-8000-000000000001',
                        'conversacion_id': '00000000-0000-4000-8000-000000000002',
                        'contenido': '¿Y si llevo menos de un año en la empresa?',
                    },
                },
                'filtrada': {
                    'summary': 'Consulta limitada a unos documentos',
                    'value': {
                        'usuario_id': '00000000-0000-4000-8000-000000000001',
                        'conversacion_id': '00000000-0000-4000-8000-000000000002',
                        'contenido': '¿Qué dice sobre las vacaciones?',
                        'filtros': {
                            'documento_ids': ['00000000-0000-4000-8000-000000000003']
                        },
                    },
                },
            }
        ),
    ],
) -> RespuestaRAG:
    if payload.conversacion_id is not None:
        conversacion = await conversaciones.get(payload.conversacion_id)
        if conversacion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'No existe una conversación con el id {payload.conversacion_id}',
            )
        if conversacion.usuario_id != payload.usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f'La conversación {payload.conversacion_id} no pertenece '
                    f'al usuario {payload.usuario_id}'
                ),
            )
        conversacion_id = payload.conversacion_id
    else:
        # El diagrama admite `{pregunta, conversacionId?}`: sin conversación se
        # abre una nueva y `responder` deja la pregunta como su primer mensaje.
        # El título se deriva de la pregunta (primeros 30 caracteres o menos)
        # para que el campo `titulo` no quede vacío.
        try:
            conversacion = await conversation_service.crear_conversacion(
                payload.usuario_id,
                titulo=_titulo_desde_pregunta(payload.contenido),
            )
        except ForeignKeyViolation as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'No existe un usuario con el id {payload.usuario_id}',
            ) from exc
        conversacion_id = conversacion.id

    # `filtros` llega tipado; solo se envía lo que traiga valor (RF6).
    filtros = payload.filtros.model_dump(exclude_none=True) if payload.filtros is not None else None
    opciones = {'filtros': filtros} if filtros else None

    try:
        return await rag.responder(
            payload.contenido,
            conversacion_id,
            usuario_id=payload.usuario_id,
            opciones=opciones,
        )
    except EmbeddingError as exc:
        # RNF6: el fallo de un servicio se traduce a un error HTTP concreto en
        # lugar de tumbar la aplicación.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
