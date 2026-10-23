"""Servicio de LLM conectado exclusivamente a través de API.

Se comunica con OpenCode Go (u cualquier proveedor OpenAI-compatible) usando
`POST {LLM_BASE_URL}/chat/completions` con autenticación `Bearer`. La API key
se lee del entorno vía `core.config.settings` y nunca se escribe en el código
ni se expone al cliente (RNF5).

Las respuestas del asistente deben citar los documentos de origen y negarse
cuando no hay evidencia relevante (RF8, RF9); el servicio entrega el texto y
deja que la capa de dominio construya los prompts con las fuentes recuperadas.

Un fallo en la llamada (sin clave, red, respuesta mal formada) levanta
`LLMError` para que la ruta lo maneje sin tumbar la aplicación (RNF6).
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from core.config import settings

# Mensajes al estilo OpenAI: {"role": "system" | "user" | "assistant", "content": "..."}.
Mensaje = dict[str, str]

# OpenCode Go exige identificar la sesión en cada petición.
SESION_OPENCODE = 'raguaco_session'

# `reasoning_effort` que entiende la API OpenAI-compatible. Omitirlo (`None`)
# deja que el proveedor aplique el valor por defecto de cada modelo.
ESFUERZOS_RAZONAMIENTO = frozenset({'low', 'medium', 'high'})
ESFUERZO_POR_DEFECTO = 'low'


class LLMError(RuntimeError):
    """El LLM remoto no pudo responder (config incompleta, red o API)."""


class LLMService:
    """Cliente asíncrono del LLM vía API (OpenCode Go, OpenAI-compatible)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._base_url = (base_url or settings.llm_base_url).rstrip('/')
        self._model = model or settings.llm_model
        self._api_key = api_key if api_key is not None else settings.llm_api_key
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def configured(self) -> bool:
        """True si hay clave y modelo: sin ellos la API rechazaría la petición."""
        return bool(self._api_key and self._model)

    def _http(self) -> httpx.AsyncClient:
        """Reutiliza un único `AsyncClient` (conexiones persistente) por proceso."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def list_models(self) -> list[str]:
        """Catálogo de modelos del proveedor (`GET {LLM_BASE_URL}/models`).

        Evita hardcodeear la lista de OpenCode Go: para RAG solo valen los
        servidos en `/chat/completions` (p. ej. deepseek-v4.1-flash, glm-5.3,
        kimi-k3, qwen3.6-plus, mimo-v2.6-flash); los modelos Anthropic
        (`/messages`) u OpenAI Responses (`/responses`) no son compatibles
        con este servicio.
        """
        try:
            respuesta = await self._http().get(
                f'{self._base_url}/models', headers=self._headers()
            )
        except httpx.HTTPError as exc:
            raise LLMError(f'No se pudo listar los modelos del LLM: {exc}') from exc
        if respuesta.status_code >= 400:
            raise LLMError(
                f'El catálogo de modelos respondió {respuesta.status_code}: {respuesta.text[:300]}'
            )
        data = respuesta.json().get('data', [])
        return [str(item['id']) for item in data if isinstance(item, dict) and 'id' in item]

    async def chat(
        self,
        mensajes: list[Mensaje],
        *,
        temperature: float = 0.2,
        reasoning_effort: str | None = ESFUERZO_POR_DEFECTO,
    ) -> str:
        """Devuelve la respuesta completa del modelo para una conversación.

        `reasoning_effort` (`low`, `medium`, `high`) gradúa cuánto razona el
        modelo antes de responder: más esfuerzo mejora preguntas complejas a
        costa de latencia. Con `None` se usa el default del proveedor.
        """
        data = await self._post(
            mensajes,
            temperature=temperature,
            stream=False,
            reasoning_effort=reasoning_effort,
        )
        try:
            contenido = data['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError('La respuesta del LLM no tiene el formato esperado') from exc
        if not isinstance(contenido, str):
            raise LLMError('La respuesta del LLM no tiene el formato esperado')
        return contenido

    async def chat_stream(
        self,
        mensajes: list[Mensaje],
        *,
        temperature: float = 0.2,
        reasoning_effort: str | None = ESFUERZO_POR_DEFECTO,
    ) -> AsyncIterator[str]:
        """Emite fragmentos de texto conforme el modelo los genera (SSE).

        El usuario no debe esperar la respuesta completa para empezar a leerla
        (RF5); si la ruta prefiere simplicidad, puede usar `chat`. Acepta el
        mismo `reasoning_effort` que `chat`.
        """
        if not self.configured:
            raise LLMError(
                'LLM sin configurar: define LLM_API_KEY y LLM_MODEL en .env'
            )
        payload = self._payload(
            mensajes,
            temperature=temperature,
            stream=True,
            reasoning_effort=reasoning_effort,
        )

        try:
            async with self._http().stream(
                'post', f'{self._base_url}/chat/completions', headers=self._headers(), json=payload
            ) as respuesta:
                if respuesta.status_code >= 400:
                    detalle = (await respuesta.aread()).decode(errors='replace')[:300]
                    raise LLMError(
                        f'El LLM respondió {respuesta.status_code}: {detalle}'
                    )
                async for linea in respuesta.aiter_lines():
                    trozo = self._fragmento(linea)
                    if trozo is None:
                        continue
                    if trozo == '[DONE]':
                        return
                    yield trozo
        except httpx.HTTPError as exc:
            raise LLMError(f'No se pudo contactar al LLM: {exc}') from exc

    async def _post(
        self,
        mensajes: list[Mensaje],
        *,
        temperature: float,
        stream: bool,
        reasoning_effort: str | None,
    ) -> dict[str, Any]:
        if not self.configured:
            raise LLMError(
                'LLM sin configurar: define LLM_API_KEY y LLM_MODEL en .env'
            )
        payload = self._payload(
            mensajes,
            temperature=temperature,
            stream=stream,
            reasoning_effort=reasoning_effort,
        )

        try:
            respuesta = await self._http().post(
                f'{self._base_url}/chat/completions',
                headers=self._headers(),
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f'No se pudo contactar al LLM: {exc}') from exc
        if respuesta.status_code >= 400:
            raise LLMError(
                f'El LLM respondió {respuesta.status_code}: {respuesta.text[:300]}'
            )
        try:
            return respuesta.json()
        except ValueError as exc:
            raise LLMError('La respuesta del LLM no es JSON válido') from exc

    def _payload(
        self,
        mensajes: list[Mensaje],
        *,
        temperature: float,
        stream: bool,
        reasoning_effort: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'model': self._model,
            'messages': mensajes,
            'temperature': temperature,
            'stream': stream,
        }
        esfuerzo = self._normalizar_esfuerzo(reasoning_effort)
        if esfuerzo is not None:
            payload['reasoning_effort'] = esfuerzo
        return payload

    @staticmethod
    def _normalizar_esfuerzo(valor: str | None) -> str | None:
        """Valida y normaliza `reasoning_effort` antes de enviarlo.

        Un valor inválido se rechaza aquí y no en el proveedor, que lo
        ignoraría en silencio y degradaría la calidad sin avisar.
        """
        if valor is None:
            return None
        esfuerzo = valor.strip().lower()
        if esfuerzo not in ESFUERZOS_RAZONAMIENTO:
            permitidos = ', '.join(sorted(ESFUERZOS_RAZONAMIENTO))
            raise ValueError(
                f'reasoning_effort inválido: {valor!r} (usa {permitidos} o None)'
            )
        return esfuerzo

    def _headers(self, *, auth: bool = True) -> dict[str, str]:
        # Clave solo en el backend; jamás llega al cliente (RNF5).
        cabeceras: dict[str, str] = {
            'Content-Type': 'application/json',
            'x-opencode-session': SESION_OPENCODE,
        }
        if auth and self._api_key:
            cabeceras['Authorization'] = f'Bearer {self._api_key}'
        return cabeceras

    @staticmethod
    def _fragmento(linea: str) -> str | None:
        """Extrae el texto de una línea SSE `data: {...}` del stream."""
        linea = linea.strip()
        if not linea.startswith('data:'):
            return None
        datos = linea[len('data:'):].strip()
        if datos == '[DONE]':
            return '[DONE]'
        try:
            evento = json.loads(datos)
        except json.JSONDecodeError:
            return None
        choices = evento.get('choices') or []
        if not choices:
            return None
        contenido = (choices[0].get('delta') or {}).get('content')
        return contenido if isinstance(contenido, str) else None
