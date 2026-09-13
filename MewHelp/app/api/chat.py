from collections.abc import AsyncIterator, Sequence
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import BaseMessage, HumanMessage
from sqlalchemy.orm import Session

from app.api.sse import encode_delta, encode_done, encode_error, encode_tool_status
from app.config import Settings
from app.core.llm import build_chat_model, build_tool_calling_model
from app.core.prompts import CUSTOMER_CHAT_PROMPT
from app.core.tool_calling import ToolCallingOrchestrator
from app.db import SessionLocal, get_db_session
from app.repositories.faq import FaqRepository
from app.repositories.tickets import TicketRepository
from app.schemas.chat import ChatRequest
from app.services.conversation_service import ConversationService
from app.tools.business import configure_business_repositories
from app.tools.registry import ToolRegistry


router = APIRouter()


def _assistant_text(chunk: object) -> str | None:
    content = getattr(chunk, "content", "")
    return content if isinstance(content, str) and content else None


@lru_cache(maxsize=1)
def get_conversation_service() -> ConversationService:
    """Keep the Chapter 2 browser-session mapping for this application process."""
    return ConversationService(SessionLocal())


def get_tool_calling_orchestrator(
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ToolCallingOrchestrator:
    configure_business_repositories(
        faq_repository=FaqRepository(db_session),
        ticket_repository=TicketRepository(db_session),
    )
    settings = Settings()
    return ToolCallingOrchestrator(
        planning_model=build_tool_calling_model(settings),
        final_model=build_chat_model(settings),
        tool_registry=ToolRegistry(),
        conversation_service=conversation_service,
    )


def _messages_for(request_message: str) -> Sequence[BaseMessage]:
    system_message = CUSTOMER_CHAT_PROMPT.format_messages(message=request_message)[0]
    return [system_message, HumanMessage(content=request_message)]


@router.post("/chat")
async def stream_chat(
    request: ChatRequest,
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    orchestrator: Annotated[ToolCallingOrchestrator, Depends(get_tool_calling_orchestrator)],
) -> StreamingResponse:
    conversation = conversation_service.get_or_create(request.session_id)
    conversation_service.record_user(conversation, request.message)
    try:
        prepared = await orchestrator.prepare_turn(_messages_for(request.message), conversation)
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
