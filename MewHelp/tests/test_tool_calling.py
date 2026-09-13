import asyncio
from collections.abc import AsyncIterator, Sequence

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, ToolMessage

from app.core.tool_calling import ToolCallingOrchestrator
from app.tools.registry import ToolExecutionResult


class FakePlanningModel:
    def __init__(self, response: AIMessage) -> None:
        self.response = response
        self.calls: list[list[BaseMessage]] = []

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        self.calls.append(list(messages))
        return self.response


class FakeFinalModel:
    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self.calls: list[list[BaseMessage]] = []
        self.bind_tools_calls = 0

    def bind_tools(self, tools: object) -> object:
        self.bind_tools_calls += 1
        raise AssertionError("the final model must not select tools")

    async def astream(self, messages: Sequence[BaseMessage]) -> AsyncIterator[AIMessageChunk]:
        self.calls.append(list(messages))
        for content in self.chunks:
            yield AIMessageChunk(content=content)


class RecordingRegistry:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def execute(self, call: dict[str, object]) -> ToolExecutionResult:
        self.calls.append(call)
        return ToolExecutionResult(
            tool_call_id=str(call["id"]),
            name=str(call["name"]),
            content=f'{call["name"]} result',
            ok=True,
        )


class RecordingConversationService:
    def __init__(self) -> None:
        self.tool_requests: list[tuple[object, list[dict[str, object]]]] = []
        self.tool_results: list[tuple[object, str, str]] = []

    def record_tool_request(self, conversation: object, tool_calls: list[dict[str, object]]) -> None:
        self.tool_requests.append((conversation, tool_calls))

    def record_tool_result(self, conversation: object, tool_call_id: str, content: str) -> None:
        self.tool_results.append((conversation, tool_call_id, content))


def collect(stream: AsyncIterator[AIMessageChunk]) -> list[str]:
    async def _collect() -> list[str]:
        return [chunk.content async for chunk in stream]

    return asyncio.run(_collect())


def test_orchestrator_executes_all_calls_in_model_order_then_streams_once() -> None:
    tool_calls = [
        {"id": "call-order", "name": "query_order", "args": {"order_no": "1001"}},
        {
            "id": "call-logistics",
            "name": "query_logistics",
            "args": {"order_no": "1001"},
        },
    ]
    planning_message = AIMessage(content="", tool_calls=tool_calls)
    planning_model = FakePlanningModel(planning_message)
    final_model = FakeFinalModel(["订单已发货", "，物流运输中。"])
    registry = RecordingRegistry()
    conversations = RecordingConversationService()
    conversation = object()
    orchestrator = ToolCallingOrchestrator(
        planning_model=planning_model,
        final_model=final_model,
        tool_registry=registry,
        conversation_service=conversations,
    )

    prepared = asyncio.run(
        orchestrator.prepare_turn([HumanMessage(content="查一下订单 1001 的物流")], conversation)
    )

    assert [item.name for item in prepared.tool_results] == ["query_order", "query_logistics"]
    assert registry.calls == planning_message.tool_calls
    assert conversations.tool_requests == [(conversation, planning_message.tool_calls)]
    assert conversations.tool_results == [
        (conversation, "call-order", "query_order result"),
        (conversation, "call-logistics", "query_logistics result"),
    ]
    assert len(planning_model.calls) == 1
    assert final_model.calls == []

    assert collect(prepared.final_stream()) == ["订单已发货", "，物流运输中。"]
    assert len(final_model.calls) == 1
    assert final_model.bind_tools_calls == 0
    final_messages = final_model.calls[0]
    assert final_messages == [
        HumanMessage(content="查一下订单 1001 的物流"),
        planning_message,
        ToolMessage(content="query_order result", tool_call_id="call-order"),
        ToolMessage(content="query_logistics result", tool_call_id="call-logistics"),
    ]


def test_no_tool_call_skips_tool_trace_and_streams_normal_answer() -> None:
    planning_model = FakePlanningModel(AIMessage(content="我可以帮您核实。"))
    final_model = FakeFinalModel(["请提供订单号。"])
    registry = RecordingRegistry()
    conversations = RecordingConversationService()
    orchestrator = ToolCallingOrchestrator(
        planning_model=planning_model,
        final_model=final_model,
        tool_registry=registry,
        conversation_service=conversations,
    )

    prepared = asyncio.run(
        orchestrator.prepare_turn([HumanMessage(content="商品有问题")], object())
    )

    assert prepared.tool_results == []
    assert registry.calls == []
    assert conversations.tool_requests == []
    assert conversations.tool_results == []
    assert collect(prepared.final_stream()) == ["请提供订单号。"]
    assert final_model.bind_tools_calls == 0
    assert final_model.calls == [[HumanMessage(content="商品有问题")]]
