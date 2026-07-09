# Runbook

状态：生效
版本：Market Harness Agent v0.1
更新日期：2026-07-09

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

Memory 高风险操作前检查：

- 备份、恢复、删除、重置或大范围改写 memory 前，必须先确认是否存在单独 Issue 和用户明确批准。
- 操作前说明目标文件、操作范围、是否包含隐私或半隐私数据、是否覆盖现有状态，以及验收方式。
- 删除或重置前必须确认已有备份，或由用户明确确认放弃备份。
- 恢复前必须确认来源备份、目标文件、覆盖范围，以及是否保留当前文件。
- 手动批量编辑、字段迁移、批量清空 `watchlist` / `focus_themes` 等，都按高风险 memory 改写处理。
- 不把 memory 内容写入治理文档、handoff、调试输出、日志或提交信息。
- 不上传 memory 到外部服务。

## 7. 运行期数据人工检查

运行期数据文件：

```text
data/xueqiu_radar_latest.json
data/xueqiu_radar_history.jsonl
data/user_memory.json
data/agent_traces.jsonl
```

只读 inspector：

```bash
python scripts/inspect_runtime_data.py
```

该脚本只报告文件存在性、体积和 JSONL 行数，不输出 memory 或 trace 的具体内容。`threshold_status` 只用于人工判断，不会触发自动清理、压缩、归档、导出或备份。

人工维护时只检查文件体积、trace 数量、history 增长和查询是否变慢；不要在没有单独 Issue、备份和用户确认时删除、压缩、归档、导出或改变保留范围。

`data/user_memory.json` 删除、重置、恢复或大范围改写必须单独确认。不要把 memory、trace 或本地运行期数据上传到外部服务，也不要把本地隐私数据写入治理文档。

Runtime data export 前检查：

- 导出前必须确认是否存在单独 Issue 和用户明确批准。
- 操作前说明导出范围、格式、保存位置、是否包含隐私或半隐私数据、是否脱敏、是否覆盖已有文件。
- latest snapshot 可再生成但仍属于本地运行数据；market history 导出前应说明时间范围和用途。
- agent traces 默认高敏，user memory 为最高敏感级别；包含 trace 或 memory 的导出必须单独确认。
- 后续导出工具默认先做 dry-run / manifest，不直接导出敏感内容。
- 导出文件不应提交到 Git。
- 不上传导出文件或本地运行期数据到外部服务。
- 不把导出内容写入治理文档、handoff、调试输出、日志或提交信息。

## 8. 常见问题

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

## 9. 变更前检查

开始任何新 Issue 前：

1. 阅读 `docs/PROJECT_SPEC.md`。
2. 阅读 `docs/AUTHORITY_MATRIX.md`。
3. 阅读 `docs/CONTRACTS.md`。
4. 确认是否需要用户批准。
5. 修改完成后更新 `docs/HANDOFF.md`。
