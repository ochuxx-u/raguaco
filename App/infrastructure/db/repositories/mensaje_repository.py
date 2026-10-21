"""Repositorio de mensajes sobre PostgreSQL."""

from uuid import UUID

from psycopg import AsyncConnection

from domain.models.mensaje import Mensaje

_COLUMNS = 'id, conversacion_id, rol, contenido, fecha'


class MensajeRepository:
    """Acceso a la tabla `mensaje`."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def list(self, conversacion_id: UUID) -> list[Mensaje]:
        cursor = await self._conn.execute(
            f"""
            select {_COLUMNS}
            from mensaje
            where conversacion_id = %s
            order by fecha
            """,
            (conversacion_id,),
        )
        return [Mensaje.model_validate(row) for row in await cursor.fetchall()]

    async def create(self, mensaje: Mensaje) -> Mensaje:
        cursor = await self._conn.execute(
            f"""
            insert into mensaje (id, conversacion_id, rol, contenido, fecha)
            values (%s, %s, %s, %s, %s)
            returning {_COLUMNS}
            """,
            (
                mensaje.id,
                mensaje.conversacion_id,
                mensaje.rol,
                mensaje.contenido,
                mensaje.fecha,
            ),
        )
        row = await cursor.fetchone()
        if row is None:  # pragma: no cover - `insert ... returning` siempre devuelve fila
            raise RuntimeError('PostgreSQL no devolvió el mensaje insertado')
        return Mensaje.model_validate(row)
