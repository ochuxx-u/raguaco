"""Configuración de la aplicación.

Los valores se leen de variables de entorno y, en desarrollo, del archivo
`App/.env` (la aplicación se ejecuta con `App/` como raíz). Ningún secreto
debe quedar escrito en el código (RNF5).
"""

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _APP_DIR.parent

# OpenCode Go expone un API OpenAI-compatible (`/chat/completions`, Bearer).
_OPENCODE_GO_BASE_URL = 'https://opencode.ai/zen/go/v1'


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

    llm_base_url: str = Field(
        default=_OPENCODE_GO_BASE_URL,
        min_length=1,
        description=(
            'URL base (OpenAI-compatible) del proveedor del LLM. Por defecto '
            'OpenCode Go; el servicio llama a `{LLM_BASE_URL}/chat/completions`.'
        ),
    )

    llm_model: str = Field(
        default='',
        description=(
            'Modelo del LLM dentro del proveedor (p. ej. deepseek-v4-flash). '
            'Lista completa en `{LLM_BASE_URL}/models`.'
        ),
    )

    llm_api_key: str = Field(
        default='',
        description=(
            'API key del LLM (OpenCode Go, de https://opencode.ai/auth). Solo '
            'se usa en el backend; nunca se expone al cliente.'
        ),
    )

    @model_validator(mode='before')
    @classmethod
    def _descartar_envios_vacios(cls, datos: object) -> object:
        """`LLM_BASE_URL=` (vacío) en `.env` debe usar el default, no aplastarlo."""
        if isinstance(datos, dict):
            return {
                clave: valor
                for clave, valor in datos.items()
                if not (isinstance(valor, str) and not valor.strip())
            }
        return datos


settings = Settings()
