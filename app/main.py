from fastapi import FastAPI

from app.api.ask import router as ask_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    application = FastAPI(title=settings.app_name)
    application.include_router(health_router)
    application.include_router(knowledge_router)
    application.include_router(ask_router)
    return application


app = create_app()
