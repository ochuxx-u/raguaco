"""Repositorio de documentos sobre PostgreSQL."""

from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from domain.models.documento import Documento

_COLUMNS = (
    'id, usuario_id, nombre, formato, ruta_original, categoria, estado, '
    'fecha_carga, metadata'
)


class DocumentoRepository:
    """Acceso a la tabla `documento` (RF1, RF6)."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def list(self, usuario_id: UUID | None = None) -> list[Documento]:
        if usuario_id is None:
            cursor = await self._conn.execute(
                f'select {_COLUMNS} from documento order by fecha_carga desc'
            )
        else:
            cursor = await self._conn.execute(
                f"""
                select {_COLUMNS}
                from documento
                where usuario_id = %s
                order by fecha_carga desc
                """,
                (usuario_id,),
            )
        return [Documento.model_validate(row) for row in await cursor.fetchall()]

    async def get(self, documento_id: UUID) -> Documento | None:
        cursor = await self._conn.execute(
            f'select {_COLUMNS} from documento where id = %s',
            (documento_id,),
        )
        row = await cursor.fetchone()
        return Documento.model_validate(row) if row is not None else None

    async def create(self, documento: Documento) -> Documento:
        cursor = await self._conn.execute(
            f"""
            insert into documento (
                id, usuario_id, nombre, formato, ruta_original, categoria,
                estado, fecha_carga, metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning {_COLUMNS}
            """,
            (
                documento.id,
                documento.usuario_id,
                documento.nombre,
                documento.formato,
                documento.ruta_original,
                documento.categoria,
                documento.estado.value,
                documento.fecha_carga,
                Jsonb(documento.metadatos),
            ),
        )
        row = await cursor.fetchone()
        if row is None:  # pragma: no cover - `insert ... returning` siempre devuelve fila
            raise RuntimeError('PostgreSQL no devolvió el documento insertado')
        return Documento.model_validate(row)

    async def delete(self, documento_id: UUID) -> bool:
        cursor = await self._conn.execute(
            'delete from documento where id = %s returning id',
            (documento_id,),
        )
        return await cursor.fetchone() is not None
