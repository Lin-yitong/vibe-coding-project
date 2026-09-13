from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.runnables import Runnable

from app.config import Settings
from app.core.llm import build_extract_model
from app.core.prompts import EXTRACT_TICKET_PROMPT
from app.schemas.extract import AfterSalesTicket, ExtractRequest


router = APIRouter()


def get_extract_model() -> Runnable:
    return build_extract_model(Settings())


@router.post("/extract", response_model=AfterSalesTicket)
async def extract_ticket(
    request: ExtractRequest,
    model: Annotated[Runnable, Depends(get_extract_model)],
) -> AfterSalesTicket:
    messages = EXTRACT_TICKET_PROMPT.format_messages(text=request.text)
    try:
        result = await model.ainvoke(messages)
        return AfterSalesTicket.model_validate(result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="upstream_error") from exc
