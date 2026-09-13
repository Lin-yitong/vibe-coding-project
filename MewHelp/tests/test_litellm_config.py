import asyncio
from pathlib import Path

import yaml
from litellm.proxy.proxy_server import ProxyConfig


def test_litellm_config_uses_public_alias_and_environment_secrets() -> None:
    config = yaml.safe_load(Path("config/litellm.yaml").read_text())
    params = config["model_list"][0]["litellm_params"]

    assert config["model_list"][0]["model_name"] == "mewhelp-after-sales"
    assert params["model"] == "os.environ/SILICONFLOW_MODEL"
    assert params["api_key"] == "os.environ/SILICONFLOW_API_KEY"
    assert "SILICONFLOW_API_KEY" not in Path("config/litellm.yaml").read_text().replace(
        "os.environ/SILICONFLOW_API_KEY", ""
    )


def test_litellm_proxy_resolves_provider_qualified_model_from_environment(monkeypatch) -> None:
    """SiliconFlow is routed as an OpenAI-compatible LiteLLM upstream."""
    monkeypatch.setenv("SILICONFLOW_API_BASE", "https://api.siliconflow.cn/v1")
    monkeypatch.setenv("SILICONFLOW_API_KEY", "upstream-key")
    monkeypatch.setenv("SILICONFLOW_MODEL", "openai/Qwen/Qwen3-8B")
    monkeypatch.setenv("LITELLM_API_KEY", "proxy-key")

    config = asyncio.run(ProxyConfig().get_config("config/litellm.yaml"))

    params = config["model_list"][0]["litellm_params"]
    assert params["model"].startswith("openai/")
    assert params["model"] == "openai/Qwen/Qwen3-8B"


def test_litellm_environment_example_uses_a_provider_qualified_model() -> None:
    template = dict(
        line.split("=", 1)
        for line in Path(".litellm.env.example").read_text().splitlines()
        if line
    )

    assert template["SILICONFLOW_MODEL"] == "openai/Qwen/Qwen3-8B"


def test_requirements_include_litellm_proxy_extra() -> None:
    requirements = Path("requirements.txt").read_text().splitlines()

    assert "litellm[proxy]>=1.81,<2.0" in requirements
