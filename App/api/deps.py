"""Dependencias compartidas de la API.

`get_db` toma una conexión del pool por petición; los proveedores de
repositorios la inyectan en las rutas. Así las rutas no conocen psycopg y se
pueden probar con repositorios falsos.
"""

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from psycopg import AsyncConnection

from infrastructure.db.repositories.conversacion_repository import ConversacionRepository
from infrastructure.db.repositories.documento_repository import DocumentoRepository
from infrastructure.db.repositories.mensaje_repository import MensajeRepository
from infrastructure.db.repositories.usuario_repository import UsuarioRepository
from infrastructure.db.session import pool
from infrastructure.embeddings.embedding_service import EmbeddingService
from infrastructure.llm.llm_service import LLMService


async def get_db() -> AsyncIterator[AsyncConnection]:
    """Entrega una conexión del pool y la devuelve al terminar la petición."""
    async with pool.connection() as conn:
        yield conn


DbConnection = Annotated[AsyncConnection, Depends(get_db)]


def get_usuario_repository(conn: DbConnection) -> UsuarioRepository:
    return UsuarioRepository(conn)


def get_documento_repository(conn: DbConnection) -> DocumentoRepository:
    return DocumentoRepository(conn)


def get_conversacion_repository(conn: DbConnection) -> ConversacionRepository:
    return ConversacionRepository(conn)


def get_mensaje_repository(conn: DbConnection) -> MensajeRepository:
    return MensajeRepository(conn)


UsuarioRepositoryDep = Annotated[UsuarioRepository, Depends(get_usuario_repository)]
DocumentoRepositoryDep = Annotated[DocumentoRepository, Depends(get_documento_repository)]
ConversacionRepositoryDep = Annotated[
    ConversacionRepository, Depends(get_conversacion_repository)
]
MensajeRepositoryDep = Annotated[MensajeRepository, Depends(get_mensaje_repository)]


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """Instancia única del LLM: reutiliza las conexiones HTTPS entre peticiones."""
    return LLMService()


LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Instancia única del modelo de embeddings: los pesos ONNX se cargan una vez.

    La carga es perezosa, así que pedir la dependencia no exige tener el modelo
    descargado; eso se comprueba con `EmbeddingService.configured`.
    """
    return EmbeddingService()


EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
