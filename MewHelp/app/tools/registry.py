"""Whitelist-only asynchronous execution for model-requested tools."""

import asyncio
from collections.abc import Sequence

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError

from app.tools.business import REGISTERED_TOOLS


class ToolExecutionResult(BaseModel):
    tool_call_id: str
    name: str
    content: str
    ok: bool


class ToolRegistry:
    def __init__(
        self, tools: Sequence[BaseTool] = REGISTERED_TOOLS, *, timeout_seconds: float = 5.0
    ) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._timeout_seconds = timeout_seconds

    async def execute(self, call: dict[str, object]) -> ToolExecutionResult:
        tool_call_id, name, args = self._validate_call(call)
        if tool_call_id is None or name is None or args is None:
            return ToolExecutionResult(
                tool_call_id=tool_call_id or "", name=name or "", content="工具调用格式无效。", ok=False
            )

        tool = self._tools.get(name)
        if tool is None:
            return ToolExecutionResult(tool_call_id=tool_call_id, name=name, content="工具不可用。", ok=False)

        try:
            tool.args_schema.model_validate(args)
        except ValidationError:
            return ToolExecutionResult(
                tool_call_id=tool_call_id, name=name, content="工具参数无效。", ok=False
            )

        for attempt in range(2):
            try:
                content = await self._execute_once(tool, args)
                return ToolExecutionResult(
                    tool_call_id=tool_call_id, name=name, content=str(content), ok=True
                )
            except asyncio.TimeoutError:
                return ToolExecutionResult(
                    tool_call_id=tool_call_id, name=name, content="工具执行超时。", ok=False
                )
            except (TypeError, ValueError):
                return ToolExecutionResult(
                    tool_call_id=tool_call_id, name=name, content="工具执行失败。", ok=False
                )
            except Exception:
                if attempt == 1:
                    return ToolExecutionResult(
                        tool_call_id=tool_call_id, name=name, content="工具执行失败。", ok=False
                    )

        raise AssertionError("unreachable")

    @staticmethod
    def _validate_call(
        call: dict[str, object],
    ) -> tuple[str | None, str | None, dict[str, object] | None]:
        tool_call_id = call.get("id") if isinstance(call.get("id"), str) else None
        name = call.get("name") if isinstance(call.get("name"), str) else None
        args = call.get("args") if isinstance(call.get("args"), dict) else None
        if not tool_call_id or not name:
            return None, None, None
        return tool_call_id, name, args

    async def _execute_once(self, tool: BaseTool, args: dict[str, object]) -> object:
        return await asyncio.wait_for(
            asyncio.to_thread(tool.invoke, args), timeout=self._timeout_seconds
        )
