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

    embedding_model: str = Field(
        default='ai-models/multilingual-e5-small',
        description=(
            'Directorio del modelo de embeddings descargado con hf download '
            '(intfloat/multilingual-e5-small). Ruta relativa a `App/`; los '
            'pesos NO viajan en git, ver README.'
        ),
    )

    embedding_dimension: int = Field(
        default=384,
        gt=0,
        description=(
            'Dimensiones que produce el modelo; debe coincidir con '
            'chunk.embedding vector(384) de App/migrations/001_schema.sql.'
        ),
    )

    storage_dir: str = Field(
        default='storage',
        description=(
            'Directorio donde StorageService guarda los archivos originales. '
            'Ruta relativa a App/ o absoluta (variable STORAGE_DIR).'
        ),
    )

    tts_model: str = Field(
        default='ai-models/kokoro-82m',
        description=(
            'Directorio del modelo TTS Kokoro-82M descargado con hf download. '
            'Ruta relativa a App/; los pesos NO viajan en git (ver README).'
        ),
    )

    tts_model_file: str = Field(
        default='onnx/model_quantized.onnx',
        description=(
            'Archivo ONNX dentro de TTS_MODEL. `onnx/model_quantized.onnx` '
            '(int8) prioriza la latencia; `onnx/model.onnx` (fp32) da la '
            'máxima calidad a costa de ~1,4x más tiempo de síntesis.'
        ),
    )

    tts_voice: str = Field(
        default='ef_dora',
        description=(
            'Voz de Kokoro (archivo `voices/{voz}.bin`). `ef_dora` es la voz '
            'femenina en español; `em_alex` es la masculina.'
        ),
    )

    tts_language: str = Field(
        default='es',
        description='Idioma para la fonemización con espeak-ng (lang de Kokoro).',
    )

    tts_speed: float = Field(
        default=1.0,
        gt=0,
        le=2,
        description='Velocidad de habla de Kokoro (1.0 = normal).',
    )

    tts_output_dir: str = Field(
        default='storage/tts',
        description=(
            'Directorio donde se escriben los WAV fragmentados. Ruta relativa '
            'a App/ o absoluta.'
        ),
    )

    tts_retention_minutes: int = Field(
        default=30,
        ge=0,
        description=(
            'Minutos que se conservan los WAV de una síntesis antes de '
            'borrarse al preparar la siguiente. 0 desactiva la limpieza.'
        ),
    )

    tts_first_chunk_chars: int = Field(
        default=100,
        gt=0,
        description=(
            'Tamaño máximo del primer fragmento. Se mantiene corto para que el '
            'primer audio llegue cuanto antes; el resto usa TTS_CHUNK_CHARS.'
        ),
    )

    tts_chunk_chars: int = Field(
        default=120,
        gt=0,
        description=(
            'Tamaño máximo de los fragmentos siguientes. Se mantiene acotado '
            'para que cada WAV esté listo antes de que termine de sonar el '
            'anterior (reproducción sin cortes).'
        ),
    )

    tts_warmup: bool = Field(
        default=True,
        description=(
            'Carga el modelo TTS en segundo plano al arrancar la API, de modo '
            'que la primera petición no pague la carga de los pesos ONNX.'
        ),
    )

    stt_model: str = Field(
        default='ai-models/faster-whisper-small',
        description=(
            'Directorio del modelo faster-whisper descargado con hf download. '
            'Ruta relativa a App/; los pesos NO viajan en git (ver README).'
        ),
    )

    stt_language: str = Field(
        default='es',
        description=(
            'Idioma forzado para la transcripción (p. ej. es). Vacío o "auto" '
            'deja que Whisper lo detecte.'
        ),
    )

    stt_device: str = Field(
        default='cpu',
        description='Dispositivo de faster-whisper: cpu o cuda.',
    )

    stt_compute_type: str = Field(
        default='int8',
        description=(
            'Precisión de cómputo de faster-whisper. int8 es la más rápida en '
            'CPU; float16 solo tiene sentido con cuda.'
        ),
    )

    stt_beam_size: int = Field(
        default=1,
        ge=1,
        description='Ancho de búsqueda de Whisper: 1 (greedy) es el más rápido.',
    )

    stt_threads: int = Field(
        default=0,
        ge=0,
        description=(
            'Hilos de CPU para Whisper. 0 deja que faster-whisper use el '
            'valor por defecto (todos los núcleos disponibles).'
        ),
    )

    stt_warmup: bool = Field(
        default=True,
        description=(
            'Carga el modelo STT en segundo plano al arrancar la API para que '
            'la primera consulta de voz no pague la carga del modelo.'
        ),
    )

    voice_silence_seconds: float = Field(
        default=1.5,
        gt=0,
        description=(
            'Segundos de silencio, después de haber detectado voz, que cierran '
            'la pregunta y disparan el procesamiento automático.'
        ),
    )

    voice_chunk_seconds: float = Field(
        default=0.5,
        gt=0,
        description=(
            'Tamaño del bloque de micrófono que analiza el detector de voz. '
            'Bloques pequeños reaccionan antes al silencio.'
        ),
    )

    voice_min_utterance_seconds: float = Field(
        default=0.35,
        gt=0,
        description=(
            'Duración mínima de voz para procesar una pregunta; descarta '
            'ruidos y toses.'
        ),
    )

    voice_max_utterance_seconds: float = Field(
        default=20.0,
        gt=0,
        description=(
            'Tope de audio que se acumula antes de procesar aunque no haya '
            'silencio (preguntas muy largas).'
        ),
    )

    voice_silence_peak: float = Field(
        default=0.12,
        gt=0,
        description=(
            'Nivel de pico (amplitud máxima) por debajo del cual un bloque se '
            'considera silencio. El script de prueba lo eleva según el ruido '
            'ambiente; súbelo si el ruido impide cerrar la pregunta.'
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
