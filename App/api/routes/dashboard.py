"""Rutas del resumen del Dashboard.

Agrega documentos, conversaciones y chunks del usuario para las tarjetas y la
actividad reciente de la pantalla de inicio. No es una entidad del dominio: es
una lectura de solo consulta sobre varias tablas.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import Field

from api.deps import DashboardRepositoryDep
from domain.models.base import ModeloBase

router = APIRouter(prefix='/v1/dashboard', tags=['dashboard'])


class ActividadDashboard(ModeloBase):
    """Evento reciente de un documento o una conversación."""

    id: str = Field(description='Identificador del documento o de la conversación')
    tipo: Literal['documento', 'conversacion'] = Field(description='Tipo de evento')
    titulo: str = Field(description='Nombre del documento o título de la conversación')
    estado: str | None = Field(
        default=None,
        description='Estado del documento; `null` en conversaciones',
    )
    progreso: int | None = Field(
        default=None,
        description='Progreso de ingesta del documento; `null` en conversaciones',
    )
    mensajes: int | None = Field(
        default=None,
        description='Número de mensajes de la conversación; `null` en documentos',
    )
    fecha: datetime = Field(description='Momento del último cambio o mensaje')


class ResumenDashboard(ModeloBase):
    """Totales y actividad reciente del Dashboard para un usuario."""

    documentos: int = Field(description='Documentos cargados por el usuario')
    conversaciones: int = Field(description='Conversaciones del usuario')
    chunks: int = Field(description='Fragmentos generados a partir de sus documentos')
    actividad: list[ActividadDashboard] = Field(
        description='Documentos y conversaciones recientes, de más nuevo a más viejo'
    )


@router.get(
    '/',
    response_model=ResumenDashboard,
    summary='Resumen del dashboard',
    description=(
        'Devuelve los totales de documentos, conversaciones y chunks del usuario, '
        'además de sus eventos más recientes para la actividad del Dashboard.'
    ),
    responses={
        422: {'description': 'Falta `usuario_id` o no es un UUID válido'},
    },
)
async def get_dashboard(
    repo: DashboardRepositoryDep,
    usuario_id: Annotated[
        UUID,
        Query(description='Usuario del que se calcula el resumen'),
    ],
) -> ResumenDashboard:
    documentos, conversaciones, chunks = await repo.resumen(usuario_id)
    actividad = await repo.actividad(usuario_id)
    return ResumenDashboard(
        documentos=documentos,
        conversaciones=conversaciones,
        chunks=chunks,
        actividad=[ActividadDashboard.model_validate(evento) for evento in actividad],
    )
