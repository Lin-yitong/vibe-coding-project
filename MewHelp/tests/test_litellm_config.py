from pathlib import Path

import yaml


def test_litellm_config_uses_public_alias_and_environment_secrets() -> None:
    config = yaml.safe_load(Path("config/litellm.yaml").read_text())
    params = config["model_list"][0]["litellm_params"]

    assert config["model_list"][0]["model_name"] == "mewhelp-after-sales"
    assert params["api_key"] == "os.environ/SILICONFLOW_API_KEY"
    assert "SILICONFLOW_API_KEY" not in Path("config/litellm.yaml").read_text().replace(
        "os.environ/SILICONFLOW_API_KEY", ""
    )


def test_requirements_include_litellm_proxy_extra() -> None:
    requirements = Path("requirements.txt").read_text().splitlines()

    assert "litellm[proxy]>=1.81,<2.0" in requirements
