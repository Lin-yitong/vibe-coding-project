# AGENTS.md

本文件是给 Codex 阅读的项目开发规范。后续在本项目中开发、修复、测试时，请优先遵守这里的约定。

## 项目概述

本项目是一个 Python + FastAPI 后端服务 + Vue 前端调试台，目标是实现“LLM 模拟 6 人狼人杀自动对战”。

当前 MVP 的范围：

- 需要一个前端调试台，用于展示状态、玩家、日志、阶段和胜负结果。
- 不需要 WebSocket。
- 不需要数据库。
- 可以接入真实 LLM API，但必须保留 `RandomAgent` fallback。
- 使用 HTTP API + 内存存储保存游戏状态。
- 没有真实 LLM API Key 时，必须仍可使用 `RandomAgent` 跑通完整游戏流程。
- 真实 LLM 调用使用 OpenAI-compatible `POST /chat/completions`。
- LLM 配置从项目根目录 `.env` 读取，`.env` 不得提交，提交 [.env.example](.env.example) 作为模板。

## 技术栈

- Python 3.11+
- FastAPI
- Pydantic
- pytest
- 内存字典存储游戏状态
- Vue 3.5
- Vite 5.4
- TypeScript

## 核心原则

后端是狼人杀规则裁判，Agent 只是提出行动建议。

所有 Agent 输出都必须经过 `RuleChecker` 校验。不能直接相信 Agent 返回的目标、投票、女巫用药、查验等结果。

如果 Agent 返回非法行动：

- 记录到 `debug_logs`。
- 由后端选择合法 fallback 行动。
- 不允许非法行动污染游戏状态。

## 日志规范

游戏日志分为两类：

- `public_logs`：给前端或公开接口展示，不能泄露隐藏身份。
- `debug_logs`：给开发者调试，可以记录完整身份、Agent 原始输出、规则校验结果、fallback 决策等信息。

公开响应默认不能暴露玩家角色。只有在明确使用 `debug=true` 时，才可以返回完整角色信息和 `debug_logs`。

前端将 `debug=true` 展示为“上帝视角”。上帝视角可以看到隐藏角色、狼人击杀目标、预言家查验目标与结果、女巫救/毒行为和夜晚结算。普通视角和 `public_logs` 仍然不能泄露身份。

## 目录结构与模块职责

建议目录结构：

```text
app/
  main.py
  api/
    game_router.py
    health_router.py
  core/
    config.py
    exceptions.py
  models/
    role.py
    game.py
    player.py
    action.py
  schemas/
    game_schema.py
    action_schema.py
  services/
    game_service.py
    agent_service.py
    log_service.py
  engine/
    game_engine.py
    phase_manager.py
    rule_checker.py
  agents/
    base_agent.py
    random_agent.py
    llm_player.py
    prompt_builder.py
    memory.py
  repositories/
    game_repository.py
  utils/
    id_generator.py
tests/
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  .env.example
  src/
    main.ts
    App.vue
    api/
    types/
    components/
    styles/
requirements.txt
README.md
```

模块职责：

- `app/main.py`：创建 FastAPI 应用，注册路由。
- `app/api/health_router.py`：健康检查接口。
- `app/api/game_router.py`：游戏相关 HTTP API。
- `app/core/config.py`：项目配置，读取项目根目录 `.env`。
- `app/core/exceptions.py`：统一异常定义。
- `app/models/`：内部领域模型，例如角色、玩家、游戏状态、行动。
- `app/schemas/`：API 请求与响应模型，负责隐藏或暴露必要字段。
- `app/services/game_service.py`：业务调度中心，负责创建游戏、推进游戏、保存状态、记录日志。
- `app/services/agent_service.py`：根据当前阶段调用对应 Agent。
- `app/services/log_service.py`：统一写入 `public_logs` 和 `debug_logs`。
- `app/engine/game_engine.py`：狼人杀规则引擎，负责状态流转、行动结算、胜负判断。
- `app/engine/phase_manager.py`：管理游戏阶段推进。
- `app/engine/rule_checker.py`：校验行动是否合法。
- `app/agents/base_agent.py`：Agent 抽象基类。
- `app/agents/random_agent.py`：第一版可运行的随机 Agent。
- `app/agents/llm_player.py`：真实 LLM 玩家接口，兼容 OpenAI-style chat completions。
- `app/agents/prompt_builder.py`：构造不同身份视角的提示词，必须避免上帝视角泄露。
- `app/agents/memory.py`：预留 Agent 记忆结构。
- `app/repositories/game_repository.py`：内存游戏仓储。
- `app/utils/id_generator.py`：生成游戏 ID、玩家 ID 等。
- `frontend/`：Vue 3 + Vite 前端调试台，只调用后端 HTTP API，不放任何 LLM API Key。

## 6 人局角色配置

固定 6 人局：

- 2 个狼人
- 1 个预言家
- 1 个女巫
- 2 个村民

角色枚举建议：

- `WEREWOLF`
- `SEER`
- `WITCH`
- `VILLAGER`

## 游戏阶段

游戏阶段枚举：

- `NIGHT_WOLF`
- `NIGHT_SEER`
- `NIGHT_WITCH`
- `DAY_ANNOUNCEMENT`
- `DAY_SPEECH`
- `DAY_VOTE`
- `EXILE`
- `GAME_OVER`

## 游戏流程

基础流程：

1. 创建游戏并随机分配身份。
2. 第 1 夜从 `NIGHT_WOLF` 开始。
3. 狼人选择击杀目标。
4. 预言家选择查验目标。
5. 女巫选择是否救人、是否毒人。
6. 白天公布夜晚死亡情况。
7. 存活玩家依次发言；当前实现中 `DAY_SPEECH` 每次 `step` 只推进一名玩家发言。
8. 存活玩家投票。
9. 最高票玩家出局。
10. 判断胜负。
11. 如果游戏未结束，进入下一夜。

## 胜利条件

- 所有狼人死亡，好人阵营胜利。
- 狼人数量大于等于好人数量，狼人阵营胜利。

## 规则要求

- 死亡玩家不能行动、不能发言、不能投票。
- 狼人每晚只能击杀一名存活玩家。
- 预言家每晚可以查验一名存活玩家。
- 女巫只有一瓶解药和一瓶毒药，每瓶只能使用一次。
- 女巫的解药和毒药使用情况必须保存在游戏状态中。
- 投票必须来自存活玩家，目标也必须是存活玩家。
- 平票策略需要明确实现，可选择无人出局或固定规则破平票，但必须可测试。
- 每次阶段推进都应保持状态一致，避免出现死循环。
- 夜晚隐藏行动细节不得写入 `public_logs`，只能写入 `debug_logs`。
- 白天发言日志必须标明几号玩家发言。

## Agent 设计

必须实现可离线运行的 Agent：

- `RandomAgent` 或 `RuleBasedAgent`：随机选择合法目标、随机投票、生成简单发言。
- `LLMPlayer`：真实 LLM 接入，必须兼容 OpenAI-style chat completions。
- LLM 失败、超时、返回非 JSON、返回非法行动时，必须写入 `debug_logs` 并 fallback 到 `RandomAgent`。
- 不允许把真实 LLM API Key 写入 Python/TypeScript 源码、README、AGENTS 或前端环境变量。
- 真实 LLM API Key 只允许放在本地 `.env` 中，且 `.env` 必须被 `.gitignore` 忽略。

Agent 行为建议返回结构化对象，不返回自由文本，例如：

```json
{
  "action": "kill",
  "target": 3,
  "reason": "怀疑 3 号是神职"
}
```

`AgentService` 根据当前阶段调用对应方法：

- `choose_wolf_target`
- `choose_seer_target`
- `choose_witch_action`
- `generate_speech`
- `vote`

## API 设计

必须提供以下接口：

- `GET /api/health`
- `POST /api/games`
- `GET /api/games/{game_id}`
- `POST /api/games/{game_id}/step`
- `POST /api/games/{game_id}/run`
- `GET /api/games/{game_id}/logs`
- `DELETE /api/games/{game_id}`

接口行为要求：

- `POST /api/games`：创建新游戏，返回 `game_id`、当前阶段、玩家列表。默认不暴露角色。
- `GET /api/games/{game_id}`：获取当前游戏状态。默认不暴露角色。支持 `debug=true` 返回完整角色信息和 `debug_logs`。
- `POST /api/games/{game_id}/step`：推进游戏下一步，返回当前阶段、新增 `public_logs`、是否结束、`winner`。
- `POST /api/games/{game_id}/run`：自动运行完整局，直到游戏结束。必须设置最大 step 数，例如 100，避免死循环。
- `GET /api/games/{game_id}/logs`：获取 `public_logs`。支持 `debug=true` 时返回 `debug_logs`。
- `DELETE /api/games/{game_id}`：删除一局游戏。

## 前端设计

前端位于 `frontend/`，技术栈：

- Vue 3.5
- Vite 5.4
- TypeScript
- 原生 CSS

前端要求：

- 使用 `VITE_API_BASE_URL` 配置后端地址，默认 `http://localhost:8000`。
- 不使用 WebSocket。
- 不实现登录注册。
- 不实现真人玩家输入。
- 不读取、不展示、不保存任何 LLM API Key。
- 普通模式不显示 `role` 和 `debug_logs`。
- 上帝视角通过 `debug=true` 显示 `role` 和 `debug_logs`。
- Public Logs 和 God View Logs 分开展示。
- 删除游戏后前端状态应清空。
- 后端需要 CORS middleware，允许 `http://localhost:5173` 和 `http://127.0.0.1:5173`。

## 测试要求

必须使用 pytest 编写基础测试，至少覆盖：

- 创建游戏。
- 角色数量正确。
- `step` 可以推进阶段。
- `run` 可以跑出 `winner`。
- 所有狼人死亡时，好人胜利。
- 狼人数量大于等于好人数量时，狼人胜利。
- 死亡玩家不能投票。
- 女巫解药和毒药只能各使用一次。
- public response 默认不能泄露角色。
- 夜晚行动细节只进入 debug logs。
- 白天发言每次 step 只推进一名玩家。

前端至少需要通过：

- `npm run build`
- 普通模式不显示角色。
- 上帝视角显示角色和 debug logs。

建议测试文件：

- `tests/test_game.py`

## 开发命令

安装依赖：

```bash
pip install -r requirements.txt
```

启动开发服务：

```bash
uvicorn app.main:app --reload
```

运行测试：

```bash
pytest
```

如果使用 conda 的 `py312` 环境：

```bash
conda run -n py312 python -m pytest
```

前端安装与启动：

```bash
cd frontend
npm install
npm run dev
```

前端构建：

```bash
cd frontend
npm run build
```

## 交付要求

开发实现时应保持：

- 代码清晰。
- 模块化。
- 可测试。
- 可扩展。
- 第一版无需真实 LLM API Key 也能完整跑通一局游戏。
- 核心模块有必要注释，但不要堆叠无意义注释。
- API 默认响应必须保护隐藏身份。
- 提交 GitHub 前不要提交真实 LLM API Key、`frontend/node_modules/`、`frontend/dist/`、`.env` 或运行日志。
- `.gitignore` 必须忽略 `.env`、`frontend/node_modules/`、`frontend/dist/`、日志文件和 Python 缓存。
