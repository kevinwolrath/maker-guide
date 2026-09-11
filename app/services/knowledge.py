from sqlalchemy.orm import Session

from app.repositories.knowledge import KnowledgeDocumentRepository
from app.schemas.knowledge import KnowledgeDocumentResponse


def list_documents(db: Session) -> list[KnowledgeDocumentResponse]:
    documents = KnowledgeDocumentRepository(db).list_all()
    return [KnowledgeDocumentResponse.model_validate(document) for document in documents]
