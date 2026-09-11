from sqlalchemy import text

from app.db.session import SessionLocal
from app.schemas.health import HealthResponse


def get_health() -> HealthResponse:
    postgres_ok = _postgres_ok()
    return HealthResponse(
        status="ok" if postgres_ok else "degraded",
        api="ok",
        postgres="ok" if postgres_ok else "unavailable",
    )


def _postgres_ok() -> bool:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
