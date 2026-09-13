from collections.abc import AsyncIterator, Sequence

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk, BaseMessage

from app.api.chat import get_conversation_service, get_tool_calling_orchestrator
from app.main import app
from app.tools.registry import ToolExecutionResult


class FakeConversationService:
    def __init__(self) -> None:
        self.conversation = object()
        self.user_messages: list[tuple[object, str]] = []
        self.final_answers: list[tuple[object, str]] = []

    def get_or_create(self, session_id: str) -> object:
        return self.conversation

    def record_user(self, conversation: object, content: str) -> None:
        self.user_messages.append((conversation, content))

    def record_final_answer(self, conversation: object, content: str) -> None:
        self.final_answers.append((conversation, content))


class FakePreparedTurn:
    def __init__(
        self,
        tool_results: list[ToolExecutionResult],
        chunks: list[str],
        error: Exception | None = None,
    ) -> None:
        self.tool_results = tool_results
        self._chunks = chunks
        self._error = error

    async def final_stream(self) -> AsyncIterator[AIMessageChunk]:
        for chunk in self._chunks:
            yield AIMessageChunk(content=chunk)
        if self._error is not None:
            raise self._error


class FakeOrchestrator:
    def __init__(self, prepared: FakePreparedTurn | None = None, error: Exception | None = None) -> None:
        self.prepared = prepared
        self.error = error
        self.calls: list[tuple[list[BaseMessage], object]] = []

    async def prepare_turn(
        self, messages: Sequence[BaseMessage], conversation: object
    ) -> FakePreparedTurn:
        self.calls.append((list(messages), conversation))
        if self.error is not None:
            raise self.error
        assert self.prepared is not None
        return self.prepared


@pytest.fixture
def conversation_service() -> FakeConversationService:
    return FakeConversationService()


@pytest.fixture
def orchestrator() -> FakeOrchestrator:
    return FakeOrchestrator(
        FakePreparedTurn(
            [
                ToolExecutionResult(
                    tool_call_id="call-order",
                    name="query_order",
                    content="order result",
                    ok=True,
                ),
                ToolExecutionResult(
                    tool_call_id="call-logistics",
                    name="query_logistics",
                    content="logistics result",
                    ok=True,
                ),
            ],
            ["已查到"],
        )
    )


@pytest.fixture
def client(
    conversation_service: FakeConversationService, orchestrator: FakeOrchestrator
) -> AsyncIterator[TestClient]:
    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_tool_calling_orchestrator] = lambda: orchestrator
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_chat_sends_tool_status_before_final_delta(
    client: TestClient, conversation_service: FakeConversationService
) -> None:
    """Catch emitting final answer text before the client sees each tool status."""
    response = client.post(
        "/api/chat", json={"session_id": "s1", "message": "订单 1001 的物流"}
    )

    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == (
        'data: {"tool_status":{"name":"query_order","state":"running"}}\n\n'
        'data: {"tool_status":{"name":"query_logistics","state":"running"}}\n\n'
        'data: {"delta":"已查到"}\n\n'
        "data: [DONE]\n\n"
    )
    assert conversation_service.user_messages == [(conversation_service.conversation, "订单 1001 的物流")]
    assert conversation_service.final_answers == [(conversation_service.conversation, "已查到")]


def test_final_stream_failure_does_not_persist_completed_answer(
    conversation_service: FakeConversationService,
) -> None:
    """Catch recording a final assistant message after its upstream stream failed."""
    orchestrator = FakeOrchestrator(
        FakePreparedTurn([], ["已查到"], RuntimeError("provider unavailable"))
    )
    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_tool_calling_orchestrator] = lambda: orchestrator
    try:
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"session_id": "s1", "message": "退款"})
    finally:
        app.dependency_overrides.clear()

    assert response.text == (
        'data: {"delta":"已查到"}\n\n'
        'data: {"error":{"code":"upstream_error","message":"provider unavailable"}}\n\n'
    )
    assert conversation_service.final_answers == []


def test_initial_planning_failure_returns_bad_gateway(
    conversation_service: FakeConversationService,
) -> None:
    """Catch opening a 200 SSE response when planning cannot reach the provider."""
    orchestrator = FakeOrchestrator(error=RuntimeError("provider unavailable"))
    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_tool_calling_orchestrator] = lambda: orchestrator
    try:
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"session_id": "s1", "message": "退款"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "upstream_error"}
    assert conversation_service.final_answers == []
