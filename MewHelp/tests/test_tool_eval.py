import asyncio
from pathlib import Path

from langchain_core.messages import BaseMessage

from app.tools.registry import ToolExecutionResult
import evals.run_tool_eval as tool_eval
from evals.run_tool_eval import load_cases, run_cases


class RecordingPlanner:
    def __init__(self, results_by_message: dict[str, list[ToolExecutionResult]]) -> None:
        self._results_by_message = results_by_message
        self.messages: list[str] = []

    async def plan_and_execute(self, message: str) -> list[ToolExecutionResult]:
        self.messages.append(message)
        return self._results_by_message[message]


def planned_results() -> dict[str, list[ToolExecutionResult]]:
    return {
        "请查询订单 1001 的物流。": [
            ToolExecutionResult(
                tool_call_id="planned-logistics-1001",
                name="query_logistics",
                content='{"order_no": "1001"}',
                ok=True,
            )
        ],
        "退货政策是什么？": [
            ToolExecutionResult(
                tool_call_id="planned-faq-return-policy",
                name="query_faq",
                content='{"matches": [{"question": "退货政策是什么"}]}',
                ok=True,
            )
        ],
        "邮费是多少？": [
            ToolExecutionResult(
                tool_call_id="planned-faq-postage",
                name="query_faq",
                content="未找到匹配 FAQ。",
                ok=True,
            )
        ],
    }


def test_eval_cases_label_expected_faq_miss() -> None:
    cases = load_cases(Path("evals/ch02_tool_cases.json"))
    postage = next(case for case in cases if case["id"] == "faq-miss-postage")

    assert postage["expected_faq_match"] is False
    assert postage["known_limitation"] == "SQL LIKE keyword recall"


def test_runner_evaluates_all_labelled_messages_through_planner_pathway() -> None:
    cases = load_cases(Path("evals/ch02_tool_cases.json"))
    planner = RecordingPlanner(planned_results())
    output: list[str] = []

    status = asyncio.run(run_cases(cases, planner, output.append))

    assert status == 0
    assert planner.messages == [case["message"] for case in cases]
    assert output == [
        "PASS logistics-1001: tools=['query_logistics']",
        "PASS faq-return-policy: FAQ matched",
        "PASS faq-miss-postage: expected FAQ miss (SQL LIKE keyword recall)",
    ]


def test_runner_fails_when_planner_emits_an_unexpected_tool() -> None:
    cases = load_cases(Path("evals/ch02_tool_cases.json"))
    results = planned_results()
    results["请查询订单 1001 的物流。"][0].name = "query_product"
    planner = RecordingPlanner(results)
    output: list[str] = []

    status = asyncio.run(run_cases(cases, planner, output.append))

    assert status == 1
    assert "FAIL logistics-1001: expected tools=['query_logistics'] actual tools=['query_product']" in output[0]


class FakePreparedTurn:
    def __init__(self, tool_results: list[ToolExecutionResult]) -> None:
        self.tool_results = tool_results


class RecordingOrchestrator:
    def __init__(self) -> None:
        self.calls: list[tuple[list[BaseMessage], object]] = []

    async def prepare_turn(
        self, messages: list[BaseMessage], conversation: object
    ) -> FakePreparedTurn:
        self.calls.append((list(messages), conversation))
        return FakePreparedTurn(planned_results()[str(messages[-1].content)])


def test_production_eval_planner_uses_the_tool_calling_orchestrator() -> None:
    conversation = object()
    orchestrator = RecordingOrchestrator()
    planner = tool_eval.OrchestratorPlanner(orchestrator, conversation)

    results = asyncio.run(planner.plan_and_execute("退货政策是什么？"))

    assert [result.name for result in results] == ["query_faq"]
    assert len(orchestrator.calls) == 1
    assert orchestrator.calls[0][1] is conversation
    assert orchestrator.calls[0][0][-1].content == "退货政策是什么？"
