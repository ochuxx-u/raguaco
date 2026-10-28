"""Entidad `Mensaje` del dominio conversacional.

Relaciones (diagrama de clases / entidad-relación):

- `Conversacion` 1 --- 0..* `Mensaje`
- `Mensaje` 1 --- 0..* `ReferenciaFuente`
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from domain.models.base import ModeloBase
from domain.models.referencia_fuente import FuenteDetalle

# El diagrama de clases declara `rol` como `string`; se acota a los tres roles que
# usa el sistema para no dejar valores libres que rompan el historial.
RolMensaje = Literal['usuario', 'asistente', 'sistema']

# Máximo de caracteres de una consulta escrita por el usuario (RF5). Es el mismo
# límite que se aplica en `PublicarMensajePeticion.contenido`
# (`api/routes/queries.py`) y en el `maxLength` del textarea del chat
# (`frontend/src/components/chat/ChatInput.jsx`): si se cambia, hay que cambiarlo
# en los tres sitios.
MAX_LONGITUD_CONSULTA = 512

# Techo del resto de roles: las respuestas del asistente (RF8) llevan fuentes y
# superan con creces el límite de la consulta.
MAX_LONGITUD_MENSAJE = 8000


class Mensaje(ModeloBase):
    """Mensaje dentro de una conversación.

    El `contenido` de un mensaje de `usuario` es una consulta (RF5) y no puede
    superar `MAX_LONGITUD_CONSULTA`; los mensajes de `asistente` y `sistema`
    admiten hasta `MAX_LONGITUD_MENSAJE`.
    """

    id: UUID = Field(default_factory=uuid4, description='Identificador único del mensaje')
    conversacion_id: UUID = Field(description='Conversación a la que pertenece el mensaje')
    rol: RolMensaje = Field(description='Emisor del mensaje: usuario, asistente o sistema')
    contenido: str = Field(min_length=1, max_length=MAX_LONGITUD_MENSAJE, description='Texto del mensaje')
    fecha: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description='Momento en que se creó el mensaje',
    )

    @model_validator(mode='after')
    def validar_longitud_segun_rol(self) -> 'Mensaje':
        """Acota el `contenido` según el rol que lo emite."""
        if self.rol == 'usuario' and len(self.contenido) > MAX_LONGITUD_CONSULTA:
            raise ValueError(
                f'un mensaje de usuario no puede superar los {MAX_LONGITUD_CONSULTA} caracteres'
            )
        return self


class MensajeConFuentes(Mensaje):
    """Mensaje del historial junto a las fuentes que lo respaldan (RF8).

    Es la forma que consume el chat al abrir una conversación: cada respuesta
    del asistente llega con sus referencias ya enriquecidas para poder pintar
    los chips `Fuente n · pág. x` y el panel de fuentes y evidencia.
    """

    fuentes: list[FuenteDetalle] = Field(
        default_factory=list,
        description='Fuentes citadas por el mensaje, en el orden en que aparecen',
    )
