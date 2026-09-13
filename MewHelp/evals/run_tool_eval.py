"""Run stable, labelled Chapter 2 tool evaluations against the real registry."""

import asyncio
import json
from pathlib import Path
from collections.abc import Callable
from typing import Any, Protocol

from app.tools.business import build_business_tools
from app.tools.registry import ToolExecutionResult, ToolRegistry


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the labelled tool cases without depending on generated model wording."""
    fixture = path or Path(__file__).with_name("ch02_tool_cases.json")
    return json.loads(fixture.read_text(encoding="utf-8"))


class PlannerClient(Protocol):
    """The planning boundary used by a labelled tool evaluation."""

    async def plan(self, message: str) -> list[dict[str, object]]: ...


class ToolExecutor(Protocol):
    async def execute(self, call: dict[str, object]) -> ToolExecutionResult: ...


class LabelledPlanner:
    """Deterministic Ch02 planning client for the fixed evaluation messages."""

    async def plan(self, message: str) -> list[dict[str, object]]:
        if message == "请查询订单 1001 的物流。":
            return [
                {
                    "id": "planned-logistics-1001",
                    "name": "query_logistics",
                    "args": {"order_no": "1001"},
                }
            ]
        if message == "退货政策是什么？":
            return [
                {
                    "id": "planned-faq-return-policy",
                    "name": "query_faq",
                    "args": {"keyword": "退货政策"},
                }
            ]
        if message == "邮费是多少？":
            return [
                {
                    "id": "planned-faq-postage",
                    "name": "query_faq",
                    "args": {"keyword": "邮费"},
                }
            ]
        return []


async def _run_case(
    case: dict[str, Any], planner: PlannerClient, registry: ToolExecutor
) -> tuple[bool, str]:
    tool_calls = await planner.plan(case["message"])
    results: list[ToolExecutionResult] = []
    for tool_call in tool_calls:
        results.append(await registry.execute(tool_call))

    actual_names = [result.name for result in results]
    if not all(result.ok for result in results) or actual_names != case["expected_tool_names"]:
        return False, (
            f"FAIL {case['id']}: expected tools={case['expected_tool_names']} "
            f"actual tools={actual_names} results={[result.model_dump() for result in results]}"
        )

    expected_faq_match = case.get("expected_faq_match")
    if expected_faq_match is None:
        return True, f"PASS {case['id']}: tools={actual_names}"

    faq_result = next((result for result in results if result.name == "query_faq"), None)
    faq_matched = faq_result is not None and faq_result.content != "未找到匹配 FAQ。"
    if faq_matched != expected_faq_match:
        return False, (
            f"FAIL {case['id']}: expected FAQ match={expected_faq_match} "
            f"actual={faq_matched} content={faq_result.content if faq_result else None}"
        )
    if not expected_faq_match:
        return True, (
            f"PASS {case['id']}: expected FAQ miss "
            f"({case['known_limitation']})"
        )
    return True, f"PASS {case['id']}: FAQ matched"


async def run_cases(
    cases: list[dict[str, Any]],
    planner: PlannerClient,
    registry: ToolExecutor,
    emit: Callable[[str], object] = print,
) -> int:
    failed = False
    for case in cases:
        passed, output = await _run_case(case, planner, registry)
        emit(output)
        failed = failed or not passed
    return 1 if failed else 0


def main() -> int:
    return asyncio.run(
        run_cases(load_cases(), LabelledPlanner(), ToolRegistry(build_business_tools()))
    )


if __name__ == "__main__":
    raise SystemExit(main())
