"""Pool de conexiones a PostgreSQL.

El pool se crea sin abrir conexiones y se abre/cierra en el ciclo de vida de
FastAPI (`App/main.py`). Cada petición toma una conexión del pool mediante
`api.deps.get_db`; el context manager de psycopg_pool hace commit al terminar
sin errores y rollback si la petición falla.
"""

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from core.config import settings

pool = AsyncConnectionPool(
    conninfo=settings.database_url,
    min_size=1,
    max_size=10,
    open=False,
    # Las filas se devuelven como dict, que es lo que consumen los modelos
    # Pydantic del dominio (`Documento.model_validate(fila)`).
    kwargs={'row_factory': dict_row},
)


async def open_pool() -> None:
    """Abre el pool y espera a que la base acepte conexiones."""
    await pool.open(wait=True, timeout=10)


async def close_pool() -> None:
    """Cierra las conexiones al apagar la aplicación."""
    await pool.close()
