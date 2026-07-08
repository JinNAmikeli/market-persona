# Architecture Freeze

状态：冻结
版本：Market Harness Agent v0.1
冻结日期：2026-07-08

## 1. 冻结目的

本文冻结 `market_radar` 当前工程形态，作为后续 Issue 拆分、实现和验收的共同基线。冻结不代表系统完成，而是规定后续改动必须在明确授权、明确 Issue 和明确验收标准下进行。

## 2. 冻结架构

v0.1 架构由以下层组成：

```text
static/
  本地看板、Agent 对话、复盘、调试台

server.py
  本地 HTTP API 与静态资源服务

market/
  数据读取、采集、信号计算、自选股观察

agent/
  Runtime 编排、planner、executor、reflector、memory、trace、wiki、tools、prompts、llm

wiki/
  结构化知识资产

schemas/
  API、runtime、market、wiki JSON Schema 契约

scripts/
  本地刷新和 runtime 验证

data/
  运行期市场快照、历史、memory、trace
```

## 3. 冻结流程

一轮 Agent Runtime 的冻结流程是：

```text
normalize input
load state
plan
execute tools
retrieve wiki
generate response
reflect
repair if needed
update memory
write trace
return response
```

后续实现可以增强单个环节，但不得绕过 Reflection、Memory 写回规则或 Trace 记录。

## 4. 冻结接口

v0.1 冻结以下 API 作为现有行为基线：

- `GET /api/signals`
- `POST /api/agent/chat`
- `POST /api/agent/briefing`
- `GET /api/agent/memory`
- `POST /api/agent/memory`
- `GET /api/agent/traces`

任何删除、重命名、响应结构破坏性变更，都需要用户批准并同步更新 `docs/CONTRACTS.md`。

## 5. 冻结数据边界

运行数据统一位于仓库内 `data/`：

- `data/xueqiu_radar_latest.json`
- `data/xueqiu_radar_history.jsonl`
- `data/user_memory.json`
- `data/agent_traces.jsonl`

其中 `user_memory.json` 和 `agent_traces.jsonl` 是运行期本地状态，不应提交。

## 6. 冻结合规边界

以下边界不可在普通实现任务中修改：

- 不给出买卖建议。
- 不给出确定收益。
- 不承诺目标价。
- 不替用户做投资决策。
- 不把热度、基本面、资金流、情绪混为同一事实。
- 不将缺少证据的内容写成确定结论。

修改这些边界需要用户明确批准。

## 7. 可以在后续 Issue 中演进的部分

允许通过单独 Issue 演进：

- 更严格的 factuality 和逐句证据绑定。
- 更完整的 Wiki 审核流和证据来源。
- 更细的 trace diff、导出和查询。
- 更强的 Memory patch builder。
- SQLite、多用户、定时任务、TTS、数字人表现层。

这些演进不得在 ISSUE-001 中实现。

