#!/usr/bin/env sh
set -eu

(
  set -a
  . ./.env
  . ./.litellm.env
  set +a
  exec litellm --config config/litellm.yaml --port 4000
) &
proxy_pid=$!
trap 'kill "$proxy_pid" 2>/dev/null || true; wait "$proxy_pid" 2>/dev/null || true' EXIT INT TERM

(
  set -a
  . ./.env
  set +a
  unset SILICONFLOW_API_BASE SILICONFLOW_API_KEY SILICONFLOW_MODEL
  exec uvicorn app.main:app --reload --port 8000
)
