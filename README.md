# A股市场雷达

本地雪球看板，用于观察 A 股指数、雪球人气榜、关注榜、热门帖子、市场主线和风险提示。

## 启动

```bash
conda activate agent-reach
python server.py --host 127.0.0.1 --port 8787
```

打开：

```text
http://127.0.0.1:8787
```

## 数据刷新

页面右上角的“刷新”会重新请求雪球 API，并更新：

```text
data/xueqiu_radar_latest.json
data/xueqiu_radar_history.jsonl
```

也可以在终端手动刷新：

```bash
python scripts/refresh_xueqiu.py
```

如果你不是在 `agent-reach` 环境里启动服务，刷新时会自动尝试执行：

```bash
conda run -n agent-reach python ...
```

如果这一步也失败，通常说明本机没有这个 conda 环境，或者 `conda` 不在当前 shell 可用路径里。

## 注意

看板只做市场观察、主线识别和风险提示，不提供买卖建议。

## DeepSeek AI 复盘

如果要启用页面里的 “DeepSeek AI 复盘”，在项目根目录的 `.env` 中加入：

```bash
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
```

保存后重启服务。密钥只保存在本机 `.env`，不要发到聊天里，也不要提交到 Git。

## 历史趋势

每次刷新都会向 `data/xueqiu_radar_history.jsonl` 追加一条轻量快照。页面会用这些快照展示指数趋势，并生成一段“自动观察稿”。

## Market Harness Agent

项目正在加入金融数字人 Agent Runtime。第一版新增后端能力：

- 统一读取 `market_radar/data/`，并兼容旧的根目录 `data/`。
- 后端计算市场主线、情绪分和拥挤度。
- `/api/agent/chat` 支持本地文字问答。
- `/api/agent/briefing` 支持复盘脚本。
- `/api/signals` 统一前后端市场信号。
- `/api/agent/traces` 支持查询最近 Agent 运行记录。
- Agent 每轮运行会写入 `data/agent_traces.jsonl`。
- 本地调试时可用 `?debug=1` 显示 Agent 调试台，查看最近 trace，按任务/执行/校验/修复筛选，并对比两条 trace。
- `?debug=1` 的 Agent 调试台会展示 `review.factuality`，包括 `supported / insufficient_evidence / evidence_conflict`、coverage 和修复前后状态。
- `/api/agent/traces` 现已支持 `query`、`task_type`、`execution_mode`、`review_passed`、`repair_changed`、`date_from`、`date_to`、`limit` 等过滤参数。
- 用户关注点和观察清单会写入 `data/user_memory.json`。
- `schemas/` 保存核心 API、runtime、market、wiki 的 JSON Schema 契约。
- `agent/prompts.py` 保存后续 LLM Execution / Reflection 使用的 prompt 契约。
- `agent/llm.py` 支持可选 LLM Execution；未配置时自动回退到模板回复。
- trace 和 chat response 会记录 `execution.mode`，用于区分 `template`、`llm`、`llm_fallback`。
- Reflection 采用双层校验：硬规则先拦截，可选 LLM Reflection 再检查证据、边界和清晰度。
- 结构化 repair 会记录 `pre_repair_content`、`post_repair_content`、替换项和修复依据。

### Agent LLM 可选配置

Agent 对话默认使用稳定模板，便于本地验证。如果要让 Agent 在执行阶段调用 LLM，在 `.env` 中选择一个模板：

```bash
# OpenAI
MARKET_AGENT_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-api-key
MARKET_AGENT_LLM_MODEL=gpt-4.1-mini
```

```bash
# DeepSeek
MARKET_AGENT_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
MARKET_AGENT_LLM_MODEL=deepseek-v4-flash
```

```bash
# Anthropic / Claude，也可以把 provider 写成 a
MARKET_AGENT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key
MARKET_AGENT_LLM_MODEL=claude-3-5-haiku-latest
```

也可以使用通用变量覆盖：

```bash
MARKET_AGENT_LLM_API_KEY=...
MARKET_AGENT_LLM_BASE_URL=...
MARKET_AGENT_LLM_MAX_TOKENS=1200
MARKET_AGENT_LLM_TEMPERATURE=0.2
```

LLM 调用失败或未配置密钥时，Agent 会自动回退到当前模板输出。荐股、目标价、确定收益等越界问题仍走固定拒绝/转向模板。

## 本地验证

每次改动 Agent Runtime 后，可以先跑：

```bash
python scripts/verify_runtime.py
```

它会覆盖市场信号、Wiki 检索、prompt builder、普通问答、拒绝荐股、自选股 Memory 和 briefing。
同时会检查关键输出是否包含 JSON Schema 要求的 required 字段。

查看最近 trace：

```bash
curl "http://127.0.0.1:8787/api/agent/traces?limit=5"
```

查看某一条完整 trace：

```bash
curl "http://127.0.0.1:8787/api/agent/traces?id=TRACE_ID"
```
