from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.exceptions import LlmError


class LlmService:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_llm_model
        self._timeout = settings.ollama_llm_timeout_seconds

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "stream": False,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise LlmError(
                "The language model is unavailable. Pull the model with: "
                f"docker compose exec ollama ollama pull {self._model}"
            ) from exc

        message = payload.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LlmError("The language model returned an empty response.")
        return content.strip()
