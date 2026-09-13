# MewHelp Ch01 — 纯对话客服设计

## 目标

在 `MewHelp/` 中交付一个仅含 FastAPI 后端的电商售后纯对话服务：支持内存多轮会话、SSE 增量输出、模板化客服 Prompt、售后描述结构化提取和按 token 预算的上下文裁剪。

## 范围

本章实现：

- `POST /api/chat`：以客户端提供的 `session_id` 保存进程内会话，并以 SSE 返回上游的增量文本块。
- `POST /api/extract`：从售后描述中提取订单号、诉求类型和期望方案。
- LangChain PromptTemplate、客服 System Prompt、`with_structured_output` 与内存历史裁剪。
- LiteLLM 本地代理与硅基流动上游的配置、测试、评估样例和 curl 演示。

本章不实现：数据库或持久化记忆、聊天页面、工具调用、Agent 循环。

## 架构

开发时由 `make dev` 或 `scripts/dev.sh` 启动两个进程：

```text
curl -> FastAPI (:8000) -> LangChain ChatOpenAI -> LiteLLM proxy (:4000) -> SiliconFlow
```

FastAPI 仅调用 LiteLLM 暴露的 OpenAI-compatible `/v1` 地址和固定模型别名。LiteLLM 的配置文件负责将模型别名路由到硅基流动；上游地址、模型名和密钥仅通过本地 `.env` 提供，不能提交到仓库。以后接入其他上游时，优先修改 LiteLLM 配置，而不修改客服业务代码。

在实现 LiteLLM、FastAPI 与 LangChain 的具体 API 前，必须使用 Context7 MCP 查询对应官方最新文档和接口定义。

## 目录与职责

```text
MewHelp/
  app/
    main.py              # FastAPI 应用入口
    config.py            # pydantic-settings 读取 .env
    api/chat.py          # POST /api/chat，SSE 响应
    api/extract.py       # POST /api/extract
    core/llm.py          # 唯一的 LangChain 模型工厂，指向 LiteLLM
    core/prompts.py      # 客服与提取 PromptTemplate
    core/memory.py       # 内存会话与 token 预算裁剪
    schemas/             # 请求、响应及 AfterSalesTicket Pydantic 模型
  config/litellm.yaml    # 模型别名和上游路由，不含真实密钥
  scripts/dev.sh         # 本地双进程启动脚本
  tests/                 # 可单测代码的 pytest 测试
  evals/                 # 标注售后样例与评估入口
  .env.example
  Makefile
  README.md
  dev-notes/ch01.md
```

## 接口契约

### `POST /api/chat`

请求：

```json
{"session_id":"demo-customer-001","message":"我的订单 20260913001 到现在还没发货怎么办？"}
```

客户端自行生成和复用 `session_id`。首次收到某个 ID 时服务端自动创建内存会话。响应 MIME 类型为 `text/event-stream`：

```text
data: {"delta":"您好，"}

data: {"delta":"我来帮您确认情况。"}

data: [DONE]
```

服务端按上游实际返回的增量文本块逐段转发；块边界不保证等于 tokenizer 的单个 token。仅在上游完整成功后，才将本轮用户消息和助手消息一同写入会话。若 SSE 已开始而上游失败，发送 `data: {"error":{"code":"upstream_error","message":"..."}}` 后关闭连接；若响应尚未开始，返回普通 HTTP 错误。

### `POST /api/extract`

请求：

```json
{"text":"订单 SF20260913001 买的耳机左耳没声音，想换货。"}
```

响应由 `AfterSalesTicket` 约束：

```json
{"order_id":"SF20260913001","request_type":"exchange","expected_solution":"换货"}
```

`request_type` 仅为 `refund`、`exchange`、`repair`、`complaint` 或 `other`。`order_id` 与 `expected_solution` 在不能从原文明确得出时返回 `null`，不得猜造。提取上游失败时返回 HTTP 502 JSON 错误。

## Prompt、模型与记忆

客服 System Prompt 使用中文，角色为电商售后客服；禁止编造订单、物流、退款状态和平台规则；信息不足时追问订单号与关键事实；不承诺具体赔付或时效；语气礼貌、简洁并给出可执行下一步；超出客服范围时明确引导。

提取 Prompt 仅允许基于原文填充结构化字段，无法确定即返回 `null`。两个 PromptTemplate 集中于 `app/core/prompts.py`。

`app/core/memory.py` 使用进程内 `dict[session_id, messages]`。默认 token 预算为 2000 且可配置：永远保留 System Prompt 和当前用户消息，然后从最新历史向前保留完整“用户 + 客服”轮次；预算不足时删除最旧完整轮次，不保留半轮。

## 配置

`.env` 至少包含 LiteLLM 地址、LiteLLM 访问凭证、硅基流动地址、硅基流动 API Key、上游模型名和 token 预算。`.env.example` 只保留变量名、无敏感值。实际 LiteLLM YAML 字段和 LangChain 初始化参数须在实现阶段按 Context7 查到的版本化文档确定。

## 验证

可单测代码遵循 TDD：会话存储与提交、token 裁剪、SSE 编码及完成/错误事件、schema 校验和两轮上下文均先写失败 pytest，再写最小实现。

纯 Prompt 与数据类产出使用标注样例评估，而不是伪造单测：至少包含退款、换货、维修、投诉、订单号缺失或诉求模糊五种样例，并真实调用 `/api/extract` 检查字段。最终使用用户提供的硅基流动凭证运行 curl：验证持续 SSE 输出、两轮上下文和结构化 JSON。

## 验收

1. curl 调用 `/api/chat` 可观察到连续 SSE `delta` 和最终 `[DONE]`。
2. 同一 `session_id` 连续两轮调用中，第二轮能正确引用第一轮事实。
3. `/api/extract` 对售后描述返回符合 `AfterSalesTicket` 的 JSON，缺失字段为 `null`。
