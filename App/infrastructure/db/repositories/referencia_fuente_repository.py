"""Repositorio de referencias a fuentes sobre PostgreSQL."""

from uuid import UUID

from psycopg import AsyncConnection

from domain.models.referencia_fuente import FuenteDetalle, ReferenciaFuente

_COLUMNAS = 'id, mensaje_id, chunk_id, similitud'

_PLANTILLA_FILA = '(%s, %s, %s, %s, %s)'

# Datos que necesita la UI para citar una fuente: el fragmento y su documento.
_COLUMNAS_DETALLE = """
    rf.id,
    rf.mensaje_id,
    rf.chunk_id,
    coalesce(rf.similitud, 0.0) as similitud,
    rf.orden,
    c.documento_id,
    c.pagina,
    c.indice,
    c.contenido as fragmento,
    d.nombre as documento,
    d.formato,
    d.categoria
"""


class ReferenciaFuenteRepository:
    """Acceso a la tabla `referencia_fuente` (RF8, RNF7)."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def create_many(self, referencias: list[ReferenciaFuente]) -> int:
        """Inserta las fuentes de un mensaje y devuelve las insertadas.

        El `orden` (1, 2, 3, …) se deriva de la posición en la lista: es la
        marca `[n]` que la respuesta cita y lo que la pantalla de evidencia
        muestra como "Fuente 1", "Fuente 2" (RF8). La lista vacía no toca la
        base de datos.
        """
        if not referencias:
            return 0

        valores: list = []
        for orden, referencia in enumerate(referencias, start=1):
            valores.extend(
                (
                    referencia.id,
                    referencia.mensaje_id,
                    referencia.chunk_id,
                    referencia.similitud,
                    orden,
                )
            )

        await self._conn.execute(
            'insert into referencia_fuente (id, mensaje_id, chunk_id, similitud, orden) values '
            + ', '.join([_PLANTILLA_FILA] * len(referencias)),
            valores,
        )
        return len(referencias)

    async def list(self, mensaje_id: UUID) -> list[ReferenciaFuente]:
        """Fuentes de un mensaje, en el orden en que la respuesta las cita."""
        cursor = await self._conn.execute(
            f"""
            select {_COLUMNAS}
            from referencia_fuente
            where mensaje_id = %s
            order by orden, id
            """,
            (mensaje_id,),
        )
        return [ReferenciaFuente.model_validate(row) for row in await cursor.fetchall()]

    async def list_detalle(self, mensaje_id: UUID) -> list[FuenteDetalle]:
        """Fuentes de un mensaje con documento, página y fragmento."""
        return await self.list_detalle_por_mensajes([mensaje_id])

    async def list_detalle_por_mensajes(
        self, mensaje_ids: list[UUID]
    ) -> list[FuenteDetalle]:
        """Fuentes de varios mensajes, para cargar un historial completo de una vez."""
        if not mensaje_ids:
            return []

        cursor = await self._conn.execute(
            f"""
            select {_COLUMNAS_DETALLE}
            from referencia_fuente rf
            join chunk c on c.id = rf.chunk_id
            join documento d on d.id = c.documento_id
            where rf.mensaje_id = any(%s)
            order by rf.mensaje_id, rf.orden nulls last, rf.id
            """,
            (mensaje_ids,),
        )
        return [FuenteDetalle.model_validate(row) for row in await cursor.fetchall()]
