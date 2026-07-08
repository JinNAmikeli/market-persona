# Market Harness Agent v0.1 Project Spec

状态：冻结基线
冻结版本：Market Harness Agent v0.1
冻结日期：2026-07-08
适用仓库：`market_radar/`

## 1. 项目定位

`market_radar` 是一个本地运行的 A 股市场观察与复盘看板。当前项目在已有雪球市场雷达基础上，加入 Market Harness Agent Runtime，用于提供可追踪、可校验、可记忆、可审计的金融数字人文字内核。

Market Harness Agent v0.1 的定位是：

```text
市场观察员 + 投资教育老师 + 风险提醒员 + 自选股陪伴型复盘助手
```

它回答四类问题：

1. 发生了什么。
2. 证据是什么。
3. 风险在哪里。
4. 下一步观察什么。

它不输出买卖指令、目标价、确定收益预测，也不替用户做投资决策。

## 2. v0.1 已冻结能力

当前基线来自 `README.md`、`docs/agent_runtime_methodology.md` 和 `docs/market_harness_agent_architecture.md`。

v0.1 已具备或被视为冻结的能力：

- 本地 HTTP 服务和静态前端看板。
- 雪球指数、人气榜、关注榜、热门帖采集与刷新。
- `data/xueqiu_radar_latest.json` 和 `data/xueqiu_radar_history.jsonl` 作为当前市场数据与历史快照。
- 后端市场信号计算，包括市场状态、主题、情绪分和拥挤度。
- Market Harness Agent 一轮 Runtime：Planning、Tool Execution、Execution、Reflection、Memory、Trace。
- `/api/signals`、`/api/agent/chat`、`/api/agent/briefing`、`/api/agent/memory`、`/api/agent/traces`。
- 最小 Wiki 检索。
- 可选 LLM Execution 和可选 LLM Reflection，未配置或失败时回退稳定模板。
- 硬规则合规拦截与结构化 repair。
- JSON Schema 契约层。
- 本地验证脚本 `scripts/verify_runtime.py`。
- `?debug=1` 下的 Agent 调试台和 trace 查询能力。

## 3. v0.1 明确不做

v0.1 不包含：

- 真实交易、自动下单或交易账户接入。
- 投资组合建议、仓位建议、收益承诺、目标价承诺。
- 多用户权限系统。
- SQLite 或外部数据库迁移。
- 复杂向量数据库。
- 定时任务和主动触达生产化。
- TTS、数字人头像、视频生成或 3D 表现层。
- 自动修改合规边界、Wiki 审核内容或投资表达模板。

## 4. 运行边界

允许：

- 市场观察。
- 主题解释。
- 风险提示。
- 自选股热度跟踪。
- 财报、公告、新闻等事实梳理。
- 投资知识教育。
- 复盘稿和口播稿生成。
- 调试 trace、验证 schema、检查 runtime 输出。

禁止：

- 给出直接买入、卖出、满仓、清仓等指令。
- 给出确定性收益预测或目标价。
- 使用无证据来源的结论冒充事实。
- 忽略数据时效。
- 绕过 Reflection 或 repair 直接返回高风险金融建议。
- 在未获批准时改动冻结架构、合规边界、数据契约或业务代码。

## 5. 仓库边界

仓库根目录是 `market_radar/`。

v0.1 治理任务只允许修改：

- `docs/`
- `.gitignore`

本轮 ISSUE-001 不允许修改业务代码、脚本、schema、前端、后端、运行数据或配置文件。

## 6. 验收基线

后续任何实现类 Issue 至少应保持以下基线：

- `python scripts/verify_runtime.py` 可作为本地回归入口。
- Agent 回复保留 trace_id。
- trace 记录 plan、工具结果、证据、review、memory patch。
- 越界买卖问题被拒绝并转写为观察维度。
- 前端和 Agent 对同一市场状态使用一致的后端信号。

