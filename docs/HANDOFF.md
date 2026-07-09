# Handoff

更新时间：2026-07-08
当前版本：Market Harness Agent v0.1
本轮任务：ISSUE-006 Trace Debugging Improvements

## 1. 本轮完成内容

本轮只完成 Trace Debugging Improvements，未改 `server.py` 路由、Agent Runtime 主流程、金融合规边界、memory/factuality 规则、外部依赖或运行期 trace 数据：

- `agent/trace.py` 增强 `summarize_trace(trace)`，新增 repair、claim binding、unsupported/conflict claim、memory patch 和 Wiki 治理摘要字段。
- `agent/trace.py` 新增纯函数 `compare_traces(left, right)`，只返回结构化 `differences` / `matches`，不写文件、不改 API 路由。
- `schemas/api/agent_traces_response.schema.json` 覆盖新增 summary 字段。
- `schemas/runtime/agent_trace.schema.json` 小范围补充 repair 后 factuality 兼容字段。
- `scripts/verify_runtime.py` 增加 trace summary、trace diff summary 和 traces response schema 回归。
- `static/app.js` 在已有 `?debug=1` 调试台里小范围展示 claim、memory operation、Wiki status/quality 等字段。
- `static/styles.css` 只补充 debug 指标块必要样式。
- `docs/CONTRACTS.md` 和 `docs/ISSUES.md` 已同步更新。

## 2. 新增 Trace Summary 字段

- `repair_status`
- `claim_binding_count`
- `unsupported_claim_count`
- `conflicting_claim_count`
- `memory_operation_count`
- `memory_patch_confidence`
- `wiki_statuses`
- `wiki_evidence_qualities`

## 3. Trace Diff

`compare_traces(left, right)` 当前比较：

- `task_type`
- `execution_mode`
- `review_passed`
- `factuality_status`
- `factuality_coverage`
- `repair_changed`
- `repair_status`
- `memory_patch_keys`
- `memory_operation_count`
- `memory_patch_confidence`
- `claim_binding_count`
- `unsupported_claim_count`
- `conflicting_claim_count`
- `wiki_statuses`
- `wiki_evidence_qualities`

## 4. 本轮未完成内容

- 未新增 trace 导出能力。
- 未新增或修改 `/api/agent/traces` 路由。
- 未新增时间范围 UI 控件。
- 未改 Runtime 写 trace 的主流程。
- 未改 memory patch、factuality、Wiki 审核或金融合规规则。

## 5. 验收提示

应运行：

- `python -m py_compile agent/trace.py scripts/verify_runtime.py`
- `python -m json.tool schemas/api/agent_traces_response.schema.json`
- `python -m json.tool schemas/runtime/agent_trace.schema.json`
- `python scripts/verify_runtime.py`

注意：`python scripts/verify_runtime.py` 会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`；这些运行期文件不应提交。

## 6. 遗留风险

- `wiki_statuses` 和 `wiki_evidence_qualities` 只在 trace 的 `wiki_hits` 已暴露对应字段时提取；旧 trace 或无 Wiki 命中的 trace 会返回空数组。
- `memory_operation_count` 对新结构 patch 使用 `operations` 数量；对旧式扁平 patch 只能做保守估算。
- `compare_traces` 当前是本地纯函数和验证覆盖，不暴露为 API；后续若要前端直接复用后端 diff，需要单独批准路由或 API 设计。
