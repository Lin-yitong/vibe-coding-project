import asyncio

import pytest

from app.tools.business import query_logistics
from app.tools.registry import ToolRegistry, TransientToolExecutionError


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry([query_logistics], timeout_seconds=0.02)


def test_registry_rejects_unknown_tool(registry: ToolRegistry) -> None:
    result = asyncio.run(registry.execute({"id": "call-1", "name": "drop_database", "args": {}}))

    assert result.ok is False
    assert result.content == "工具不可用。"


def test_registry_rejects_invalid_call_and_schema(registry: ToolRegistry) -> None:
    malformed = asyncio.run(
        registry.execute({"id": "call-1", "name": "query_logistics", "args": []})
    )
    invalid = asyncio.run(
        registry.execute(
            {"id": "call-2", "name": "query_logistics", "args": {"order_no": " "}}
        )
    )

    assert malformed.ok is False
    assert invalid.ok is False
    assert malformed.content == "工具调用格式无效。"
    assert invalid.content == "工具参数无效。"


def test_registry_retries_once_after_transient_failure(
    monkeypatch: pytest.MonkeyPatch, registry: ToolRegistry
) -> None:
    attempts = 0

    def flaky_invoke(*, order_no: str) -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TransientToolExecutionError("temporary failure")
        return '{"ok": true}'

    monkeypatch.setattr(query_logistics, "func", flaky_invoke)

    result = asyncio.run(
        registry.execute(
            {"id": "call-1", "name": "query_logistics", "args": {"order_no": "1001"}}
        )
    )

    assert attempts == 2
    assert result.ok is True
    assert result.content == '{"ok": true}'


def test_registry_does_not_retry_permanent_execution_failure(
    monkeypatch: pytest.MonkeyPatch, registry: ToolRegistry
) -> None:
    attempts = 0

    def permanently_broken(*, order_no: str) -> str:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("repository unavailable")

    monkeypatch.setattr(query_logistics, "func", permanently_broken)

    result = asyncio.run(
        registry.execute(
            {"id": "call-1", "name": "query_logistics", "args": {"order_no": "1001"}}
        )
    )

    assert attempts == 1
    assert result.ok is False
    assert result.content == "工具执行失败。"


def test_registry_returns_safe_timeout_without_retry(
    monkeypatch: pytest.MonkeyPatch, registry: ToolRegistry
) -> None:
    attempts = 0

    def slow_invoke(*, order_no: str) -> str:
        nonlocal attempts
        attempts += 1
        import time

        time.sleep(0.1)
        return "late"

    monkeypatch.setattr(query_logistics, "func", slow_invoke)

    result = asyncio.run(
        registry.execute(
            {"id": "call-1", "name": "query_logistics", "args": {"order_no": "1001"}}
        )
    )

    assert result.ok is False
    assert result.content == "工具执行超时。"
    assert attempts == 1
