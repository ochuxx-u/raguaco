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

from domain.services.conversation_service import ConversationService
from domain.services.document_ingestion_service import DocumentIngestionService
from domain.services.rag_service import RAGService
from domain.services.voice_service import VoiceService
from infrastructure.db.repositories.conversacion_repository import ConversacionRepository
from infrastructure.db.repositories.dashboard_repository import DashboardRepository
from infrastructure.db.repositories.documento_repository import DocumentoRepository
from infrastructure.db.repositories.mensaje_repository import MensajeRepository
from infrastructure.db.repositories.referencia_fuente_repository import ReferenciaFuenteRepository
from infrastructure.db.repositories.usuario_repository import UsuarioRepository
from infrastructure.db.session import pool
from infrastructure.embeddings.embedding_service import EmbeddingService
from infrastructure.llm.llm_service import LLMService
from infrastructure.loaders.chunking_service import ChunkingService
from infrastructure.loaders.document_loader import DocumentLoader
from infrastructure.loaders.text_cleaner import TextCleaner
from infrastructure.retrieval.retriever import Retriever
from infrastructure.storage.local_storage import StorageService
from infrastructure.stt.whisper_stt import WhisperSTT
from infrastructure.tts.kokoro_tts import KokoroTTS
from infrastructure.vector.pgvector_repository import VectorRepository


async def get_db() -> AsyncIterator[AsyncConnection]:
    """Entrega una conexión del pool y la devuelve al terminar la petición."""
    async with pool.connection() as conn:
        yield conn


DbConnection = Annotated[AsyncConnection, Depends(get_db)]


def get_usuario_repository(conn: DbConnection) -> UsuarioRepository:
    return UsuarioRepository(conn)


def get_documento_repository(conn: DbConnection) -> DocumentoRepository:
    return DocumentoRepository(conn)


def get_dashboard_repository(conn: DbConnection) -> DashboardRepository:
    return DashboardRepository(conn)


def get_conversacion_repository(conn: DbConnection) -> ConversacionRepository:
    return ConversacionRepository(conn)


def get_mensaje_repository(conn: DbConnection) -> MensajeRepository:
    return MensajeRepository(conn)


def get_referencia_fuente_repository(conn: DbConnection) -> ReferenciaFuenteRepository:
    return ReferenciaFuenteRepository(conn)


UsuarioRepositoryDep = Annotated[UsuarioRepository, Depends(get_usuario_repository)]
DocumentoRepositoryDep = Annotated[DocumentoRepository, Depends(get_documento_repository)]
DashboardRepositoryDep = Annotated[
    DashboardRepository, Depends(get_dashboard_repository)
]
ConversacionRepositoryDep = Annotated[
    ConversacionRepository, Depends(get_conversacion_repository)
]
MensajeRepositoryDep = Annotated[MensajeRepository, Depends(get_mensaje_repository)]
ReferenciaFuenteRepositoryDep = Annotated[
    ReferenciaFuenteRepository, Depends(get_referencia_fuente_repository)
]


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """Instancia única del LLM: reutiliza las conexiones HTTPS entre peticiones."""
    return LLMService()


LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]


@lru_cache(maxsize=1)
def get_tts_engine() -> KokoroTTS:
    """Motor TTS único por proceso: los pesos ONNX se cargan una sola vez.

    La carga es perezosa; el lifespan lo precarga en segundo plano (ver
    `TTS_WARMUP`) para que la primera síntesis no pague ese costo.
    """
    return KokoroTTS()


@lru_cache(maxsize=1)
def get_stt_service() -> WhisperSTT:
    """Modelo STT único por proceso: faster-whisper tarda segundos en cargar."""
    return WhisperSTT()


STTServiceDep = Annotated[WhisperSTT, Depends(get_stt_service)]


@lru_cache(maxsize=1)
def get_voice_service() -> VoiceService:
    """Servicio de voz único para el TTS: comparte motor y directorio de WAV.

    No depende de la base de datos: `POST /v1/voice/tts` debe funcionar aunque
    el RAG no esté disponible.
    """
    return VoiceService(tts=get_tts_engine())


VoiceServiceDep = Annotated[VoiceService, Depends(get_voice_service)]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Instancia única del modelo de embeddings: los pesos ONNX se cargan una vez.

    La carga es perezosa, así que pedir la dependencia no exige tener el modelo
    descargado; eso se comprueba con `EmbeddingService.configured`.
    """
    return EmbeddingService()


EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]


def get_vector_repository(conn: DbConnection) -> VectorRepository:
    """Repositorio vectorial sobre la misma conexión que el resto de repositorios."""
    return VectorRepository(conn)


VectorRepositoryDep = Annotated[VectorRepository, Depends(get_vector_repository)]


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    """Instancia única del almacenamiento local: no guarda estado por petición."""
    return StorageService()


def get_document_loader() -> DocumentLoader:
    """Extractor de texto de los documentos cargados."""
    return DocumentLoader()


def get_text_cleaner() -> TextCleaner:
    """Normalizador del texto extraído."""
    return TextCleaner()


def get_chunking_service() -> ChunkingService:
    """Fragmentador del texto limpio en chunks."""
    return ChunkingService()


StorageServiceDep = Annotated[StorageService, Depends(get_storage_service)]
DocumentLoaderDep = Annotated[DocumentLoader, Depends(get_document_loader)]
TextCleanerDep = Annotated[TextCleaner, Depends(get_text_cleaner)]
ChunkingServiceDep = Annotated[ChunkingService, Depends(get_chunking_service)]


def get_document_ingestion_service(
    storage: StorageServiceDep,
    loader: DocumentLoaderDep,
    cleaner: TextCleanerDep,
    chunking: ChunkingServiceDep,
    embeddings: EmbeddingServiceDep,
    vector_repo: VectorRepositoryDep,
    documento_repo: DocumentoRepositoryDep,
) -> DocumentIngestionService:
    """Ensambla el pipeline ETL de ingesta de documentos (RF2) con sus piezas."""
    return DocumentIngestionService(
        storage=storage,
        loader=loader,
        cleaner=cleaner,
        chunking=chunking,
        embeddings=embeddings,
        vector_repo=vector_repo,
        documento_repo=documento_repo,
    )


DocumentIngestionServiceDep = Annotated[
    DocumentIngestionService, Depends(get_document_ingestion_service)
]


def get_conversation_service(
    conversaciones: ConversacionRepositoryDep,
    mensajes: MensajeRepositoryDep,
    referencias: ReferenciaFuenteRepositoryDep,
) -> ConversationService:
    """Servicio de conversaciones: historial, mensajes y sus fuentes."""
    return ConversationService(
        conversaciones=conversaciones,
        mensajes=mensajes,
        referencias=referencias,
    )


ConversationServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]


def get_retriever(
    embeddings: EmbeddingServiceDep,
    vector_repo: VectorRepositoryDep,
) -> Retriever:
    """Recuperador semántico: vectoriza la consulta y busca fragmentos."""
    return Retriever(embeddings=embeddings, vector_repo=vector_repo)


RetrieverDep = Annotated[Retriever, Depends(get_retriever)]


def get_rag_service(
    conversation_service: ConversationServiceDep,
    llm: LLMServiceDep,
    retriever: RetrieverDep,
) -> RAGService:
    """Orquestador del flujo RAG con sus piezas sustituibles."""
    return RAGService(
        conversation_service=conversation_service,
        llm=llm,
        retriever=retriever,
    )


RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]


def get_voice_flow_service(
    stt: STTServiceDep,
    rag: RAGServiceDep,
    conversation_service: ConversationServiceDep,
) -> VoiceService:
    """Ensambla la secuencia completa voz → STT → RAG → TTS (RF12).

    Comparte el motor TTS con `get_voice_service` para no cargar Kokoro dos
    veces; el STT sí es propio del flujo de voz.
    """
    return VoiceService(
        tts=get_tts_engine(),
        stt=stt,
        rag=rag,
        conversations=conversation_service,
    )


VoiceFlowServiceDep = Annotated[VoiceService, Depends(get_voice_flow_service)]
