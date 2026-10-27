"""Servicio de conversaciones: historial y mensajes con sus fuentes.

Es el `ConversationService` del diagrama de secuencia
(`Docs/UML/imagenes/DIA-SECUENCIA_Ask-With-PNL.png`), con
`obtenerHistorial(conversacionId)` y `agregarMensaje(conversacionId, mensaje,
referencias)`. Centraliza la persistencia conversacional sobre los repositorios
de PostgreSQL para que la API y `RAGService` no hablen directamente con las
tablas (RNF1: componentes modulares y sustituibles).

`crear_conversacion(usuario_id)` no aparece en el diagrama: lo usa la ruta
`POST /v1/queries/` cuando el cliente no trae `conversacion_id`, que el propio
diagrama declara opcional (`{pregunta, conversacionId?}`).
"""

from uuid import UUID

from domain.models.conversacion import Conversacion
from domain.models.mensaje import Mensaje
from domain.models.referencia_fuente import ReferenciaFuente
from infrastructure.db.repositories.conversacion_repository import ConversacionRepository
from infrastructure.db.repositories.mensaje_repository import MensajeRepository
from infrastructure.db.repositories.referencia_fuente_repository import ReferenciaFuenteRepository


class ConversationService:
    """Conversaciones, mensajes y fuentes sobre los repositorios de PostgreSQL."""

    def __init__(
        self,
        conversaciones: ConversacionRepository,
        mensajes: MensajeRepository,
        referencias: ReferenciaFuenteRepository,
    ) -> None:
        self._conversaciones = conversaciones
        self._mensajes = mensajes
        self._referencias = referencias

    async def crear_conversacion(self, usuario_id: UUID) -> Conversacion:
        """Abre una conversación nueva para el usuario."""
        conversacion = await self._conversaciones.create(Conversacion(usuario_id=usuario_id))
        print(f'[conversacion] crearConversacion({usuario_id}) → {conversacion.id}')
        return conversacion

    async def obtener_historial(self, conversacion_id: UUID) -> list[Mensaje]:
        """Historial de la conversación, del más antiguo al más reciente."""
        historial = await self._mensajes.list(conversacion_id)
        print(f'[conversacion] obtenerHistorial({conversacion_id}) → {len(historial)} mensajes')
        return historial

    async def agregar_mensaje(
        self,
        conversacion_id: UUID,
        mensaje: Mensaje,
        referencias: list[ReferenciaFuente] | None = None,
    ) -> Mensaje:
        """Guarda un mensaje y, si tiene, las fuentes que lo respaldan (RF8, RNF7).

        `conversacion_id` es el del diagrama y el que se persiste en el mensaje:
        garantiza que quede en la conversación que dice la llamada. El `orden`
        de cada referencia se guarda al insertarlas según su posición en la
        lista (la marca `[n]` citada en la respuesta). `referencias=None` es el
        caso de los mensajes del usuario, que no citan fuentes.
        """
        mensaje.conversacion_id = conversacion_id
        guardado = await self._mensajes.create(mensaje)
        if referencias:
            await self._referencias.create_many(referencias)
        print(
            f'[conversacion] agregarMensaje({conversacion_id}, rol={mensaje.rol}, '
            f'referencias={len(referencias or [])}) → mensaje {guardado.id}'
        )
        return guardado
