"""Entidad `Chunk` del dominio documental.

Relaciones (diagrama de clases / entidad-relación):

- `Documento` 1 --- 0..* `Chunk`
- `Chunk` 1 --- 0..* `ReferenciaFuente`

Igual que en `Documento`, el atributo se llama `metadatos` pero acepta la clave
`metadata` (columna del diagrama entidad-relación) al construirse desde la base de datos.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import AliasChoices, Field

from domain.models.base import ModeloBase


class Chunk(ModeloBase):
    """Fragmento de un documento, listo para ser indexado como vector."""

    id: UUID = Field(default_factory=uuid4, description='Identificador único del fragmento')
    documento_id: UUID = Field(description='Documento al que pertenece el fragmento')
    contenido: str = Field(min_length=1, description='Texto limpio del fragmento')
    indice: int = Field(ge=0, description='Posición del fragmento dentro del documento')
    pagina: int | None = Field(
        default=None,
        ge=1,
        description='Página del documento original; `None` en formatos sin paginación',
    )
    metadatos: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices('metadatos', 'metadata'),
        description='Metadatos libres del fragmento (columna `metadata` en base de datos)',
    )
    embedding: list[float] = Field(
        min_length=1,
        description='Vector de embeddings; en base de datos se guarda como tipo `vector` (pgvector)',
    )
