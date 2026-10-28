"""Orquestador del flujo RAG: responde a una consulta con fuentes (RF5, RF8, RF9).

`RAGService` implementa el caso de uso `responder(pregunta, conversacionId)` del
diagrama de clases (`Docs/UML/imagenes/Diagrama_Clases.png`), de principio a fin:

1. `obtenerHistorial(conversacionId)` → `historial` — `ConversationService`.
2. `agregarMensaje(conversacionId, mensaje, referencias=None)` → `ok` —
   `ConversationService`: guarda el mensaje del usuario en la conversación.
3. `recuperar(consulta, usuarioId, opciones)` → `fragmentos con similitud` —
   `Retriever`. La consulta se transforma en un embedding (RF5) y se buscan los
   fragmentos más similares de los documentos del usuario.
4. `generarRespuesta(prompt, contexto)` → `respuesta` — `LLMService` (desviación
   (b): en la práctica es `LLMService.chat(mensajes)`). El texto se convierte a
   texto plano (`infrastructure.llm.plain_text.limpiar_markdown`) antes de
   guardarlo y devolverlo: el chat del frontend no interpreta Markdown.
5. `agregarMensaje(conversacionId, mensaje, referencias)` → `ok` —
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
    `DocumentIngestionService.procesar_documento`. El mensaje del usuario lo
    guarda este servicio tras leer el historial, como muestra el diagrama
    (`agregarMensaje(conversacionId, mensaje, referencias=None)`).

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
from domain.models.referencia_fuente import FuenteDetalle, ReferenciaFuente
from infrastructure.llm.llm_service import LLMService
from infrastructure.llm.plain_text import limpiar_markdown

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

# Sustituto cuando la respuesta del LLM queda vacía después de quitarle la
# notación Markdown (p. ej. solo devolvió una valla de código sin texto): un
# mensaje de asistente no puede guardarse vacío (`Mensaje.contenido`).
MENSAJE_RESPUESTA_VACIA = (
    'El asistente no ha devuelto una respuesta legible con los documentos '
    'recuperados. Prueba a reformular la pregunta.'
)

# Cuántos mensajes del historial se envían al LLM como contexto conversacional.
# Acota el prompt aunque la conversación siga creciendo; los más recientes son
# los relevantes para la pregunta actual.
MAX_MENSAJES_HISTORIAL = 10

# Longitud máxima (en caracteres) de la respuesta del asistente: el flujo
# recorta el texto generado por el LLM a este límite y el prompt de sistema
# pide al modelo que lo respete.
MAX_CARACTERES_RESPUESTA = 1000

# Roles de los mensajes del dominio (`Mensaje.rol`) → roles que entiende la API
# del LLM (mensajes estilo OpenAI en `LLMService.chat`).
ROLES_CHAT = {'sistema': 'system', 'usuario': 'user', 'asistente': 'assistant'}


class RespuestaRAG(ModeloBase):
    """Respuesta del asistente junto a las fuentes que la respaldan (RF8).

    Cada `FuenteDetalle` vincula el mensaje con el `Chunk` citado, su similitud
    (RNF7, trazabilidad) y los datos que muestra la UI (documento, página y
    fragmento); la posición en `referencias` se corresponde con la marca `[n]`
    citada en el texto de la respuesta.
    """

    mensaje: Mensaje
    referencias: list[FuenteDetalle]


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
        `agregarMensaje(conversacionId, mensaje, referencias=None)` (mensaje del
        usuario) → `recuperar(consulta, usuarioId, opciones)` →
        `generarRespuesta(prompt, contexto)` → `agregarMensaje(conversacionId,
        mensaje, referencias)`.

        Devuelve la respuesta del asistente ya guardada en la conversación, con
        `referencias` vacías si no hubo evidencia relevante (RF9). Los errores de
        los colaboradores (LLM, recuperación, persistencia) se propagan para que
        la ruta los traduzca sin tumbar la aplicación (RNF6).
        """
        # obtenerHistorial(conversacionId) → historial
        historial = await self._conversation_service.obtener_historial(conversacion_id)

        # agregarMensaje(conversacionId, mensaje, referencias=None) → ok
        # El mensaje del usuario lo guarda el propio flujo, como en el diagrama.
        await self._conversation_service.agregar_mensaje(
            conversacion_id,
            Mensaje(conversacion_id=conversacion_id, rol='usuario', contenido=pregunta),
            None,
        )

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
        # El texto del modelo se convierte a texto plano antes de guardarlo: el
        # chat del frontend no interpreta Markdown y mostraría los asteriscos,
        # las almohadillas o los enlaces tal cual. La limpieza va antes del
        # recorte para no dejar marcas a medias y conserva las citas `[n]` (RF8).
        respuesta = await self._llm.chat(self._mensajes_llm(pregunta, historial, resultados))
        contenido = limpiar_markdown(respuesta) or MENSAJE_RESPUESTA_VACIA
        if len(contenido) > MAX_CARACTERES_RESPUESTA:
            print(
                f'[rag] respuesta de {len(contenido)} caracteres recortada '
                f'a {MAX_CARACTERES_RESPUESTA}'
            )
            contenido = contenido[:MAX_CARACTERES_RESPUESTA].rstrip()

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
        # Se devuelven las fuentes enriquecidas (documento, página, fragmento)
        # para que el chat pueda citarlas sin una petición adicional (RF8).
        fuentes = await self._conversation_service.obtener_fuentes(mensaje.id)
        return RespuestaRAG(mensaje=mensaje, referencias=fuentes)

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

        # El historial se lee antes de guardar el mensaje del usuario, así que la
        # pregunta actual se añade al final para que nunca se pierda (y no se
        # duplica si ya viniera en el historial).
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
            f'Responde de forma concisa, en máximo {MAX_CARACTERES_RESPUESTA} caracteres.',
            'Escribe en texto plano, sin notación Markdown (sin negritas, encabezados, '
            'viñetas, tablas, bloques de código ni enlaces); conserva las citas [n] '
            'del contexto.',
            'Responde a la pregunta del usuario usando ÚNICAMENTE los fragmentos (referencias) '
            'de documentos del siguiente contexto.',
            'Cita los fragmentos que uses con su número entre corchetes, por '
            'ejemplo [1] o [2][3] pero no los uses como parte de la conversación en el sentido de habla, ejemplo, decir algo como "En [3] también se agrup" porque carece de contexto en medio de la charla.',
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
