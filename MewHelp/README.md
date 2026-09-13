# MewHelp Ch02

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

- `.env` is the FastAPI application's configuration. It contains
  `LITELLM_BASE_URL`, `LITELLM_API_KEY`, `TOKEN_BUDGET`, and `DATABASE_URL`;
  its LiteLLM API key is also the proxy's master key.
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

Start the reproducible MySQL demo database before starting the API:

```bash
docker compose up -d
# Equivalent Make target: make db-up
docker compose ps
```

Wait until MySQL reports `healthy`. The initialization scripts create the
schema and seed the Chapter 2 FAQ records on every new database container.

The compose file currently publishes MySQL on host port `3306`. If that port
is occupied, first identify its owner with `docker ps --format 'table {{.Names}}\t{{.Ports}}'`.
Do not run `docker compose down` in another project. Stop that known container
only when it is safe to do so, or use a local copy of this project's compose
configuration with an unused host port and set the matching `DATABASE_URL` in
your untracked `.env` (for example, `127.0.0.1:3307`).

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

The labelled Chapter 2 tool evaluation only needs the MySQL demo database. It
uses labelled expectations and a deterministic injected planner rather than
model-generated wording, and verifies the seed-data FAQ result as well as the
planner's emitted tool selection:

```bash
make eval-tools
```

It reports three cases: logistics for order `1001`, a matching return-policy
FAQ, and the `faq-miss-postage` case. The postage case is a successful expected
miss and explicitly records the known `SQL LIKE keyword recall` limitation.

## Reset the demo database

These commands destroy only this Compose project's MySQL container and its
ephemeral data, then rerun the schema and seed scripts:

```bash
make db-reset
```

Use `make db-down` when you want to remove the demo database without starting
it again. Do not use either command against another project's Compose setup.

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

## Browser acceptance for Chapter 2

With MySQL healthy, `.env` and `.litellm.env` configured, and `make dev`
running, start the frontend in another terminal:

```bash
make frontend-dev
```

Open the Vite URL (normally `http://localhost:5173`) and verify these flows:

1. Send `请查询订单 1001 的物流。`; the streamed assistant response should show a
   查询物流 badge.
2. Send `退货政策是什么？`; it should show a 查询常见问题 badge and use the seeded
   return-policy FAQ.
3. Send `邮费是多少？`; it should show a 查询常见问题 badge, while the FAQ lookup
   has no match. This is the documented Chapter 2 recall limitation, not a
   browser acceptance failure.

For a clean repeat, run `make db-reset`, restart `make dev` if it has an open
database connection, and repeat the three messages in a new conversation.
