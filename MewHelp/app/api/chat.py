from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI

from app.api.sse import encode_delta, encode_done, encode_error
from app.config import Settings
from app.core.llm import build_chat_model
from app.core.memory import SessionStore
from app.core.prompts import CUSTOMER_CHAT_PROMPT
from app.core.token_counting import count_message_tokens
from app.schemas.chat import ChatRequest


router = APIRouter()


def _assistant_text(chunk: object) -> str | None:
    content = getattr(chunk, "content", "")
    return content if isinstance(content, str) and content else None


@lru_cache(maxsize=1)
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
        count_message_tokens,
    )
    try:
        stream = model.astream(messages)
        first_text: str | None = None
        async for chunk in stream:
            first_text = _assistant_text(chunk)
            if first_text is not None:
                break
    except Exception as exc:
        raise HTTPException(status_code=502, detail="upstream_error") from exc

    async def events() -> AsyncIterator[str]:
        fragments: list[str] = []

        if first_text is not None:
            fragments.append(first_text)
            yield encode_delta(first_text)

        try:
            async for chunk in stream:
                content = _assistant_text(chunk)
                if content is None:
                    continue
                fragments.append(content)
                yield encode_delta(content)
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
