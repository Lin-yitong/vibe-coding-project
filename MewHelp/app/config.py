from collections.abc import Callable
from typing import Any

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    litellm_base_url: str
    litellm_api_key: str
    token_budget: int = 2000
    model_alias: str = "mewhelp-after-sales"
    database_url: str = (
        "mysql+pymysql://mewhelp:mewhelp@127.0.0.1:3306/mewhelp?charset=utf8mb4"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource | Callable[[], dict[str, Any]], ...]:
        def without_database_url(
            source: PydanticBaseSettingsSource,
        ) -> Callable[[], dict[str, Any]]:
            def load() -> dict[str, Any]:
                values = source()
                values.pop("database_url", None)
                return values

            return load

        # DATABASE_URL is intentionally accepted only from the configured .env file.
        return (
            without_database_url(init_settings),
            without_database_url(env_settings),
            dotenv_settings,
            file_secret_settings,
        )
