from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import BaseMessage

from app.main import app


class FakeStructuredModel:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[list[BaseMessage]] = []

    async def ainvoke(self, messages: list[BaseMessage]) -> object:
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return self.response


@pytest.fixture
def fake_structured_model() -> FakeStructuredModel:
    return FakeStructuredModel(
        {"order_id": "SF1", "request_type": "exchange", "expected_solution": "换货"}
    )


@pytest.fixture
def failing_structured_model() -> FakeStructuredModel:
    return FakeStructuredModel(error=RuntimeError("provider unavailable"))


@pytest.fixture
def client(fake_structured_model: FakeStructuredModel) -> AsyncIterator[TestClient]:
    from app.api.extract import get_extract_model

    app.dependency_overrides[get_extract_model] = lambda: fake_structured_model
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_extract_returns_validated_ticket(
    client: TestClient, fake_structured_model: FakeStructuredModel
) -> None:
    """Catch an extraction route that bypasses structured ticket validation."""
    response = client.post("/api/extract", json={"text": "订单 SF1 左耳无声，想换货"})

    assert response.status_code == 200
    assert response.json() == {
        "order_id": "SF1",
        "request_type": "exchange",
        "expected_solution": "换货",
    }
    assert [message.content for message in fake_structured_model.calls[0]][-1] == (
        "订单 SF1 左耳无声，想换货"
    )


def test_extract_translates_model_failure_to_502(
    failing_structured_model: FakeStructuredModel,
) -> None:
    """Catch leaking provider failures instead of the stable gateway error."""
    from app.api.extract import get_extract_model

    app.dependency_overrides[get_extract_model] = lambda: failing_structured_model
    try:
        with TestClient(app) as client:
            response = client.post("/api/extract", json={"text": "我要售后"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "upstream_error"


def test_extract_translates_invalid_ticket_to_502() -> None:
    """Catch returning an unvalidated or malformed provider ticket to callers."""
    from app.api.extract import get_extract_model

    malformed_model = FakeStructuredModel({"request_type": "cancel"})
    app.dependency_overrides[get_extract_model] = lambda: malformed_model
    try:
        with TestClient(app) as client:
            response = client.post("/api/extract", json={"text": "订单 SF1 想取消"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "upstream_error"}
