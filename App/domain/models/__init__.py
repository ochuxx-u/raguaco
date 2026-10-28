"""Modelos de dominio de raguaco.

Entidades del diagrama de clases (`Docs/UML/imagenes/Diagrama_Clases.png`) y del
diagrama entidad-relación (`Docs/UML/imagenes/diagrama entidad relacion.png`).

Estos modelos representan el dominio; la API los expone directamente, sin una capa
de DTO propia.

    from domain.models import Documento, EstadoDocumento
"""

from domain.models.base import ModeloBase
from domain.models.chunk import Chunk
from domain.models.conversacion import Conversacion, ConversacionResumen
from domain.models.documento import Documento, EstadoDocumento
from domain.models.mensaje import Mensaje, MensajeConFuentes, RolMensaje
from domain.models.referencia_fuente import FuenteDetalle, ReferenciaFuente
from domain.models.usuario import Usuario

__all__ = [
    'Chunk',
    'Conversacion',
    'ConversacionResumen',
    'Documento',
    'EstadoDocumento',
    'FuenteDetalle',
    'Mensaje',
    'MensajeConFuentes',
    'ModeloBase',
    'ReferenciaFuente',
    'RolMensaje',
    'Usuario',
]
