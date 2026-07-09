# Handoff

更新时间：2026-07-09
当前版本：Market Harness Agent v0.1
本轮任务：ISSUE-012 Runtime Data Retention Inspector

## 1. 本轮完成内容

本轮只实现运行期数据只读检查器，未执行任何清理、归档、导出、备份或存储迁移：

- 阅读并对照了 `docs/PROJECT_SPEC.md`、`docs/ARCHITECTURE_FREEZE.md`、`docs/AUTHORITY_MATRIX.md`、`docs/CONTRACTS.md`、`docs/AGENT_RULES.md`、`docs/ISSUES.md`、`docs/HANDOFF.md` 和 `docs/RUNBOOK.md`。
- 新增 `scripts/inspect_runtime_data.py`，用于只读检查运行期数据文件状态。
- 在 `docs/ISSUES.md` 登记并完成 ISSUE-012 Runtime Data Retention Inspector。
- 在 `docs/RUNBOOK.md` 补充只读 inspector 的运行方式和边界。
- 更新本 `docs/HANDOFF.md`，记录完成内容、未做事项、验证结果、inspector 输出摘要和后续建议。

## 2. 修改文件列表

- `docs/ISSUES.md`
- `docs/HANDOFF.md`
- `docs/RUNBOOK.md`
- `scripts/inspect_runtime_data.py`

## 3. ISSUE-012 完成内容

- `scripts/inspect_runtime_data.py` 只使用 Python 标准库。
- 检查 `data/xueqiu_radar_latest.json`、`data/xueqiu_radar_history.jsonl`、`data/user_memory.json`、`data/agent_traces.jsonl`。
- 输出 JSON 报告，字段包含 `file_path`、`exists`、`size_bytes`、`size_mb`、`line_count`、`threshold_status`、`note`。
- 仅对 JSONL 文件统计 `line_count`；不解析、不打印 JSONL 记录内容。
- 对 memory 只报告存在性和体积，不读取或输出具体内容。
- 对 trace 只统计行数和体积，不输出具体 trace 内容。
- 缺失文件友好返回报告项，不作为致命错误。
- trace 约 10,000 行或约 50 MB 为 `exceeds`，接近阈值为 `watch`。
- market history 约 50 MB 时提示 `watch`，并说明单次检查不能证明持续增长。
- 脚本正常检查完成返回 0；参数错误返回非 0。

## 4. 明确未做事项

- 未删除、压缩、归档、导出、备份或修改任何 `data/` 文件。
- 未实现清理工具、归档工具、导出工具、备份/恢复工具。
- 未修改 JSON / JSONL 存储方式。
- 未引入 SQLite、外部数据库、外部依赖、定时任务、主动触达或多用户能力。
- 未修改 `server.py`、API 路由、agent runtime 主流程、market 采集逻辑、前端 UI 或 schema。
- 未修改金融合规边界、荐股/目标价/收益预测拒绝策略。

## 5. 验收命令/检查结果

本轮不需要运行 `python scripts/verify_runtime.py`，因为本 Issue 不涉及 runtime 行为，且该脚本会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`。

已执行的检查：

- `python -m py_compile scripts/inspect_runtime_data.py`：通过。
- `python scripts/inspect_runtime_data.py`：通过，退出码为 0。
- `git status --short`：只显示 `docs/HANDOFF.md`、`docs/ISSUES.md`、`docs/RUNBOOK.md` 和新增 `scripts/inspect_runtime_data.py`。
- `git diff --stat`：只显示已跟踪的允许范围文档；新增脚本因未 staged，不出现在普通 diff stat 中。
- `git diff`：未发现 `data/`、`server.py`、`agent/`、`market/`、`static/`、`schemas/` 改动。
- 人工检查 Markdown 标题层级和列表格式：已检查。

## 6. Inspector 输出摘要

- `data/xueqiu_radar_latest.json`：存在，20,567 bytes，0.02 MB，状态 `ok`。
- `data/xueqiu_radar_history.jsonl`：存在，937 bytes，0.001 MB，JSONL 行数 1，状态 `ok`。
- `data/user_memory.json`：存在，7,843 bytes，0.007 MB，状态 `ok`；未输出 memory 内容。
- `data/agent_traces.jsonl`：存在，2,504,795 bytes，2.389 MB，JSONL 行数 211，状态 `ok`；未输出 trace 内容。

## 7. 是否发现需要用户批准的新事项

- 本轮未发现必须立即批准的新事项。
- inspector 当前输出均未触发 `watch` 或 `exceeds`，不需要清理、归档、导出或迁移决策。
- 后续任何删除、压缩、归档、导出、改变保留范围、memory 删除/重置/恢复、或 SQLite Migration Design 启动，仍需要单独 Issue 和用户确认。

## 8. 后续建议 Issue

- Trace Archive and Cleanup：在策略基础上设计 trace 分段归档、压缩、导出和清理；执行前必须确认备份和删除边界。
- Market History Retention Tooling：定义 market history 保留窗口、归档格式、人工验收和恢复检查。
- Memory Backup and Restore Policy/Tooling：定义 memory 备份、恢复、删除、重置的单独确认流程。
- Runtime Data Export Policy/Tooling：定义本地导出范围、脱敏规则、用户确认和不上传外部服务边界。
- SQLite Migration Design：仅在触发条件满足且用户批准后启动；先设计 schema、迁移/回滚、兼容读取、备份恢复和验收标准。
