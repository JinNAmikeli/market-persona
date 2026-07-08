# Runbook

状态：生效
版本：Market Harness Agent v0.1
更新日期：2026-07-08

## 1. 本地启动

推荐环境：

```bash
conda activate agent-reach
python server.py --host 127.0.0.1 --port 8787
```

打开：

```text
http://127.0.0.1:8787
```

## 2. 刷新市场数据

页面右上角“刷新”会更新：

```text
data/xueqiu_radar_latest.json
data/xueqiu_radar_history.jsonl
```

也可以手动执行：

```bash
python scripts/refresh_xueqiu.py
```

如果当前 shell 不在 `agent-reach` 环境，服务会尝试使用：

```bash
conda run -n agent-reach python ...
```

## 3. Agent LLM 配置

Agent 默认可用模板回复。需要启用 LLM Execution 时，在本机 `.env` 配置 provider 和 key。

`.env` 不得提交，不得粘贴到对话中。

支持的配置入口以 README 为准：

- OpenAI
- DeepSeek
- Anthropic 或 `a`
- 通用 `MARKET_AGENT_LLM_*`

## 4. 本地验证

Runtime 改动后运行：

```bash
python scripts/verify_runtime.py
```

验证覆盖：

- 市场信号。
- JSON Schema required 字段。
- Wiki 检索。
- prompt builder。
- 市场概览问答。
- 越界买卖问题转写。
- 自选股 memory。
- briefing。

## 5. Trace 查询

最近 trace：

```bash
curl "http://127.0.0.1:8787/api/agent/traces?limit=5"
```

单条 trace：

```bash
curl "http://127.0.0.1:8787/api/agent/traces?id=TRACE_ID"
```

前端调试台：

```text
http://127.0.0.1:8787?debug=1
```

## 6. Memory 查看

后端 memory 文件：

```text
data/user_memory.json
```

通过 API 查看：

```bash
curl "http://127.0.0.1:8787/api/agent/memory"
```

注意：memory 是本地用户状态，不提交到 Git。

## 7. 常见问题

### 服务无法刷新

检查：

- 是否已经 `conda activate agent-reach`。
- `conda` 是否在当前 shell 可用。
- 雪球接口是否临时失败。
- `data/` 是否可写。

### Agent 回复缺少 LLM 风格

这是允许状态。未配置 key 或 LLM 调用失败时，Agent 会回退模板输出。

### 回答被拒绝或被改写

如果问题涉及买卖建议、目标价、确定收益等，Reflection 会拒绝或 repair 为观察维度。

### Trace 或 Memory 出现在 Git 状态中

不应提交：

```text
data/agent_traces.jsonl
data/user_memory.json
```

检查 `.gitignore` 是否仍包含对应规则。

## 8. 变更前检查

开始任何新 Issue 前：

1. 阅读 `docs/PROJECT_SPEC.md`。
2. 阅读 `docs/AUTHORITY_MATRIX.md`。
3. 阅读 `docs/CONTRACTS.md`。
4. 确认是否需要用户批准。
5. 修改完成后更新 `docs/HANDOFF.md`。

