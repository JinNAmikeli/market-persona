# Handoff

更新时间：2026-07-08
当前版本：Market Harness Agent v0.1
本轮任务：ISSUE-005 Memory Patch Builder

## 1. 本轮完成内容

本轮只完成 Memory Patch Builder，未改 UI、`server.py`、`market/collector.py`、金融合规边界、外部依赖或多用户权限：

- 在 `agent/memory.py` 新增规则型 `build_memory_patch(request, plan, draft, review, evidence)`。
- 新 memory patch 结构包含 `source`、`reason`、`confidence`、`operations`、`evidence_refs`；每条 operation 保留 `op`、`path`、`value`、`source`、`reason`、`confidence`。
- 将旧的 memory patch 生成从 `agent/executor.py` 收窄掉，改由 `agent/runtime.py` 在 review / repair 后统一调用 builder、应用 patch 并写入 trace。
- `apply_patch` 支持新结构 `operations`，并保持旧式扁平 patch 兼容。
- `focus_themes` 只在用户明确表达关注、跟踪、观察等主题意图时写入。
- `watchlist` 只在用户明确表达关注、添加、加入自选等意图时写入。
- `knowledge_level` 与 `risk_preferences` 只做规则型、低风险、带 reason 的保守更新。
- 更新 `schemas/runtime/agent_trace.schema.json`，要求 trace 中 memory_patch 保留审计字段。
- 更新 `schemas/runtime/user_memory.schema.json`，补充 `risk_preferences.needs_stronger_risk_warning` 类型。
- 更新 `scripts/verify_runtime.py`，增加 memory patch 误写防护、trace 审计字段和旧 patch 兼容回归。
- 更新 `docs/CONTRACTS.md` 和 `docs/ISSUES.md`。

## 2. 本轮未完成内容

按任务边界，本轮没有处理：

- 未使用 LLM 抽取 memory。
- 未做复杂 NLP、实体库或行情数据反查。
- 未新增外部依赖或上传 memory。
- 未引入多用户权限系统。
- 未修改 UI、`server.py`、`market/collector.py`。
- 未改变金融合规边界、拒绝策略或投资表达模板。
- 未处理 trace diff、存储迁移、主动触达等其他 Issue。

## 3. Memory Patch 新结构

新 patch 示例：

```json
{
  "version": 1,
  "source": "user_message",
  "reason": "规则型 memory builder 识别到明确、低风险的用户记忆更新意图。",
  "confidence": "high",
  "operations": [
    {
      "op": "append_unique",
      "path": "watchlist",
      "value": "中际旭创",
      "source": "user_message",
      "reason": "用户明确要求关注、添加或加入自选股。",
      "confidence": "high"
    }
  ],
  "evidence_refs": ["evidence:market_signal"]
}
```

支持的 operation 当前为 `set`、`append_unique`、`prepend_unique`。允许写入路径限制在既有 memory 白名单字段及 `risk_preferences.needs_stronger_risk_warning`、`journey_state.*` 等受控路径内。

## 4. 测试结果

已运行：

- `python -m py_compile agent/memory.py agent/runtime.py agent/executor.py scripts/verify_runtime.py`
- `python -m json.tool schemas/runtime/user_memory.schema.json`
- `python -m json.tool schemas/runtime/agent_trace.schema.json`
- `python scripts/verify_runtime.py`

结果：全部通过。

注意：`python scripts/verify_runtime.py` 会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`；这些运行期文件不应提交。

## 5. 遗留风险

- 规则型抽取是保守启发式，不覆盖所有自然语言表达；后续若扩展，应继续优先避免误写。
- 主题与股票的区分依赖关键词和明确意图，不做复杂实体识别；少数模糊表达可能只记录问题而不写入偏好。
- planner 当前仍会把含“关注”的问题归入 `watchlist_review`，本轮只收窄 memory 写入，不调整任务规划。
