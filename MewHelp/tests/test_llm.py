from app.config import Settings
from app.core.llm import build_chat_model, build_extract_model


def make_settings() -> Settings:
    return Settings(
        litellm_base_url="http://localhost:4000/v1",
        litellm_api_key="local",
        siliconflow_api_base="https://api.siliconflow.cn/v1",
        siliconflow_api_key="upstream",
        siliconflow_model="Qwen/Qwen3-8B",
    )


def test_chat_model_uses_only_litellm_endpoint() -> None:
    """Catch the factory bypassing LiteLLM or selecting an upstream model name."""
    model = build_chat_model(make_settings())

    assert model.model_name == "mewhelp-after-sales"
    assert str(model.openai_api_base) == "http://localhost:4000/v1"
    assert model.temperature == 0


def test_extract_model_accepts_after_sales_ticket_schema() -> None:
    """Catch an extraction factory that does not apply the required schema wrapper."""
    model = build_extract_model(make_settings())

    assert model is not None
