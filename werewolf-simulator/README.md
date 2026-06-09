# AI Werewolf Simulator

Python + FastAPI 后端 + Vue 3 前端调试台，用于模拟 6 人狼人杀自动对战。后端作为规则裁判，Agent 只提出行动建议；前端用于查看游戏状态、玩家列表、日志、阶段变化和胜负结果。

当前版本支持：

- 固定 6 人狼人杀自动对战。
- `RandomAgent` 离线兜底。
- OpenAI-compatible LLM 接入，可配置 `base_url`、模型名和 API Key。
- Vue 3 + Vite 前端调试台。
- 普通公开视角不泄露身份。
- 上帝视角通过 `debug=true` 查看角色、夜晚行动、查验结果、女巫用药和规则调试日志。
- 白天发言阶段每次 `step` 只推进一名玩家发言，避免整轮 LLM 调用造成过长等待。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
uvicorn app.main:app --reload
```

如果使用 conda 的 `py312` 环境：

```bash
conda run -n py312 uvicorn app.main:app --reload
```

服务启动后访问：

```text
http://127.0.0.1:8000/docs
```

## 启动前端调试台

前端位于 [frontend](frontend)，使用 Vue 3.5 + Vite 5.4。默认后端地址通过环境变量配置：

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

[frontend/.env.example](frontend/.env.example) 默认内容：

```text
VITE_API_BASE_URL=http://localhost:8000
```

启动后访问：

```text
http://127.0.0.1:5173
```

页面功能：

- 创建新游戏。
- 执行下一步 `step`。
- 自动跑完整局 `run`。
- 刷新当前游戏状态。
- 获取日志。
- 删除当前游戏。
- 开启/关闭上帝视角。
- 展示玩家存活状态、当前阶段、胜负结果、Public Logs 和 God View Logs。

构建前端：

```bash
cd frontend
npm run build
```

## 运行测试

```bash
pytest
```

如果使用 conda 的 `py312` 环境：

```bash
conda run -n py312 python -m pytest
```

## LLM 配置

默认可以使用 `RandomAgent` 跑通完整流程。需要接入真实模型时，复制并编辑项目根目录的 `.env`：

```bash
copy .env.example .env
```

```text
LLM_ENABLED=true
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=30
```

把你的真实 API Key 填到本地 `.env` 的 `LLM_API_KEY` 后面即可。

接口按 OpenAI-compatible `POST /chat/completions` 调用。LLM 只提供行动建议，所有目标仍会经过 `RuleChecker` 校验；超时、非 JSON、非法行动都会写入 `debug_logs` 并回退到 `RandomAgent`。

注意：不要把真实 API Key 提交到 GitHub。当前 [.gitignore](.gitignore) 已忽略 `.env`，请只提交 [.env.example](.env.example)。

## API 示例

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

创建游戏：

```bash
curl -X POST http://127.0.0.1:8000/api/games
```

获取游戏状态：

```bash
curl http://127.0.0.1:8000/api/games/{game_id}
```

上帝视角获取完整角色和 debug logs：

```bash
curl "http://127.0.0.1:8000/api/games/{game_id}?debug=true"
```

推进一步：

```bash
curl -X POST http://127.0.0.1:8000/api/games/{game_id}/step
```

自动跑完整局：

```bash
curl -X POST "http://127.0.0.1:8000/api/games/{game_id}/run?max_steps=100"
```

获取日志：

```bash
curl http://127.0.0.1:8000/api/games/{game_id}/logs
```

删除游戏：

```bash
curl -X DELETE http://127.0.0.1:8000/api/games/{game_id}
```

## 规则说明

- 固定 6 人局：2 狼人、1 预言家、1 女巫、2 村民。
- 游戏阶段：`NIGHT_WOLF`、`NIGHT_SEER`、`NIGHT_WITCH`、`DAY_ANNOUNCEMENT`、`DAY_SPEECH`、`DAY_VOTE`、`EXILE`、`GAME_OVER`。
- 后端是规则裁判，Agent 只提出建议。
- 所有行动都必须经过 `RuleChecker` 校验。
- 普通响应和 `public_logs` 默认不泄露身份。
- `debug=true` 作为上帝视角，才返回完整角色和 `debug_logs`。
- 夜晚隐藏行动、预言家查验结果、女巫用药细节只进入 `debug_logs`。
- 白天发言阶段每次 `step` 只推进一名存活玩家发言。

## GitHub 提交前检查

建议提交前确认：

```bash
conda run -n py312 python -m pytest
cd frontend
npm run build
```

不要提交：

- 真实 LLM API Key。
- `frontend/node_modules/`
- `frontend/dist/`
- `.env`
- 运行日志文件。
