"""Data access layer for persisted chat messages (conversation audit trail)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage


class ChatRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add_message(
        self, session_id: str, role: str, content: str, tool_used: str | None = None
    ) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content, tool_used=tool_used)
        self._db.add(message)
        self._db.flush()
        return message

    def list_for_session(self, session_id: str, limit: int = 100) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
            .limit(limit)
        )
        return list(self._db.execute(stmt).scalars().all())
