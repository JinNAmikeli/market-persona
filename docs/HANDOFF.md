# Handoff

更新时间：2026-07-08
当前版本：Market Harness Agent v0.1
本轮任务：ISSUE-004 Wiki Governance

## 1. 本轮完成内容

本轮只完成 Wiki 内容治理，未改 UI、`server.py`、`market/collector.py`、金融合规边界、外部依赖或 factuality 新规则：

- 更新 `schemas/wiki/wiki_page.schema.json`，将 `status` 限定为 `draft` / `reviewed` / `deprecated`，将 `evidence_quality` 限定为 `low` / `medium` / `high`，并新增页面级 `reviewed_at`、`sources` 结构约束。
- 为现有 `wiki/themes/*.json` 和 `wiki/risks/*.json` 补齐最小治理字段；正文未扩写，当前页面均保持 `draft`，`reviewed_at` 为 `null`，`evidence_quality` 为 `low`。
- 更新 `agent/wiki.py`，让检索结果保留 `version`、`status`、`reviewed_at`、`evidence_quality`、`sources`、`applicable_tasks`、`forbidden_use` 和 section 更新时间，供 factuality 与 trace 使用。
- 更新 `scripts/verify_runtime.py`，增加 schema enum 校验、Wiki 页面治理字段检查、draft 检索结果暴露 `status` / `evidence_quality` 检查，以及 `forbidden_use` / `applicable_tasks` 类型检查。
- 更新 `docs/CONTRACTS.md` 的 Wiki 契约。
- 在 `docs/ISSUES.md` 标记 ISSUE-004 完成。

## 2. 本轮未完成内容

按任务边界，本轮没有处理：

- 未联网抓取或补充外部来源。
- 未新增外部来源白名单。
- 未定义 reviewed / deprecated 的审核流程自动化。
- 未修改金融合规边界或投资表达模板。
- 未实现新的 factuality 判定规则。
- 未处理 memory、trace debug、TTS、定时任务或存储迁移。

## 3. 业务代码状态

本轮修改范围限制在用户允许文件：

- `schemas/wiki/wiki_page.schema.json`
- `wiki/themes/*.json`
- `wiki/risks/*.json`
- `agent/wiki.py`
- `scripts/verify_runtime.py`
- `docs/CONTRACTS.md`
- `docs/ISSUES.md`
- `docs/HANDOFF.md`

`draft` 页面仍可被检索，但检索结果必须暴露治理字段。当前 Wiki 来源均为内部手工说明，因此证据质量统一标为 `low`，避免把未审核内容提升为高质量事实来源。

## 4. 测试结果

已运行：

- `python -m json.tool schemas/wiki/wiki_page.schema.json`
- `python -m json.tool wiki/index.json`
- `python -m json.tool wiki/themes/ai_hardware.json`
- `python -m json.tool wiki/themes/semiconductor.json`
- `python -m json.tool wiki/themes/lithium_energy.json`
- `python -m json.tool wiki/risks/crowding.json`
- `python -m json.tool wiki/risks/chasing_hotspots.json`
- `python -m json.tool wiki/risks/data_staleness.json`
- `python -m py_compile agent/wiki.py scripts/verify_runtime.py`
- `python scripts/verify_runtime.py`

结果：全部通过。

注意：`python scripts/verify_runtime.py` 会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`；本轮运行后这些运行期文件未出现在 Git 待提交状态中。

## 5. 遗留风险

- 当前 Wiki 页面仍是 `draft`，来源为内部手工说明，不能当作已审核外部事实库使用。
- `reviewed_at`、`reviewed` 状态流转和外部来源白名单仍需要后续单独 Issue 与用户批准。
- `deprecated` 页面是否从回答中排除尚未定义，本轮只保证状态会被检索结果显式暴露。
