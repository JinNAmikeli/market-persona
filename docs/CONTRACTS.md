# Contracts

状态：冻结
版本：Market Harness Agent v0.1
更新日期：2026-07-08

## 1. 契约原则

契约用于约束前端、后端、Agent Runtime、数据文件和治理文档之间的协作。后续实现可以扩展字段，但不得无批准破坏 v0.1 已存在调用方。

基本原则：

- API 响应优先保持向后兼容。
- JSON Schema 是结构化契约的主要载体。
- trace 必须能解释一次 Agent 回复的来源、规划、证据、校验和记忆写回。
- memory 是用户旅程状态，不是临时聊天缓存。
- Wiki 是结构化知识资产，不是散乱 prompt 片段。

## 2. API 契约

冻结 API：

| API | 目的 | 兼容要求 |
| --- | --- | --- |
| `GET /api/signals` | 返回统一市场信号 | 保留市场状态、情绪、拥挤度、主题信息 |
| `POST /api/agent/chat` | 用户自然语言问答 | 保留 `trace_id`、`task_type`、`content`、`evidence`、`risk_flags`、`next_watch`、`review` |
| `POST /api/agent/briefing` | 生成复盘或口播稿 | 保留 `trace_id`、`title`、`script`、`sections` |
| `GET /api/agent/memory` | 查看用户 memory | 保留 `user_id`、自选股、关注主题、知识水平、观察清单 |
| `POST /api/agent/memory` | 同步用户 memory | 请求只接受白名单字段；保留已有未知兼容字段；不得写入请求中的未知字段 |
| `GET /api/agent/traces` | 查询 trace 摘要或详情 | 保留按 `limit` 和 `id` 查询的能力 |

破坏性变更必须先更新本文件和对应 schema，并获得用户批准。

## 3. Runtime 契约

Agent Runtime 每轮必须包含：

- request 输入。
- state summary。
- plan。
- tool results。
- wiki hits。
- execution 信息。
- draft 或 final response。
- review。
- repair 信息，如发生修复。
- memory patch。
- trace id。

禁止在未写 trace 的情况下返回看似完整的 Agent 回复。

## 4. Reflection 契约

Reflection 至少检查：

- 是否出现买卖指令、目标价、确定收益等越界表达。
- 事实是否能由市场数据、历史数据或 Wiki 证据支撑。
- 是否混淆热度、基本面、资金流、情绪。
- 是否给出可执行的下一步观察清单。

命中硬拦截时，必须拒绝或 repair 为观察维度。

## 5. Memory 契约

Memory 当前使用 `data/user_memory.json`。

至少保留：

- `user_id`
- `watchlist`
- `focus_themes`
- `knowledge_level`
- `risk_preferences`
- `journey_state`
- `open_questions`
- `blockers`
- `next_priority`
- `last_questions`
- `last_next_watch`
- `updated_at`

后续新增字段必须兼容旧数据。不得在无用户批准时把 memory 上传到外部服务。

`POST /api/agent/memory` 是受控同步入口，只接受以下白名单字段：

- `watchlist`
- `focus_themes`
- `knowledge_level`
- `open_questions`
- `blockers`
- `next_priority`
- `journey_state`

请求体中的未知字段不得写入 memory，以避免污染用户状态；但已有本地 memory 中的未知兼容字段应在更新时保留。

## 6. Trace 契约

Trace 当前使用 `data/agent_traces.jsonl`。

每条 trace 应支持：

- 唯一 `trace_id`。
- 创建时间。
- 请求、状态、规划、工具、知识、执行、校验、修复、memory、最终回复。
- 调试台查询和人工审计。

运行期 trace 不提交到 Git。

## 7. Wiki 契约

Wiki 页面应包含：

- `topic_id`
- `title`
- `version`
- `status`
- `tags`
- `applicable_tasks`
- `forbidden_use`
- `sections`

section 应包含标题、正文、证据、更新时间。投资相关 Wiki 内容更新需要人工审核。
