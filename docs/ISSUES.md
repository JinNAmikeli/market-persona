# Issues

状态：Issue 登记簿
更新日期：2026-07-09

## ISSUE-001 Governance Docs Landing

状态：完成
范围：仅治理文档和 `.gitignore`

已完成：

- 创建 Market Harness Agent v0.1 治理文档。
- 冻结当前项目为 Market Harness Agent v0.1。
- 明确允许、禁止和需要用户批准的修改。
- 登记后续阶段 Issue。
- 更新 `.gitignore`，允许指定治理文档被 Git 跟踪。

未实现：

- 未修改业务代码。
- 未新增功能。
- 未重构现有代码。

## ISSUE-002 Contract Audit

状态：完成
建议优先级：高

目标：

- 对照 `docs/CONTRACTS.md` 检查现有 API、trace、memory、schema 是否一致。
- 记录字段缺口和兼容性风险。
- 不做大规模实现，只输出最小修复建议或小范围契约补齐。

验收：

- 列出每个冻结 API 的实际字段和契约字段差异。
- 列出 schema 与 runtime 输出差异。
- 明确哪些差异可以修复，哪些需要用户批准。

审计结论：

- `GET /api/signals`：实际返回 `generated_at` 和 `signals`；`signals` 内含 `tone`、`sentiment_score`、`crowding`、`themes` 等契约字段。差异：缺少顶层 API response schema 与 HTTP wrapper 验证。类型：schema 漏验。风险：低。建议：修 schema / 验证脚本。
- `POST /api/agent/chat`：实际返回 `trace_id`、`task_type`、`content`、`evidence`、`risk_flags`、`next_watch`、`review`，并额外返回 `execution`、`repair`。差异：额外字段为兼容扩展；chat schema 未强制 dataclass 当前总会输出的 `execution`、`repair`。类型：schema 漏验。风险：低。建议：修 schema 或暂不处理。
- `POST /api/agent/briefing`：实际返回 `trace_id`、`title`、`briefing_type`、`style`、`script`、`sections`、`evidence`、`risk_flags`、`next_watch`、`review`。契约只要求保留 `trace_id`、`title`、`script`、`sections`。差异：缺少 briefing response schema，验证脚本只做基础字段检查。类型：schema 漏验。风险：中。建议：修 schema / 验证脚本。
- `GET /api/agent/memory`：实际返回 `user_id`、`watchlist`、`focus_themes`、`knowledge_level`、`risk_preferences`、`journey_state`、`open_questions`、`blockers`、`next_priority`、`last_questions`、`last_next_watch`、`updated_at`。与 memory 契约和 `user_memory` schema 对齐。类型：无差异。风险：低。建议：暂不处理。
- `POST /api/agent/memory`：实际只接受 `watchlist`、`focus_themes`、`knowledge_level`、`open_questions`、`blockers`、`next_priority`、`journey_state`，不接受新提交的未知兼容字段，也不能显式同步 `risk_preferences`、`last_questions`、`last_next_watch`。类型：缺字段 / 文档过度承诺。风险：中。建议：修代码以兼容合并允许字段，或修文档收窄 POST 契约。
- `GET /api/agent/traces`：实际支持 `limit`、`id`/`trace_id`，并额外支持 `query`、`task_type`、`execution_mode`、`review_passed`、`repair_changed`、`date_from`、`date_to`。差异：缺少 trace list wrapper / summary schema。类型：schema 漏验。风险：低。建议：修 schema / 验证脚本。
- dataclass vs JSON Schema：`AgentResponse` 与 chat schema 主字段一致；`ReflectionResult` 的 `compliance`、`clarity`、`repair_suggestions`、`issues` 未被 schema required 约束；`AgentRequest`、`AgentPlan` 没有独立 schema，trace schema 仅把 request/plan 标为 object。类型：schema 漏验。风险：中。建议：修 schema。
- trace 实际写入字段 vs trace schema：实际 trace 含 `trace_id`、`created_at`、`request`、`state_summary`、`plan`、`tool_results`、`wiki_hits`、`execution`、`draft`、`repair`、`review`、`memory_patch`、`updated_memory`、`final_response`；schema 覆盖顶层字段，但未深验 request、plan、state_summary.memory、review.factuality、repair、final_response。类型：schema 漏验。风险：中。建议：修 schema / 验证脚本。
- memory 实际字段 vs `user_memory` schema：`default_memory()` / `load_memory()` 与 required 字段一致；trace 的 `state_summary.memory` 是裁剪快照，不含 `user_id`、`last_questions`、`last_next_watch`、`updated_at`，当前 trace schema 未定义该快照结构。类型：schema 漏验。风险：低。建议：修 trace schema 或补 memory snapshot schema。
- `scripts/verify_runtime.py` 覆盖：市场信号、Wiki 页面、工具结果、prompt builder、LLM config、普通 chat、拒绝问题、reflection layers/factuality/repair、memory 持久化、briefing 基础、trace lookup、trace schema、trace summary/filter。遗漏：HTTP API wrapper、briefing response schema、traces list response schema、memory POST 未知字段兼容、dataclass/schema parity、JSON Schema 类型与嵌套校验。类型：schema 漏验。风险：中。建议：修验证脚本。

高风险差异：

- 未发现高风险契约差异。

注意：

- 本次审计未运行 `scripts/verify_runtime.py`，因为该脚本会调用 runtime 并写入 `data/user_memory.json` 与 `data/agent_traces.jsonl`。
- 未新增 `docs/CONTRACT_AUDIT.md`，因为当前 `.gitignore` 默认忽略 `docs/*.md`，只放行既有治理文档。

## ISSUE-003 Factuality Evidence Binding

状态：完成
建议优先级：高

目标：

- 增强 factuality，使重要判断能绑定市场数据、历史数据或 Wiki section。
- 提升 evidence coverage 的可解释性。

限制：

- 不改变合规边界。
- 不引入外部数据库。
- 不输出买卖建议。

已完成：

- `review.factuality` 新增 `claim_bindings`、`coverage_summary`、`required_evidence_types`，用于说明重要判断绑定到哪些 market signal / history / wiki evidence。
- `review.factuality.coverage` 改为 `supported`、`partial`、`insufficient` 三档。
- `market_overview`、`theme_explanation`、`briefing_script` 的核心市场判断会检查当前市场状态、上涨数量、情绪分、拥挤度、主题集中度等是否由工具结果或 evidence 支撑。
- 无证据强判断进入 `insufficient_evidence`；与工具结果冲突的情绪分、拥挤度等进入 `evidence_conflict`。
- `executor` 在不改变 UI 和路由的前提下，为 evidence 补充稳定 `id`、`source` 和 `fields`。
- `scripts/verify_runtime.py` 已增加有证据市场概览、主题解释、briefing 绑定、无证据强判断、工具结果冲突的回归覆盖。

验收：

- `python scripts/verify_runtime.py` 已通过。

## ISSUE-004 Wiki Governance

状态：完成
建议优先级：中

目标：

- 为 Wiki 增加审核状态、版本流转、证据质量要求和更新流程。
- 补齐 draft 内容与真实来源之间的差距。

已完成：

- `schemas/wiki/wiki_page.schema.json` 新增并约束 `status`、`reviewed_at`、`evidence_quality`、`sources` 等治理字段。
- 现有 Wiki 页面补齐最小页面级治理字段，保持正文不扩写；当前均为 `draft`、`evidence_quality: low`，来源记录为内部手工说明。
- `agent/wiki.py` 检索结果保留 `version`、`status`、`reviewed_at`、`evidence_quality`、`sources`、`applicable_tasks`、`forbidden_use` 和 section 更新时间。
- `scripts/verify_runtime.py` 增加 Wiki schema、枚举、draft 检索暴露治理字段、`forbidden_use` / `applicable_tasks` 类型检查。
- `docs/CONTRACTS.md` 更新 Wiki 契约，明确 draft 可检索但必须暴露治理字段。

未实现：

- 未联网抓取来源。
- 未新增外部来源白名单。
- 未修改投资相关表达模板或金融合规边界。
- 未做 factuality 新规则，仅为 factuality evidence binding 暴露治理数据。

验收：

- `python -m json.tool` 检查修改过的 Wiki/schema JSON 应通过。
- `python -m py_compile agent/wiki.py scripts/verify_runtime.py` 应通过。
- `python scripts/verify_runtime.py` 应通过。

## ISSUE-005 Memory Patch Builder

状态：完成
建议优先级：中

目标：

- 强化从用户自然语言中抽取关注主题、自选股、知识水平和风险偏好的能力。
- 让 memory patch 更可审计、更少误写。

限制：

- 不上传用户 memory。
- 不引入多用户权限系统。

已完成：

- 在 `agent/memory.py` 新增规则型 `build_memory_patch(request, plan, draft, review, evidence)`，统一生成结构化 memory patch。
- 新结构 patch 包含 `source`、`reason`、`confidence`、`operations` 和 `evidence_refs`；每条 operation 包含 `op`、`path`、`value`、`source`、`reason`、`confidence`。
- 将 `executor` 中旧的 focus_themes / risk flag 直接写入逻辑迁移到 runtime review 后的 memory builder，避免普通主题解释自动写 memory。
- `focus_themes` 只在用户明确表达关注、跟踪、观察等主题意图时写入；“今天市场怎么样”“AI硬件为什么热”不自动写关注主题。
- `watchlist` 只在用户明确表达关注、添加、加入自选等意图时写入；普通“中际旭创今天怎么样”不自动加入自选。
- `knowledge_level`、`risk_preferences` 只做规则型保守更新，并在 operation 中保留 reason。
- `apply_patch` 支持新结构 `operations`，同时保留旧式扁平 patch 兼容。
- `schemas/runtime/agent_trace.schema.json` 增加 memory_patch 审计字段约束；`schemas/runtime/user_memory.schema.json` 补充 `risk_preferences.needs_stronger_risk_warning` 类型。
- `scripts/verify_runtime.py` 增加普通市场问题、明确关注主题、明确加入自选、普通个股提及、trace 审计字段和旧 patch 兼容回归。
- `docs/CONTRACTS.md` 更新 Memory 契约。

验收：

- `python -m py_compile agent/memory.py agent/runtime.py agent/executor.py scripts/verify_runtime.py` 已通过。
- `python -m json.tool schemas/runtime/user_memory.schema.json` 已通过。
- `python -m json.tool schemas/runtime/agent_trace.schema.json` 已通过。
- `python scripts/verify_runtime.py` 已通过。

注意：

- 本轮未使用 LLM 抽取 memory，未新增外部依赖，未修改 UI、`server.py`、`market/collector.py` 或金融合规边界。
- 验证脚本会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`；这些运行期文件不应提交。

## ISSUE-006 Trace Debugging Improvements

状态：完成
建议优先级：中

目标：

- 增强 trace 调试能力，让开发者更容易查看 factuality、repair、memory patch 和 execution 信息。

限制：

- 不改变 trace 基础契约。
- 不提交运行期 trace 数据。

已完成：

- `summarize_trace(trace)` 新增 `repair_status`、`claim_binding_count`、`unsupported_claim_count`、`conflicting_claim_count`、`memory_operation_count`、`memory_patch_confidence`、`wiki_statuses`、`wiki_evidence_qualities`。
- 新增纯函数 `compare_traces(left, right)`，返回结构化 `differences` / `matches`，覆盖 task、execution、review、factuality、repair、memory patch 和 Wiki 治理摘要等关键项。
- `schemas/api/agent_traces_response.schema.json` 覆盖新增 summary 字段。
- `schemas/runtime/agent_trace.schema.json` 小范围补充 repair 后 factuality 兼容字段。
- `scripts/verify_runtime.py` 增加 trace summary 字段、trace diff summary 和 traces response schema 回归。
- `?debug=1` 调试台小范围增加 claim、memory operation、Wiki status/quality 等摘要展示。
- `docs/CONTRACTS.md` 更新 Trace 契约。

未实现：

- 未新增 trace 导出 API 或导出按钮。
- 未修改 `server.py` 路由。
- 未修改 Agent Runtime 主流程、memory/factuality 规则或金融合规边界。

## ISSUE-007 Storage Strategy Decision

状态：完成
建议优先级：低

目标：

- 评估是否从 JSON 文件迁移到 SQLite。

决策结论：

- 当前 v0.1 是本地单用户工具，继续使用 JSON / JSONL。
- 现在不迁移 SQLite，不新增数据库文件，不写迁移脚本，不改 runtime 存储代码。
- 当前优先补运行期数据保留、归档、清理、导出和备份策略。
- SQLite 只作为未来触发条件满足后的候选方案，需要单独设计 Issue 和用户批准。

方案评估：

1. 继续 JSON / JSONL

   - 优点：与冻结架构和现有代码完全一致；本地可读、易审计、易备份；无依赖、无迁移风险；适合 v0.1 单用户低并发使用。
   - 缺点：trace 查询需要读 JSONL 文件；跨日期复杂查询、统计聚合和局部删除不方便；文件持续增长后需要治理策略。
   - 工程成本：最低，仅需维持现有验证和 `.gitignore` 边界。
   - 对 v0.1 架构影响：无影响，符合“SQLite 或外部数据库迁移不属于 v0.1”的冻结边界。
   - 对 trace / memory / market history 的影响：trace 继续 append JSONL；memory 继续单 JSON；market latest/history 继续 JSON/JSONL；需要关注文件体积和读取耗时。
   - 是否需要用户批准：继续现状不需要；但任何存储迁移仍需要批准。

2. JSON / JSONL + 更严格的数据保留、归档、清理策略

   - 优点：保留当前架构，同时控制 trace 和 history 增长；可先定义保留天数、最大文件体积、归档压缩、导出、清理和备份规则；风险低，便于人工检查。
   - 缺点：需要新增策略设计和可能的后续实现；归档后的跨文件查询仍不如数据库；清理策略若设计不当可能影响审计追溯。
   - 工程成本：低到中，先做文档策略，再按单独 Issue 实现清理/归档工具。
   - 对 v0.1 架构影响：小，只是治理现有文件生命周期，不改变 API 和 runtime 主流程。
   - 对 trace / memory / market history 的影响：trace 可按日期或体积分段归档；market history 可设置保留窗口；memory 应优先备份而非自动清理，避免误删用户旅程状态。
   - 是否需要用户批准：策略设计可先登记；实际删除、压缩、归档、导出或改变保留范围前需要用户确认验收口径。

3. SQLite 本地单机库

   - 优点：更适合跨日期查询、过滤、聚合和索引；trace、memory、market history 可以获得更强一致性和结构化查询能力；未来可支持更复杂调试台。
   - 缺点：引入数据库文件、schema 演进、迁移脚本、备份/恢复流程和兼容风险；会改变冻结数据边界；对当前单用户 v0.1 属于过早复杂化。
   - 工程成本：高，需要 schema 设计、迁移/回滚方案、读写适配、验证脚本、旧 JSON/JSONL 兼容、数据备份和用户批准。
   - 对 v0.1 架构影响：中到高，属于存储迁移，不能在决策 Issue 中实现。
   - 对 trace / memory / market history 的影响：trace 可索引查询；memory 可事务写入；market history 可按时间和主题查询；但迁移会带来数据一致性、旧文件读取和审计链路风险。
   - 是否需要用户批准：需要。根据 `docs/AUTHORITY_MATRIX.md`，迁移运行数据存储必须先获用户明确批准。

4. 暂缓迁移，等触发条件满足后再开迁移 Issue

   - 优点：保留当前低风险路径，同时给未来迁移设置明确门槛；避免为尚未出现的问题付出数据库成本；符合 v0.1 冻结边界。
   - 缺点：需要持续观察 trace/history 体积和读取性能；如果没有保留策略，问题可能以文件膨胀形式累积。
   - 工程成本：低，当前只需记录触发条件和下一步治理 Issue。
   - 对 v0.1 架构影响：无破坏性影响。
   - 对 trace / memory / market history 的影响：短期不变；后续若触发条件满足，再设计 SQLite schema、迁移路径和兼容读写。
   - 是否需要用户批准：暂缓不需要；未来打开 SQLite Migration Design 或执行迁移需要批准。

SQLite 迁移触发条件：

- `data/agent_traces.jsonl` trace 数量达到约 10,000 条，或单文件体积达到约 50 MB，并且调试台查询、过滤或打开详情出现可感知延迟。
- `data/xueqiu_radar_history.jsonl` 需要稳定支持跨日期、多条件、主题/个股维度的复杂查询，而不是只读取最近有限条记录。
- 项目进入多用户使用场景，需要隔离用户数据、审计不同用户行为或处理并发写入。
- memory 写入需要事务一致性，例如多个 runtime turn、手动同步和后续任务可能并发修改同一用户状态。
- JSONL 整文件读取、倒序查找或过滤明显变慢，影响 `/api/agent/traces`、调试台或验证脚本体验。
- 数据治理需求超过简单文件策略，例如需要可靠归档、压缩、导出、清理、恢复、校验和增量备份。

下一步建议 Issue：

- Runtime Data Retention Policy：定义 trace、memory、market history 的保留窗口、最大体积、备份频率、隐私边界和人工确认规则。
- Trace Archive and Cleanup：在保留策略批准后，设计 trace 按日期/体积分段归档、压缩、导出和清理的最小实现。
- SQLite Migration Design：仅在上述触发条件满足后启动；先设计 schema、迁移/回滚、兼容读取、备份恢复和验收标准，再申请用户批准。

遗留风险：

- 当前 trace 查询和过滤依赖整文件读取，文件增长后会逐步变慢。
- 当前缺少明确保留和清理策略，长期运行可能积累较大的本地 trace/history 文件。
- memory 是单 JSON 文件，适合本地单用户；未来并发、多用户或事务一致性需求出现时需要重新评估。
- 归档或清理如果先于策略设计实现，可能破坏审计追溯。

已确认不做：

- 未修改业务代码。
- 未新增 SQLite。
- 未新增数据库文件。
- 未写迁移脚本。
- 未改 `data_store.py`、`agent/memory.py`、`agent/trace.py`、`server.py` 或 API。
- 未修改运行期 data 文件。
- 未新增依赖。
- 未做多用户权限系统。

## ISSUE-008 Active Briefing and Scheduling

状态：待决策
建议优先级：低

目标：

- 评估早盘、午盘、收盘、周末复盘等主动触达模式。

需要用户批准：

- 定时任务。
- 通知渠道。
- 主动触达策略和频率。

## ISSUE-009 Contract Schema and Verification Alignment

状态：完成
建议优先级：高

目标：

- 补齐 `POST /api/agent/briefing` response schema。
- 补齐 `GET /api/agent/traces` list wrapper / summary schema。
- 加强 `agent_trace` schema 对 request、plan、review.factuality、repair、final_response 的嵌套校验。
- 检查 `AgentResponse` / `ReflectionResult` / `UserMemory` 与 schema required 字段一致性。
- 更新 `scripts/verify_runtime.py` 检查新增 schema。
- 收窄 `POST /api/agent/memory` 文档契约，明确只接受白名单字段，保留已有未知兼容字段，不写入请求未知字段。

已完成：

- 新增 `schemas/api/agent_briefing_response.schema.json`。
- 新增 `schemas/api/agent_traces_response.schema.json`。
- 更新 `schemas/api/agent_chat_response.schema.json`，将当前 `AgentResponse` / `ReflectionResult` 输出字段纳入 required 校验。
- 更新 `schemas/runtime/agent_trace.schema.json`，补齐 request、state summary memory snapshot、plan、draft、review.factuality、repair、final_response 的关键字段结构。
- 更新 `scripts/verify_runtime.py`，在不新增外部依赖的前提下增加轻量递归 schema 校验、本地 `$ref` 解析、新 schema 检查、dataclass/schema parity 检查和 memory POST 白名单契约检查。
- 更新 `docs/CONTRACTS.md`，收窄 `POST /api/agent/memory` 契约。

验收：

- `python scripts/verify_runtime.py` 应通过。
- 运行验证会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`，这些运行期文件不应提交。

## ISSUE-010 Factuality Edge Case Repair

状态：完成
建议优先级：高

背景：

- Reviewer 发现 ISSUE-003 的 factuality 规则存在三个边界问题：
  - 无事实 claim 的普通回复会被误判 `insufficient_evidence`。
  - repair 后 final review 会丢掉修复前 factuality 语义。
  - LLM reflection prompt 仍使用旧 coverage 示例。

已完成：

- `agent/reflector.py` 修复 0-claim 边界：非核心任务或普通回复在 `checked_claims == 0` 且无 unsupported/conflict 时通过 factuality。
- `agent/reflector.py` 保留核心任务保护：`market_overview`、`theme_explanation`、`briefing_script` 若无可绑定核心判断，仍失败并记录“缺少可绑定的核心市场判断”。
- `agent/reflector.py` 新增兼容字段写入 helper，repair 后 final review 会附带 `repair_status: claims_removed` 和 `repaired_from_factuality`，保留原始 factuality 摘要与 unsupported/conflict 细节。
- `agent/runtime.py` 在 repair 后二次 review 完成时调用上述保留逻辑。
- `agent/prompts.py` 将 LLM Reflection coverage 示例更新为 `supported`，并明确允许值为 `supported`、`partial`、`insufficient`。
- `scripts/verify_runtime.py` 增加回归覆盖：
  - “你好，我可以帮你做市场观察。” 通过。
  - “我还没有读取到你的自选股。” 通过。
  - disclaimer-only 回复通过。
  - core factuality task 的 0-claim 回复仍失败。
  - repair 后 final review 保留修复前 factuality。
  - reflection prompt 不再出现旧 `"coverage": "sufficient"` 示例。

验收：

- `python -m py_compile agent/reflector.py agent/runtime.py agent/prompts.py scripts/verify_runtime.py` 已通过。
- `python scripts/verify_runtime.py` 已通过。

注意：

- 本轮未修改 UI、`server.py`、合规边界、Wiki 内容或外部依赖。
- 新增字段为兼容扩展，未加入 schema required，以兼容旧 trace 与硬规则拦截结果。

## ISSUE-011 Runtime Data Retention Policy

状态：完成
建议优先级：中

背景：

- ISSUE-007 已决定 v0.1 继续使用本地 JSON / JSONL。
- 当前不迁移 SQLite，不新增数据库文件，不写迁移脚本，不改 runtime 存储代码。
- `docs/CONTRACTS.md` 已明确运行期数据保留、归档、压缩、导出、清理和备份能力尚未实现。

目标：

- 定义运行期数据保留策略边界。
- 覆盖 latest snapshot、market history、user memory、agent traces 四类本地运行期数据。
- 明确人工确认、隐私、提交和后续 Issue 拆分规则。
- 保持本轮为文档治理任务，不实现清理、归档、导出或备份工具。

已完成：

- 在 `docs/CONTRACTS.md` 补充运行期数据性质：
  - `data/xueqiu_radar_latest.json` 是 latest snapshot，可再生成，不等同于审计历史。
  - `data/xueqiu_radar_history.jsonl` 是 market history，可在未来定义归档或清理窗口，本轮不执行。
  - `data/user_memory.json` 是 user memory，优先保护，不自动清理。
  - `data/agent_traces.jsonl` 是 agent traces，优先保护审计链，不在无归档/备份/人工确认时删除。
- 在 `docs/CONTRACTS.md` 明确保留优先级：memory、traces、market history、latest snapshot。
- 在 `docs/CONTRACTS.md` 补充建议观察阈值和触发条件：trace 数量、trace 文件体积、history 文件体积、查询变慢、复杂查询需求和 memory 备份/恢复需求。
- 在 `docs/CONTRACTS.md` 明确上述阈值只用于触发后续数据治理或存储设计讨论，不构成 SQLite 迁移计划。
- 在 `docs/CONTRACTS.md` 补充人工确认规则：任何删除、压缩、归档、导出、改变保留范围的实际操作，都必须在后续单独 Issue 中实现并经用户确认；删除前必须有备份或明确放弃确认；memory 删除或重置必须单独确认。
- 在 `docs/CONTRACTS.md` 补充隐私和提交边界：`data/user_memory.json` 和 `data/agent_traces.jsonl` 不应提交；不上传 memory、trace 或本地数据到外部服务；不把本地隐私数据写入治理文档。
- 在 `docs/RUNBOOK.md` 小范围补充运行期数据人工检查提示，强调只检查和记录，不执行清理。
- 在 `docs/HANDOFF.md` 更新本轮交接、验收方式和后续建议 Issue。

未实现：

- 未实现 trace 清理、归档、压缩或导出工具。
- 未实现 market history 清理、归档、压缩或导出工具。
- 未实现 memory 备份、恢复、删除或重置工具。
- 未实现 runtime data export 工具。
- 未修改 JSON / JSONL 存储方式。
- 未引入 SQLite、外部数据库、外部依赖、定时任务或主动触达。
- 未修改 API、runtime、schema、`server.py`、`agent/`、`market/`、`static/`、`scripts/` 或 `data/`。
- 未修改金融合规边界、荐股/目标价/收益预测拒绝策略。

后续建议 Issue：

- Trace Archive and Cleanup：在策略基础上设计 trace 分段归档、压缩、导出和清理的最小实现；执行前必须确认备份和删除边界。
- Market History Retention Tooling：定义 market history 保留窗口、归档格式、人工验收和恢复检查；本轮未实现。
- Memory Backup and Restore Policy/Tooling：定义 memory 备份、恢复、删除、重置的单独确认流程；memory 不参与普通自动清理。
- Runtime Data Export Policy/Tooling：定义本地导出范围、脱敏规则、用户确认和不上传外部服务边界。
- SQLite Migration Design：仅在触发条件满足且用户批准后启动；先设计 schema、迁移/回滚、兼容读取、备份恢复和验收标准。

验收：

- `git diff --stat` 应只显示允许范围内的文档修改。
- `git diff` 应确认没有运行期 `data/`、代码、schema 或脚本改动。
- 本轮不需要运行 `python scripts/verify_runtime.py`，因为该脚本会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`。

## ISSUE-012 Runtime Data Retention Inspector

状态：完成
建议优先级：中

背景：

- ISSUE-011 已完成 Runtime Data Retention Policy。
- 当前任何删除、压缩、归档、导出、改变保留范围，都必须后续单独 Issue + 用户确认。
- 在进入 Trace Archive and Cleanup 前，需要一个只读 inspector，用于人工判断 trace/history 是否接近阈值。

目标：

- 新增只读脚本检查运行期数据文件状态。
- 只报告文件存在性、体积和 JSONL 行数，不读取或输出 memory/trace 具体内容。
- 不修改任何 `data/` 文件，不实现治理动作。

已完成：

- 新增 `scripts/inspect_runtime_data.py`。
- 脚本只使用 Python 标准库。
- 检查以下运行期文件：
  - `data/xueqiu_radar_latest.json`
  - `data/xueqiu_radar_history.jsonl`
  - `data/user_memory.json`
  - `data/agent_traces.jsonl`
- 输出 JSON 报告，字段包含 `file_path`、`exists`、`size_bytes`、`size_mb`、`line_count`、`threshold_status`、`note`。
- 仅对 JSONL 文件统计 `line_count`；不解析、不打印 JSONL 记录内容。
- 对 `data/user_memory.json` 只报告存在性和体积，不读取或输出内容。
- 对 `data/agent_traces.jsonl` 只统计行数和体积，不读取或输出具体 trace 内容。
- 缺失文件友好返回报告项，不作为致命错误。
- trace 阈值参考 ISSUE-011：约 10,000 行或约 50 MB 为 `exceeds`，接近阈值为 `watch`。
- market history 体积达到约 50 MB 时提示 `watch`，并说明单次检查不能证明持续增长。
- 在 `docs/RUNBOOK.md` 补充只读 inspector 的运行方式和边界。
- 更新 `docs/HANDOFF.md` 记录本轮完成内容、未做事项、验证结果和后续建议。

未实现：

- 未删除、压缩、归档、导出、备份或修改任何 `data/` 文件。
- 未实现清理工具、归档工具、导出工具、备份/恢复工具。
- 未修改 JSON / JSONL 存储方式。
- 未引入 SQLite、外部数据库、外部依赖、定时任务、主动触达或多用户能力。
- 未修改 `server.py`、API 路由、agent runtime 主流程、market 采集逻辑、前端 UI、schema 或金融合规边界。

验收：

- `python -m py_compile scripts/inspect_runtime_data.py` 已通过。
- `python scripts/inspect_runtime_data.py` 已通过，退出码为 0。
- inspector 输出只包含文件路径、存在性、体积、JSONL 行数、阈值状态和说明；未输出 memory 或 trace 内容。
- `git diff --stat` 只显示允许范围内文件。
- `git diff` 确认没有 `data/`、`server.py`、`agent/`、`market/`、`static/`、`schemas/` 改动。
- 未运行 `python scripts/verify_runtime.py`，因为本 Issue 不涉及 runtime 行为，且该脚本会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`。
