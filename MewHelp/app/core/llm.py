from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from app.config import Settings
from app.schemas.extract import AfterSalesTicket


def build_chat_model(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.model_alias,
        base_url=settings.litellm_base_url,
        api_key=settings.litellm_api_key,
        temperature=0,
    )


def build_extract_model(settings: Settings) -> Runnable:
    return build_chat_model(settings).with_structured_output(
        AfterSalesTicket, method="json_schema"
    )
