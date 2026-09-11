from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.conversation import Conversation, Message
from app.repositories.conversation import ConversationRepository
from app.services.exceptions import ConversationNotFoundError

_TASK_HINT_MAX_CHARS = 300


class ConversationService:
    def __init__(self, db: Session) -> None:
        settings = get_settings()
        self._db = db
        self._conversations = ConversationRepository(db)
        self._window_size = settings.conversation_window_messages
        self._message_max_chars = settings.conversation_message_max_chars

    def resolve(self, conversation_id: uuid.UUID | None) -> Conversation:
        if conversation_id is None:
            conversation = self._conversations.add(Conversation())
            self._db.commit()
            return conversation
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError()
        return conversation

    def recent_window(self, conversation_id: uuid.UUID) -> list[Message]:
        return self._conversations.list_recent_messages(
            conversation_id,
            self._window_size,
        )

    def add_turn(self, conversation_id: uuid.UUID, role: str, content: str) -> Message:
        message = self._conversations.add_message(
            Message(conversation_id=conversation_id, role=role, content=content)
        )
        self._db.commit()
        return message

    def retrieval_query(self, question: str, history: list[Message]) -> str:
        prior_user = [
            message.content.strip()
            for message in history
            if message.role == "user" and message.content.strip()
        ][-2:]
        if not prior_user:
            return question
        hint = " ".join(prior_user)
        if len(hint) > _TASK_HINT_MAX_CHARS:
            hint = hint[-_TASK_HINT_MAX_CHARS:]
        return f"{question}\n\nRelated task: {hint}"

    def format_window(self, history: list[Message]) -> str:
        if not history:
            return ""
        lines = ["Recent conversation (task context only; not manufacturer documentation):"]
        for message in history:
            excerpt = self._clip(message.content)
            lines.append(f"{message.role}: {excerpt}")
        return "\n".join(lines)

    def _clip(self, content: str) -> str:
        cleaned = content.strip()
        if len(cleaned) <= self._message_max_chars:
            return cleaned
        return cleaned[: self._message_max_chars].rstrip() + "..."
