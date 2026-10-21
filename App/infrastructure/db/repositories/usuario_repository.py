"""Repositorio de usuarios sobre PostgreSQL."""

from uuid import UUID

from psycopg import AsyncConnection

from domain.models.usuario import Usuario

_COLUMNS = 'id, nombre, email'


class UsuarioRepository:
    """Acceso a la tabla `usuario`."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def get(self, usuario_id: UUID) -> Usuario | None:
        cursor = await self._conn.execute(
            f'select {_COLUMNS} from usuario where id = %s',
            (usuario_id,),
        )
        row = await cursor.fetchone()
        return Usuario.model_validate(row) if row is not None else None

    async def get_by_email(self, email: str) -> Usuario | None:
        cursor = await self._conn.execute(
            f'select {_COLUMNS} from usuario where lower(email) = lower(%s)',
            (email,),
        )
        row = await cursor.fetchone()
        return Usuario.model_validate(row) if row is not None else None

    async def create(self, usuario: Usuario) -> Usuario:
        cursor = await self._conn.execute(
            f"""
            insert into usuario (id, nombre, email)
            values (%s, %s, %s)
            returning {_COLUMNS}
            """,
            (usuario.id, usuario.nombre, str(usuario.email)),
        )
        row = await cursor.fetchone()
        if row is None:  # pragma: no cover - `insert ... returning` siempre devuelve fila
            raise RuntimeError('PostgreSQL no devolvió el usuario insertado')
        return Usuario.model_validate(row)
