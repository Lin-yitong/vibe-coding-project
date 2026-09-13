# MewHelp Ch02 Function Calling 工具链 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 为现有 MewHelp SSE 客服聊天接入 MySQL 持久化与 LangChain Function Calling，使模型可在单次规划中调用多个业务工具并基于工具结果流式回答。

**架构：** FastAPI 路由保留为 SSE 编排入口；SQLAlchemy 2.0 的 repository/service 层管理会话、消息、FAQ 和工单事务；工具注册中心提供白名单、Pydantic 参数校验、超时和一次重试。第一次 `bind_tools` 模型调用只负责产生工具申请，所有 `ToolMessage` 一次回灌到第二次模型调用，后者只流式输出最终文本。

**技术栈：** FastAPI、SQLAlchemy 2.0、PyMySQL、MySQL 8 Docker Compose、LangChain `@tool` / `bind_tools`、Pydantic 2、Vue 3、Vitest、pytest。

**Spec：** `docs/superpowers/specs/2026-09-13-mewhelp-ch02-function-calling-design.md`

## 全局约束

- 保留现有 LiteLLM 双进程和 `POST /api/chat` SSE 协议；新 `tool_status` 必须先于首个最终 `delta`。
- MySQL 无持久化卷；初始化时按用户提供的 DDL 语义建 `faq`、`conversations`、`messages`、`tickets` 四张表并灌固定数据。
- `conversations.status` 只能为 `进行中`、`已转人工`、`已结束`；`tickets.ticket_type` 只能为 `售后`、`投诉`、`咨询`；无法归类时使用 `咨询`。
- 工具仅允许白名单中的 `query_order`、`query_product`、`query_logistics`、`query_faq`、`create_ticket`；订单/商品/物流返回确定性 mock 数据。
- 每条客户消息只允许一个工具规划阶段，可执行该阶段的多个调用；工具结果回灌后不得再触发工具选择。
- 代码改动遵循 TDD。纯 Prompt 与种子数据行为使用标注评估集，不以脆弱的模型文案断言代替评估。
- 聊天页工具徽章是用户授权的 Vibe Coding 例外：不执行 brainstorm、TDD 或代码审查流程，但必须人工浏览器验收。
- 每完成一个任务，在 `MewHelp/dev-notes/ch02.md` 追加命令、决策和结果；不得写入密钥。

---

## 文件结构

| 文件 | 责任 |
| --- | --- |
| `MewHelp/docker-compose.yml` | 可重建 MySQL 8 服务、健康检查和初始化目录挂载 |
| `MewHelp/db/init/001_schema.sql` | 参考 DDL 的 MySQL 建表语句 |
| `MewHelp/db/init/002_seed.sql` | 固定 FAQ 种子数据 |
| `MewHelp/app/db/base.py` | SQLAlchemy `DeclarativeBase` |
| `MewHelp/app/db/session.py` | engine、`sessionmaker`、FastAPI session dependency |
| `MewHelp/app/db/models.py` | 四张表的 ORM 模型及枚举 |
| `MewHelp/app/repositories/*.py` | FAQ、会话/消息、工单的窄数据库操作 |
| `MewHelp/app/services/conversation_service.py` | `session_id` 到会话的内存映射及消息落库顺序 |
| `MewHelp/app/tools/schemas.py` | 五个工具的 Pydantic 输入模型 |
| `MewHelp/app/tools/business.py` | 五个 `@tool` 定义和确定性 mock/数据库业务逻辑 |
| `MewHelp/app/tools/registry.py` | 工具白名单、校验、超时、一次重试、结构化结果 |
| `MewHelp/app/core/tool_calling.py` | `bind_tools` 调用、工具申请持久化、ToolMessage 回灌与最终流式模型调用 |
| `MewHelp/app/api/sse.py` | 新增 `encode_tool_status` |
| `MewHelp/app/api/chat.py` | 用 Ch02 编排替换 Ch01 内存提交路径，同时保留错误边界 |
| `MewHelp/frontend/src/api/chatClient.ts` | 解析 `tool_status` 帧并回调 |
| `MewHelp/frontend/src/types/chat.ts` | 助手消息的 `toolNames` 数据 |
| `MewHelp/frontend/src/components/MessageBubble.vue` | 助手气泡的工具徽章显示 |
| `MewHelp/frontend/src/App.vue` | 当前流式助手消息累积工具名称 |
| `MewHelp/evals/ch02_tool_cases.json` | 三条标注工具/FAQ 评估样例 |
| `MewHelp/evals/run_tool_eval.py` | 运行评估集并报告预期 FAQ 漏召回 |

## Task 1：MySQL 演示环境与 SQLAlchemy 基建

**文件：**
- 新建：`MewHelp/docker-compose.yml`
- 新建：`MewHelp/db/init/001_schema.sql`
- 新建：`MewHelp/db/init/002_seed.sql`
- 新建：`MewHelp/app/db/__init__.py`、`base.py`、`session.py`、`models.py`
- 修改：`MewHelp/app/config.py`、`MewHelp/requirements.txt`、`MewHelp/.env.example`、`MewHelp/Makefile`
- 测试：`MewHelp/tests/test_db_models.py`、`MewHelp/tests/test_docker_compose.py`

**接口：**
- 产出 `Base`、`SessionLocal`、`get_db_session()` 和 ORM 类 `Conversation`、`Message`、`Faq`、`Ticket`。
- `Settings.database_url` 默认指向 `mysql+pymysql://mewhelp:mewhelp@127.0.0.1:3306/mewhelp?charset=utf8mb4`，仅由 `.env` 读取。

- [ ] **Step 1：写失败测试，锁定配置、DDL 和模型约束。**

```python
def test_ticket_model_uses_business_primary_key() -> None:
    assert Ticket.__table__.primary_key.columns.keys() == ["ticket_no"]
    assert Ticket.__table__.c.ticket_type.type.enums == ("售后", "投诉", "咨询")

def test_compose_has_ephemeral_mysql_and_healthcheck() -> None:
    compose = Path("docker-compose.yml").read_text()
    assert "mysql:8" in compose
    assert "healthcheck:" in compose
    assert "volumes:" not in compose.split("services:", 1)[1]
```

- [ ] **Step 2：运行测试，确认失败。**

运行：`pytest tests/test_db_models.py tests/test_docker_compose.py -v`

预期：失败，导入 `app.db` 或目标文件不存在。

- [ ] **Step 3：实现最小可用数据库环境。**

使用 `DeclarativeBase` 和同步 `sessionmaker`；在 compose 为 MySQL 定义数据库、用户和密码环境变量，挂载 `./db/init:/docker-entrypoint-initdb.d:ro`，但不声明 named volume。DDL 依照用户给出的列、枚举、外键与索引；种子 FAQ 包含退货政策，且不插入“邮费”关键词。将 `sqlalchemy>=2.0,<3.0` 与 `pymysql>=1.1,<2.0` 加入 requirements，并提供 `make db-up`、`make db-down`、`make db-reset`。

- [ ] **Step 4：运行测试，确认通过。**

运行：`pytest tests/test_db_models.py tests/test_docker_compose.py -v`

预期：通过。

- [ ] **Step 5：记录并提交。**

在 `dev-notes/ch02.md` 追加 Docker/ORM 决策与测试结果。

```bash
git add MewHelp/docker-compose.yml MewHelp/db MewHelp/app/db MewHelp/app/config.py MewHelp/requirements.txt MewHelp/.env.example MewHelp/Makefile MewHelp/tests/test_db_models.py MewHelp/tests/test_docker_compose.py MewHelp/dev-notes/ch02.md
git commit -m "feat: add MewHelp MySQL persistence foundation"
```

## Task 2：Repository 与会话消息持久化服务

**文件：**
- 新建：`MewHelp/app/repositories/faq.py`、`conversations.py`、`tickets.py`
- 新建：`MewHelp/app/services/conversation_service.py`
- 测试：`MewHelp/tests/test_repositories.py`、`MewHelp/tests/test_conversation_service.py`

**接口：**
- 消费 `Session`、`Conversation`、`Message`、`Faq`、`Ticket`。
- 产出 `ConversationService.get_or_create(session_id: str) -> Conversation`、`record_user(...)`、`record_tool_request(...)`、`record_tool_result(...)`、`record_final_answer(...)`。
- 产出 `FaqRepository.search(keyword: str) -> list[Faq]` 和 `TicketRepository.create(...) -> Ticket`。

- [ ] **Step 1：写失败测试，锁定事务和消息顺序。**

```python
def test_conversation_service_reuses_same_conversation_for_session(db_session) -> None:
    service = ConversationService(db_session)
    assert service.get_or_create("browser-1").id == service.get_or_create("browser-1").id

def test_message_trace_is_user_request_tool_final_answer(db_session) -> None:
    # record_user → record_tool_request → record_tool_result → record_final_answer
    assert [message.role for message in rows] == ["user", "assistant", "tool", "assistant"]
    assert rows[1].tool_calls == [{"id": "call-1", "name": "query_faq", "args": {"keyword": "退货"}}]
    assert rows[2].tool_call_id == "call-1"
```

- [ ] **Step 2：运行失败测试。**

运行：`pytest tests/test_repositories.py tests/test_conversation_service.py -v`

预期：失败，repository/service 不存在。

- [ ] **Step 3：实现窄 repository 与 service。**

`FaqRepository.search` 对 `question`、`answer`、`category` 使用参数化 `%keyword%` LIKE，不能拼接 SQL。`ConversationService` 的实例保有 `{session_id: conversation_id}` 映射，创建时写 `demo-user` 与 `进行中`；每个 public 写方法在短事务内 commit，读操作不修改数据。`TicketRepository` 用安全、确定的工单号生成器（如 UUID 的固定前缀）生成最多 32 字符的 `ticket_no`。

- [ ] **Step 4：运行通过测试。**

运行：`pytest tests/test_repositories.py tests/test_conversation_service.py -v`

预期：通过；包含 LIKE 命中“退货”和未命中“邮费”的断言。

- [ ] **Step 5：记录并提交。**

```bash
git add MewHelp/app/repositories MewHelp/app/services MewHelp/tests/test_repositories.py MewHelp/tests/test_conversation_service.py MewHelp/dev-notes/ch02.md
git commit -m "feat: persist MewHelp conversations and support data"
```

## Task 3：五个 LangChain 工具与白名单注册中心

**文件：**
- 新建：`MewHelp/app/tools/__init__.py`、`schemas.py`、`business.py`、`registry.py`
- 测试：`MewHelp/tests/test_tools.py`、`MewHelp/tests/test_tool_registry.py`

**接口：**
- 产出 `REGISTERED_TOOLS: list[BaseTool]`。
- 产出 `async ToolRegistry.execute(call: dict[str, object]) -> ToolExecutionResult`，其中结果含 `tool_call_id`、`name`、`content`、`ok`。
- 消费 FAQ/Ticket repository；mock 工具不访问数据库。

- [ ] **Step 1：写失败测试，锁定工具 schema、确定性和失败模式。**

```python
async def test_registry_rejects_unknown_tool() -> None:
    result = await registry.execute({"id": "call-1", "name": "drop_database", "args": {}})
    assert result.ok is False
    assert result.content == "工具不可用。"

def test_query_logistics_is_deterministic() -> None:
    assert query_logistics.invoke({"order_no": "1001"}) == query_logistics.invoke({"order_no": "1001"})

def test_registry_retries_once_after_transient_failure(monkeypatch) -> None:
    assert attempts == 2
    assert result.ok is True
```

- [ ] **Step 2：运行失败测试。**

运行：`pytest tests/test_tools.py tests/test_tool_registry.py -v`

预期：失败，工具或 registry 不存在。

- [ ] **Step 3：实现工具与执行器。**

用 `@tool(args_schema=...)` 定义所有五个函数，函数 docstring 写明模型何时使用。订单、商品、物流根据规范化输入返回 JSON 字符串；`query_faq` 返回命中问答或明确的“未找到匹配 FAQ”；`create_ticket` 只接受 DDL 中的三种类型。注册中心把 `AIMessage.tool_calls` 的 `{id,name,args}` 映射为工具调用，Pydantic 校验失败、未知名称、超时、一次重试后异常均转为无堆栈的 `ToolExecutionResult`。同步工具执行放入 `asyncio.to_thread`，用 `asyncio.wait_for` 实现超时，且只对可重试执行错误再试一次。

- [ ] **Step 4：运行通过测试。**

运行：`pytest tests/test_tools.py tests/test_tool_registry.py -v`

预期：通过，包括 schema 非法、未知工具、超时、一次重试、FAQ 和工单路径。

- [ ] **Step 5：记录并提交。**

```bash
git add MewHelp/app/tools MewHelp/tests/test_tools.py MewHelp/tests/test_tool_registry.py MewHelp/dev-notes/ch02.md
git commit -m "feat: add MewHelp function calling tools"
```

## Task 4：单次工具规划和模型回灌编排

**文件：**
- 新建：`MewHelp/app/core/tool_calling.py`
- 修改：`MewHelp/app/core/llm.py`、`MewHelp/app/core/prompts.py`
- 测试：`MewHelp/tests/test_tool_calling.py`、`MewHelp/tests/test_llm.py`、`MewHelp/tests/test_prompts.py`

**接口：**
- 产出 `ToolCallingOrchestrator.prepare_turn(messages, conversation) -> PreparedTurn` 与 `PreparedTurn.final_stream()`。
- `PreparedTurn.tool_results` 按模型 `tool_calls` 顺序排列；`final_stream()` 不再绑定工具。

- [ ] **Step 1：写失败测试，锁定“一个规划阶段、多个工具、一次回灌”。**

```python
async def test_orchestrator_executes_all_calls_then_streams_once(fake_model) -> None:
    prepared = await orchestrator.prepare_turn(messages, conversation)
    assert [item.name for item in prepared.tool_results] == ["query_order", "query_logistics"]
    assert fake_model.bind_tools_calls == 1
    assert fake_model.final_model_calls == 1

async def test_no_tool_call_skips_tool_result_messages(fake_model) -> None:
    prepared = await orchestrator.prepare_turn(messages, conversation)
    assert prepared.tool_results == []
```

- [ ] **Step 2：运行失败测试。**

运行：`pytest tests/test_tool_calling.py tests/test_llm.py tests/test_prompts.py -v`

预期：失败，orchestrator 尚未实现。

- [ ] **Step 3：实现最小编排。**

`build_tool_calling_model(settings)` 返回 `build_chat_model(settings).bind_tools(REGISTERED_TOOLS)`。第一次使用 `ainvoke` 获取 `AIMessage`；持久化其工具申请后，按返回顺序执行所有 call，持久化每条 `tool` 结果，并创建带原始 call id 的 `ToolMessage`。最终模型调用只接收普通聊天模型和“历史 + 工具申请 + ToolMessage”，调用 `astream`，绝不再 `.bind_tools()`。更新 System Prompt：有工具结果时只根据结果回答；无结果时不得编造业务事实并按原有安全规则追问。

- [ ] **Step 4：运行通过测试。**

运行：`pytest tests/test_tool_calling.py tests/test_llm.py tests/test_prompts.py -v`

预期：通过，并明确断言不会出现第二次工具选择。

- [ ] **Step 5：记录并提交。**

```bash
git add MewHelp/app/core/tool_calling.py MewHelp/app/core/llm.py MewHelp/app/core/prompts.py MewHelp/tests/test_tool_calling.py MewHelp/tests/test_llm.py MewHelp/tests/test_prompts.py MewHelp/dev-notes/ch02.md
git commit -m "feat: orchestrate MewHelp tool calling turns"
```

## Task 5：SSE Chat 入口接入与持久化错误边界

**文件：**
- 修改：`MewHelp/app/api/chat.py`、`MewHelp/app/api/sse.py`、`MewHelp/app/main.py`
- 测试：`MewHelp/tests/test_chat_api.py`、`MewHelp/tests/test_sse.py`

**接口：**
- 新增 `encode_tool_status(name: str, state: str = "running") -> str`。
- `/api/chat` 依赖 `ConversationService` 和 `ToolCallingOrchestrator`，响应仍为 `text/event-stream`。

- [ ] **Step 1：写失败测试，锁定 SSE 顺序和落库边界。**

```python
async def test_chat_sends_tool_status_before_final_delta(client, fake_orchestrator) -> None:
    frames = await collect_sse(client.post("/api/chat", json={"session_id": "s1", "message": "订单 1001 的物流"}))
    assert frames == [
        {"tool_status": {"name": "query_order", "state": "running"}},
        {"tool_status": {"name": "query_logistics", "state": "running"}},
        {"delta": "已查到"},
        "[DONE]",
    ]

async def test_final_stream_failure_does_not_persist_completed_answer(...) -> None:
    assert repository.final_answers == []
```

- [ ] **Step 2：运行失败测试。**

运行：`pytest tests/test_chat_api.py tests/test_sse.py -v`

预期：失败，因为没有 `tool_status` 或 Ch01 route 仍使用内存 store。

- [ ] **Step 3：实现入口编排。**

路由先完成 `prepare_turn`，确认首次模型调用成功后返回 `StreamingResponse`。事件生成器依次发出每项 `prepared.tool_results` 的状态帧、最终模型 token 的 delta 帧、完成后写最终 assistant 消息和 `[DONE]`。首次模型失败为 HTTP 502；最终流失败发既有 error 帧并停止，不写最终完成消息。`app/main.py` 用 Ch02 标题更新但保留 health endpoint。

- [ ] **Step 4：运行通过测试和完整后端回归。**

运行：`pytest tests/test_chat_api.py tests/test_sse.py -v && make test`

预期：所有 Chat/SSE 测试及完整后端测试通过。

- [ ] **Step 5：记录并提交。**

```bash
git add MewHelp/app/api/chat.py MewHelp/app/api/sse.py MewHelp/app/main.py MewHelp/tests/test_chat_api.py MewHelp/tests/test_sse.py MewHelp/dev-notes/ch02.md
git commit -m "feat: stream MewHelp tool calling chat turns"
```

## Task 6：聊天页工具轨迹徽章（Vibe Coding 例外）

**文件：**
- 修改：`MewHelp/frontend/src/api/chatClient.ts`、`types/chat.ts`、`components/MessageBubble.vue`、`App.vue`、`styles/index.css`

**接口：**
- `ChatStreamHandlers` 新增 `onToolStatus(name: string): void`。
- `ChatMessage` 的 assistant 消息新增 `toolNames: string[]`。

- [ ] **Step 1：按 Vibe Coding 直接改造数据流。**

在 SSE parser 识别 `{tool_status:{name,state}}` 并调用 `onToolStatus`；`App.vue` 将名称去重后放入当前 streaming assistant message；`MessageBubble.vue` 仅在 `toolNames.length > 0` 时显示中文名称徽章。将 `query_order`、`query_product`、`query_logistics`、`query_faq`、`create_ticket` 映射成“查询订单”“查询商品”“查询物流”“查询常见问题”“创建人工工单”。

- [ ] **Step 2：浏览器人工验收。**

启动 Docker MySQL、后端与前端；发送“订单 1001 的物流到哪了”，确认回复前气泡出现订单/物流工具徽章且文本逐字增长；再发送“退货政策是什么”，确认显示 FAQ 徽章。

- [ ] **Step 3：记录并提交。**

```bash
git add MewHelp/frontend/src/api/chatClient.ts MewHelp/frontend/src/types/chat.ts MewHelp/frontend/src/components/MessageBubble.vue MewHelp/frontend/src/App.vue MewHelp/frontend/src/styles/index.css MewHelp/dev-notes/ch02.md
git commit -m "feat: show MewHelp tool traces in chat"
```

## Task 7：标注评估、运行手册和最终验证

**文件：**
- 新建：`MewHelp/evals/ch02_tool_cases.json`、`MewHelp/evals/run_tool_eval.py`
- 修改：`MewHelp/README.md`、`MewHelp/Makefile`、`MewHelp/dev-notes/ch02.md`
- 测试：`MewHelp/tests/test_tool_eval.py`

**接口：**
- `make db-up` / `make db-down` / `make db-reset` 管理可重建 MySQL。
- `make eval-tools` 读取标注样例，输出工具选择、FAQ 命中与预期漏召回结果。

- [ ] **Step 1：先写评估解析测试。**

```python
def test_eval_cases_label_expected_faq_miss() -> None:
    cases = load_cases(Path("evals/ch02_tool_cases.json"))
    postage = next(case for case in cases if case["id"] == "faq-miss-postage")
    assert postage["expected_faq_match"] is False
    assert postage["known_limitation"] == "SQL LIKE keyword recall"
```

- [ ] **Step 2：运行失败测试。**

运行：`pytest tests/test_tool_eval.py -v`

预期：失败，评估集和运行器尚不存在。

- [ ] **Step 3：实现评估和文档。**

评估集写入物流、退货政策、邮费三条中文标注样例。运行器调用真实 Ch02 编排或测试客户端，检查工具名称和 FAQ 命中期望；“邮费”输出已知限制但返回成功退出码。README 给出从零开始的命令：`docker compose up -d`、依赖安装、`make dev`、`make frontend-dev`、`make eval-tools`、浏览器验收步骤及数据库重建方式。

- [ ] **Step 4：运行最终验证。**

```bash
make db-reset
make test
make frontend-build
make eval-tools
git diff --check
```

预期：后端和前端测试/构建通过；三条评估均按标签完成，其中“邮费”明确标注为预期漏召回。

- [ ] **Step 5：记录并提交。**

```bash
git add MewHelp/evals/ch02_tool_cases.json MewHelp/evals/run_tool_eval.py MewHelp/tests/test_tool_eval.py MewHelp/README.md MewHelp/Makefile MewHelp/dev-notes/ch02.md
git commit -m "docs: add MewHelp Ch02 evaluation workflow"
```

## Plan 自检

- Spec 覆盖：Task 1 覆盖 Docker/四表/种子；Task 2 覆盖持久化；Task 3 覆盖五工具、Schema、白名单、超时重试；Task 4 覆盖单次多工具规划与回灌；Task 5 覆盖 SSE；Task 6 覆盖页面徽章；Task 7 覆盖三条验收评估、文档与留痕。
- 占位符扫描：无 `TBD`、`TODO`、未定义的“适当处理”或“稍后实现”步骤。
- 类型一致性：`ToolRegistry.execute` 输出 `ToolExecutionResult`；`PreparedTurn.tool_results` 消费该输出；chat route 和前端仅消费稳定的名称/状态/文本契约。
