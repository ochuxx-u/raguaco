"""Entidad `Documento` y enumeración `EstadoDocumento` del dominio documental.

Relaciones (diagrama de clases / entidad-relación):

- `Usuario` 1 --- 0..* `Documento`
- `Documento` 1 --- 0..* `Chunk`
- `Documento` --> `EstadoDocumento`

Nota de nomenclatura: el diagrama de clases llama a este campo `metadata` y el
diagrama entidad-relación usa la columna `metadata`. En Python el atributo se llama
`metadatos`; el modelo acepta ambas claves (`metadatos` y `metadata`) para que el
repositorio pueda mapear la columna sin sorpresas.
"""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import AliasChoices, Field, model_validator

from domain.models.base import ModeloBase


class EstadoDocumento(str, Enum):
    """Estado del documento dentro del pipeline de ingesta."""

    PENDIENTE = 'pendiente'
    PROCESANDO = 'procesando'
    LISTO = 'listo'
    ERROR = 'error'

    @property
    def es_final(self) -> bool:
        """`True` si el documento ya no va a cambiar de estado."""
        return self in (EstadoDocumento.LISTO, EstadoDocumento.ERROR)


class Documento(ModeloBase):
    """Documento cargado por el usuario y procesado por el pipeline de ingesta."""

    id: UUID = Field(default_factory=uuid4, description='Identificador único del documento')
    usuario_id: UUID = Field(description='Usuario propietario del documento')
    nombre: str = Field(min_length=1, max_length=255, description='Nombre original del archivo')
    formato: str = Field(
        min_length=1,
        max_length=20,
        description='Formato del archivo (pdf, docx, txt, ...). Texto libre para no limitar '
        'la extensibilidad de formatos (RNF8)',
    )
    ruta_original: str = Field(
        min_length=1,
        description='Ruta del archivo original en el almacenamiento local (StorageService)',
    )
    categoria: str | None = Field(
        default=None,
        max_length=100,
        description='Categoría temática opcional; los documentos pueden no tenerla (RF1)',
    )
    estado: EstadoDocumento = Field(
        default=EstadoDocumento.PENDIENTE,
        description='Estado actual del procesamiento del documento',
    )
    fecha_carga: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description='Momento en que se cargó el documento',
    )
    metadatos: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices('metadatos', 'metadata'),
        description='Metadatos libres del documento (columna `metadata` en base de datos)',
    )

    @model_validator(mode='before')
    @classmethod
    def _reconocer_datos_desde_la_ruta(cls, data: Any) -> Any:
        """Deriva `nombre` y `formato` a partir de `ruta_original`.

        Permite registrar un documento indicando solo la ruta del archivo: el
        servidor reconoce el nombre y el formato a partir de ella. Si el cliente
        los envía, se respetan.

        También exige que la ruta incluya la extensión del archivo, porque de ella
        depende `formato` (un documento sin formato no se puede procesar).
        """
        if not isinstance(data, dict):
            return data

        ruta = data.get('ruta_original')
        if not isinstance(ruta, str) or not ruta.strip():
            return data

        base = Path(ruta)
        if not base.suffix:
            raise ValueError(
                'La ruta del archivo debe incluir su extensión (por ejemplo, /docs/manual.pdf)'
            )

        data = dict(data)
        if not data.get('nombre'):
            data['nombre'] = base.name
        if not data.get('formato'):
            data['formato'] = base.suffix.lstrip('.').lower()
        return data

    def iniciar_procesamiento(self) -> None:
        """Marca el documento como en procesamiento (inicio del pipeline de ingesta)."""
        self.estado = EstadoDocumento.PROCESANDO

    def marcar_listo(self) -> None:
        """Marca el documento como procesado y listo para ser consultado."""
        self.estado = EstadoDocumento.LISTO

    def marcar_error(self, motivo: str) -> None:
        """Marca el documento como fallido y guarda el motivo en los metadatos.

        Los fallos de un documento no deben tumbar la aplicación (RNF6), por eso el
        motivo queda registrado en `metadatos` en lugar de propagarse como excepción.
        """
        self.estado = EstadoDocumento.ERROR
        self.metadatos['error'] = motivo
