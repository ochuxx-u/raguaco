"""Recuperación semántica: vectoriza la consulta y busca fragmentos similares.

Es el `Retriever` del diagrama de secuencia
(`Docs/UML/imagenes/DIA-SECUENCIA_Ask-With-PNL.png`). El diagrama separa
`generarEmbedding(pregunta)` (EmbeddingService) de `recuperar(embeddingConsulta,
usuarioId, {topK, umbral, filtros})`, pero `RAGService` entrega el texto de la
consulta (`recuperar(consulta, usuario_id, opciones)`) y este servicio hace
ambos pasos: vectorizar y buscar.

La vectorización usa `EmbeddingService.embeber_consulta` —nunca
`generar_embedding`— porque `multilingual-e5-small` exige el prefijo `query: `
en las preguntas (`passage: ` es solo para fragmentos de documento); con el
prefijo equivocado la recuperación se degrada en silencio (AGENTS.md).
"""

from typing import Any
from uuid import UUID

from domain.models.chunk import Chunk
from infrastructure.embeddings.embedding_service import EmbeddingService
from infrastructure.vector.pgvector_repository import VectorRepository

# Valores por defecto de la búsqueda (RF6: Top-K y umbral de similitud); se
# sobrescriben con `opciones`. El umbral corta los fragmentos poco relacionados
# y es lo que dispara el rechazo explícito de RF9 cuando no hay evidencia.
TOP_K_DEFECTO = 5
UMBRAL_DEFECTO = 0.5


class Retriever:
    """Recupera los fragmentos más similares a una consulta."""

    def __init__(self, embeddings: EmbeddingService, vector_repo: VectorRepository) -> None:
        self._embeddings = embeddings
        self._vector_repo = vector_repo

    async def recuperar(
        self,
        consulta: str,
        usuario_id: UUID,
        opciones: dict[str, Any] | None = None,
    ) -> list[tuple[Chunk, float]]:
        """Fragmentos de `usuario_id` similares a `consulta`, con su similitud 0..1.

        `opciones` acepta `top_k`, `umbral` y `filtros` (RF6: documento,
        metadatos o categorías opcionales); lo que no venga usa los valores por
        defecto. Devuelve los más similares primero y `[]` si ninguno supera el
        umbral: la señal de "sin evidencia relevante" que `RAGService` traduce
        en rechazo explícito (RF9).
        """
        opciones = opciones or {}
        top_k = max(1, int(opciones.get('top_k', TOP_K_DEFECTO)))
        umbral = float(opciones.get('umbral', UMBRAL_DEFECTO))
        filtros = opciones.get('filtros')

        embedding = await self._embeddings.embeber_consulta(consulta)
        print(
            f'[retriever] generarEmbedding(consulta) → vector de {len(embedding)} '
            'dimensiones (prefijo «query: »)'
        )
        resultados = await self._vector_repo.buscar_similares(
            embedding,
            usuario_id=usuario_id,
            top_k=top_k,
            umbral=umbral,
            filtros=filtros,
        )
        print(
            f'[retriever] buscarSimilares(top_k={top_k}, umbral={umbral}, filtros={filtros}) '
            f'→ {len(resultados)} fragmentos'
        )
        for numero, (chunk, similitud) in enumerate(resultados, start=1):
            origen = f'documento {chunk.documento_id}'
            if chunk.pagina is not None:
                origen += f', página {chunk.pagina}'
            texto = chunk.contenido if len(chunk.contenido) <= 80 else chunk.contenido[:80] + '…'
            print(f'    [{numero}] {origen} · similitud {similitud:.3f} · «{texto}»')
        return resultados
