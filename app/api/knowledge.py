from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.knowledge import (
    KnowledgeDocumentResponse,
    KnowledgeIngestResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.schemas.retrieval import RetrievalFilters
from app.services.exceptions import AppError
from app.services.ingestion import DocumentIngestionService
from app.services.knowledge import list_documents
from app.services.search import KnowledgeSearchService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
def get_knowledge_documents(db: Session = Depends(get_db)) -> list[KnowledgeDocumentResponse]:
    return list_documents(db)


@router.post("/documents", response_model=KnowledgeIngestResponse)
def upload_knowledge_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    source_url: str | None = Form(default=None),
    manufacturer: str | None = Form(default=None),
    material: str | None = Form(default=None),
    category: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> KnowledgeIngestResponse:
    # Sync endpoint on purpose: ingestion makes blocking DB and embedding
    # calls, so FastAPI runs it in its threadpool instead of the event loop.
    data = file.file.read()
    try:
        return DocumentIngestionService(db).ingest(
            filename=file.filename or "upload",
            declared_type=file.content_type,
            data=data,
            title=title,
            source_url=source_url,
            manufacturer=manufacturer,
            material=material,
            category=category,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    payload: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
) -> KnowledgeSearchResponse:
    try:
        return KnowledgeSearchService(db).search(
            payload.query,
            payload.top_k,
            RetrievalFilters(
                manufacturer=payload.manufacturer,
                material=payload.material,
                category=payload.category,
            ),
        ).response
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
