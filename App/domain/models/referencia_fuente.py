"""Entidad `ReferenciaFuente` del dominio conversacional.

Relaciones (diagrama de clases / entidad-relación):

- `Mensaje` 1 --- 0..* `ReferenciaFuente`
- `Chunk` 1 --- 0..* `ReferenciaFuente`

Una referencia es la evidencia que respalda una respuesta: RF8 pide mostrar los
documentos que respaldan la respuesta y RNF7 pide trazabilidad. `similitud` guarda
la puntuación del retrieval para poder reconstruir por qué se citar ese fragmento.
"""

from uuid import UUID, uuid4

from pydantic import Field

from domain.models.base import ModeloBase


class ReferenciaFuente(ModeloBase):
    """Vínculo entre un mensaje (respuesta) y el chunk que lo sustenta."""

    id: UUID = Field(default_factory=uuid4, description='Identificador único de la referencia')
    mensaje_id: UUID = Field(description='Mensaje al que pertenece la referencia')
    chunk_id: UUID = Field(description='Fragmento citado como fuente')
    similitud: float = Field(
        ge=0.0,
        le=1.0,
        description='Similitud entre la consulta y el fragmento, en el rango 0..1',
    )
