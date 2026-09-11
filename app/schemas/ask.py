import uuid

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    conversation_id: uuid.UUID | None = None
    manufacturer: str | None = None
    material: str | None = None
    category: str | None = None
    diagnostics: bool = False


class AskSource(BaseModel):
    id: int
    title: str
    manufacturer: str | None
    material: str | None
    page_number: int | None
    source_url: str | None
    score: float


class AskDiagnosticChunk(BaseModel):
    document_id: uuid.UUID
    title: str
    filename: str | None = None
    manufacturer: str | None
    material: str | None
    category: str | None
    source_url: str | None
    chunk_index: int
    page_number: int | None
    content: str
    score: float


class AskDiagnosticTimings(BaseModel):
    embedding_seconds: float
    retrieval_seconds: float
    generation_seconds: float


class AskDiagnostics(BaseModel):
    embedding_model: str
    generative_model: str
    retrieval_top_k: int
    retrieved_chunks: list[AskDiagnosticChunk]
    llm_context: str
    timings: AskDiagnosticTimings


class AskResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    sources: list[AskSource]
    diagnostics: AskDiagnostics | None = None
