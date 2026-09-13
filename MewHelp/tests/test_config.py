from app.config import Settings


def test_token_budget_defaults_to_2000() -> None:
    settings = Settings(
        litellm_base_url="http://localhost:4000/v1",
        litellm_api_key="local",
        _env_file=None,
    )

    assert settings.model_dump() == {
        "litellm_base_url": "http://localhost:4000/v1",
        "litellm_api_key": "local",
        "token_budget": 2000,
        "model_alias": "mewhelp-after-sales",
    }
