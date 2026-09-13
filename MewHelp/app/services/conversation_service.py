from typing import Any

from sqlalchemy.orm import Session

from app.db import Conversation, Message
from app.repositories.conversations import ConversationRepository


class ConversationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._conversations_by_session: dict[str, int] = {}
        self._repository = ConversationRepository(session)

    def get_or_create(self, session_id: str) -> Conversation:
        conversation_id = self._conversations_by_session.get(session_id)
        if conversation_id is not None:
            conversation = self._session.get(Conversation, conversation_id)
            if conversation is not None:
                return conversation

        conversation = self._repository.create(user_id="demo-user", status="进行中")
        self._conversations_by_session[session_id] = conversation.id
        return conversation

    def record_user(self, conversation: Conversation, content: str) -> Message:
        return self._repository.add_message(conversation.id, role="user", content=content)

    def record_tool_request(
        self, conversation: Conversation, tool_calls: list[dict[str, Any]]
    ) -> Message:
        return self._repository.add_message(
            conversation.id, role="assistant", tool_calls=tool_calls
        )

    def record_tool_result(
        self, conversation: Conversation, tool_call_id: str, content: str
    ) -> Message:
        return self._repository.add_message(
            conversation.id,
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
        )

    def record_final_answer(self, conversation: Conversation, content: str) -> Message:
        return self._repository.add_message(conversation.id, role="assistant", content=content)
