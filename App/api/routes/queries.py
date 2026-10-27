"""Rutas de consultas al asistente.

Inicio de la secuencia *Ask with PNL*
(`Docs/UML/imagenes/DIA-SECUENCIA_Ask-With-PNL.png`): el usuario publica su
mensaje en la conversación (`POST /messages`). El historial de una conversación
se lee en `GET /v1/models/conversations/{conversacion_id}/messages`. Los pasos
siguientes del flujo RAG (embeddings, recuperación y respuesta con fuentes) se
construirán sobre esta base.
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import Field

from api.deps import ConversacionRepositoryDep, MensajeRepositoryDep
from domain.models.base import ModeloBase
from domain.models.mensaje import MAX_LONGITUD_CONSULTA, Mensaje

router = APIRouter(prefix='/v1/queries', tags=['queries'])


class PublicarMensajePeticion(ModeloBase):
    """Cuerpo de la petición para publicar un mensaje del usuario.

    El `id` y la `fecha` del mensaje los asigna el servidor en UTC y el `rol` es
    siempre `usuario`; `usuario_id` no se guarda en el mensaje, solo sirve para
    comprobar que la conversación pertenece a quien publica. El `contenido` es la
    consulta del usuario (RF5) y se acota a `MAX_LONGITUD_CONSULTA` caracteres,
    el mismo límite que el campo de texto del chat en el frontend.
    """

    usuario_id: UUID = Field(description='Usuario que publica el mensaje')
    conversacion_id: UUID = Field(description='Conversación donde se publica el mensaje')
    contenido: str = Field(
        min_length=1,
        max_length=MAX_LONGITUD_CONSULTA,
        description=f'Texto del mensaje (máximo {MAX_LONGITUD_CONSULTA} caracteres)',
    )


@router.post(
    '/messages',
    response_model=Mensaje,
    status_code=status.HTTP_201_CREATED,
    summary='Publicar un mensaje',
    description=(
        'Publica un mensaje del usuario en una conversación (primer paso de la '
        'secuencia Ask with PNL). La conversación debe existir y pertenecer a '
        '`usuario_id`. El `id` y la `fecha` los asigna el servidor en UTC y el '
        '`rol` es siempre `usuario`: los que vengan en el cuerpo se ignoran.'
    ),
    responses={
        403: {'description': 'La conversación no pertenece al usuario indicado'},
        404: {'description': 'No existe una conversación con ese identificador'},
        422: {'description': 'Los identificadores o el mensaje no son válidos'},
    },
)
async def publish_message(
    conversaciones: ConversacionRepositoryDep,
    mensajes: MensajeRepositoryDep,
    payload: Annotated[
        PublicarMensajePeticion,
        Body(
            openapi_examples={
                'valido': {
                    'summary': 'Mensaje válido',
                    'value': {
                        'usuario_id': '00000000-0000-4000-8000-000000000001',
                        'conversacion_id': '00000000-0000-4000-8000-000000000002',
                        'contenido': '¿Cuántos días de vacaciones me corresponden?',
                    },
                }
            }
        ),
    ],
) -> Mensaje:
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

    mensaje = Mensaje(
        id=uuid4(),
        conversacion_id=payload.conversacion_id,
        rol='usuario',
        contenido=payload.contenido,
        fecha=datetime.now(timezone.utc),
    )
    return await mensajes.create(mensaje)
