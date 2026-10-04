from typing import Any
from threading import Lock

from sqlalchemy.orm import Session

from app.db import Conversation, Message
from app.repositories.conversations import ConversationRepository


class ConversationSessionMap:
    """Thread-safe, process-local mapping without retaining database sessions."""

    def __init__(self) -> None:
        self._conversation_ids: dict[str, int] = {}
        self.lock = Lock()

    def get(self, session_id: str) -> int | None:
        return self._conversation_ids.get(session_id)

    def set(self, session_id: str, conversation_id: int) -> None:
        self._conversation_ids[session_id] = conversation_id


class ConversationService:
    def __init__(
        self, session: Session, conversation_sessions: ConversationSessionMap | None = None
    ) -> None:
        self._session = session
        self._conversation_sessions = conversation_sessions or ConversationSessionMap()
        self._repository = ConversationRepository(session)

    def get_or_create(self, session_id: str) -> Conversation:
        with self._conversation_sessions.lock:
            conversation_id = self._conversation_sessions.get(session_id)
            if conversation_id is not None:
                conversation = self._session.get(Conversation, conversation_id)
                if conversation is not None:
                    return conversation

            conversation = self._repository.create(user_id="demo-user", status="进行中")
            self._conversation_sessions.set(session_id, conversation.id)
            return conversation

    def completed_turns_for(self, conversation: Conversation) -> list[tuple[str, str]]:
        """Return prior complete user/final-assistant pairs without tool trace internals."""
        completed_turns: list[tuple[str, str]] = []
        pending_user: str | None = None
        for message in self._repository.list_messages(conversation.id):
            if message.role == "user" and message.content is not None:
                pending_user = message.content
            elif (
                message.role == "assistant"
                and message.content is not None
                and pending_user is not None
            ):
                completed_turns.append((pending_user, message.content))
                pending_user = None
        return completed_turns

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
