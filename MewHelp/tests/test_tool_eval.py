import asyncio
from pathlib import Path

from app.tools.registry import ToolExecutionResult
from evals.run_tool_eval import load_cases, run_cases


class RecordingPlanner:
    def __init__(self, calls_by_message: dict[str, list[dict[str, object]]]) -> None:
        self._calls_by_message = calls_by_message
        self.messages: list[str] = []

    async def plan(self, message: str) -> list[dict[str, object]]:
        self.messages.append(message)
        return self._calls_by_message[message]


class RecordingRegistry:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def execute(self, call: dict[str, object]) -> ToolExecutionResult:
        self.calls.append(call)
        content = (
            '{"matches": [{"question": "退货政策是什么"}]}'
            if call["args"] == {"keyword": "退货政策"}
            else "未找到匹配 FAQ。"
        )
        return ToolExecutionResult(
            tool_call_id=str(call["id"]),
            name=str(call["name"]),
            content=content,
            ok=True,
        )


def planned_calls() -> dict[str, list[dict[str, object]]]:
    return {
        "请查询订单 1001 的物流。": [
            {
                "id": "planned-logistics-1001",
                "name": "query_logistics",
                "args": {"order_no": "1001"},
            }
        ],
        "退货政策是什么？": [
            {
                "id": "planned-faq-return-policy",
                "name": "query_faq",
                "args": {"keyword": "退货政策"},
            }
        ],
        "邮费是多少？": [
            {
                "id": "planned-faq-postage",
                "name": "query_faq",
                "args": {"keyword": "邮费"},
            }
        ],
    }


def test_eval_cases_label_expected_faq_miss() -> None:
    cases = load_cases(Path("evals/ch02_tool_cases.json"))
    postage = next(case for case in cases if case["id"] == "faq-miss-postage")

    assert postage["expected_faq_match"] is False
    assert postage["known_limitation"] == "SQL LIKE keyword recall"


def test_runner_evaluates_all_labelled_messages_through_planner_pathway() -> None:
    cases = load_cases(Path("evals/ch02_tool_cases.json"))
    planner = RecordingPlanner(planned_calls())
    registry = RecordingRegistry()
    output: list[str] = []

    status = asyncio.run(run_cases(cases, planner, registry, output.append))

    assert status == 0
    assert planner.messages == [case["message"] for case in cases]
    assert [call["name"] for call in registry.calls] == [
        "query_logistics",
        "query_faq",
        "query_faq",
    ]
    assert output == [
        "PASS logistics-1001: tools=['query_logistics']",
        "PASS faq-return-policy: FAQ matched",
        "PASS faq-miss-postage: expected FAQ miss (SQL LIKE keyword recall)",
    ]


def test_runner_fails_when_planner_emits_an_unexpected_tool() -> None:
    cases = load_cases(Path("evals/ch02_tool_cases.json"))
    calls = planned_calls()
    calls["请查询订单 1001 的物流。"][0]["name"] = "query_product"
    planner = RecordingPlanner(calls)
    output: list[str] = []

    status = asyncio.run(run_cases(cases, planner, RecordingRegistry(), output.append))

    assert status == 1
    assert "FAIL logistics-1001: expected tools=['query_logistics'] actual tools=['query_product']" in output[0]
