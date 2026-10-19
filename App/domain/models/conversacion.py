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
    """Conversación mantenida entre un usuario y el asistente (RF10)."""

    id: UUID = Field(default_factory=uuid4, description='Identificador único de la conversación')
    usuario_id: UUID = Field(description='Usuario dueño de la conversación')
    fecha_creacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description='Momento en que se creó la conversación',
    )
