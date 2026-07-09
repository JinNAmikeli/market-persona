# Handoff

更新时间：2026-07-09
当前版本：Market Harness Agent v0.1
本轮任务：ISSUE-011 Runtime Data Retention Policy

## 1. 本轮完成内容

本轮只定义运行期数据保留策略，未实现任何清理、归档、导出、备份或存储迁移能力：

- 阅读并对照了 `docs/PROJECT_SPEC.md`、`docs/ARCHITECTURE_FREEZE.md`、`docs/AUTHORITY_MATRIX.md`、`docs/CONTRACTS.md`、`docs/AGENT_RULES.md`、`docs/ISSUES.md`、`docs/HANDOFF.md` 和 `docs/RUNBOOK.md`。
- 在 `docs/ISSUES.md` 登记并完成 ISSUE-011 Runtime Data Retention Policy。
- 在 `docs/CONTRACTS.md` 补充运行期数据保留策略边界，覆盖 latest snapshot、market history、user memory、agent traces。
- 在 `docs/RUNBOOK.md` 小范围补充人工检查提示，强调只检查和记录，不执行清理。
- 更新本 `docs/HANDOFF.md`，记录完成内容、未完成内容、验收方式、后续建议 Issue 和用户批准事项。

## 2. 修改文件列表

- `docs/ISSUES.md`
- `docs/CONTRACTS.md`
- `docs/HANDOFF.md`
- `docs/RUNBOOK.md`

## 3. ISSUE-011 完成内容

- 定义 `data/xueqiu_radar_latest.json` 为 latest snapshot：可刷新再生成，不等同于审计历史。
- 定义 `data/xueqiu_radar_history.jsonl` 为 market history：未来可以设置归档或清理窗口，本轮不执行。
- 定义 `data/user_memory.json` 为 user memory：优先保护，不自动清理；删除、重置、恢复或大范围改写必须单独确认。
- 定义 `data/agent_traces.jsonl` 为 agent traces：优先保护审计链，不在无归档/备份/人工确认时删除。
- 明确保留优先级：memory、traces、market history、latest snapshot。
- 补充建议观察阈值和触发条件：trace 数量约 10,000 条、trace 文件约 50 MB、trace 查询变慢、history 文件体积增长、history 复杂查询需求、memory 备份/恢复需求。
- 明确任何删除、压缩、归档、导出或改变保留范围的实际操作，都必须在后续单独 Issue 中实现并经用户确认。
- 明确删除前必须有备份，或由用户明确确认放弃备份。
- 明确 `data/user_memory.json` 和 `data/agent_traces.jsonl` 不应提交，不上传 memory、trace 或本地运行期数据到外部服务，不把本地隐私数据写入治理文档。

## 4. 明确未做事项

- 未实现清理、归档、压缩、导出或备份工具。
- 未修改 JSON / JSONL 存储方式。
- 未引入 SQLite、外部数据库、外部依赖、定时任务、主动触达或多用户能力。
- 未修改 API、runtime、schema、`server.py`、`agent/`、`market/`、`static/`、`scripts/`。
- 未修改任何运行期 `data/` 文件。
- 未修改金融合规边界、荐股/目标价/收益预测拒绝策略。

## 5. 验收命令/检查结果

本轮为文档策略型 Issue，不需要运行 `python scripts/verify_runtime.py`，因为该脚本会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`。

已执行的检查：

- `git diff --stat`：只显示 `docs/CONTRACTS.md`、`docs/HANDOFF.md`、`docs/ISSUES.md`、`docs/RUNBOOK.md` 4 个文档文件。
- `git diff -- docs/ISSUES.md docs/CONTRACTS.md docs/HANDOFF.md docs/RUNBOOK.md`：未发现运行期 `data/`、代码、schema 或脚本改动。
- 人工检查 Markdown 标题层级和列表格式：已检查，`docs/RUNBOOK.md` 新增章节后编号已顺延。

检查目标：

- diff 只包含允许范围内的文档。
- 没有运行期 `data/`、代码、schema、脚本改动。
- 没有新增文档文件。

## 6. 后续建议 Issue

- Trace Archive and Cleanup：在策略基础上设计 trace 分段归档、压缩、导出和清理；执行前必须确认备份和删除边界。
- Market History Retention Tooling：定义 market history 保留窗口、归档格式、人工验收和恢复检查。
- Memory Backup and Restore Policy/Tooling：定义 memory 备份、恢复、删除、重置的单独确认流程。
- Runtime Data Export Policy/Tooling：定义本地导出范围、脱敏规则、用户确认和不上传外部服务边界。
- SQLite Migration Design：仅在触发条件满足且用户批准后启动；先设计 schema、迁移/回滚、兼容读取、备份恢复和验收标准。

## 7. 是否发现需要用户批准的新事项

- 本轮未发现必须立即批准的新事项。
- 后续任何删除、压缩、归档、导出、改变保留范围、memory 删除/重置/恢复、或 SQLite Migration Design 启动，都需要单独 Issue 和用户确认。
