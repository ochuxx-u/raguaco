"""Orquestador del flujo RAG: responde a una consulta con fuentes (RF5, RF8, RF9).

`RAGService` implementa el caso de uso `responder(pregunta, conversacionId)` del
diagrama de clases (`Docs/UML/imagenes/Diagrama_Clases.png`), de principio a fin:

1. `obtenerHistorial(conversacionId)` → `historial` — `ConversationService`.
2. `recuperar(consulta, usuarioId, opciones)` → `fragmentos con similitud` —
   `Retriever`. La consulta se transforma en un embedding (RF5) y se buscan los
   fragmentos más similares de los documentos del usuario.
3. `generarRespuesta(prompt, contexto)` → `respuesta` — `LLMService` (desviación
   (b): en la práctica es `LLMService.chat(mensajes)`).
4. `agregarMensaje(conversacionId, mensaje, referencias)` → `ok` —
   `ConversationService`: la respuesta del asistente se guarda con las fuentes
   que la respaldan (RF8, RNF7).

Si la recuperación no encuentra evidencia relevante (RF9) **no se invoca al
LLM**: se devuelve un mensaje de rechazo explícito (`MENSAJE_SIN_EVIDENCIA`) sin
referencias, para no generar una respuesta sin fundamento documental. Cuando hay
evidencia, el prompt obliga al modelo a responder solo con los fragmentos
recuperados y a citarlos con `[n]`; cada `[n]` se corresponde con la posición del
fragmento en `RespuestaRAG.referencias` (RF8).

Dos desviaciones conscientes respecto al diagrama:

(a) `responder` recibe además `usuario_id` como palabra clave. El propio
    diagrama lo pide en `recuperar(consulta, usuarioId, opciones)` (para acotar
    la búsqueda a los documentos del usuario), pero `responder(pregunta,
    conversacionId)` no lo transporta. Mismo criterio que `usuario_id` en
    `DocumentIngestionService.procesar_documento`. El mensaje del usuario no se
    guarda aquí: lo publica antes `POST /v1/queries/messages`.

(b) El `generarRespuesta(prompt, contexto)` del diagrama es en la práctica
    `LLMService.chat(mensajes)`, que recibe mensajes estilo OpenAI y solo llama
    al modelo (su docstring deja la construcción de los prompts a la capa de
    dominio). Este servicio arma esos mensajes: uno de sistema con las
    instrucciones y el contexto numerado de fragmentos, el historial reciente de
    la conversación y la pregunta actual.

Pendientes que este servicio usa pero que aún no existen (se importan solo para
comprobación de tipos, de modo que el módulo se puede importar y probar sin
ellos):

- `domain/services/conversation_service.py` → `ConversationService`, con
  `obtener_historial(conversacion_id) -> list[Mensaje]`,
  `agregar_mensaje(conversacion_id, mensaje, referencias)` y
  `crear_conversacion(usuario_id)` (esta última la usa la ruta, no este servicio).
- `infrastructure/retrieval/retriever.py` → `Retriever` (ruta provisional), con
  `recuperar(consulta, usuario_id, opciones) -> list[tuple[Chunk, float]]`:
  devuelve cada fragmento con su similitud en el rango 0..1 (para
  `ReferenciaFuente.similitud`); `opciones` es un diccionario libre de
  parámetros de búsqueda (p. ej. `top_k`, `umbral`, `filtros`) que este servicio
  traslada sin interpretar.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from domain.models.base import ModeloBase
from domain.models.chunk import Chunk
from domain.models.mensaje import Mensaje
from domain.models.referencia_fuente import ReferenciaFuente
from infrastructure.llm.llm_service import LLMService

if TYPE_CHECKING:
    from domain.services.conversation_service import ConversationService
    from infrastructure.retrieval.retriever import Retriever

# Rechazo explícito cuando la recuperación no encuentra evidencia relevante
# (RF9): se devuelve tal cual, sin invocar al LLM ni registrar referencias.
MENSAJE_SIN_EVIDENCIA = (
    'No he encontrado información suficientemente relacionada con tu pregunta '
    'en tus documentos, así que no puedo responderla con fundamento documental. '
    'Prueba a reformularla o a subir documentos que traten sobre el tema.'
)

# Cuántos mensajes del historial se envían al LLM como contexto conversacional.
# Acota el prompt aunque la conversación siga creciendo; los más recientes son
# los relevantes para la pregunta actual.
MAX_MENSAJES_HISTORIAL = 10

# Roles de los mensajes del dominio (`Mensaje.rol`) → roles que entiende la API
# del LLM (mensajes estilo OpenAI en `LLMService.chat`).
ROLES_CHAT = {'sistema': 'system', 'usuario': 'user', 'asistente': 'assistant'}


class RespuestaRAG(ModeloBase):
    """Respuesta del asistente junto a las fuentes que la respaldan (RF8).

    Cada `ReferenciaFuente` vincula el mensaje con el `Chunk` citado y su
    similitud (RNF7, trazabilidad); la posición en `referencias` se corresponde
    con la marca `[n]` citada en el texto de la respuesta.
    """

    mensaje: Mensaje
    referencias: list[ReferenciaFuente]


class RAGService:
    """Responde a una consulta del usuario con fuentes documentales (RF5, RF8, RF9).

    Recibe sus componentes por constructor (inyección de dependencias) para que
    cada pieza sea sustituible (RNF1): servicio de conversaciones, LLM y
    recuperador.
    """

    def __init__(
        self,
        conversation_service: 'ConversationService',
        llm: LLMService,
        retriever: 'Retriever',
    ) -> None:
        self._conversation_service = conversation_service
        self._llm = llm
        self._retriever = retriever

    async def responder(
        self,
        pregunta: str,
        conversacion_id: UUID,
        *,
        usuario_id: UUID,
        opciones: dict[str, Any] | None = None,
    ) -> RespuestaRAG:
        """Responde `pregunta` en la conversación y devuelve la respuesta con sus fuentes.

        Pasos, según el diagrama de clases: `obtenerHistorial(conversacionId)` →
        `recuperar(consulta, usuarioId, opciones)` → `generarRespuesta(prompt,
        contexto)` → `agregarMensaje(conversacionId, mensaje, referencias)`.

        Devuelve la respuesta del asistente ya guardada en la conversación, con
        `referencias` vacías si no hubo evidencia relevante (RF9). Los errores de
        los colaboradores (LLM, recuperación, persistencia) se propagan para que
        la ruta los traduzca sin tumbar la aplicación (RNF6).
        """
        # obtenerHistorial(conversacionId) → historial
        historial = await self._conversation_service.obtener_historial(conversacion_id)

        # recuperar(consulta, usuarioId, opciones) → fragmentos con similitud
        resultados = await self._retriever.recuperar(pregunta, usuario_id, opciones)

        # RF9: sin evidencia relevante, rechazo explícito en lugar de una
        # respuesta sin fundamento documental. No se invoca al LLM.
        if not resultados:
            mensaje = Mensaje(
                conversacion_id=conversacion_id,
                rol='asistente',
                contenido=MENSAJE_SIN_EVIDENCIA,
            )
            # agregarMensaje(conversacionId, mensaje, referencias) → ok
            await self._conversation_service.agregar_mensaje(conversacion_id, mensaje, [])
            return RespuestaRAG(mensaje=mensaje, referencias=[])

        # generarRespuesta(prompt, contexto) → respuesta (desviación (b))
        contenido = await self._llm.chat(self._mensajes_llm(pregunta, historial, resultados))

        mensaje = Mensaje(
            conversacion_id=conversacion_id,
            rol='asistente',
            contenido=contenido,
        )
        # La posición en `referencias` es la marca `[n]` citada en la respuesta.
        referencias = [
            ReferenciaFuente(mensaje_id=mensaje.id, chunk_id=chunk.id, similitud=similitud)
            for chunk, similitud in resultados
        ]

        # agregarMensaje(conversacionId, mensaje, referencias) → ok
        await self._conversation_service.agregar_mensaje(conversacion_id, mensaje, referencias)
        return RespuestaRAG(mensaje=mensaje, referencias=referencias)

    def _mensajes_llm(
        self,
        pregunta: str,
        historial: list[Mensaje],
        resultados: list[tuple[Chunk, float]],
    ) -> list[dict[str, str]]:
        """Construye los mensajes estilo OpenAI para `LLMService.chat`.

        Orden: instrucciones + contexto numerado de fragmentos (prompt de
        sistema), historial reciente de la conversación y pregunta actual.
        """
        mensajes: list[dict[str, str]] = [
            {'role': 'system', 'content': self._prompt_sistema(resultados)},
        ]
        for mensaje in historial[-MAX_MENSAJES_HISTORIAL:]:
            mensajes.append({'role': ROLES_CHAT[mensaje.rol], 'content': mensaje.contenido})

        # El mensaje del usuario ya suele estar en el historial (lo publica
        # `POST /v1/queries/messages` antes de invocar a `responder`); si no lo
        # está, se añade para que la pregunta nunca se pierda.
        if not historial or (historial[-1].rol, historial[-1].contenido) != ('usuario', pregunta):
            mensajes.append({'role': 'user', 'content': pregunta})
        return mensajes

    @staticmethod
    def _prompt_sistema(resultados: list[tuple[Chunk, float]]) -> str:
        """Prompt de sistema con las instrucciones y el contexto numerado (RF8).

        Las marcas `[n]` del contexto son las que el modelo debe citar en su
        respuesta y las que se corresponden con `RespuestaRAG.referencias`.
        """
        lineas = [
            'Eres el asistente documental de Raguaco.',
            'Responde a la pregunta del usuario usando ÚNICAMENTE los fragmentos '
            'de documentos del siguiente contexto.',
            'Cita los fragmentos que uses con su número entre corchetes, por '
            'ejemplo [1] o [2][3].',
            'Si el contexto no contiene información suficiente para responder, '
            'dilo explícitamente e indica que no se encontró evidencia relevante; '
            'no inventes datos ni respondas con conocimiento general.',
            '',
            'Contexto:',
        ]
        for numero, (chunk, _) in enumerate(resultados, start=1):
            origen = f'documento {chunk.documento_id}'
            if chunk.pagina is not None:
                origen += f', página {chunk.pagina}'
            lineas.append(f'[{numero}] ({origen}): {chunk.contenido}')
        return '\n'.join(lineas)
