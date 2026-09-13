# MewHelp Ch01

MewHelp is a FastAPI after-sales chat service backed by a local LiteLLM proxy.

## Local setup

From this directory, create and activate a virtual environment, install the
dependencies, and make a local environment file:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp .litellm.env.example .litellm.env
```

Use the two environment files for separate concerns:

- `.env` is the FastAPI application's configuration. It contains only
  `LITELLM_BASE_URL`, `LITELLM_API_KEY`, and `TOKEN_BUDGET`; its LiteLLM API
  key is also the proxy's master key.
- `.litellm.env` is the LiteLLM proxy's upstream-provider configuration. Set
  `SILICONFLOW_API_BASE`, `SILICONFLOW_API_KEY`, and `SILICONFLOW_MODEL` there.
  `SILICONFLOW_MODEL` must contain the complete LiteLLM model identifier,
  including its OpenAI-compatible provider prefix, for example
  `openai/Qwen/Qwen3-8B`.

Keep `LITELLM_BASE_URL` at `http://localhost:4000/v1`. Both local files are
ignored by Git. `make dev` loads both files for the LiteLLM subprocess, but
loads only `.env` for FastAPI. The application code only knows LiteLLM;
SiliconFlow settings never enter the FastAPI process.

## Run locally

Start LiteLLM on port 4000 and FastAPI on port 8000 together:

```bash
make dev
```

OpenAPI is available at `http://localhost:8000/openapi.json`.

## Chat UI

Install the frontend dependencies once:

```bash
cd frontend
npm install
```

Then start the API and the Vite development server in separate terminals from
the `MewHelp` directory:

```bash
make dev
```

```bash
make frontend-dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`) in your
browser. To manually accept the chat UI, send a question and confirm the
assistant response grows while it streams; send a follow-up in the same
conversation and confirm it retains the prior context; then start a new
conversation and confirm the two message lists do not mix.

## Test and evaluate

Run the unit tests:

```bash
make test
```

Run the frontend test suite and production build:

```bash
make frontend-test
make frontend-build
```

With `make dev` running in another terminal, run the extraction evaluation:

```bash
make eval-extract
```

## Manual acceptance

With `.env` and `.litellm.env` configured and `make dev` running, call the chat endpoint:

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H 'content-type: application/json' \
  -d '{"session_id":"demo-customer-001","message":"我的订单 20260913001 到现在还没发货怎么办？"}'
```

It should print multiple `data: {"delta":...}` lines followed by
`data: [DONE]`. Send another message using the same `session_id` to verify that
the service retains the prior turn.

Call the structured extraction endpoint:

```bash
curl -sS -X POST http://localhost:8000/api/extract \
  -H 'content-type: application/json' \
  -d '{"text":"订单 SF20260913001 买的耳机左耳没声音，想换货。"}'
```

The response should be schema-valid JSON.
