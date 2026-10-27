"""Repositorio de referencias a fuentes sobre PostgreSQL."""

from uuid import UUID

from psycopg import AsyncConnection

from domain.models.referencia_fuente import ReferenciaFuente

_COLUMNAS = 'id, mensaje_id, chunk_id, similitud'

_PLANTILLA_FILA = '(%s, %s, %s, %s, %s)'


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
