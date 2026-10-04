# MewHelp Ch02 · Function Calling 工具链设计

## 目标

在现有 SSE 流式客服聊天中加入数据查询能力：模型自行选择业务工具，获得工具结果后，再流式输出有依据的最终回答；客服会话和完整工具轨迹保存到 MySQL。

## 本章范围

- 使用 FastAPI、SQLAlchemy 2.0、Docker Compose MySQL。
- 新建 `faq`、`conversations`、`messages`、`tickets` 四张 MySQL 表。
- 使用 LangChain `@tool` 定义订单、商品、物流、FAQ、创建工单五个工具。
- 每条用户消息只经历一次工具规划：模型可在这一次规划中申请 0 个、1 个或多个工具；全部执行结果只回灌模型一次，模型据此输出最终回答；模型不会再根据工具结果申请新工具。
- SSE 增加工具状态帧；前端在助手气泡中展示本轮工具轨迹徽章。
- 代码走 TDD；纯 Prompt 与种子数据行为用标注评估集验证。

## 本章不做

- 多轮自动 Agent Loop。
- 向量检索、Embedding、RAG 或向量数据库。
- 真实订单、商品、物流系统集成。这三个查询工具只返回确定性的演示 mock 数据。
- 用户登录。Ch02 固定使用 `user_id = "demo-user"`。

## 数据库

Docker Compose 启动一个可重建的演示 MySQL：不挂持久化卷，执行 `docker compose down -v` 后再次启动会重新建表并灌入固定种子数据。全库统一使用 MySQL `InnoDB` 与 `utf8mb4`。

SQLAlchemy 模型严格对齐用户提供的 DDL：

- `conversations`：无符号 bigint 主键、`user_id`、中文状态枚举（`进行中`、`已转人工`、`已结束`）、创建/更新时间、`user_id` 索引。
- `messages`：无符号 bigint 主键、会话外键、角色枚举（`user`、`assistant`、`tool`）、可空正文、可空 JSON `tool_calls`、可空 `tool_call_id`、创建时间、会话索引。
- `faq`：无符号 bigint 主键、问题、答案、分类、创建/更新时间、分类索引。
- `tickets`：业务主键 `ticket_no`、会话外键、问题描述、中文工单类型枚举（`售后`、`投诉`、`咨询`）、状态枚举（`待处理`、`已处理`）、创建时间、会话索引。

浏览器第一次以某个 `session_id` 发消息时，后端为 `demo-user` 创建一条 `conversations` 记录；后续相同 `session_id` 复用该数据库会话。Ch02 的映射仅保存在应用内存中；接入登录后的章节再替换为真实用户 ID 与持久化映射。

FAQ 种子数据必须包含“退货政策是什么”的答案，且故意不包含“邮费是多少”的关键词匹配项，确保评估能记录 SQL `LIKE` 的预期漏召回。

## 工具契约

五个工具均使用 `@tool(args_schema=...)` 和显式 Pydantic 参数模型，并注册到白名单注册中心。

| 工具 | 参数 | 数据来源 |
| --- | --- | --- |
| `query_order` | `order_no` | 确定性的订单 mock 数据 |
| `query_product` | `product_name` | 确定性的商品 mock 数据 |
| `query_logistics` | `order_no` | 确定性的物流 mock 数据 |
| `query_faq` | `keyword` | 查询 `faq` 表的 SQL `LIKE` |
| `create_ticket` | `description`、`ticket_type` | 向 `tickets` 表插入工单 |

`ticket_type` 只允许 `售后`、`投诉`、`咨询`；无法归类时使用 `咨询`。三个 mock 工具根据输入稳定地产生数据，不使用无种子的随机值，以保证测试和演示可复现。

注册中心负责验证工具名称和参数、统一执行超时策略、在瞬态失败后重试一次。失败耗尽时返回结构化且安全的工具错误结果，不暴露异常堆栈。

## 聊天与持久化流程

1. `POST /api/chat` 接收 `session_id` 与用户消息。
2. 会话服务创建或获取数据库会话，并写入一条 `user` 消息。
3. 将 ChatOpenAI 与五个注册工具绑定，发送现有 System Prompt 与当前用户消息。
4. 模型的 `AIMessage.tool_calls` 可包含 0 个或多个调用申请。后端写入一条 `assistant` 消息，其 `tool_calls` JSON 原样保存申请内容。
5. 按模型返回顺序，对每个工具调用做校验和执行；每个执行结果写入一条 `tool` 消息，携带对应的 `tool_call_id`。
6. 在最终文本开始前，SSE 为本轮每个工具发送一条 `tool_status` 帧；前端据此将工具名称添加为正在生成的助手气泡徽章。
7. 将工具申请和全部 `ToolMessage` 结果一次性回灌模型；最终自然语言答案沿用 `delta` 帧流式输出，随后发送 `[DONE]`；完成文本写入一条最终 `assistant` 消息。

若模型未选择工具，接口保留 Ch01 的普通流式回答路径，仅写用户和最终助手两条消息。工具执行失败时，安全错误结果会回灌模型，让模型说明下一步；首次模型调用失败仍返回 HTTP 502。最终回答流中发生异常时，发送既有 SSE error 帧，且不写入“已完成”的最终助手消息。

## SSE 与前端契约

既有帧格式保持不变：

```text
data: {"delta":"..."}

data: [DONE]
```

新增状态帧，且必须在首个最终 `delta` 前发送：

```text
data: {"tool_status":{"name":"query_logistics","state":"running"}}
```

前端解析器把工具名称传给 `App.vue`。正在生成的助手气泡展示简洁的中文工具徽章，同时保留逐字渲染和既有像素风格。本段前端改造遵循用户指定的 Vibe Coding 例外：不走脑暴、TDD 或代码审查流程。

## 验证

代码测试覆盖 ORM 模型与服务、注册中心校验、超时与重试、FAQ 命中与未命中、工单写入、消息持久化顺序、多工具调用处理，以及 `tool_status` / `delta` / `DONE` 的 SSE 顺序。集成测试连接 Docker MySQL。

Prompt 与种子数据行为使用标注评估集，最少覆盖：

1. “订单 1001 的物流到哪了”：选择必要的订单/物流工具，并根据 mock 返回值作答。
2. “退货政策是什么”：调用 `query_faq`，返回种子数据中的答案。
3. “邮费是多少”：产生预期的 FAQ 未命中。该结果记录为 SQL `LIKE` 的已知召回限制，留给下一章升级，而非测试失败。

## 开发留痕

`MewHelp/dev-notes/ch02.md` 会在设计、Context7 调研、数据库初始化、工具基础设施、聊天/页面接入、评估和最终验证后持续追加，记录命令、决策、发现和测试结果；不得写入 API Key 或其他密钥。
