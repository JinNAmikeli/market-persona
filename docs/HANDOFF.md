# Handoff

更新时间：2026-07-09
当前版本：Market Harness Agent v0.1
本轮任务：ISSUE-013 Memory Backup and Restore Policy

## 1. 本轮完成内容

本轮只定义 memory 备份、恢复、删除、重置和大范围改写的治理规则，未实现任何工具或修改运行期数据：

- 阅读并对照了 `docs/PROJECT_SPEC.md`、`docs/ARCHITECTURE_FREEZE.md`、`docs/AUTHORITY_MATRIX.md`、`docs/CONTRACTS.md`、`docs/AGENT_RULES.md`、`docs/ISSUES.md`、`docs/HANDOFF.md` 和 `docs/RUNBOOK.md`。
- 在 `docs/ISSUES.md` 登记并完成 ISSUE-013 Memory Backup and Restore Policy。
- 在 `docs/CONTRACTS.md` 补充 memory backup / restore / delete / reset 的策略边界。
- 在 `docs/RUNBOOK.md` 补充 memory 高风险操作前人工检查规则，未提供复制或删除真实文件的命令。
- 更新本 `docs/HANDOFF.md`，记录完成内容、未做事项、验收方式和后续建议。

## 2. 修改文件列表

- `docs/ISSUES.md`
- `docs/CONTRACTS.md`
- `docs/HANDOFF.md`
- `docs/RUNBOOK.md`

## 3. ISSUE-013 完成内容

- 明确 `data/user_memory.json` 是本地用户旅程状态，不是临时缓存。
- 明确 memory 可能包含用户自选、关注主题、知识水平、风险偏好、旅程状态等敏感或半敏感信息。
- 明确备份必须由用户明确触发，或由后续单独 Issue 授权。
- 明确备份前应说明备份位置、范围、是否包含隐私数据，以及是否覆盖既有备份。
- 明确不允许自动上传 memory 到外部服务。
- 明确不允许把 memory 内容写入治理文档、handoff、调试输出、日志或提交信息。
- 明确恢复前必须确认目标文件、来源备份、覆盖范围和是否需要保留当前文件。
- 明确恢复属于高风险本地状态改写，必须单独确认。
- 明确恢复后可建议运行只读 inspector 或 memory 查看 API 做人工检查，但本轮不实现，也不读取或输出 memory 内容。
- 明确删除或重置 memory 必须单独确认，不得作为 trace/history 清理的附带步骤。
- 明确删除前必须有备份，或用户明确确认放弃备份。
- 明确手动批量编辑、字段迁移、批量清空 `watchlist` / `focus_themes` 等都属于高风险 memory 改写，需要单独 Issue、影响字段说明、验收方式和回退方案。

## 4. 明确未做事项

- 未实现备份脚本、恢复脚本、导出工具或清理工具。
- 未复制、读取、打印或修改 `data/user_memory.json` 内容。
- 未修改任何 `data/` 文件。
- 未修改 JSON / JSONL 存储方式。
- 未引入 SQLite、外部数据库、外部依赖、定时任务、主动触达或多用户能力。
- 未修改 `server.py`、API、agent runtime、market、static、schemas、scripts。
- 未修改金融合规边界、荐股/目标价/收益预测拒绝策略。

## 5. 验收命令/检查结果

本轮为文档策略型 Issue，不运行 `python scripts/verify_runtime.py`，也不运行会读取或输出 memory 内容的命令。

已执行的检查：

- `git diff --stat`：只显示允许范围内文档。
- `git diff -- docs/ISSUES.md docs/CONTRACTS.md docs/RUNBOOK.md docs/HANDOFF.md`：已人工检查文档内容。
- `git diff -- data scripts server.py agent market static schemas`：无输出，确认禁止范围无改动。
- `git status --short`：只显示允许范围内文档修改。
- 人工检查 Markdown 标题层级和列表格式：已检查。

## 6. 是否发现需要用户批准的新事项

- 本轮未发现必须立即批准的新事项。
- 后续任何 memory 备份、恢复、删除、重置或大范围改写，都需要单独 Issue 和用户确认。
- 后续任何上传外部服务、存储迁移或自动化备份/恢复，也需要单独批准。

## 7. 后续建议 Issue

- Memory Backup Tooling：定义本地备份位置、命名、覆盖策略、人工确认和验收方式。
- Memory Restore Tooling：定义来源备份校验、覆盖范围、保留当前文件、恢复后人工检查和回退流程。
- Memory Reset Confirmation Flow：定义删除/重置前确认、备份或放弃备份确认、结果验收和审计记录边界。
- Runtime Data Export Policy/Tooling：定义本地导出范围、脱敏规则、用户确认和不上传外部服务边界。
