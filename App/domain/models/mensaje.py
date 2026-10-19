"""Entidad `Mensaje` del dominio conversacional.

Relaciones (diagrama de clases / entidad-relación):

- `Conversacion` 1 --- 0..* `Mensaje`
- `Mensaje` 1 --- 0..* `ReferenciaFuente`
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from domain.models.base import ModeloBase

# El diagrama de clases declara `rol` como `string`; se acota a los tres roles que
# usa el sistema para no dejar valores libres que rompan el historial.
RolMensaje = Literal['usuario', 'asistente', 'sistema']


class Mensaje(ModeloBase):
    """Mensaje dentro de una conversación."""

    id: UUID = Field(default_factory=uuid4, description='Identificador único del mensaje')
    conversacion_id: UUID = Field(description='Conversación a la que pertenece el mensaje')
    rol: RolMensaje = Field(description='Emisor del mensaje: usuario, asistente o sistema')
    contenido: str = Field(min_length=1, description='Texto del mensaje')
    fecha: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description='Momento en que se creó el mensaje',
    )
