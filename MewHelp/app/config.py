from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    litellm_base_url: str
    litellm_api_key: str
    siliconflow_api_base: str
    siliconflow_api_key: str
    siliconflow_model: str
    token_budget: int = 2000
    model_alias: str = "mewhelp-after-sales"
