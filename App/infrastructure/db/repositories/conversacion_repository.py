"""Repositorio de conversaciones sobre PostgreSQL."""

from uuid import UUID

from psycopg import AsyncConnection

from domain.models.conversacion import Conversacion, ConversacionResumen

_COLUMNS = 'id, usuario_id, titulo, fecha_creacion, fecha_actualizacion'


class ConversacionRepository:
    """Acceso a la tabla `conversacion`."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def list(self, usuario_id: UUID) -> list[Conversacion]:
        cursor = await self._conn.execute(
            f"""
            select {_COLUMNS} from conversacion
            where usuario_id = %s
            order by fecha_creacion desc
            """,
            (usuario_id,),
        )
        return [Conversacion.model_validate(row) for row in await cursor.fetchall()]

    async def list_resumen(self, usuario_id: UUID) -> list[ConversacionResumen]:
        """Conversaciones del usuario con su última pregunta y total de mensajes.

        El Historial necesita ese resumen por fila; resolverlo en una sola
        consulta evita pedir los mensajes de cada conversación por separado.
        """
        cursor = await self._conn.execute(
            """
            select
              c.id,
              c.usuario_id,
              c.titulo,
              c.fecha_creacion,
              c.fecha_actualizacion,
              (
                select count(*)
                from mensaje m
                where m.conversacion_id = c.id
              )::int as mensaje_count,
              (
                select m.contenido
                from mensaje m
                where m.conversacion_id = c.id and m.rol = 'usuario'
                order by m.fecha desc, m.id desc
                limit 1
              ) as ultima_pregunta
            from conversacion c
            where c.usuario_id = %s
            order by c.fecha_actualizacion desc, c.fecha_creacion desc
            """,
            (usuario_id,),
        )
        return [
            ConversacionResumen.model_validate(row) for row in await cursor.fetchall()
        ]

    async def get(self, conversacion_id: UUID) -> Conversacion | None:
        cursor = await self._conn.execute(
            f'select {_COLUMNS} from conversacion where id = %s',
            (conversacion_id,),
        )
        row = await cursor.fetchone()
        return Conversacion.model_validate(row) if row is not None else None

    async def create(self, conversacion: Conversacion) -> Conversacion:
        cursor = await self._conn.execute(
            f"""
            insert into conversacion (
              id, usuario_id, titulo, fecha_creacion, fecha_actualizacion
            )
            values (%s, %s, %s, %s, %s)
            returning {_COLUMNS}
            """,
            (
                conversacion.id,
                conversacion.usuario_id,
                conversacion.titulo,
                conversacion.fecha_creacion,
                conversacion.fecha_actualizacion,
            ),
        )
        row = await cursor.fetchone()
        if row is None:  # pragma: no cover - `insert ... returning` siempre devuelve fila
            raise RuntimeError('PostgreSQL no devolvió la conversación insertada')
        return Conversacion.model_validate(row)

    async def touch(self, conversacion_id: UUID) -> None:
        """Refresca `fecha_actualizacion` para ordenar el Historial por actividad."""
        await self._conn.execute(
            'update conversacion set fecha_actualizacion = now() where id = %s',
            (conversacion_id,),
        )
