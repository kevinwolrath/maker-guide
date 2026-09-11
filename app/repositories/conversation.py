import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        return self._db.get(Conversation, conversation_id)

    def add(self, conversation: Conversation) -> Conversation:
        self._db.add(conversation)
        self._db.flush()
        return conversation

    def list_recent_messages(
        self,
        conversation_id: uuid.UUID,
        limit: int,
    ) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        rows = list(self._db.scalars(statement))
        rows.reverse()
        return rows

    def add_message(self, message: Message) -> Message:
        self._db.add(message)
        self._db.flush()
        return message
