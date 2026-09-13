# MewHelp Ch02 Function Calling Design

## Goal

Extend the existing SSE customer-service chat so a model can select business
tools, receive their results, and then stream a grounded final answer. The
feature persists customer-service conversations and tool traces in MySQL.

## Scope

- FastAPI, SQLAlchemy 2.0 and a Docker Compose MySQL development database.
- Four MySQL tables: `faq`, `conversations`, `messages`, and `tickets`.
- Five LangChain `@tool` tools: order, product, logistics, FAQ, and ticket
  creation.
- One planning round per customer turn. That planning round may contain zero,
  one, or several tool calls; after all selected tools finish, the model gets
  their results once and emits its final response. It must not select further
  tools from those results.
- SSE status frames and frontend badges that show the selected tool trace.
- TDD for code; a labelled evaluation set for prompts and seed-data behaviour.

## Out of Scope

- Automatic multi-round Agent loops.
- Vector retrieval, embeddings, RAG, or a vector database.
- Real order, catalogue, or logistics integrations. The three lookup tools
  return deterministic demonstration data.
- User login. Every Ch02 conversation uses `user_id = "demo-user"`.

## Database

Docker Compose runs an ephemeral MySQL instance. It has no persistent volume;
`docker compose down -v` followed by `docker compose up` rebuilds tables and
fixed seed data. Use MySQL `InnoDB` and `utf8mb4` throughout.

SQLAlchemy models mirror the supplied DDL exactly:

- `conversations`: unsigned bigint id, `user_id`, Chinese status enum
  (`进行中`, `已转人工`, `已结束`), timestamps, and an index on `user_id`.
- `messages`: unsigned bigint id, conversation FK, role enum
  (`user`, `assistant`, `tool`), nullable text content, nullable JSON
  `tool_calls`, nullable `tool_call_id`, timestamp, and a conversation index.
- `faq`: unsigned bigint id, question, answer, category, timestamps, and a
  category index.
- `tickets`: `ticket_no` business primary key, conversation FK, description,
  Chinese ticket type enum (`售后`, `投诉`, `咨询`), status enum
  (`待处理`, `已处理`), timestamp, and a conversation index.

The first request with a browser `session_id` creates one `conversations` row
for `demo-user`; later requests reuse the mapped conversation. The mapping is
held by the application for this demonstration release. A future authenticated
release replaces `demo-user` and makes the mapping durable.

Seed FAQ data includes an answer for “退货政策是什么”. It deliberately has no
keyword match for “邮费是多少”, so the expected Ch02 evaluation records the
SQL-LIKE miss rather than hiding it.

## Tool Contracts

All tools use `@tool(args_schema=...)` with explicit Pydantic inputs and are
registered in a whitelist registry.

| Tool | Input | Result source |
| --- | --- | --- |
| `query_order` | `order_no` | Deterministic mock order data |
| `query_product` | `product_name` | Deterministic mock product data |
| `query_logistics` | `order_no` | Deterministic mock logistics data |
| `query_faq` | `keyword` | `faq` SQL `LIKE` query |
| `create_ticket` | `description`, `ticket_type` | Insert into `tickets` |

`ticket_type` is exactly `售后`, `投诉`, or `咨询`; ambiguous cases use `咨询`.
The mock tools must generate stable answers from their input rather than using
unseeded randomness, so tests and demonstrations remain reproducible.

The registry validates tool name and arguments, enforces one timeout policy
and one retry after a transient execution failure, and returns a structured,
safe error result after failure. It never exposes exception stack traces.

## Chat and Persistence Flow

1. `POST /api/chat` receives `session_id` and message.
2. The conversation service creates or loads the database conversation, then
   writes the user `messages` row.
3. The ChatOpenAI model is bound to the five registered tools and receives the
   existing system prompt plus the current customer message.
4. Its `AIMessage.tool_calls` contains zero or more requests. The application
   writes an assistant row whose `tool_calls` JSON preserves those requests.
5. For each call in returned order, the registry validates and executes the
   registered tool. It writes a `tool` message with matching `tool_call_id`.
6. Before final text starts, SSE sends a `tool_status` frame naming each tool
   used in this turn. The frontend adds these names to the active assistant
   bubble as badges.
7. The assistant request and all `ToolMessage` results are returned to the
   model once. Its final natural-language answer streams as existing `delta`
   frames, then `[DONE]`; the completed assistant text is written to
   `messages`.

If no tool is selected, the endpoint retains the ordinary Ch01 streaming
path and writes only user and final assistant messages. A tool execution error
is returned to the final model as a safe tool result so it can explain the
next step; an initial model failure remains HTTP 502. A failure while streaming
the final answer emits the existing SSE error frame and does not write a
completed assistant answer.

## SSE and UI Contract

Existing frames remain unchanged:

```text
data: {"delta":"..."}

data: [DONE]
```

New status frames are sent before the first final `delta`:

```text
data: {"tool_status":{"name":"query_logistics","state":"running"}}
```

The frontend parser delivers the tool name to `App.vue`. The same assistant
bubble that receives deltas displays compact Chinese tool badges. The page
uses the existing pixel visual language. This focused frontend work follows
the requested Vibe Coding exception rather than brainstorm, TDD, or code
review process.

## Verification

Code tests cover ORM models/services, registry validation, timeout/retry,
FAQ hits and misses, ticket insertion, persisted message ordering, multi-tool
tool-call handling, and `tool_status`/delta/DONE SSE ordering. Integration
tests use the Docker MySQL service.

Prompt and data behaviour uses a labelled evaluation set with these minimum
cases:

1. “订单 1001 的物流到哪了” selects the required order/logistics tools and
   answers from their returned mock data.
2. “退货政策是什么” uses `query_faq` and returns the seeded answer.
3. “邮费是多少” produces the expected FAQ miss. This is recorded as a known
   SQL-LIKE recall limitation for the next chapter, not as a test failure.

## Development Record

`MewHelp/dev-notes/ch02.md` is appended after design, Context7 research,
database setup, tool infrastructure, chat/UI integration, evaluation, and
final verification. It contains commands, decisions, findings, and test
results, but never API keys or other secrets.
