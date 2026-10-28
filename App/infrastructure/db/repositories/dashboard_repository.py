"""Repositorio de consultas agregadas para el Dashboard."""

from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import dict_row


class DashboardRepository:
    """Resumen de documentos, conversaciones, chunks y actividad reciente.

    Es una consulta de lectura que cruza varias tablas; no representa una
    entidad del dominio, por eso vive en un repositorio propio.
    """

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def resumen(self, usuario_id: UUID) -> tuple[int, int, int]:
        """Devuelve `(documentos, conversaciones, chunks)` del usuario."""
        cursor = await self._conn.execute(
            """
            select
              (select count(*) from documento where usuario_id = %(usuario_id)s)
                as documentos,
              (select count(*) from conversacion where usuario_id = %(usuario_id)s)
                as conversaciones,
              (
                select count(*)
                from chunk c
                join documento d on d.id = c.documento_id
                where d.usuario_id = %(usuario_id)s
              ) as chunks
            """,
            {'usuario_id': usuario_id},
        )
        row = await cursor.fetchone()

        if row is None:  # pragma: no cover - los count siempre devuelven fila
            return 0, 0, 0

        if isinstance(row, dict):
            return row['documentos'], row['conversaciones'], row['chunks']

        return row

    async def documentos_recientes(
        self,
        usuario_id: UUID,
        limite: int = 3,
    ) -> list[dict]:
        """Últimos documentos actualizados por el pipeline del usuario."""
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                """
                select
                  id::text as id,
                  'documento' as tipo,
                  nombre as titulo,
                  estado,
                  progreso,
                  null::bigint as mensajes,
                  fecha_actualizacion as fecha
                from documento
                where usuario_id = %(usuario_id)s
                order by fecha_actualizacion desc
                limit %(limite)s
                """,
                {'usuario_id': usuario_id, 'limite': limite},
            )
            return list(await cursor.fetchall())

    async def conversaciones_recientes(
        self,
        usuario_id: UUID,
        limite: int = 3,
    ) -> list[dict]:
        """Últimas conversaciones del usuario con su número de mensajes."""
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                """
                select
                  c.id::text as id,
                  'conversacion' as tipo,
                  coalesce(c.titulo, 'Sin título') as titulo,
                  null::text as estado,
                  null::integer as progreso,
                  count(m.id) as mensajes,
                  coalesce(max(m.fecha), c.fecha_creacion) as fecha
                from conversacion c
                left join mensaje m on m.conversacion_id = c.id
                where c.usuario_id = %(usuario_id)s
                group by c.id, c.titulo, c.fecha_creacion
                order by fecha desc
                limit %(limite)s
                """,
                {'usuario_id': usuario_id, 'limite': limite},
            )
            return list(await cursor.fetchall())

    async def actividad(
        self,
        usuario_id: UUID,
        limite_por_tipo: int = 3,
    ) -> list[dict]:
        """Mezcla documentos y conversaciones recientes, de más nuevo a más viejo."""
        documentos = await self.documentos_recientes(usuario_id, limite_por_tipo)
        conversaciones = await self.conversaciones_recientes(usuario_id, limite_por_tipo)
        eventos = documentos + conversaciones
        eventos.sort(key=lambda evento: evento['fecha'], reverse=True)
        return eventos
