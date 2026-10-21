from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes.conversations import router as conversations_router
from api.routes.documents import router as documents_router
from api.routes.queries import router as queries_router
from api.routes.users import router as users_router
from api.routes.voice import router as voice_router
from infrastructure.db.session import close_pool, open_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Abre el pool de PostgreSQL al arrancar y lo cierra al apagar."""
    await open_pool()
    yield
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
