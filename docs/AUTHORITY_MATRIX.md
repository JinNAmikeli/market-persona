# Authority Matrix

状态：生效
版本：Market Harness Agent v0.1
更新日期：2026-07-08

## 1. 权威顺序

当文档、代码、历史说明之间出现冲突时，按以下顺序判断：

1. 用户在当前任务中的明确要求。
2. `docs/PROJECT_SPEC.md`、`docs/ARCHITECTURE_FREEZE.md`、`docs/AUTHORITY_MATRIX.md`。
3. `docs/CONTRACTS.md`、`docs/AGENT_RULES.md`、`docs/RUNBOOK.md`。
4. `README.md`。
5. `docs/agent_runtime_methodology.md`。
6. `docs/market_harness_agent_architecture.md`。
7. JSON Schema、验证脚本和现有代码行为。

如果高权威文件与低权威文件冲突，应先更新低权威文件或登记 Issue，不应静默改动业务代码。

## 2. 角色与权限

| 角色 | 可以做 | 不可以做 |
| --- | --- | --- |
| 用户 | 批准范围、变更优先级、合规边界、架构演进 | 无 |
| Governance Docs Implementer | 更新治理文档、登记 Issue、修正文档跟踪规则 | 修改业务代码、新增功能、重构 |
| Runtime Implementer | 在批准 Issue 范围内修改 agent、market、server、static、schemas、scripts | 越过冻结边界、扩大功能范围 |
| Reviewer | 检查风险、回归、契约破坏、缺失测试 | 在 review 任务中直接重构 |

## 3. 普通改动允许范围

无需额外用户批准，但必须有对应 Issue 或明确任务：

- 修正文档错字、过期说明和命名不一致。
- 补充 Runbook、合规说明、验收步骤。
- 增加非破坏性的测试或验证覆盖。
- 修复明确 bug，且不改变公开 API 契约。
- 补充 trace 字段，但保持兼容。

## 4. 需要用户批准的修改

以下修改必须先获得用户明确批准：

- 修改金融合规边界。
- 修改荐股、目标价、收益预测相关拒绝策略。
- 删除或重命名已冻结 API。
- 改变已冻结 API 的请求或响应结构。
- 迁移运行数据存储，例如 JSON 文件迁移到 SQLite。
- 引入新外部服务、云服务、数据库或长期运行进程。
- 新增真实交易、账户、下单、投资组合、仓位相关能力。
- 新增主动触达、定时任务或通知能力。
- 将本地数据、trace、memory 上传到外部系统。
- 提交或暴露 `.env`、API key、个人隐私数据。
- 大规模重构目录结构或模块职责。

## 5. 禁止修改

除非用户在同一任务中明确要求，否则禁止：

- 修改业务代码来完成治理文档任务。
- 删除用户未要求删除的文件。
- 回滚用户已有改动。
- 提交运行期私有数据。
- 用无证据输出替代现有 trace、schema 或验证流程。

## 6. 冲突处理

遇到冲突时应按以下顺序处理：

1. 停止扩大改动范围。
2. 在 `docs/ISSUES.md` 登记冲突或待决策项。
3. 在 `docs/HANDOFF.md` 说明风险和建议。
4. 需要批准时等待用户确认，不自行假设。

