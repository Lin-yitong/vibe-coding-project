"""Single-pass tool planning and result reinjection for customer support turns."""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from app.db import Conversation
from app.services.conversation_service import ConversationService
from app.tools.registry import ToolExecutionResult, ToolRegistry


class PlanningModel(Protocol):
    async def ainvoke(self, messages: Sequence[BaseMessage]) -> AIMessage: ...


class FinalModel(Protocol):
    def astream(self, messages: Sequence[BaseMessage]) -> AsyncIterator[object]: ...


@dataclass
class PreparedTurn:
    tool_results: list[ToolExecutionResult]
    _final_model: FinalModel
    _final_messages: list[BaseMessage]

    def final_stream(self) -> AsyncIterator[object]:
        """Stream the final answer through the normal, unbound chat model."""
        return self._final_model.astream(self._final_messages)


class ToolCallingOrchestrator:
    def __init__(
        self,
        *,
        planning_model: PlanningModel,
        final_model: FinalModel,
        tool_registry: ToolRegistry,
        conversation_service: ConversationService,
    ) -> None:
        self._planning_model = planning_model
        self._final_model = final_model
        self._tool_registry = tool_registry
        self._conversation_service = conversation_service

    async def prepare_turn(
        self, messages: Sequence[BaseMessage], conversation: Conversation
    ) -> PreparedTurn:
        planning_message = await self._planning_model.ainvoke(messages)
        tool_calls: list[dict[str, Any]] = planning_message.tool_calls
        if not tool_calls:
            return PreparedTurn(
                tool_results=[],
                _final_model=self._final_model,
                _final_messages=list(messages),
            )

        self._conversation_service.record_tool_request(conversation, tool_calls)
        tool_results: list[ToolExecutionResult] = []
        tool_messages: list[ToolMessage] = []
        for tool_call in tool_calls:
            result = await self._tool_registry.execute(tool_call)
            tool_results.append(result)
            self._conversation_service.record_tool_result(
                conversation, result.tool_call_id, result.content
            )
            tool_messages.append(
                ToolMessage(content=result.content, tool_call_id=result.tool_call_id)
            )

        return PreparedTurn(
            tool_results=tool_results,
            _final_model=self._final_model,
            _final_messages=[*messages, planning_message, *tool_messages],
        )
