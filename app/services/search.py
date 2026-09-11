from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.orm import Session

from app.repositories.knowledge import KnowledgeChunkRepository
from app.schemas.knowledge import KnowledgeSearchResponse, KnowledgeSearchResult
from app.schemas.retrieval import RetrievalFilters
from app.services.embedding import EmbeddingService
from app.services.exceptions import AppError


@dataclass
class SearchOutcome:
    response: KnowledgeSearchResponse
    embedding_seconds: float
    retrieval_seconds: float


class KnowledgeSearchService:
    def __init__(self, db: Session) -> None:
        self._chunks = KnowledgeChunkRepository(db)
        self._embeddings = EmbeddingService()

    def search(
        self,
        query: str,
        top_k: int,
        filters: RetrievalFilters | None = None,
    ) -> SearchOutcome:
        cleaned = query.strip()
        if not cleaned:
            raise AppError("Query is required.", status_code=400)
        active_filters = filters or RetrievalFilters()

        started = perf_counter()
        query_embedding = self._embeddings.embed(cleaned)
        embedding_seconds = perf_counter() - started

        started = perf_counter()
        matches = self._chunks.search_similar(query_embedding, top_k, active_filters)
        retrieval_seconds = perf_counter() - started

        results = [
            KnowledgeSearchResult(
                document_id=chunk.document_id,
                title=chunk.document.title,
                filename=chunk.document.filename,
                manufacturer=chunk.document.manufacturer,
                material=chunk.document.material,
                category=chunk.document.category,
                source_url=chunk.document.source_url,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                content=chunk.content,
                score=round(max(0.0, min(1.0, 1.0 - distance)), 4),
            )
            for chunk, distance in matches
        ]
        return SearchOutcome(
            response=KnowledgeSearchResponse(
                query=cleaned,
                filters=active_filters.active(),
                results=results,
            ),
            embedding_seconds=round(embedding_seconds, 3),
            retrieval_seconds=round(retrieval_seconds, 3),
        )
