"""Repositorio vectorial sobre PostgreSQL + pgvector.

Es el `VectorRepository` del diagrama de clases, con `guardarChunks(chunks)`;
`buscarSimilares(...)` pertenece a la fase de recuperación y se implementará
aparte.

El diagrama de secuencia (ETL de documentos) resume la persistencia como
"INSERT documento, chunks, embeddings", pero la fila de `documento` la inserta
`DocumentoRepository` (`infrastructure/db/repositories/documento_repository.py`):
así el documento se observa con sus estados `pendiente → procesando →
listo/error` mientras corre el pipeline. Aquí se guardan los fragmentos con sus
vectores, es decir, `chunks` + `embeddings`.
"""

from typing import Any

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from domain.models.chunk import Chunk

_COLUMNAS = 'id, documento_id, contenido, indice, pagina, metadata, embedding'

# Cada fila lleva 7 parámetros; el último es el embedding como literal de texto
# pgvector (`'[0.1,0.2,...]'`) casteado en SQL con `%s::vector`.
_PLANTILLA_FILA = '(%s, %s, %s, %s, %s, %s, %s::vector)'


def _serializar_embedding(embedding: list[float]) -> str:
    """Serializa un vector como literal de texto pgvector: `'[0.1,0.2,...]'`.

    pgvector acepta ese formato de texto y lo convierte al tipo `vector` al
    aplicarle el casteo `::vector` en la sentencia.
    """
    return '[' + ','.join(str(float(valor)) for valor in embedding) + ']'


class VectorRepository:
    """Acceso a la tabla `chunk` (fragmentos con su embedding)."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def guardar_chunks(self, chunks: list[Chunk]) -> int:
        """Inserta los fragmentos con sus embeddings y devuelve los insertados.

        Los `Chunk` llegan ya vectorizados desde el pipeline de ingesta; aquí se
        insertan en `chunk (id, documento_id, contenido, indice, pagina,
        metadata, embedding)`. La lista vacía no toca la base de datos.
        """
        if not chunks:
            return 0

        valores: list[Any] = []
        for chunk in chunks:
            valores.extend(
                (
                    chunk.id,
                    chunk.documento_id,
                    chunk.contenido,
                    chunk.indice,
                    chunk.pagina,
                    Jsonb(chunk.metadatos),
                    _serializar_embedding(chunk.embedding),
                )
            )

        # Una sola sentencia multi-valores: todos los fragmentos del documento
        # se insertan juntos.
        await self._conn.execute(
            f'insert into chunk ({_COLUMNAS}) values '
            + ', '.join([_PLANTILLA_FILA] * len(chunks)),
            valores,
        )
        return len(chunks)
