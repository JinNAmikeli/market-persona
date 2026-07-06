# A股市场雷达

本地雪球看板，用于观察 A 股指数、雪球人气榜、关注榜、热门帖子、市场主线和风险提示。

## 启动

```bash
conda activate agent-reach
python market_radar/server.py --host 127.0.0.1 --port 8787
```

打开：

```text
http://127.0.0.1:8787
```

## 数据刷新

页面右上角的“刷新”会重新请求雪球 API，并更新：

```text
market_radar/data/xueqiu_radar_latest.json
market_radar/data/xueqiu_radar_history.jsonl
```

也可以在终端手动刷新：

```bash
python tools/xueqiu_radar_collect.py
```

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

每次刷新都会向 `market_radar/data/xueqiu_radar_history.jsonl` 追加一条轻量快照。页面会用这些快照展示指数趋势，并生成一段“自动观察稿”。

## Market Harness Agent

项目正在加入金融数字人 Agent Runtime。第一版新增后端能力：

- 统一读取 `market_radar/data/`，并兼容旧的根目录 `data/`。
- 后端计算市场主线、情绪分和拥挤度。
- `/api/agent/chat` 支持本地文字问答。
- Agent 每轮运行会写入 `market_radar/data/agent_traces.jsonl`。
- 用户关注点和观察清单会写入 `market_radar/data/user_memory.json`。

相关设计文档：

```text
market_radar/docs/agent_runtime_methodology.md
market_radar/docs/market_harness_agent_architecture.md
```
