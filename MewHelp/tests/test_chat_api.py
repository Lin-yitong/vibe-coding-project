from collections.abc import AsyncIterator, Callable, Sequence

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage

from app.api.chat import get_chat_model, get_session_store
from app.main import app


class FakeSessionStore:
    def __init__(self) -> None:
        self._pairs: dict[str, list[tuple[str, str]]] = {}

    def build_messages(
        self,
        session_id: str,
        current_message: str,
        system_message: BaseMessage,
        count_tokens: Callable[[Sequence[BaseMessage]], int],
    ) -> list[BaseMessage]:
        messages: list[BaseMessage] = [system_message]
        for user_message, assistant_message in self._pairs.get(session_id, []):
            messages.extend(
                [HumanMessage(content=user_message), AIMessage(content=assistant_message)]
            )
        messages.append(HumanMessage(content=current_message))
        return messages

    def commit(self, session_id: str, user_message: str, assistant_message: str) -> None:
        self._pairs.setdefault(session_id, []).append((user_message, assistant_message))

    def pairs_for(self, session_id: str) -> list[tuple[str, str]]:
        return self._pairs.get(session_id, [])


class FakeModel:
    def __init__(self, chunks: list[str], error: Exception | None = None) -> None:
        self.chunks = chunks
        self.error = error
        self.calls: list[list[BaseMessage]] = []

    def get_num_tokens_from_messages(self, messages: Sequence[BaseMessage]) -> int:
        return len(messages)

    async def astream(
        self, messages: Sequence[BaseMessage]
    ) -> AsyncIterator[AIMessageChunk]:
        self.calls.append(list(messages))
        for chunk in self.chunks:
            yield AIMessageChunk(content=chunk)
        if self.error is not None:
            raise self.error


class InitialFailureModel(FakeModel):
    def astream(self, messages: Sequence[BaseMessage]) -> AsyncIterator[AIMessageChunk]:
        raise RuntimeError("provider unavailable")


@pytest.fixture
def store() -> FakeSessionStore:
    return FakeSessionStore()


@pytest.fixture
def fake_model() -> FakeModel:
    return FakeModel(["您好", "，我来协助您确认。"])


@pytest.fixture
def client(store: FakeSessionStore, fake_model: FakeModel) -> AsyncIterator[TestClient]:
    app.dependency_overrides[get_session_store] = lambda: store
    app.dependency_overrides[get_chat_model] = lambda: fake_model
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_stream_commits_only_after_done(
    client: TestClient, fake_model: FakeModel, store: FakeSessionStore
) -> None:
    """Catch a route that omits streamed text, done marker, or successful commit."""
    response = client.post(
        "/api/chat", json={"session_id": "s", "message": "订单 A 未发货"}
    )

    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'data: {"delta":"您好"}' in response.text
    assert response.text.endswith("data: [DONE]\n\n")
    assert store.pairs_for("s") == [("订单 A 未发货", "您好，我来协助您确认。")]


def test_late_upstream_error_emits_error_and_does_not_commit(
    store: FakeSessionStore,
) -> None:
    """Catch committing a partial reply after the provider fails mid-stream."""
    failing_after_first_chunk = FakeModel(["您好"], RuntimeError("provider unavailable"))
    app.dependency_overrides[get_session_store] = lambda: store
    app.dependency_overrides[get_chat_model] = lambda: failing_after_first_chunk
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"session_id": "s", "message": "退款"})
    app.dependency_overrides.clear()

    assert '"code":"upstream_error"' in response.text
    assert store.pairs_for("s") == []


def test_initial_upstream_error_returns_bad_gateway(store: FakeSessionStore) -> None:
    """Catch sending a 200 stream when the first upstream chunk cannot be fetched."""
    unavailable_model = InitialFailureModel([])
    app.dependency_overrides[get_session_store] = lambda: store
    app.dependency_overrides[get_chat_model] = lambda: unavailable_model
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"session_id": "s", "message": "退款"})
    app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "upstream_error"}


def test_second_call_receives_committed_history(
    client: TestClient, fake_model: FakeModel
) -> None:
    """Catch a route that commits replies but does not use them as later context."""
    client.post("/api/chat", json={"session_id": "s", "message": "订单 A 未发货"})
    client.post("/api/chat", json={"session_id": "s", "message": "我要催发货"})

    assert [message.content for message in fake_model.calls[1]][-3:] == [
        "订单 A 未发货",
        "您好，我来协助您确认。",
        "我要催发货",
    ]


def test_default_session_store_preserves_history_between_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch a dependency factory that creates a new store for every request."""
    monkeypatch.setenv("LITELLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "local")
    monkeypatch.setenv("SILICONFLOW_API_BASE", "https://api.siliconflow.cn/v1")
    monkeypatch.setenv("SILICONFLOW_API_KEY", "upstream")
    monkeypatch.setenv("SILICONFLOW_MODEL", "Qwen/Qwen3-8B")
    clear_cache = getattr(get_session_store, "cache_clear", lambda: None)
    clear_cache()
    model = FakeModel(["您好", "，我来协助您确认。"])
    app.dependency_overrides[get_chat_model] = lambda: model

    try:
        with TestClient(app) as client:
            client.post("/api/chat", json={"session_id": "s", "message": "订单 A 未发货"})
            client.post("/api/chat", json={"session_id": "s", "message": "我要催发货"})
    finally:
        app.dependency_overrides.clear()
        clear_cache()

    assert [message.content for message in model.calls[1]][-3:] == [
        "订单 A 未发货",
        "您好，我来协助您确认。",
        "我要催发货",
    ]
