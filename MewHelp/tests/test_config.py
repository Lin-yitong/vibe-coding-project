from app.config import Settings


def test_token_budget_defaults_to_2000() -> None:
    settings = Settings(
        litellm_base_url="http://localhost:4000/v1",
        litellm_api_key="local",
        siliconflow_api_base="https://api.siliconflow.cn/v1",
        siliconflow_api_key="upstream",
        siliconflow_model="Qwen/Qwen3-8B",
    )

    assert settings.token_budget == 2000
    assert settings.model_alias == "mewhelp-after-sales"
