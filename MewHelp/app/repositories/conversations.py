from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Conversation, Message


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, user_id: str, status: str) -> Conversation:
        conversation = Conversation(user_id=user_id, status=status)
        self._session.add(conversation)
        self._session.commit()
        return conversation

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
        )
        self._session.add(message)
        self._session.commit()
        return message

    def list_messages(self, conversation_id: int) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        )
        return list(self._session.scalars(statement))
