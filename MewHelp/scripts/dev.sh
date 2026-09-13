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
  proxy_bypass="${NO_PROXY-}"
  if [ -n "${no_proxy-}" ]; then
    proxy_bypass="${proxy_bypass:+${proxy_bypass},}${no_proxy}"
  fi
  proxy_bypass="${proxy_bypass:+${proxy_bypass},}localhost,127.0.0.1"
  export NO_PROXY="$proxy_bypass"
  export no_proxy="$proxy_bypass"
  unset proxy_bypass
  exec uvicorn app.main:app --reload --port 8000
)
