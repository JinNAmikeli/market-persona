# Handoff

更新时间：2026-07-08
当前版本：Market Harness Agent v0.1
本轮任务：ISSUE-003 Factuality Evidence Binding

## 1. 本轮完成内容

本轮只完成 factuality evidence binding，未改 UI、路由、合规边界、Wiki 内容或外部依赖：

- 增强 `agent/reflector.py` 的规则 factuality 检查，将重要判断绑定到 market signal、history 或 wiki evidence。
- `review.factuality.coverage` 改为三档：`supported`、`partial`、`insufficient`。
- `review.factuality` 新增兼容扩展字段：
  - `claim_bindings`：逐条记录被检查的重要判断、判断类型、状态、证据引用和原因。
  - `coverage_summary`：解释已绑定判断数量。
  - `required_evidence_types`：说明本轮 factuality 认可的证据类型。
- `market_overview`、`theme_explanation`、`briefing_script` 至少检查核心市场判断，例如市场 tone、上涨数量、情绪分、拥挤度、主题集中度、主题热度证据。
- 缺证据强判断进入 `insufficient_evidence`；与工具结果冲突的情绪分、拥挤度等进入 `evidence_conflict`，再由现有 repair 流程处理。
- `agent/executor.py` 仅补充 evidence 结构，为 market、history、wiki、theme evidence 增加 `id`、`source`、`fields`，供 factuality 绑定引用。
- 小范围补齐 schema 中 factuality/evidence binding 相关字段定义，保持新增字段兼容、不破坏原 required 字段。
- 更新 `scripts/verify_runtime.py`，覆盖：
  - 有证据的市场概览通过。
  - 主题解释和 briefing 的核心判断有 evidence binding。
  - 无证据强判断失败。
  - 与 tool_results 冲突的情绪分/拥挤度失败。
- 在 `docs/ISSUES.md` 标记 ISSUE-003 完成。

## 2. 本轮未完成内容

按任务要求，本轮没有处理其他 Issue：

- 未修改 UI。
- 未修改 `server.py` 路由。
- 未新增外部依赖。
- 未修改金融合规边界。
- 未扩写 Wiki 内容。
- 未大改 LLM Reflection。
- 未做数字人表现层、TTS、定时任务。

## 3. 业务代码状态

本轮修改范围限制在用户允许文件：

- `agent/reflector.py`
- `agent/executor.py`
- `schemas/api/agent_chat_response.schema.json`
- `schemas/api/agent_briefing_response.schema.json`
- `schemas/runtime/agent_trace.schema.json`
- `scripts/verify_runtime.py`
- `docs/ISSUES.md`
- `docs/HANDOFF.md`

开始任务前工作区已有非本轮变更；本轮未回滚用户已有改动。

## 4. 测试结果

已运行：

- `python -m py_compile agent/reflector.py agent/executor.py scripts/verify_runtime.py`
- `python -m json.tool schemas/api/agent_chat_response.schema.json`
- `python -m json.tool schemas/api/agent_briefing_response.schema.json`
- `python -m json.tool schemas/runtime/agent_trace.schema.json`
- `python scripts/verify_runtime.py`

结果：全部通过。

注意：`python scripts/verify_runtime.py` 会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`。运行期数据不应提交。

## 5. 遗留风险

- factuality binding 仍是规则型、轻量级判断，不是完整自然语言事实证明系统；复杂句子可能只绑定其中最先命中的核心判断。
- `claim_bindings.evidence_refs` 绑定到当前工具结果与 evidence id，适合 trace 审计；前端尚未展示这些新字段。
- schema 仅兼容性补齐新字段结构，没有把新字段设为 required，以保留旧 trace 和硬拦截默认结果兼容。

## 6. 交接注意事项

后续如果继续增强 factuality，可以单独开 Issue 处理：

- 多事实句拆分成多个 claim binding。
- 更细的 history trend 证据提取。
- 将 claim binding 展示到 debug UI。
- 将 Wiki evidence 的质量等级与审核状态纳入 factuality。
