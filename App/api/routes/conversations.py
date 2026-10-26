"""Rutas de conversaciones.

Conectan la API con las entidades de dominio `Conversacion` y `Mensaje`
(`domain/models/conversacion.py`, `domain/models/mensaje.py`) y con las tablas
`conversacion` y `mensaje` de PostgreSQL. El servidor es dueño del `id` y de
las fechas (siempre en UTC); el cliente solo indica a qué usuario pertenece la
conversación. Los mensajes se publican desde `api/routes/queries.py` (flujo
*Ask with PNL*) y aquí solo se leen como historial de la conversación.
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, HTTPException, Path, Query, status
from psycopg.errors import ForeignKeyViolation

from api.deps import ConversacionRepositoryDep, MensajeRepositoryDep
from domain.models.conversacion import Conversacion
from domain.models.mensaje import Mensaje

router = APIRouter(prefix='/v1/models/conversations', tags=['conversations'])


@router.get(
    '/',
    response_model=list[Conversacion],
    summary='Listar conversaciones',
    description=(
        'Devuelve las conversaciones del usuario indicado, de la más reciente a la más '
        'antigua. `usuario_id` es obligatorio.'
    ),
    responses={
        422: {'description': 'Falta `usuario_id` o no es un UUID válido'},
    },
)
async def list_conversations(
    repo: ConversacionRepositoryDep,
    usuario_id: Annotated[
        UUID,
        Query(description='Identificador del usuario dueño de las conversaciones'),
    ],
) -> list[Conversacion]:
    return await repo.list(usuario_id)


@router.post(
    '/',
    response_model=Conversacion,
    status_code=status.HTTP_201_CREATED,
    summary='Crear una conversación',
    description=(
        'Crea una conversación para un usuario. '
        'El `id` y la `fecha_creacion` los asigna el servidor en UTC: '
        'los que vengan en el cuerpo se ignoran.'
    ),
    responses={
        404: {'description': 'No existe el usuario indicado'},
    },
)
async def create_conversation(
    repo: ConversacionRepositoryDep,
    payload: Annotated[
        Conversacion,
        Body(
            openapi_examples={
                'valida': {
                    'summary': 'Creación válida',
                    'value': {'usuario_id': '00000000-0000-4000-8000-000000000001'},
                }
            }
        ),
    ],
) -> Conversacion:
    conversacion = Conversacion(
        id=uuid4(),
        usuario_id=payload.usuario_id,
        fecha_creacion=datetime.now(timezone.utc),
    )
    try:
        return await repo.create(conversacion)
    except ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe un usuario con el id {payload.usuario_id}',
        ) from exc


@router.get(
    '/{conversacion_id}',
    response_model=Conversacion,
    summary='Obtener una conversación',
    description='Devuelve la conversación con el identificador indicado.',
    responses={
        404: {'description': 'No existe una conversación con ese identificador'},
        422: {'description': 'El identificador no es un UUID válido'},
    },
)
async def get_conversation(
    repo: ConversacionRepositoryDep,
    conversacion_id: Annotated[
        UUID,
        Path(description='Identificador de la conversación'),
    ],
) -> Conversacion:
    conversacion = await repo.get(conversacion_id)
    if conversacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe una conversación con el id {conversacion_id}',
        )
    return conversacion


@router.get(
    '/{conversacion_id}/messages',
    response_model=list[Mensaje],
    summary='Obtener los mensajes de una conversación',
    description=(
        'Devuelve el historial de mensajes de la conversación, del más antiguo al más '
        'reciente. Si la conversación todavía no tiene mensajes, devuelve una lista vacía.'
    ),
    responses={
        404: {'description': 'No existe una conversación con ese identificador'},
        422: {'description': 'El identificador no es un UUID válido'},
    },
)
async def list_messages(
    conversaciones: ConversacionRepositoryDep,
    mensajes: MensajeRepositoryDep,
    conversacion_id: Annotated[
        UUID,
        Path(description='Identificador de la conversación'),
    ],
) -> list[Mensaje]:
    if await conversaciones.get(conversacion_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe una conversación con el id {conversacion_id}',
        )
    return await mensajes.list(conversacion_id)
