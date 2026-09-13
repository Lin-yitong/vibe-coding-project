"""Run stable, labelled Chapter 2 tool evaluations against the real registry."""

import asyncio
import json
from pathlib import Path
from typing import Any

from app.tools.business import build_business_tools
from app.tools.registry import ToolExecutionResult, ToolRegistry


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the labelled tool cases without depending on generated model wording."""
    fixture = path or Path(__file__).with_name("ch02_tool_cases.json")
    return json.loads(fixture.read_text(encoding="utf-8"))


async def _run_case(case: dict[str, Any], registry: ToolRegistry) -> tuple[bool, str]:
    results: list[ToolExecutionResult] = []
    for tool_call in case["tool_calls"]:
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


async def _main() -> int:
    registry = ToolRegistry(build_business_tools())
    failed = False
    for case in load_cases():
        passed, output = await _run_case(case, registry)
        print(output)
        failed = failed or not passed
    return 1 if failed else 0


def main() -> int:
    return asyncio.run(_main())


if __name__ == "__main__":
    raise SystemExit(main())
