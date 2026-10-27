"""Repositorio vectorial sobre PostgreSQL + pgvector.

Es el `VectorRepository` del diagrama de clases: `guardarChunks(chunks)` en la
ingesta y `buscarSimilares(embedding, {parametros})` en la recuperación (RF6),
que devuelve los fragmentos similares a una consulta con su similitud acotada
al rango 0..1 que espera `ReferenciaFuente.similitud`.

El diagrama de secuencia (ETL de documentos) resume la persistencia como
"INSERT documento, chunks, embeddings", pero la fila de `documento` la inserta
`DocumentoRepository` (`infrastructure/db/repositories/documento_repository.py`):
así el documento se observa con sus estados `pendiente → procesando →
listo/error` mientras corre el pipeline. Aquí se guardan los fragmentos con sus
vectores, es decir, `chunks` + `embeddings`.
"""

from typing import Any
from uuid import UUID

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


def _deserializar_embedding(valor: Any) -> list[float]:
    """Convierte la columna `vector` de PostgreSQL en `list[float]`.

    Sin adaptador de pgvector registrado, psycopg devuelve la columna como su
    literal de texto (`'[0.1,0.2,...]'`); si algún día llega ya convertida en
    secuencia numérica, se acepta tal cual.
    """
    if isinstance(valor, str):
        return [float(parte) for parte in valor.strip().strip('[]').split(',') if parte.strip()]
    return [float(parte) for parte in valor]


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

    async def buscar_similares(
        self,
        embedding: list[float],
        usuario_id: UUID,
        *,
        top_k: int = 5,
        umbral: float = 0.0,
        filtros: dict[str, Any] | None = None,
    ) -> list[tuple[Chunk, float]]:
        """`buscarSimilares(embedding, {parametros})`: los fragmentos más similares.

        Busca solo entre los documentos de `usuario_id` y devuelve cada `Chunk`
        con su similitud coseno `1 - (embedding <=> consulta)`, **acotada a
        0..1** para que `ReferenciaFuente.similitud` nunca se salga de su rango.
        El `umbral` descarta lo poco relacionado antes de devolver (es lo que
        permite el rechazo explícito de RF9) y `top_k` acota el número de
        resultados.

        `filtros` soporta los opcionales de RF6: `documento_ids` (lista de
        UUIDs), `categoria` (la del documento) y `metadatos` (contención JSONB
        sobre los del fragmento). Una clave desconocida es un `ValueError`, no
        un filtro silencioso.
        """
        filtros = filtros or {}
        desconocidos = set(filtros) - {'documento_ids', 'categoria', 'metadatos'}
        if desconocidos:
            raise ValueError(f'Filtros de búsqueda no soportados: {sorted(desconocidos)}')

        consulta = _serializar_embedding(embedding)

        condiciones = ['d.usuario_id = %s']
        parametros_where: list[Any] = [usuario_id]
        if 'documento_ids' in filtros:
            condiciones.append('c.documento_id = any(%s)')
            parametros_where.append([UUID(str(valor)) for valor in filtros['documento_ids']])
        if 'categoria' in filtros:
            condiciones.append('d.categoria = %s')
            parametros_where.append(filtros['categoria'])
        if 'metadatos' in filtros:
            condiciones.append('c.metadata @> %s::jsonb')
            parametros_where.append(Jsonb(filtros['metadatos']))

        # El umbral se aplica sobre la misma expresión de similitud que se
        # devuelve; se repite en el `where` porque SQL no reutiliza el alias del
        # `select` en sus cláusulas.
        condiciones.append('1 - (c.embedding <=> %s::vector) >= %s')
        parametros_where.extend((consulta, float(umbral)))

        cursor = await self._conn.execute(
            f"""
            select c.id, c.documento_id, c.contenido, c.indice, c.pagina,
                   c.metadata, c.embedding,
                   1 - (c.embedding <=> %s::vector) as similitud
            from chunk as c
            join documento as d on d.id = c.documento_id
            where {' and '.join(condiciones)}
            order by c.embedding <=> %s::vector
            limit %s
            """,
            [consulta, *parametros_where, consulta, max(1, int(top_k))],
        )

        resultados: list[tuple[Chunk, float]] = []
        for fila in await cursor.fetchall():
            similitud = min(1.0, max(0.0, float(fila['similitud'])))
            chunk = Chunk.model_validate({**fila, 'embedding': _deserializar_embedding(fila['embedding'])})
            resultados.append((chunk, similitud))
        return resultados
