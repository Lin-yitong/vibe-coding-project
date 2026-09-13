from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI

from app.api.sse import encode_delta, encode_done, encode_error
from app.config import Settings
from app.core.llm import build_chat_model
from app.core.memory import SessionStore
from app.core.prompts import CUSTOMER_CHAT_PROMPT
from app.schemas.chat import ChatRequest


router = APIRouter()


def get_session_store() -> SessionStore:
    return SessionStore(token_budget=Settings().token_budget)


def get_chat_model() -> ChatOpenAI:
    return build_chat_model(Settings())


@router.post("/chat")
async def stream_chat(
    request: ChatRequest,
    store: Annotated[SessionStore, Depends(get_session_store)],
    model: Annotated[ChatOpenAI, Depends(get_chat_model)],
) -> StreamingResponse:
    system_message = CUSTOMER_CHAT_PROMPT.format_messages(message=request.message)[0]
    messages = store.build_messages(
        request.session_id,
        request.message,
        system_message,
        model.get_num_tokens_from_messages,
    )
    try:
        stream = model.astream(messages)
        first_chunk = await anext(stream)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="upstream_error") from exc

    async def events() -> AsyncIterator[str]:
        fragments: list[str] = []

        def encode_chunk(chunk: object) -> str | None:
            content = getattr(chunk, "content", "")
            if not isinstance(content, str) or not content:
                return None
            fragments.append(content)
            return encode_delta(content)

        first_event = encode_chunk(first_chunk)
        if first_event is not None:
            yield first_event

        try:
            async for chunk in stream:
                event = encode_chunk(chunk)
                if event is not None:
                    yield event
        except Exception as exc:
            yield encode_error(str(exc))
            return

        store.commit(request.session_id, request.message, "".join(fragments))
        yield encode_done()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
