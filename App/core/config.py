"""Configuración de la aplicación.

Los valores se leen de variables de entorno y, en desarrollo, del archivo
`App/.env` (la aplicación se ejecuta con `App/` como raíz). Ningún secreto
debe quedar escrito en el código (RNF5).
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _APP_DIR.parent


class Settings(BaseSettings):
    """Variables de entorno que necesita el backend."""

    model_config = SettingsConfigDict(
        # Se acepta `.env` en la raíz del repositorio o dentro de `App/`.
        env_file=(_APP_DIR / '.env', _REPO_ROOT / '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    database_url: str = Field(
        default='postgresql://raguaco:raguaco@localhost:5433/raguaco',
        min_length=1,
        description=(
            'Cadena de conexión de PostgreSQL (libpq). En local apunta al '
            'contenedor de Docker; en producción, a Supabase.'
        ),
    )


settings = Settings()
