from pathlib import Path

from pydantic import BaseModel


def _load_dotenv() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_env = _load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = _env.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    value = _env.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = _env.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class Settings(BaseModel):
    app_name: str = _env.get("APP_NAME", "LLM Werewolf MVP")
    max_run_steps: int = _env_int("MAX_RUN_STEPS", 100)
    llm_enabled: bool = _env_bool("LLM_ENABLED", False)
    llm_base_url: str = _env.get("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_api_key: str = _env.get("LLM_API_KEY", "")
    llm_model: str = _env.get("LLM_MODEL", "gpt-4o-mini")
    llm_timeout_seconds: float = _env_float("LLM_TIMEOUT_SECONDS", 30.0)


settings = Settings()
