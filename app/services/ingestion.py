from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.repositories.knowledge import KnowledgeChunkRepository, KnowledgeDocumentRepository
from app.schemas.knowledge import KnowledgeIngestResponse
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.services.exceptions import EmptyDocumentError, IngestionError, PersistenceError
from app.services.extraction import extract_segments, resolve_content_type


class DocumentIngestionService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._documents = KnowledgeDocumentRepository(db)
        self._chunks = KnowledgeChunkRepository(db)
        self._chunking = ChunkingService()
        self._embeddings = EmbeddingService()

    def ingest(
        self,
        *,
        filename: str,
        declared_type: str | None,
        data: bytes,
        title: str,
        source_url: str | None,
        manufacturer: str | None,
        material: str | None,
        category: str | None,
    ) -> KnowledgeIngestResponse:
        content_type = resolve_content_type(filename, declared_type)
        if not title.strip():
            raise IngestionError("Title is required.", status_code=400)
        segments = extract_segments(data, content_type)
        prepared = self._chunking.split(segments)
        if not prepared:
            raise EmptyDocumentError()

        vectors = self._embeddings.embed_many([item.content for item in prepared])

        document = KnowledgeDocument(
            title=title.strip(),
            filename=filename,
            source_url=_optional(source_url),
            manufacturer=_optional(manufacturer),
            material=_optional(material),
            category=_optional(category),
            content_type=content_type,
        )
        chunks = [
            KnowledgeChunk(
                chunk_index=item.chunk_index,
                content=item.content,
                page_number=item.page_number,
                embedding=vector,
            )
            for item, vector in zip(prepared, vectors, strict=True)
        ]

        try:
            stored = self._documents.add(document)
            for chunk in chunks:
                chunk.document_id = stored.id
            self._chunks.add_many(chunks)
            self._db.commit()
        except SQLAlchemyError as exc:
            self._db.rollback()
            raise PersistenceError() from exc

        return KnowledgeIngestResponse(
            document_id=stored.id,
            title=stored.title,
            filename=stored.filename,
            chunks_created=len(chunks),
        )


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
