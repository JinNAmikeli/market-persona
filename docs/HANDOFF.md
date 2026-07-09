# Handoff

更新时间：2026-07-09
当前版本：Market Harness Agent v0.1
本轮任务：ISSUE-014 Runtime Data Export Policy

## 1. 本轮完成内容

本轮只定义 runtime data export 的治理边界，未实现任何导出工具、未新增导出文件、未读取或输出 memory/trace 内容：

- 阅读并对照了 `docs/PROJECT_SPEC.md`、`docs/ARCHITECTURE_FREEZE.md`、`docs/AUTHORITY_MATRIX.md`、`docs/CONTRACTS.md`、`docs/AGENT_RULES.md`、`docs/ISSUES.md`、`docs/HANDOFF.md` 和 `docs/RUNBOOK.md`。
- 在 `docs/ISSUES.md` 登记并完成 ISSUE-014 Runtime Data Export Policy。
- 在 `docs/CONTRACTS.md` 补充 runtime data export 策略边界。
- 在 `docs/RUNBOOK.md` 补充 runtime data export 前人工检查规则，未提供导出命令。
- 更新本 `docs/HANDOFF.md`，记录完成内容、未做事项、验收结果和后续建议。

## 2. 修改文件列表

- `docs/ISSUES.md`
- `docs/CONTRACTS.md`
- `docs/HANDOFF.md`
- `docs/RUNBOOK.md`

## 3. ISSUE-014 完成内容

- 明确 latest snapshot 可再生成、低敏，但仍属于本地运行数据；导出前需说明用途、格式、保存位置和覆盖行为。
- 明确 market history 可用于本地分析；导出前应说明时间范围、字段范围、用途、格式和保存位置。
- 明确 agent traces 包含用户问题、工具证据、review、repair、memory patch 和最终回复等审计信息，默认高敏，导出必须单独确认。
- 明确 user memory 是最高敏感级别，导出必须单独确认，默认不进入普通 runtime data export。
- 明确导出前必须说明范围、格式、保存位置、是否包含隐私数据、是否脱敏、是否覆盖已有文件。
- 明确导出文件不应提交到 Git。
- 明确不允许自动上传导出文件或本地运行期数据到外部服务。
- 明确不允许把导出内容写入 docs、handoff、调试输出、日志或提交信息。
- 明确后续导出工具必须单独 Issue，并默认先做 dry-run / manifest，不直接导出敏感内容。

## 4. 明确未做事项

- 未实现任何导出工具、导出脚本、导出 API 或导出文件。
- 未导出、读取、打印 memory 或 trace 具体内容。
- 未新增脚本。
- 未新增导出文件。
- 未上传任何本地数据到外部服务。
- 未修改任何 `data/` 文件。
- 未修改 JSON / JSONL 存储方式。
- 未引入 SQLite、外部依赖、定时任务、多用户能力。
- 未修改 `server.py`、API、agent runtime、market、static、schemas、scripts、wiki、README 或 `.gitignore`。
- 未修改金融合规边界。

## 5. 验收命令/检查结果

本轮为文档策略型 Issue，不运行 `python scripts/verify_runtime.py`，也不运行会读取或输出 memory/trace 内容的命令。

已执行的检查：

- `git diff --stat`：只显示允许范围内文档。
- `git diff -- docs/ISSUES.md docs/CONTRACTS.md docs/RUNBOOK.md docs/HANDOFF.md`：已人工检查文档内容。
- `git diff -- data scripts server.py agent market static schemas`：无输出，确认禁止范围无改动。
- `git status --short`：只显示允许范围内文档修改。
- 未新增导出文件或脚本。
- 人工检查 Markdown 标题层级和列表格式：已检查。

## 6. 是否发现需要用户批准的新事项

- 本轮未发现必须立即批准的新事项。
- 后续任何 runtime data export 工具实现、包含 trace 的导出、包含 memory 的导出、自动上传外部服务、存储迁移或自动化导出，都需要单独 Issue 和用户确认。
- 当前未发现需要立即启动导出工具实现的事项。

## 7. 后续建议 Issue

- Runtime Data Export Tooling：实现前先设计 dry-run / manifest、字段范围、脱敏策略、保存位置和用户确认流程。
- Trace Export Redaction Policy：单独定义 trace 导出字段、敏感字段脱敏、memory patch 处理和审计验收。
- Market History Export Tooling：定义 market history 时间范围、格式、保存位置和本地分析用途。
- Memory Export Approval Flow：仅在用户明确需要时设计 memory 导出确认、脱敏和保存流程；默认不进入普通导出。
