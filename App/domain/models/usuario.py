"""Entidad `Usuario` del dominio conversacional.

Relaciones (diagrama de clases / entidad-relación):

- `Usuario` 1 --- 0..* `Documento`
- `Usuario` 1 --- 0..* `Conversacion`
"""

from uuid import UUID, uuid4

from pydantic import EmailStr, Field

from domain.models.base import ModeloBase


class Usuario(ModeloBase):
    """Usuario registrado en el sistema.

    Las operaciones `chatear()` y `hablar()` que aparecen en el diagrama de clases
    no viven aquí: son casos de uso de `RAGService` y `VoiceService` respectivamente.
    Mantener la entidad sin dependencias de servicios evita acoplar el dominio a la
    capa de aplicación (RNF1, RNF2).
    """

    id: UUID = Field(default_factory=uuid4, description='Identificador único del usuario')
    nombre: str = Field(min_length=2, max_length=100, description='Nombre visible del usuario')
    email: EmailStr = Field(description='Correo electrónico; debe ser único en el sistema')
