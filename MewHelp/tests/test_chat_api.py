from collections.abc import AsyncIterator, Sequence
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.chat import (
    get_conversation_service,
    get_conversation_sessions,
    get_db_session,
    get_tool_calling_orchestrator,
)
from app.main import app
from app.tools.business import query_logistics, query_order
from app.tools.registry import ToolExecutionResult


class FakeConversationService:
    def __init__(self) -> None:
        self.conversation = object()
        self.user_messages: list[tuple[object, str]] = []
        self.final_answers: list[tuple[object, str]] = []
        self.completed_turns: list[tuple[str, str]] = []

    def get_or_create(self, session_id: str) -> object:
        return self.conversation

    def record_user(self, conversation: object, content: str) -> None:
        self.user_messages.append((conversation, content))

    def record_final_answer(self, conversation: object, content: str) -> None:
        self.final_answers.append((conversation, content))

    def completed_turns_for(self, conversation: object) -> list[tuple[str, str]]:
        return self.completed_turns


class FakePreparedTurn:
    def __init__(
        self,
        tool_results: list[ToolExecutionResult],
        chunks: list[object],
        error: Exception | None = None,
    ) -> None:
        self.tool_results = tool_results
        self._chunks = chunks
        self._error = error

    async def final_stream(self) -> AsyncIterator[AIMessageChunk]:
        for chunk in self._chunks:
            if isinstance(chunk, AIMessageChunk):
                yield chunk
            else:
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
    app.dependency_overrides[get_tool_calling_orchestrator] = lambda: (
        lambda conversation: orchestrator
    )
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


def test_chat_reuses_completed_turns_as_model_history(
    client: TestClient,
    conversation_service: FakeConversationService,
    orchestrator: FakeOrchestrator,
) -> None:
    """Catch dropping persisted completed turns before the next plan is prepared."""
    conversation_service.completed_turns = [("订单 A 未发货", "我来协助确认。")]

    client.post("/api/chat", json={"session_id": "s1", "message": "我要催发货"})

    assert [message.content for message in orchestrator.calls[0][0]][-3:] == [
        "订单 A 未发货",
        "我来协助确认。",
        "我要催发货",
    ]


def test_final_stream_failure_does_not_persist_completed_answer(
    conversation_service: FakeConversationService,
) -> None:
    """Catch recording a final assistant message after its upstream stream failed."""
    orchestrator = FakeOrchestrator(
        FakePreparedTurn([], ["已查到"], RuntimeError("provider unavailable"))
    )
    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_tool_calling_orchestrator] = lambda: (
        lambda conversation: orchestrator
    )
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
    app.dependency_overrides[get_tool_calling_orchestrator] = lambda: (
        lambda conversation: orchestrator
    )
    try:
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"session_id": "s1", "message": "退款"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "upstream_error"}
    assert conversation_service.final_answers == []


def test_metadata_chunks_are_not_sent_or_persisted_as_answer_text(
    conversation_service: FakeConversationService,
) -> None:
    """Catch exposing reasoning metadata or recording it as assistant content."""
    orchestrator = FakeOrchestrator(
        FakePreparedTurn(
            [],
            [
                AIMessageChunk(content="", additional_kwargs={"reasoning_content": "internal"}),
                "您好",
            ],
        )
    )
    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_tool_calling_orchestrator] = lambda: (
        lambda conversation: orchestrator
    )
    try:
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"session_id": "s1", "message": "退款"})
    finally:
        app.dependency_overrides.clear()

    assert response.text == 'data: {"delta":"您好"}\n\ndata: [DONE]\n\n'
    assert conversation_service.final_answers == [(conversation_service.conversation, "您好")]


def test_empty_completed_stream_sends_done_and_persists_empty_answer(
    conversation_service: FakeConversationService,
) -> None:
    """Catch treating a successful no-text final stream as an upstream failure."""
    orchestrator = FakeOrchestrator(FakePreparedTurn([], []))
    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_tool_calling_orchestrator] = lambda: (
        lambda conversation: orchestrator
    )
    try:
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"session_id": "s1", "message": "退款"})
    finally:
        app.dependency_overrides.clear()

    assert response.text == "data: [DONE]\n\n"
    assert conversation_service.final_answers == [(conversation_service.conversation, "")]


class RecordingPlanningModel:
    def __init__(self) -> None:
        self.calls: list[list[BaseMessage]] = []

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        self.calls.append(list(messages))
        return AIMessage(content="")


class RecordingFinalModel:
    async def astream(self, messages: Sequence[BaseMessage]) -> AsyncIterator[AIMessageChunk]:
        yield AIMessageChunk(content="已记录")


def test_default_orchestrator_factory_binds_tools_to_active_conversation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch binding one global tool list while executing another request-scoped list."""
    monkeypatch.setenv("LITELLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "local")
    tools = [query_order, query_logistics]
    seen: dict[str, object] = {}

    def build_tools(*, conversation_id: int) -> list[object]:
        seen["conversation_id"] = conversation_id
        return tools

    def build_planner(settings: object, bound_tools: list[object]) -> object:
        seen["planning_tools"] = bound_tools
        return RecordingPlanningModel()

    monkeypatch.setattr("app.api.chat.build_business_tools", build_tools)
    monkeypatch.setattr("app.api.chat.build_tool_calling_model", build_planner)
    monkeypatch.setattr("app.api.chat.build_chat_model", lambda settings: RecordingFinalModel())

    factory = get_tool_calling_orchestrator(FakeConversationService())
    factory(SimpleNamespace(id=42))

    assert seen == {"conversation_id": 42, "planning_tools": tools}


def test_default_dependencies_use_request_sessions_and_persist_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch sharing a cached SQLAlchemy session or losing history across route requests."""
    monkeypatch.setenv("LITELLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "local")
    planning_model = RecordingPlanningModel()
    monkeypatch.setattr(
        "app.api.chat.build_tool_calling_model", lambda settings, tools: planning_model
    )
    monkeypatch.setattr("app.api.chat.build_chat_model", lambda settings: RecordingFinalModel())
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.connection.driver_connection.executescript(
            """
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(64) NOT NULL,
                status VARCHAR(16) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role VARCHAR(16) NOT NULL,
                content TEXT,
                tool_calls JSON,
                tool_call_id VARCHAR(128),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    request_sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def db_dependency() -> AsyncIterator[Session]:
        with request_sessions() as session:
            yield session

    app.dependency_overrides[get_db_session] = db_dependency
    try:
        with TestClient(app) as client:
            first = client.post("/api/chat", json={"session_id": "s1", "message": "订单 A 未发货"})
            second = client.post("/api/chat", json={"session_id": "s1", "message": "我要催发货"})
    finally:
        app.dependency_overrides.clear()
        clear_cache = getattr(get_conversation_service, "cache_clear", lambda: None)
        clear_cache()
        get_conversation_sessions.cache_clear()
        engine.dispose()

    assert first.status_code == 200
    assert second.status_code == 200
    assert [message.content for message in planning_model.calls[1]][-3:] == [
        "订单 A 未发货",
        "已记录",
        "我要催发货",
    ]
