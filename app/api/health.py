from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.health import HealthResponse
from app.services.health import get_health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse | JSONResponse:
    payload = get_health()
    if payload.status != "ok":
        return JSONResponse(status_code=503, content=payload.model_dump())
    return payload
