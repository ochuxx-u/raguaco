"""Entidad `Conversacion` del dominio conversacional.

Relaciones (diagrama de clases / entidad-relación):

- `Usuario` 1 --- 0..* `Conversacion`
- `Conversacion` 1 --- 0..* `Mensaje`
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import Field

from domain.models.base import ModeloBase


class Conversacion(ModeloBase):
    """Conversación mantenida entre un usuario y el asistente."""

    id: UUID = Field(default_factory=uuid4, description='Identificador único de la conversación')
    usuario_id: UUID = Field(description='Usuario dueño de la conversación')
    titulo: str | None = Field(
        default=None,
        description=(
            'Título de la conversación para el historial; al crearla desde una '
            'consulta se toma de los primeros caracteres de la pregunta'
        ),
    )
    fecha_creacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description='Momento en que se creó la conversación',
    )
    fecha_actualizacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description='Momento del último mensaje; es la fecha que muestra el Historial',
    )


class ConversacionResumen(Conversacion):
    """Conversación con los datos agregados que muestra el Historial."""

    ultima_pregunta: str | None = Field(
        default=None,
        description='Texto de la última pregunta del usuario; `None` si no hay mensajes',
    )
    mensaje_count: int = Field(
        default=0,
        ge=0,
        description='Número de mensajes de la conversación',
    )
