import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.deps import (
    get_llm_service,
    get_stt_service,
    get_tts_engine,
    get_voice_service,
)
from api.routes.conversations import router as conversations_router
from api.routes.dashboard import router as dashboard_router
from api.routes.documents import router as documents_router
from api.routes.queries import router as queries_router
from api.routes.users import router as users_router
from api.routes.voice import router as voice_router
from core.config import settings
from infrastructure.db.session import close_pool, open_pool


def _preparar_voz() -> None:
    """Limpia WAV viejos y precarga STT/TTS sin bloquear el arranque (RNF6).

    La carga de Kokoro tarda ~0,7 s y la de faster-whisper ~2 s; hacerlas en un
    hilo aparte evita que la primera petición de voz pague esa latencia. Si
    algún modelo no está descargado, solo se registra el aviso.
    """
    try:
        get_voice_service().limpiar_antiguos()
        if settings.tts_warmup:
            get_tts_engine().precargar()
        if settings.stt_warmup:
            get_stt_service().precargar()
    except Exception as exc:  # noqa: BLE001 - la API debe arrancar igual
        print(f'[voz] no se pudo preparar el motor de voz: {exc}', flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Abre el pool de PostgreSQL al arrancar y cierra recursos al apagar."""
    await open_pool()
    if settings.tts_warmup or settings.stt_warmup:
        threading.Thread(
            target=_preparar_voz,
            name='voz-warmup',
            daemon=True,
        ).start()
    yield
    await get_llm_service().aclose()
    await close_pool()


app = FastAPI(lifespan=lifespan)

app.include_router(conversations_router)
app.include_router(dashboard_router)
app.include_router(documents_router)
app.include_router(queries_router)
app.include_router(users_router)
app.include_router(voice_router)


@app.get('/')
def root():
    return {'message': 'Changing'}


@app.get('/health')
def health():
    return {'message': 'OK!'}
