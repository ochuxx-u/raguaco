"""Rutas de conversaciones.

Conectan la API con la entidad de dominio `Conversacion`
(`domain/models/conversacion.py`). El servidor es dueño del `id` y de la
`fecha_creacion` (siempre en UTC); el cliente solo indica a qué usuario
pertenece la conversación.
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Path, status

from domain.models.conversacion import Conversacion

router = APIRouter(prefix='/api/v1/conversations', tags=['conversations'])

# Almacenamiento temporal en memoria para poder probar los endpoints desde /docs.
# TODO: reemplazar por ConversacionRepository (infrastructure/db/repositories)
# inyectado con Depends(get_db).
_CONVERSACIONES: dict[UUID, Conversacion] = {}


@router.get(
    '/',
    response_model=list[Conversacion],
    summary='Listar conversaciones',
    description='Devuelve todas las conversaciones registradas, de la más reciente a la más antigua.',
)
async def list_conversations() -> list[Conversacion]:
    return sorted(_CONVERSACIONES.values(), key=lambda c: c.fecha_creacion, reverse=True)


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
)
async def create_conversation(
    payload: Annotated[
        Conversacion,
        Body(
            openapi_examples={
                'valida': {
                    'summary': 'Creación válida',
                    'value': {'usuario_id': '8b1c0f4e-2a7d-4d6f-9c3b-5e8a1d2f7a10'},
                }
            }
        ),
    ],
) -> Conversacion:
    conversacion = Conversacion(
        usuario_id=payload.usuario_id,
        fecha_creacion=datetime.now(timezone.utc),
    )
    _CONVERSACIONES[conversacion.id] = conversacion
    return conversacion


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
    conversacion_id: Annotated[
        UUID,
        Path(description='Identificador de la conversación'),
    ],
) -> Conversacion:
    conversacion = _CONVERSACIONES.get(conversacion_id)
    if conversacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe una conversación con el id {conversacion_id}',
        )
    return conversacion
