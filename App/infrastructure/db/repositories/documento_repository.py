"""Repositorio de documentos sobre PostgreSQL."""

from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from domain.models.documento import Documento

_COLUMNS = (
    'id, usuario_id, nombre, formato, ruta_original, categoria, estado, '
    'fecha_carga, num_paginas, progreso, metadata'
)

# `num_chunks` es un dato derivado (no vive en `documento`): se calcula al leer
# para que la UI pueda mostrar "N chunks" sin una consulta adicional.
_SELECT_COLUMNS = (
    f'{_COLUMNS}, '
    '(select count(*) from chunk c where c.documento_id = documento.id) as num_chunks'
)


class DocumentoRepository:
    """Acceso a la tabla `documento` (RF1, RF6)."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def list(self, usuario_id: UUID | None = None) -> list[Documento]:
        if usuario_id is None:
            cursor = await self._conn.execute(
                f'select {_SELECT_COLUMNS} from documento order by fecha_carga desc'
            )
        else:
            cursor = await self._conn.execute(
                f"""
                select {_SELECT_COLUMNS}
                from documento
                where usuario_id = %s
                order by fecha_carga desc
                """,
                (usuario_id,),
            )
        return [Documento.model_validate(row) for row in await cursor.fetchall()]

    async def get(self, documento_id: UUID) -> Documento | None:
        cursor = await self._conn.execute(
            f'select {_SELECT_COLUMNS} from documento where id = %s',
            (documento_id,),
        )
        row = await cursor.fetchone()
        return Documento.model_validate(row) if row is not None else None

    async def create(self, documento: Documento) -> Documento:
        cursor = await self._conn.execute(
            f"""
            insert into documento (
                id, usuario_id, nombre, formato, ruta_original, categoria,
                estado, fecha_carga, num_paginas, progreso, metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                documento.num_paginas,
                documento.progreso,
                Jsonb(documento.metadatos),
            ),
        )
        row = await cursor.fetchone()
        if row is None:  # pragma: no cover - `insert ... returning` siempre devuelve fila
            raise RuntimeError('PostgreSQL no devolvió el documento insertado')
        return Documento.model_validate(row)

    async def update(self, documento: Documento) -> Documento:
        """Actualiza los datos editables del documento y devuelve su estado actual.

        El pipeline de ingesta lo usa para persistir los cambios de estado
        (`pendiente → procesando → listo/error`), el avance (`num_paginas`,
        `progreso`) y el motivo de un fallo en `metadata` (RNF6). La columna
        `fecha_actualizacion` se refresca con `now()` para que "Actividad
        reciente" tenga sentido.
        """
        cursor = await self._conn.execute(
            f"""
            update documento
            set nombre = %s, formato = %s, ruta_original = %s, categoria = %s,
                estado = %s, num_paginas = %s, progreso = %s, metadata = %s,
                fecha_actualizacion = now()
            where id = %s
            returning {_COLUMNS}
            """,
            (
                documento.nombre,
                documento.formato,
                documento.ruta_original,
                documento.categoria,
                documento.estado.value,
                documento.num_paginas,
                documento.progreso,
                Jsonb(documento.metadatos),
                documento.id,
            ),
        )
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError(f'PostgreSQL no devolvió el documento actualizado {documento.id}')
        return Documento.model_validate(row)

    async def delete(self, documento_id: UUID) -> bool:
        cursor = await self._conn.execute(
            'delete from documento where id = %s returning id',
            (documento_id,),
        )
        return await cursor.fetchone() is not None
