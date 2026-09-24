import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.schemas.retrieval import RetrievalFilters


class KnowledgeDocumentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[KnowledgeDocument]:
        statement = select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
        return list(self._db.scalars(statement))

    def get_by_id(self, document_id: uuid.UUID) -> KnowledgeDocument | None:
        return self._db.get(KnowledgeDocument, document_id)

    def add(self, document: KnowledgeDocument) -> KnowledgeDocument:
        self._db.add(document)
        self._db.flush()
        return document


class KnowledgeChunkRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_document(self, document_id: uuid.UUID) -> list[KnowledgeChunk]:
        statement = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document_id)
            .order_by(KnowledgeChunk.chunk_index)
        )
        return list(self._db.scalars(statement))

    def add_many(self, chunks: list[KnowledgeChunk]) -> None:
        self._db.add_all(chunks)
        self._db.flush()

    def search_similar(
        self,
        embedding: list[float],
        top_k: int,
        filters: RetrievalFilters | None = None,
    ) -> list[tuple[KnowledgeChunk, float]]:
        distance = KnowledgeChunk.embedding.cosine_distance(embedding)
        statement = (
            select(KnowledgeChunk, distance)
            .join(KnowledgeDocument)
            .options(joinedload(KnowledgeChunk.document))
            .where(KnowledgeChunk.embedding.is_not(None))
            # Cosine distance is NaN for zero vectors; NaN != NaN filters them out.
            .where(distance == distance)
        )
        statement = _apply_metadata_filters(statement, filters)
        statement = statement.order_by(distance).limit(top_k)
        rows = self._db.execute(statement).unique().all()
        return [(chunk, float(dist)) for chunk, dist in rows if dist == dist]


def _ilike_contains(column, value: str):
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{escaped}%", escape="\\")


def _apply_metadata_filters(statement, filters: RetrievalFilters | None):
    if filters is None or filters.is_empty():
        return statement

    clauses = {
        "manufacturer": lambda value: _ilike_contains(KnowledgeDocument.manufacturer, value),
        "category": lambda value: _ilike_contains(KnowledgeDocument.category, value),
        "material": lambda value: or_(
            _ilike_contains(KnowledgeDocument.material, value),
            _ilike_contains(
                func.concat_ws(" ", KnowledgeDocument.manufacturer, KnowledgeDocument.material),
                value,
            ),
        ),
    }
    for name, value in filters.active().items():
        builder = clauses.get(name)
        if builder is not None:
            statement = statement.where(builder(value))
    return statement
