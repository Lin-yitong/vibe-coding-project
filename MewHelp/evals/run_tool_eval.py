"""Run labelled Chapter 2 tool evaluations through the production planner."""

import asyncio
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.core.llm import build_chat_model, build_tool_calling_model
from app.core.prompts import CUSTOMER_CHAT_PROMPT
from app.core.tool_calling import ToolCallingOrchestrator
from app.db import Conversation, SessionLocal
from app.services.conversation_service import ConversationService
from app.tools.business import build_business_tools
from app.tools.registry import ToolExecutionResult, ToolRegistry


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the labelled tool cases without depending on generated model wording."""
    fixture = path or Path(__file__).with_name("ch02_tool_cases.json")
    return json.loads(fixture.read_text(encoding="utf-8"))


class PlannerClient(Protocol):
    """The injected planning-and-execution boundary used by the evaluation."""

    async def plan_and_execute(self, message: str) -> list[ToolExecutionResult]: ...


class OrchestratorPlanner:
    """Exercise tool selection through the same bound planner used by chat."""

    def __init__(
        self, orchestrator: ToolCallingOrchestrator, conversation: Conversation
    ) -> None:
        self._orchestrator = orchestrator
        self._conversation = conversation

    async def plan_and_execute(self, message: str) -> list[ToolExecutionResult]:
        prepared = await self._orchestrator.prepare_turn(
            list(CUSTOMER_CHAT_PROMPT.format_messages(message=message)),
            self._conversation,
        )
        return prepared.tool_results


async def _run_case(
    case: dict[str, Any], planner: PlannerClient
) -> tuple[bool, str]:
    results = await planner.plan_and_execute(case["message"])

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
    emit: Callable[[str], object] = print,
) -> int:
    failed = False
    for case in cases:
        passed, output = await _run_case(case, planner)
        emit(output)
        failed = failed or not passed
    return 1 if failed else 0


async def run_live_cases(emit: Callable[[str], object] = print) -> int:
    """Build the production bound planner and execute all labelled cases."""
    settings = Settings()
    with SessionLocal() as session:
        conversation_service = ConversationService(session)
        conversation = conversation_service.get_or_create("ch02-tool-eval")
        tools = build_business_tools(conversation_id=conversation.id)
        orchestrator = ToolCallingOrchestrator(
            planning_model=build_tool_calling_model(settings, tools),
            final_model=build_chat_model(settings),
            tool_registry=ToolRegistry(tools),
            conversation_service=conversation_service,
        )
        return await run_cases(
            load_cases(), OrchestratorPlanner(orchestrator, conversation), emit
        )


def main() -> int:
    try:
        return asyncio.run(run_live_cases())
    except ValidationError:
        print(
            "ERROR eval-tools requires valid LITELLM_BASE_URL and "
            "LITELLM_API_KEY values in MewHelp/.env.",
            file=sys.stderr,
        )
    except SQLAlchemyError:
        print(
            "ERROR eval-tools could not use the project MySQL database; "
            "run `make db-up` and wait for it to become healthy.",
            file=sys.stderr,
        )
    except Exception as exc:
        print(
            "ERROR eval-tools could not call the bound planning model "
            f"({type(exc).__name__}); verify the LiteLLM proxy and provider credentials.",
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
