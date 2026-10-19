"""Modelos de dominio de raguaco.

Entidades del diagrama de clases (`Docs/UML/imagenes/Diagrama_Clases.png`) y del
diagrama entidad-relación (`Docs/UML/imagenes/diagrama entidad relacion.png`).

Estos modelos representan el dominio; los DTO de la API viven en `domain/schemas`.

    from domain.models import Documento, EstadoDocumento
"""

from domain.models.base import ModeloBase
from domain.models.chunk import Chunk
from domain.models.conversacion import Conversacion
from domain.models.documento import Documento, EstadoDocumento
from domain.models.mensaje import Mensaje, RolMensaje
from domain.models.referencia_fuente import ReferenciaFuente
from domain.models.usuario import Usuario

__all__ = [
    'Chunk',
    'Conversacion',
    'Documento',
    'EstadoDocumento',
    'Mensaje',
    'ModeloBase',
    'ReferenciaFuente',
    'RolMensaje',
    'Usuario',
]
