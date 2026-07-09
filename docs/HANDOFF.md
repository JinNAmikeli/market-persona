# Handoff

更新时间：2026-07-09
当前版本：Market Harness Agent v0.1
本轮任务：ISSUE-007 Storage Strategy Decision

## 1. 本轮完成内容

本轮只完成 Storage Strategy Decision 决策评估，未实现任何存储迁移：

- 阅读并对照了 `docs/PROJECT_SPEC.md`、`docs/ARCHITECTURE_FREEZE.md`、`docs/AUTHORITY_MATRIX.md`、`docs/CONTRACTS.md`、`docs/AGENT_RULES.md`、`docs/ISSUES.md`、`docs/HANDOFF.md`。
- 阅读了 `market/data_store.py`、`agent/memory.py`、`agent/trace.py`、`scripts/verify_runtime.py` 和 `.gitignore`，确认当前 runtime 数据使用本地 JSON / JSONL。
- 在 `docs/ISSUES.md` 将 ISSUE-007 标记为完成，并记录四种方案比较、推荐结论、SQLite 触发条件、下一步 Issue 和遗留风险。
- 在 `docs/CONTRACTS.md` 补充 v0.1 当前存储边界：继续使用 `data/xueqiu_radar_latest.json`、`data/xueqiu_radar_history.jsonl`、`data/user_memory.json`、`data/agent_traces.jsonl`。
- 未新增 `docs/STORAGE_STRATEGY.md`，因为 `.gitignore` 默认忽略新增 `docs/*.md`，且既有治理文档足够承载本轮决策。

## 2. 决策结论

- 当前 v0.1 是本地单用户工具，继续使用 JSON / JSONL。
- 现在不迁移 SQLite。
- 当前优先补数据保留、归档、清理、导出和备份策略。
- SQLite 只作为未来触发条件满足后的候选方案。

## 3. SQLite 迁移触发条件

- `data/agent_traces.jsonl` trace 数量达到约 10,000 条，或单文件体积达到约 50 MB，并且查询或打开详情出现可感知延迟。
- `data/xueqiu_radar_history.jsonl` 需要跨日期、多条件、主题/个股维度的复杂查询。
- 项目进入多用户使用场景，需要隔离用户数据、审计不同用户行为或处理并发写入。
- memory 写入需要事务一致性，例如多个 runtime turn、手动同步和后续任务可能并发修改同一用户状态。
- JSONL 整文件读取、倒序查找或过滤明显变慢，影响 `/api/agent/traces`、调试台或验证脚本体验。
- 数据治理需求超过简单文件策略，需要可靠归档、压缩、导出、清理、恢复、校验和增量备份。

## 4. 下一步建议 Issue

- Runtime Data Retention Policy：定义 trace、memory、market history 的保留窗口、最大体积、备份频率、隐私边界和人工确认规则。
- Trace Archive and Cleanup：在保留策略批准后，设计 trace 按日期/体积分段归档、压缩、导出和清理的最小实现。
- SQLite Migration Design：仅在触发条件满足后启动；先设计 schema、迁移/回滚、兼容读取、备份恢复和验收标准，再申请用户批准。

## 5. 本轮未完成内容

- 未修改业务代码。
- 未新增 SQLite、数据库文件、迁移脚本或外部依赖。
- 未改 `market/data_store.py`、`agent/memory.py`、`agent/trace.py`、`server.py` 或 API。
- 未修改运行期 `data/` 文件。
- 未做多用户权限系统。
- 未实现数据保留、归档、清理、导出或备份工具。

## 6. 验收提示

本轮为文档决策型 Issue，无需运行 `python scripts/verify_runtime.py`。该脚本会写入 `data/user_memory.json` 和 `data/agent_traces.jsonl`，本轮明确不修改运行期 data 文件。

建议检查：

- `git diff -- docs/ISSUES.md docs/HANDOFF.md docs/CONTRACTS.md`
- `git diff --stat`

## 7. 遗留风险

- 当前 trace 查询和过滤依赖整文件读取，文件增长后会逐步变慢。
- 当前缺少明确保留和清理策略，长期运行可能积累较大的本地 trace/history 文件。
- memory 是单 JSON 文件，适合本地单用户；未来并发、多用户或事务一致性需求出现时需要重新评估。
- 归档或清理如果先于策略设计实现，可能破坏审计追溯。
