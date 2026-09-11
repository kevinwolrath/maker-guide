from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.embeddings import EMBEDDING_DIMENSION
from app.services.exceptions import EmbeddingError


class EmbeddingService:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.embedding_model

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self._base_url}/api/embed",
                    json={"model": self._model, "input": texts},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise EmbeddingError(
                "Embedding service is unavailable. Pull the embedding model "
                f"with: docker compose exec ollama ollama pull {self._model}"
            ) from exc

        vectors = payload.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise EmbeddingError("Embedding service returned an unexpected response.")

        for vector in vectors:
            if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSION:
                raise EmbeddingError(
                    f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}."
                )
        return vectors
