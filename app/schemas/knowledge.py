import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    filename: str
    source_url: str | None
    manufacturer: str | None
    material: str | None
    category: str | None
    content_type: str
    created_at: datetime


class KnowledgeIngestResponse(BaseModel):
    document_id: uuid.UUID
    title: str
    filename: str
    chunks_created: int


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    manufacturer: str | None = None
    material: str | None = None
    category: str | None = None


class KnowledgeSearchResult(BaseModel):
    document_id: uuid.UUID
    title: str
    filename: str
    manufacturer: str | None
    material: str | None
    category: str | None
    source_url: str | None
    chunk_index: int
    page_number: int | None
    content: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    filters: dict[str, str]
    results: list[KnowledgeSearchResult]
