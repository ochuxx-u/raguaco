"""Repositorio de conversaciones sobre PostgreSQL."""

from uuid import UUID

from psycopg import AsyncConnection

from domain.models.conversacion import Conversacion

_COLUMNS = 'id, usuario_id, fecha_creacion'


class ConversacionRepository:
    """Acceso a la tabla `conversacion`."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def list(self) -> list[Conversacion]:
        cursor = await self._conn.execute(
            f'select {_COLUMNS} from conversacion order by fecha_creacion desc'
        )
        return [Conversacion.model_validate(row) for row in await cursor.fetchall()]

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
            insert into conversacion (id, usuario_id, fecha_creacion)
            values (%s, %s, %s)
            returning {_COLUMNS}
            """,
            (
                conversacion.id,
                conversacion.usuario_id,
                conversacion.fecha_creacion,
            ),
        )
        row = await cursor.fetchone()
        if row is None:  # pragma: no cover - `insert ... returning` siempre devuelve fila
            raise RuntimeError('PostgreSQL no devolvió la conversación insertada')
        return Conversacion.model_validate(row)
