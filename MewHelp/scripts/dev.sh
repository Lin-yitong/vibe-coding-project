#!/usr/bin/env sh
set -eu

set -a
. ./.env
set +a

litellm --config config/litellm.yaml --port 4000 &
proxy_pid=$!
trap 'kill "$proxy_pid" 2>/dev/null || true' EXIT INT TERM

uvicorn app.main:app --reload --port 8000
