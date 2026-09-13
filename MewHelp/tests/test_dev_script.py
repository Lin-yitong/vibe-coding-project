import os
import shutil
import subprocess
from pathlib import Path


def test_dev_script_scopes_proxy_secrets_to_litellm_subprocess(tmp_path: Path) -> None:
    """Catch loading upstream credentials into the FastAPI process or omitting them from LiteLLM."""
    project = tmp_path / "project"
    scripts = project / "scripts"
    bin_dir = tmp_path / "bin"
    scripts.mkdir(parents=True)
    bin_dir.mkdir()
    shutil.copy(Path("scripts/dev.sh"), scripts / "dev.sh")
    (project / ".env").write_text(
        "LITELLM_BASE_URL=http://app-proxy/v1\n"
        "LITELLM_API_KEY=app-key\n"
        "TOKEN_BUDGET=1234\n"
    )
    (project / ".litellm.env").write_text(
        "SILICONFLOW_API_BASE=https://upstream.example/v1\n"
        "SILICONFLOW_API_KEY=upstream-key\n"
        "SILICONFLOW_MODEL=example/model\n"
    )
    proxy_env = tmp_path / "proxy.env"
    app_env = tmp_path / "app.env"
    proxy_stop = tmp_path / "proxy.stop"
    (bin_dir / "litellm").write_text(
        "#!/usr/bin/env sh\n"
        'env > "$CAPTURE_PROXY_ENV"\n'
        "trap 'touch \"$CAPTURE_PROXY_STOP\"; exit 0' TERM INT\n"
        "while :; do sleep 1; done\n"
    )
    (bin_dir / "uvicorn").write_text(
        "#!/usr/bin/env sh\n"
        'while [ ! -f "$CAPTURE_PROXY_ENV" ]; do sleep 0.01; done\n'
        'env > "$CAPTURE_APP_ENV"\n'
        "exit 0\n"
    )
    for executable in bin_dir.iterdir():
        executable.chmod(0o755)

    environment = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "CAPTURE_PROXY_ENV": str(proxy_env),
        "CAPTURE_APP_ENV": str(app_env),
        "CAPTURE_PROXY_STOP": str(proxy_stop),
        "SILICONFLOW_API_BASE": "https://inherited.example/v1",
        "SILICONFLOW_API_KEY": "inherited-key",
        "SILICONFLOW_MODEL": "inherited/model",
    }
    subprocess.run(["sh", "scripts/dev.sh"], cwd=project, env=environment, check=True)

    proxy_values = dict(line.split("=", 1) for line in proxy_env.read_text().splitlines())
    app_values = dict(line.split("=", 1) for line in app_env.read_text().splitlines())

    assert proxy_values["SILICONFLOW_API_KEY"] == "upstream-key"
    assert proxy_values["LITELLM_API_KEY"] == "app-key"
    assert app_values["LITELLM_API_KEY"] == "app-key"
    assert "SILICONFLOW_API_KEY" not in app_values
    assert "SILICONFLOW_API_BASE" not in app_values
    assert "SILICONFLOW_MODEL" not in app_values
    assert proxy_stop.exists()
