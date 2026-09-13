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
    def __init__(
        self, chunks: list[str | AIMessageChunk], error: Exception | None = None
    ) -> None:
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
            if isinstance(chunk, AIMessageChunk):
                yield chunk
            else:
                yield AIMessageChunk(content=chunk)
        if self.error is not None:
            raise self.error


class AliasWithoutTokenCounterModel(FakeModel):
    def get_num_tokens_from_messages(self, messages: Sequence[BaseMessage]) -> int:
        raise NotImplementedError("token counting is unavailable for this model alias")


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


def test_metadata_chunks_before_text_are_skipped_from_sse_and_history(
    store: FakeSessionStore,
) -> None:
    """Catch forwarding reasoning metadata instead of the assistant text delta."""
    metadata_then_text = FakeModel(
        [
            AIMessageChunk(
                content="", additional_kwargs={"reasoning_content": "internal reasoning"}
            ),
            AIMessageChunk(content="", additional_kwargs={"role": "assistant"}),
            AIMessageChunk(content="您好"),
        ]
    )
    app.dependency_overrides[get_session_store] = lambda: store
    app.dependency_overrides[get_chat_model] = lambda: metadata_then_text
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"session_id": "s", "message": "退款"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text == 'data: {"delta":"您好"}\n\ndata: [DONE]\n\n'
    assert store.pairs_for("s") == [("退款", "您好")]


def test_failure_after_metadata_before_text_returns_bad_gateway(
    store: FakeSessionStore,
) -> None:
    """Catch committing HTTP 200 before an assistant text delta arrives."""
    metadata_then_failure = FakeModel(
        [AIMessageChunk(content="", additional_kwargs={"reasoning_content": "internal"})],
        RuntimeError("provider unavailable"),
    )
    app.dependency_overrides[get_session_store] = lambda: store
    app.dependency_overrides[get_chat_model] = lambda: metadata_then_failure
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"session_id": "s", "message": "退款"})
    app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "upstream_error"}


def test_metadata_only_completed_stream_emits_done_and_commits_empty_reply(
    store: FakeSessionStore,
) -> None:
    """Catch treating a successfully completed no-text stream as an upstream failure."""
    metadata_only = FakeModel(
        [AIMessageChunk(content="", additional_kwargs={"reasoning_content": "internal"})]
    )
    app.dependency_overrides[get_session_store] = lambda: store
    app.dependency_overrides[get_chat_model] = lambda: metadata_only
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"session_id": "s", "message": "退款"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text == "data: [DONE]\n\n"
    assert store.pairs_for("s") == [("退款", "")]


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


def test_second_request_works_when_model_alias_cannot_count_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch routing history trimming through an alias-specific LiteLLM counter."""
    monkeypatch.setenv("LITELLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "local")
    clear_cache = getattr(get_session_store, "cache_clear", lambda: None)
    clear_cache()
    model = AliasWithoutTokenCounterModel(["您好"])
    app.dependency_overrides[get_chat_model] = lambda: model

    try:
        with TestClient(app) as client:
            first = client.post("/api/chat", json={"session_id": "s", "message": "订单 A 未发货"})
            second = client.post("/api/chat", json={"session_id": "s", "message": "我要催发货"})
    finally:
        app.dependency_overrides.clear()
        clear_cache()

    assert first.status_code == 200
    assert second.status_code == 200
    assert [message.content for message in model.calls[1]][-3:] == [
        "订单 A 未发货",
        "您好",
        "我要催发货",
    ]
