import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.deps import get_llm_service, get_tts_engine, get_voice_service
from api.routes.conversations import router as conversations_router
from api.routes.documents import router as documents_router
from api.routes.queries import router as queries_router
from api.routes.users import router as users_router
from api.routes.voice import router as voice_router
from core.config import settings
from infrastructure.db.session import close_pool, open_pool


def _preparar_voz() -> None:
    """Limpia WAV viejos y precarga Kokoro sin bloquear el arranque (RNF6).

    La carga de los pesos tarda ~0,7 s (variante cuantizada); hacerla en un
    hilo aparte evita que la primera petición de voz pague esa latencia. Si el
    modelo no está descargado, solo se registra el aviso.
    """
    try:
        get_voice_service().limpiar_antiguos()
        get_tts_engine().precargar()
    except Exception as exc:  # noqa: BLE001 - la API debe arrancar igual
        print(f'[tts] no se pudo preparar el motor de voz: {exc}', flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Abre el pool de PostgreSQL al arrancar y cierra recursos al apagar."""
    await open_pool()
    if settings.tts_warmup:
        threading.Thread(
            target=_preparar_voz,
            name='tts-warmup',
            daemon=True,
        ).start()
    yield
    await get_llm_service().aclose()
    await close_pool()


app = FastAPI(lifespan=lifespan)

app.include_router(conversations_router)
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
