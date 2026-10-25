"""Servicio de embeddings: vectoriza pasajes y consultas con multilingual-e5-small.

Corre **en local**, sin API externa: los pesos ONNX se leen del directorio
`EMBEDDING_MODEL` de `.env` (ruta relativa a `App/`) y la inferencia va sobre
`onnxruntime` —el mismo motor que ya usa el TTS— sin `sentence-transformers` ni
PyTorch. El modelo no viaja en git: hay que descargarlo primero según el README
(`hf download intfloat/multilingual-e5-small --local-dir App/ai-models/multilingual-e5-small`).

El agrupamiento replica lo que declara el propio modelo (`1_Pooling/config.json`):
mean-pooling sobre tokens no-pad seguido de normalización L2, igual que la prueba
local `App/tests/probar_embeddings.py`. Con vectores unitarios el producto punto
es la similitud de coseno que compara pgvector.

`multilingual-e5-small` exige prefijos: `query: ` para preguntas del usuario y
`passage: ` para fragmentos de documento. Sin ellos la recuperación se degrada
en silencio, así que la única puerta de entrada al modelo son `embeber_consulta`
y `embeber_pasajes`, que los agregan por dentro.

La carga es perezosa: la aplicación arranca aunque el modelo no esté instalado
(RNF6) y el fallo aparece solo al vectorizar, con `EmbeddingError` que señala la
descarga pendiente. La dimensión del resultado se valida contra
`EMBEDDING_DIMENSION`, que debe coincidir con `chunk.embedding vector(384)` del
esquema (`App/migrations/001_schema.sql`).
"""

import asyncio
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from core.config import settings

if TYPE_CHECKING:
    import onnxruntime as rt
    from tokenizers import Tokenizer

# Prefijos que exige e5: pregunta del usuario vs. fragmento de documento.
PREFIJO_CONSULTA = 'query: '
PREFIJO_PASAJE = 'passage: '

# Límite de tokens del modelo (max_position_embeddings de su config.json): los
# textos más largos se truncan aquí en lugar de fallar en la inferencia.
MAX_LENGTH = 512

NOMBRE_TOKENIZER = 'tokenizer.json'
NOMBRE_MODELO = 'model.onnx'

# Mensaje único para todos los fallos de instalación: la causa casi nunca es un
# bug, es que el modelo bajó falta o a media descarga.
_INSTRUCCION_DESCARGA = (
    'Descárgalo según el README: hf download intfloat/multilingual-e5-small '
    '--local-dir App/ai-models/multilingual-e5-small'
)


class EmbeddingError(RuntimeError):
    """El modelo local de embeddings no pudo cargar o vectorizar."""


class EmbeddingService:
    """Cliente del modelo multilingual-e5-small ejecutándose en local.

    Se usa como instancia única por proceso (`get_embedding_service` en
    `api/deps.py`): los pesos ONNX pesan cientos de MB y no deben recargarse en
    cada petición.
    """

    def __init__(
        self,
        model_dir: str | Path | None = None,
        dimension: int | None = None,
        max_length: int = MAX_LENGTH,
    ) -> None:
        # `App/` es la raíz de ejecución; resolver contra el paquete ancla las
        # rutas relativas a `App/` sin depender del cwd (como core/config.py).
        self._app_dir = Path(__file__).resolve().parents[2]
        crudo = str(model_dir if model_dir is not None else settings.embedding_model).strip()
        self._ruta_configurada = bool(crudo)
        self._dir = self._resolver(crudo)
        self._dimension = int(dimension or settings.embedding_dimension)
        self._max_length = max_length
        self._sesion: 'rt.InferenceSession | None' = None
        self._tokenizador: 'Tokenizer | None' = None
        self._carga = threading.Lock()

    def _resolver(self, ruta: str | Path | None) -> Path:
        crudo = str(ruta or '').strip()
        if not crudo:
            return self._app_dir
        camino = Path(crudo).expanduser()
        return camino if camino.is_absolute() else self._app_dir / camino

    @property
    def configured(self) -> bool:
        """True si `EMBEDDING_MODEL` apunta a un modelo ya descargado en disco.

        Permite que una ruta informe 'vectorización no disponible' sin intentar
        cargar los pesos (RNF6).
        """
        return (
            self._ruta_configurada
            and self._ruta_modelo().is_file()
            and self._ruta_tokenizer().is_file()
        )

    @property
    def dimension(self) -> int:
        """Dimensiones esperadas; coincide con `vector(...)` de la base de datos."""
        return self._dimension

    def _ruta_modelo(self) -> Path:
        # La variante ONNX del repo vive en el subdirectorio `onnx/`.
        return self._dir / 'onnx' / NOMBRE_MODELO

    def _ruta_tokenizer(self) -> Path:
        # El repo trae `tokenizer.json` también en la raíz; se usa `onnx/` si está.
        en_onnx = self._dir / 'onnx' / NOMBRE_TOKENIZER
        return en_onnx if en_onnx.is_file() else self._dir / NOMBRE_TOKENIZER

    async def embeber_consulta(self, texto: str) -> list[float]:
        """Vectoriza la pregunta del usuario con prefijo `query: `.

        Devuelve `list[float]` para que encaje directo en `Chunk.embedding` y en
        pgvector sin conversión intermedia.
        """
        return (await self._embeber([f'{PREFIJO_CONSULTA}{texto}']))[0]

    async def embeber_pasajes(self, textos: list[str]) -> list[list[float]]:
        """Vectoriza fragmentos de documento con prefijo `passage: `.

        Se pasa el lote completo: tokenizar de una en una daría largos distintos
        y el agrupamiento perdería la ventaja del padding por lote.
        """
        if not textos:
            return []
        return await self._embeber([f'{PREFIJO_PASAJE}{texto}' for texto in textos])

    async def generar_embedding(self, texto: str) -> list[float]:
        """Vectoriza un fragmento de documento: es `generarEmbedding(texto)` del
        diagrama de clases.

        Delega en `embeber_pasajes` para conservar el prefijo `passage: ` que
        exige e5.
        """
        return (await self.embeber_pasajes([texto]))[0]

    async def _embeber(self, textos_prefijados: list[str]) -> list[list[float]]:
        # La inferencia ONNX es intensiva en CPU: va en un hilo de trabajo para
        # no bloquear el loop de eventos mientras la API sirve otras peticiones.
        return await asyncio.to_thread(self._embeber_sync, textos_prefijados)

    def _embeber_sync(self, textos_prefijados: list[str]) -> list[list[float]]:
        sesion, tokenizador = self._cargar()

        codificados = tokenizador.encode_batch(textos_prefijados)
        entradas = {
            'input_ids': np.array([c.ids for c in codificados], dtype=np.int64),
            'attention_mask': np.array([c.attention_mask for c in codificados], dtype=np.int64),
            'token_type_ids': np.array([c.type_ids for c in codificados], dtype=np.int64),
        }

        nombres = [entrada.name for entrada in sesion.get_inputs()]
        faltantes = set(nombres) - set(entradas)
        if faltantes:
            raise EmbeddingError(
                f'El modelo ONNX pide entradas no proveídas: {sorted(faltantes)}. '
                'Verifica que descargaste la variante ONNX de '
                'multilingual-e5-small.'
            )
        # e5-small usa token_type_ids; otros proveedores lo omiten.
        usadas = {nombre: entradas[nombre] for nombre in nombres}

        ultima_capa = sesion.run(None, usadas)[0]
        vectores = self._mean_pool(np.asarray(ultima_capa), entradas['attention_mask'])
        normas = np.linalg.norm(vectores, axis=1, keepdims=True)
        vectores = vectores / np.clip(normas, a_min=1e-12, a_max=None)

        if vectores.shape[1] != self._dimension:
            raise EmbeddingError(
                f'El modelo devuelve {vectores.shape[1]} dimensiones, pero '
                f'EMBEDDING_DIMENSION={self._dimension}. Debe coincidir con '
                'chunk.embedding vector(...) del esquema.'
            )
        return [[float(valor) for valor in vector] for vector in vectores]

    def _cargar(self) -> tuple['rt.InferenceSession', 'Tokenizer']:
        """Carga perezosa con doble chequeo: los pesos se leen una sola vez.

        El tokenizer (~12 MB) se valida antes de abrir ONNX (cientos de MB) para
        que un directorio incompleto falle rápido y con mensaje claro.
        """
        if self._sesion is not None and self._tokenizador is not None:
            return self._sesion, self._tokenizador
        with self._carga:
            if self._sesion is not None and self._tokenizador is not None:
                return self._sesion, self._tokenizador

            if not self._ruta_configurada:
                raise EmbeddingError(
                    'Embeddings sin configurar: define EMBEDDING_MODEL en .env '
                    '(p. ej. ai-models/multilingual-e5-small).'
                )

            import onnxruntime as rt
            from tokenizers import Tokenizer

            ruta_tokenizer = self._ruta_tokenizer()
            if not ruta_tokenizer.is_file():
                raise EmbeddingError(
                    f'No encuentro el tokenizador en {self._dir} '
                    f'(busqué {ruta_tokenizer}). ' + _INSTRUCCION_DESCARGA
                )
            try:
                tokenizador = Tokenizer.from_file(str(ruta_tokenizer))
            except Exception as exc:  # tokenizers lanza errores de formato variados
                raise EmbeddingError(f'No se pudo leer {ruta_tokenizer}: {exc}') from exc

            tokenizador.enable_truncation(max_length=self._max_length)
            pad_id = tokenizador.token_to_id('<pad>')
            if pad_id is None:
                raise EmbeddingError(
                    f"El tokenizador de {self._dir} no tiene '<pad>'; la "
                    'descarga del modelo quedó incompleta. ' + _INSTRUCCION_DESCARGA
                )
            # Sin `length`: rellena hasta el largo del texto más largo del lote.
            tokenizador.enable_padding(pad_id=pad_id, pad_token='<pad>')

            ruta_modelo = self._ruta_modelo()
            if not ruta_modelo.is_file():
                raise EmbeddingError(
                    f'No encuentro {ruta_modelo}. ' + _INSTRUCCION_DESCARGA
                )
            try:
                sesion = rt.InferenceSession(
                    str(ruta_modelo), providers=['CPUExecutionProvider']
                )
            except Exception as exc:
                raise EmbeddingError(f'No se pudo cargar {ruta_modelo}: {exc}') from exc

            self._tokenizador = tokenizador
            self._sesion = sesion
            return sesion, tokenizador

    @staticmethod
    def _mean_pool(ultima_capa: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        """Media ponderada por attention_mask: los tokens de padding no cuentan."""
        mascara = np.expand_dims(attention_mask, -1).astype(ultima_capa.dtype)
        suma = np.sum(ultima_capa * mascara, axis=1)
        conteo = np.clip(np.sum(mascara, axis=1), a_min=1e-9, a_max=None)
        return suma / conteo
