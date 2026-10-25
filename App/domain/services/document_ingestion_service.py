"""Orquestador del pipeline de ingesta de documentos (RF2).

`DocumentIngestionService` implementa la secuencia ETL del diagrama
`Docs/UML/imagenes/DIA-SECUENCIA_ETL-DOCUMENTS.png`, de principio a fin, para
una petición `POST /documents (archivo)`:

1. `guardarOriginal(archivo)` → `rutaOriginal` — `StorageService`.
2. Registro del `Documento` — `DocumentoRepository`.
3. `extraerTexto(archivo)` → `texto` — `DocumentLoader`.
4. `limpiar(texto)` → `textoLimpio` — `TextCleaner`.
5. `fragmentar(textoLimpio)` → `chunks` — `ChunkingService`.
6. *loop por cada chunk*: `generarEmbedding(chunk.contenido)` → `embedding` —
   `EmbeddingService`.
7. `guardarChunks(chunks con embeddings)` → `ok` — `VectorRepository`
   (INSERT de chunks + embeddings).
8. `documento listo` → la API responde `201 Created`.

Dos desviaciones conscientes respecto al diagrama:

(a) La fila de `documento` se inserta **al inicio** del pipeline (paso 2) y sus
    estados se persisten con `update` (`pendiente → procesando → listo/error`),
    no junto a los chunks en el paso 7. El diagrama resume la persistencia como
    "INSERT documento, chunks, embeddings", pero insertar el documento primero
    permite observar su estado en la UI mientras el pipeline corre y registrar
    el motivo de un fallo en `metadatos['error']` (RNF6).

(b) La extracción de texto (paso 3) se hace sobre la **copia guardada** en el
    paso 1 (`rutaOriginal`), no sobre el archivo recibido por la API: son los
    mismos bytes, y así el pipeline no depende del transporte (¿ruta, stream o
    subida?) ni de que el original desaparezca después de guardarlo.

Un fallo en el procesamiento de un documento no tumba la aplicación (RNF6): el
documento queda en estado `error` con el motivo en `metadatos['error']` y el
servicio lo devuelve en lugar de relanzar la excepción.
"""

import os
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID

from domain.models.chunk import Chunk
from domain.models.documento import Documento
from infrastructure.db.repositories.documento_repository import DocumentoRepository
from infrastructure.embeddings.embedding_service import EmbeddingService
from infrastructure.loaders.chunking_service import ChunkingService
from infrastructure.loaders.document_loader import DocumentLoader
from infrastructure.loaders.text_cleaner import TextCleaner
from infrastructure.storage.local_storage import StorageService
from infrastructure.vector.pgvector_repository import VectorRepository


class DocumentIngestionService:
    """Ejecuta el pipeline ETL de ingesta de un documento (RF2).

    Recibe sus componentes por constructor (inyección de dependencias) para que
    cada pieza sea sustituible (RNF1): almacenamiento, cargador, limpiador,
    fragmentador, embeddings, repositorio vectorial y repositorio de documentos.
    """

    def __init__(
        self,
        storage: StorageService,
        loader: DocumentLoader,
        cleaner: TextCleaner,
        chunking: ChunkingService,
        embeddings: EmbeddingService,
        vector_repo: VectorRepository,
        documento_repo: DocumentoRepository,
    ) -> None:
        self._storage = storage
        self._loader = loader
        self._cleaner = cleaner
        self._chunking = chunking
        self._embeddings = embeddings
        self._vector_repo = vector_repo
        self._documento_repo = documento_repo

    async def procesar_documento(
        self,
        archivo: str | Path | BinaryIO,
        *,
        usuario_id: UUID,
        categoria: str | None = None,
        metadatos: dict[str, Any] | None = None,
    ) -> Documento:
        """Procesa un archivo con el pipeline ETL completo y devuelve su `Documento`.

        El resultado final refleja el desenlace del pipeline: `estado` `listo`
        con los fragmentos y sus embeddings ya guardados, o `estado` `error` con
        el motivo en `metadatos['error']` (RNF6). Los errores de registro del
        documento (clave ajena inexistente, validación) sí se propagan para que
        la API los traduzca a 404/422; los del procesamiento no.

        Pasos, según el diagrama de secuencia: `guardarOriginal(archivo)` →
        `extraerTexto` (sobre la copia guardada) → `limpiar` → `fragmentar` →
        `generarEmbedding` por cada fragmento → `guardarChunks` → documento
        listo.
        """
        # guardarOriginal(archivo) → rutaOriginal
        ruta_original = self._storage.guardar_original(archivo)

        # Desviación (a): el documento se registra al inicio, en estado
        # `pendiente`, para poder observar sus estados durante el pipeline.
        # El modelo deriva `nombre` y `formato` de la ruta.
        try:
            documento = Documento(
                usuario_id=usuario_id,
                ruta_original=ruta_original,
                categoria=categoria,
                metadatos={**(metadatos or {}), 'tamano_bytes': os.path.getsize(ruta_original)},
            )
            documento = await self._documento_repo.create(documento)
        except Exception:
            # El registro no llegó a completarse (usuario inexistente,
            # validación): la copia huérfana no debe quedarse en el almacén.
            self._storage.eliminar_original(ruta_original)
            raise

        documento.iniciar_procesamiento()
        documento = await self._documento_repo.update(documento)

        try:
            # extraerTexto(archivo) → texto (desviación (b): sobre la copia)
            texto = self._loader.extraer_texto(ruta_original)
            # limpiar(texto) → textoLimpio
            texto_limpio = self._cleaner.limpiar(texto)
            # fragmentar(textoLimpio) → chunks
            fragmentos = self._chunking.fragmentar(texto_limpio)

            chunks: list[Chunk] = []
            for fragmento in fragmentos:
                # loop [por cada chunk]: generarEmbedding(chunk.contenido) → embedding
                embedding = await self._embeddings.generar_embedding(fragmento.contenido)
                chunks.append(
                    Chunk(
                        documento_id=documento.id,
                        contenido=fragmento.contenido,
                        indice=fragmento.indice,
                        pagina=fragmento.pagina,
                        metadatos=fragmento.metadatos,
                        embedding=embedding,
                    )
                )

            # guardarChunks(chunks con embeddings) → ok
            await self._vector_repo.guardar_chunks(chunks)

            # documento listo
            documento.marcar_listo()
            documento = await self._documento_repo.update(documento)
            return documento
        except Exception as exc:
            # RNF6: el fallo de un documento no tumba la app; el motivo queda en
            # `metadatos['error']`. Solo el propio `update` del error se deja
            # propagar: sin él no hay nada mejor que hacer.
            documento.marcar_error(f'{type(exc).__name__}: {exc}')
            documento = await self._documento_repo.update(documento)
            return documento
