from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MakerGuide"
    database_url: str = (
        "postgresql+psycopg://makerguide:makerguide@postgres:5432/makerguide"
    )
    ollama_base_url: str = "http://ollama:11434"
    embedding_dimension: int = 768
    embedding_model: str = "nomic-embed-text"
    ollama_llm_model: str = "gpt-oss:20b"
    ollama_llm_timeout_seconds: float = 600.0
    rag_top_k: int = 5
    conversation_window_messages: int = 6
    conversation_message_max_chars: int = 400
    chunk_size: int = 800
    chunk_overlap: int = 150


@lru_cache
def get_settings() -> Settings:
    return Settings()
