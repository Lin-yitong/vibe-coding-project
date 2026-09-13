from collections.abc import AsyncIterator, Sequence
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.orm import Session

from app.api.sse import encode_delta, encode_done, encode_error, encode_tool_status
from app.config import Settings
from app.core.llm import build_chat_model, build_tool_calling_model
from app.core.prompts import CUSTOMER_CHAT_PROMPT
from app.core.tool_calling import ToolCallingOrchestrator
from app.db import get_db_session
from app.schemas.chat import ChatRequest
from app.services.conversation_service import ConversationService, ConversationSessionMap
from app.tools.business import build_business_tools
from app.tools.registry import ToolRegistry


router = APIRouter()


def _assistant_text(chunk: object) -> str | None:
    content = getattr(chunk, "content", "")
    return content if isinstance(content, str) and content else None


@lru_cache(maxsize=1)
def get_conversation_sessions() -> ConversationSessionMap:
    """Keep only the Chapter 2 process-local browser-session mapping."""
    return ConversationSessionMap()


def get_conversation_service(
    db_session: Annotated[Session, Depends(get_db_session)],
    conversation_sessions: Annotated[ConversationSessionMap, Depends(get_conversation_sessions)],
) -> ConversationService:
    return ConversationService(db_session, conversation_sessions)


def get_tool_calling_orchestrator(
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ToolCallingOrchestrator:
    settings = Settings()
    return ToolCallingOrchestrator(
        planning_model=build_tool_calling_model(settings),
        final_model=build_chat_model(settings),
        tool_registry=ToolRegistry(build_business_tools()),
        conversation_service=conversation_service,
    )


def _messages_for(
    request_message: str, completed_turns: Sequence[tuple[str, str]]
) -> Sequence[BaseMessage]:
    system_message = CUSTOMER_CHAT_PROMPT.format_messages(message=request_message)[0]
    messages: list[BaseMessage] = [system_message]
    for user_message, assistant_message in completed_turns:
        messages.extend([HumanMessage(content=user_message), AIMessage(content=assistant_message)])
    messages.append(HumanMessage(content=request_message))
    return messages


@router.post("/chat")
async def stream_chat(
    request: ChatRequest,
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    orchestrator: Annotated[ToolCallingOrchestrator, Depends(get_tool_calling_orchestrator)],
) -> StreamingResponse:
    conversation = conversation_service.get_or_create(request.session_id)
    messages = _messages_for(
        request.message, conversation_service.completed_turns_for(conversation)
    )
    conversation_service.record_user(conversation, request.message)
    try:
        prepared = await orchestrator.prepare_turn(messages, conversation)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="upstream_error") from exc

    async def events() -> AsyncIterator[str]:
        for result in prepared.tool_results:
            yield encode_tool_status(result.name)

        fragments: list[str] = []
        try:
            async for chunk in prepared.final_stream():
                content = _assistant_text(chunk)
                if content is None:
                    continue
                fragments.append(content)
                yield encode_delta(content)
            conversation_service.record_final_answer(conversation, "".join(fragments))
        except Exception as exc:
            yield encode_error(str(exc))
            return

        yield encode_done()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
