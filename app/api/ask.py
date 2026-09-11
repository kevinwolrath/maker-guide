from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ask import AskRequest, AskResponse
from app.schemas.retrieval import RetrievalFilters
from app.services.exceptions import AppError
from app.services.rag import RagService

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse, response_model_exclude_none=True)
def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    try:
        return RagService(db).ask(
            payload.question,
            RetrievalFilters(
                manufacturer=payload.manufacturer,
                material=payload.material,
                category=payload.category,
            ),
            payload.conversation_id,
            payload.diagnostics,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
