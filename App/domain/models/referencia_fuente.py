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


class FuenteDetalle(ReferenciaFuente):
    """Referencia enriquecida con los datos que muestra la UI (RF8).

    La tabla `referencia_fuente` solo guarda los ids; el chat y la pantalla de
    evidencia necesitan el nombre del documento, la página y el fragmento para
    poder citarlos. Esta vista se compone en el repositorio al leer las
    referencias y mantiene la misma identidad (`id`) que la referencia original.
    """

    documento_id: UUID = Field(description='Documento al que pertenece el fragmento')
    documento: str = Field(description='Nombre original del documento citado')
    formato: str = Field(description='Formato del documento (pdf, docx, txt, ...)')
    categoria: str | None = Field(
        default=None,
        description='Categoría del documento; puede estar vacía',
    )
    pagina: int | None = Field(
        default=None,
        description='Página del fragmento; `None` en formatos sin paginación',
    )
    indice: int = Field(ge=0, description='Posición del fragmento dentro del documento')
    fragmento: str = Field(min_length=1, description='Texto del fragmento citado')
    orden: int | None = Field(
        default=None,
        description='Posición de la fuente en la respuesta (1, 2, 3, …)',
    )
