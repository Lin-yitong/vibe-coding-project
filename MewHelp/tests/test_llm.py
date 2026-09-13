from app.config import Settings
from app.core.llm import build_chat_model, build_extract_model, build_tool_calling_model


def make_settings() -> Settings:
    return Settings(
        litellm_base_url="http://localhost:4000/v1",
        litellm_api_key="local",
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


def test_tool_calling_model_binds_exactly_the_registered_tools(monkeypatch) -> None:
    class FakeChatModel:
        def __init__(self) -> None:
            self.bound_tools: list[object] | None = None
            self.bind_tools_calls = 0

        def bind_tools(self, tools: list[object]) -> object:
            self.bind_tools_calls += 1
            self.bound_tools = tools
            return "bound-model"

    chat_model = FakeChatModel()
    tools = [object(), object()]
    monkeypatch.setattr("app.core.llm.build_chat_model", lambda settings: chat_model)

    result = build_tool_calling_model(make_settings(), tools)

    assert result == "bound-model"
    assert chat_model.bind_tools_calls == 1
    assert chat_model.bound_tools is tools
