# Contracts

状态：冻结
版本：Market Harness Agent v0.1
更新日期：2026-07-09

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

Agent Runtime 的 memory 写回必须通过规则型 memory patch builder，例如：

```text
build_memory_patch(request, plan, draft, review, evidence)
```

memory patch 是审计记录，不是自由文本抽取结果。每个新结构 patch 至少包含：

- `source`：只能表示主要来源，例如 `user_message`、`agent_response`、`review`。
- `reason`：说明本轮为什么可以写入或为什么只记录低风险运行状态。
- `confidence`：`low`、`medium`、`high`。
- `operations`：逐条记录 `op`、`path`、`value`、`source`、`reason`、`confidence`。

写入规则：

- `focus_themes` 只能在用户明确表达“关注、跟踪、观察、添加关注”等主题意图时写入；普通市场问题或主题解释问题不得自动写入。
- `watchlist` 只能在用户明确表达“关注、添加、加入自选、我的股票/自选”等自选股意图时写入；普通提到热门股或询问个股表现不得自动加入自选。
- `knowledge_level` 只能根据“我是小白/新手/刚入门/我有基础”等低风险自我描述更新，并必须在 operation 中保留 reason。
- `risk_preferences` 只能做保守更新，例如用户明确要求更多风险提示，或本轮触发买卖、目标价、确定收益等拒绝/转写任务；不得降低风险提示强度。
- `last_questions`、`last_next_watch` 可以作为低风险运行状态写入，但也必须通过 operations 保留审计字段。

`apply_patch` 必须兼容旧式扁平 patch，同时支持新结构的 `operations`。旧式 patch 仍可包含 `watchlist`、`focus_themes`、`knowledge_level`、`last_next_watch`、`question` 等既有字段。

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

`GET /api/agent/traces` 列表返回的是 trace summary，summary 由原始 trace 派生，至少保留：

- `trace_id`、`created_at`、`user_id`、`message`、`mode`。
- `task_type`、`execution_mode`、`llm_provider`、`llm_model`。
- `factuality_status`、`factuality_coverage`、`review_passed`。
- `repair_mode`、`repair_changed`、`repair_status`。
- `claim_binding_count`、`unsupported_claim_count`、`conflicting_claim_count`。
- `evidence_count`、`risk_flags`。
- `memory_patch_keys`、`memory_operation_count`、`memory_patch_confidence`。
- `wiki_statuses`、`wiki_evidence_qualities`。
- `generated_at`。

`compare_traces(left, right)` 是本地纯函数，只返回结构化差异，不修改 trace、不写文件、不改变 API 路由。它用于比较 task、execution、review、factuality、repair、memory patch 和 Wiki 治理摘要等关键调试项。

运行期 trace 不提交到 Git。

## 7. Wiki 契约

Wiki 页面应包含：

- `topic_id`
- `title`
- `version`：页面治理版本，当前用日期字符串表示。
- `status`：只能是 `draft`、`reviewed`、`deprecated`。
- `reviewed_at`：人工审核时间；`draft` 可为 `null`。
- `evidence_quality`：只能是 `low`、`medium`、`high`。
- `sources`：页面级来源记录。
- `tags`
- `applicable_tasks`
- `forbidden_use`
- `sections`

`applicable_tasks` 和 `forbidden_use` 必须始终存在且为数组，用于让 factuality、trace 和回答生成识别 Wiki 内容的适用范围与禁用边界。

section 应包含 `section_id`、标题、正文、证据和更新时间。页面级 `sources` 与 section 级 `evidence` 都应记录 `type`、`source`、`title`、`url`；没有外部 URL 时可使用 `null`，但不得把内部手工说明伪装成外部来源。

Wiki 检索可以返回 `draft` 页面，但检索结果必须暴露 `status`、`version`、`reviewed_at`、`evidence_quality`、`sources`、`applicable_tasks` 和 `forbidden_use`，方便 factuality evidence binding、trace 审计和后续审核流使用。`deprecated` 页面是否参与回答需要由后续单独 Issue 定义；本契约只要求状态被显式暴露。

## 8. 存储边界

v0.1 当前运行期存储保持本地 JSON / JSONL 文件：

- `data/xueqiu_radar_latest.json`：当前市场快照。
- `data/xueqiu_radar_history.jsonl`：市场历史快照。
- `data/user_memory.json`：本地用户 memory。
- `data/agent_traces.jsonl`：Agent trace 审计记录。

当前不引入 SQLite、外部数据库或存储迁移脚本。任何从 JSON / JSONL 迁移到 SQLite、外部数据库或其他长期存储的改动，都属于存储迁移，必须先登记单独 Issue、说明触发条件与迁移设计，并获得用户批准。

数据保留、归档、压缩、导出、清理和备份策略尚未实现；这些能力应先作为运行期数据治理 Issue 设计和验收，不应被默认为已存在的存储能力。
