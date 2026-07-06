# Market Harness Agent 工程架构草案

本文档把 `agent_runtime_methodology.md` 中的方法论落成 `market_radar` 的工程设计。目标是先构建一个文字版金融数字人 Agent 内核，再逐步扩展到语音、口播和数字人表现层。

## 1. 工程目标

第一阶段目标：

```text
在现有 A 股市场雷达基础上，新增一个可对话、可追踪、可校验、可记忆的 Market Harness Agent。
```

它应支持：

- 回答用户关于当前市场、主线、自选股、热门帖和风险的问题。
- 生成带证据的每日复盘和下一步观察清单。
- 维护用户关注主题、自选股、知识水平和历史观察点。
- 每轮运行留下 trace，方便调试、审计和后续优化。
- 明确拦截荐股、确定收益、目标价等越界输出。

第一阶段暂不做：

- 真实交易。
- 自动下单。
- 投资组合建议。
- 多用户权限系统。
- 复杂向量数据库。
- 数字人 3D 形象或视频生成。

## 2. 当前项目基线

当前 `market_radar` 已有：

```text
market_radar/
  server.py                 本地 HTTP 服务
  deepseek_agent.py          DeepSeek 单次复盘
  static/                    前端页面
  data/                      雷达数据副本

tools/
  xueqiu_radar_collect.py    雪球数据采集，实际写入根目录 data/

data/
  xueqiu_radar_latest.json
  xueqiu_radar_history.jsonl
```

已存在能力：

- 采集指数、雪球人气榜、关注榜、热门帖。
- 保存最新快照和历史快照。
- 前端计算主线、情绪分、拥挤度。
- 调用 DeepSeek 生成单次复盘。
- 支持本地自选股观察。

需要改造的问题：

- 根目录 `data/` 与 `market_radar/data/` 存在双数据目录。
- 主线识别逻辑在前端，Agent 后端无法复用。
- DeepSeek 调用是单次 recap，不是完整 runtime。
- 没有 chat 接口、memory、trace、wiki、reflection。

## 3. 目标目录结构

建议采用保守拆分，先保持纯 Python 标准库可运行，后续再引入 FastAPI、SQLite、向量库或任务队列。

```text
market_radar/
  server.py
  deepseek_agent.py

  agent/
    __init__.py
    runtime.py              Agent 总编排
    planner.py              任务规划
    executor.py             回复生成
    reflector.py            事实与合规校验
    memory.py               用户状态读写
    trace.py                运行轨迹记录
    schemas.py              结构化数据模型
    prompts.py              Prompt 模板

  market/
    __init__.py
    data_store.py           雷达数据与历史快照读写
    signals.py              主线、情绪、拥挤度等信号计算
    watchlist.py            自选股匹配与观察

  wiki/
    index.json              Wiki 页面索引
    themes/
      ai_hardware.json
      semiconductor.json
      lithium_energy.json
      consumer_bluechip.json
      resource_cycle.json
    risks/
      crowding.json
      chasing_hotspots.json
      data_staleness.json

  data/
    xueqiu_radar_latest.json
    xueqiu_radar_history.jsonl
    user_memory.json
    agent_traces.jsonl

  static/
    index.html
    styles.css
    app.js
```

说明：

- `agent/` 只关心一轮 Agent 如何运行。
- `market/` 只关心行情数据和市场信号。
- `wiki/` 是结构化知识资产，不直接写在 prompt 里。
- `data/` 是运行期数据，后续可迁移到 SQLite。

## 4. 数据目录统一策略

建议把实际运行数据统一到：

```text
market_radar/data/
```

同时修改：

- `market_radar/server.py` 的 `DATA_FILE` 和 `HISTORY_FILE`。
- `tools/xueqiu_radar_collect.py` 的 `DATA_DIR`。
- `README.md` 的说明。

迁移策略：

1. 优先读取 `market_radar/data/`。
2. 如果不存在，再兼容读取根目录 `data/`。
3. 下一次刷新时统一写入 `market_radar/data/`。
4. 稳定后删除兼容逻辑。

## 5. Runtime 主流程

一轮 Agent 运行建议如下：

```text
run_agent_turn(input)
  1. normalize_input
  2. load_state
  3. plan
  4. execute_tools
  5. retrieve_wiki
  6. generate_response
  7. reflect
  8. repair_if_needed
  9. update_memory
  10. write_trace
  11. return response
```

伪代码：

```python
def run_agent_turn(request: AgentRequest) -> AgentResponse:
    state = state_reader.load(request.user_id)
    plan = planner.plan(request, state)
    tool_results = tool_runner.run(plan.required_tools, state)
    wiki_hits = wiki.search(plan.knowledge_queries)
    draft = executor.generate(request, state, plan, tool_results, wiki_hits)
    review = reflector.review(draft, plan, tool_results, wiki_hits)

    if not review.passed:
        draft = executor.repair(draft, review)
        review = reflector.review(draft, plan, tool_results, wiki_hits)

    memory_patch = memory_builder.build_patch(request, plan, draft, review)
    memory_store.apply_patch(request.user_id, memory_patch)
    trace_store.append(request, state, plan, tool_results, wiki_hits, draft, review, memory_patch)

    return AgentResponse(content=draft.content, review=review, trace_id=trace.id)
```

## 6. API 设计

### `GET /api/agent/status`

沿用现有接口，增加 runtime 能力状态。

响应示例：

```json
{
  "configured": true,
  "provider": "deepseek",
  "model_env": "DEEPSEEK_MODEL",
  "default_model": "deepseek-v4-flash",
  "runtime": {
    "memory": true,
    "trace": true,
    "wiki": true,
    "reflection": true
  }
}
```

### `POST /api/agent/chat`

新增对话接口。

请求：

```json
{
  "user_id": "local",
  "message": "今天 AI 硬件为什么这么热？",
  "context": {
    "active_symbols": ["SH000001"],
    "source": "dashboard"
  }
}
```

响应：

```json
{
  "trace_id": "20260706-162930-local-001",
  "task_type": "theme_explanation",
  "content": "从当前雷达看，AI 硬件/光通信的热度主要来自...",
  "evidence": [
    {
      "type": "market_signal",
      "title": "热榜信号",
      "summary": "人气榜和关注榜中多只相关个股重复出现。"
    },
    {
      "type": "wiki_section",
      "topic_id": "theme_ai_hardware",
      "section": "热度驱动因素"
    }
  ],
  "risk_flags": ["theme_crowding", "data_staleness"],
  "next_watch": [
    "观察相关主题是否从少数个股扩散到更多标的。",
    "观察创业板指、科创50是否继续强于宽基指数。"
  ],
  "review": {
    "passed": true,
    "blocked_terms": []
  }
}
```

### `POST /api/agent/briefing`

用于主动触达或数字人口播稿。

请求：

```json
{
  "user_id": "local",
  "briefing_type": "close",
  "style": "plain_beginner"
}
```

响应：

```json
{
  "trace_id": "20260706-close-local-001",
  "title": "收盘市场观察",
  "script": "今天市场偏结构分化...",
  "sections": [
    {"title": "一句话市场状态", "content": "..."},
    {"title": "主线", "content": "..."},
    {"title": "风险", "content": "..."},
    {"title": "下一步观察", "content": "..."}
  ]
}
```

### `GET /api/agent/memory`

本地调试用，查看用户记忆。

响应示例：

```json
{
  "user_id": "local",
  "watchlist": ["中际旭创", "宁德时代"],
  "focus_themes": ["AI硬件/光通信", "半导体/存储"],
  "knowledge_level": "beginner",
  "last_next_watch": [
    "观察 AI 硬件是否继续扩散。",
    "观察人气榜和关注榜重合度是否下降。"
  ],
  "updated_at": "2026-07-06T16:29:30"
}
```

## 7. 核心数据结构

### AgentRequest

```json
{
  "user_id": "local",
  "mode": "passive",
  "message": "今天市场怎么样？",
  "trigger": null,
  "created_at": "2026-07-06T16:29:30"
}
```

### AgentPlan

```json
{
  "task_type": "market_overview",
  "intent": "解释当前市场状态",
  "required_state": ["latest_radar", "history_tail", "user_memory"],
  "required_tools": ["get_market_snapshot", "get_market_signals"],
  "knowledge_queries": ["市场情绪", "拥挤度", "结构分化"],
  "response_format": "evidence_answer",
  "forbidden_outputs": ["buy_sell_instruction", "guaranteed_return", "target_price"]
}
```

### ToolResult

```json
{
  "name": "get_market_signals",
  "ok": true,
  "data": {
    "tone": "结构分化",
    "sentiment_score": 68,
    "crowding": "中",
    "top_themes": ["AI硬件/光通信", "PCB/电子材料"]
  }
}
```

### ReflectionResult

```json
{
  "passed": true,
  "factuality": "passed",
  "compliance": "passed",
  "clarity": "passed",
  "blocked_terms": [],
  "repair_suggestions": []
}
```

### AgentTrace

```json
{
  "trace_id": "20260706-162930-local-001",
  "created_at": "2026-07-06T16:29:30",
  "request": {},
  "state_summary": {},
  "plan": {},
  "tool_results": [],
  "wiki_hits": [],
  "draft": {},
  "review": {},
  "memory_patch": {},
  "final_response": {}
}
```

## 8. Planning 规则

第一阶段可以先用规则 + LLM 兜底，不必一开始就做复杂 planner。

建议任务类型：

```text
market_overview        市场概览
theme_explanation      主题解释
stock_context          个股上下文观察
watchlist_review       自选股观察
risk_review            风险提示
term_explanation       术语解释
briefing_script        口播/复盘稿
refusal_or_redirect    越界请求转写
```

规则示例：

- 包含“今天市场、行情、指数、大盘”：`market_overview`
- 包含“为什么、主线、热点、板块”：`theme_explanation`
- 包含“自选、我的股票、关注”：`watchlist_review`
- 包含“能买吗、要不要卖、目标价、会涨吗”：`refusal_or_redirect`
- 包含“解释、什么意思、什么是”：`term_explanation`
- 包含“口播、脚本、复盘”：`briefing_script`

## 9. Tool 设计

第一阶段工具保持本地同步函数。

```text
get_market_snapshot()
  返回最新雷达数据。

get_history_tail(limit=20)
  返回最近历史快照。

get_market_signals()
  返回市场状态、情绪分、主题排序、拥挤度。

get_theme_signals(theme_name)
  返回某主题对应股票、帖子、热度证据和历史变化。

get_watchlist_status(user_id)
  返回用户自选股是否进入热榜、是否被帖子提及。

search_wiki(query, top_k=5)
  返回结构化 Wiki section。

write_memory_patch(user_id, patch)
  写回用户关注点和下一步观察清单。

write_trace(trace)
  追加 JSONL trace。
```

## 10. 市场信号层

应从 `static/app.js` 迁移到后端的逻辑：

- `THEME_RULES`
- `classifyText`
- `getThemeStats`
- `deriveMarket`
- `allHotStocks`
- `uniqueBySymbol`
- 自选股匹配逻辑

建议输出：

```json
{
  "tone": "结构分化",
  "growth_avg": 1.2,
  "broad_avg": 0.4,
  "positive_count": 4,
  "avg_pct": 0.7,
  "duplicate_count": 12,
  "limit_like_count": 3,
  "sentiment_score": 68,
  "crowding": "中",
  "themes": [
    {
      "name": "AI硬件/光通信",
      "score": 9,
      "stocks": ["中际旭创", "新易盛"],
      "posts": 3
    }
  ]
}
```

这能保证前端、复盘、聊天、口播使用同一套市场判断。

## 11. Memory 设计

第一阶段用单文件 JSON：

```text
market_radar/data/user_memory.json
```

结构：

```json
{
  "local": {
    "user_id": "local",
    "watchlist": [],
    "focus_themes": [],
    "knowledge_level": "beginner",
    "risk_preferences": {
      "needs_stronger_risk_warning": true
    },
    "last_questions": [],
    "last_next_watch": [],
    "updated_at": "2026-07-06T16:29:30"
  }
}
```

写回规则：

- 用户提到股票或主题，加入候选关注项。
- 用户多次问基础概念，降低或保持 `knowledge_level=beginner`。
- 用户追问“能买吗/会涨吗”，设置更强风险提示。
- 每次复盘后写入 `last_next_watch`。
- Memory 写回必须进入 trace。

## 12. Wiki 设计

第一阶段不需要向量库，先用 JSON 页面 + 简单关键词匹配。

Wiki 页面结构：

```json
{
  "topic_id": "theme_ai_hardware",
  "title": "AI硬件/光通信",
  "version": "2026-07-06",
  "status": "draft",
  "tags": ["AI硬件", "光通信", "光模块", "算力"],
  "applicable_tasks": ["theme_explanation", "market_overview", "briefing_script"],
  "forbidden_use": ["buy_sell_instruction", "target_price"],
  "sections": [
    {
      "section_id": "drivers",
      "title": "热度驱动因素",
      "content": "AI 硬件主题通常受算力资本开支、光模块需求、业绩预期和海外映射影响。",
      "evidence": [
        {
          "type": "internal_note",
          "source": "manual",
          "title": "主题初始说明",
          "url": null
        }
      ],
      "updated_at": "2026-07-06"
    }
  ]
}
```

搜索策略：

1. 标题命中。
2. tags 命中。
3. section 标题命中。
4. content 简单关键词命中。
5. 按命中数排序返回 TopK。

## 13. Reflection 与合规拦截

第一阶段先用规则校验 + LLM 校验可选。

硬拦截词：

```text
可以买
必须买
必须卖
满仓
梭哈
稳赚
一定涨
确定上涨
目标价
翻倍
无风险
```

如果命中，执行 repair：

```text
把买卖建议转写为观察维度。
把确定性预测转写为情景分析。
补充数据时效和风险提示。
```

标准免责声明：

```text
以上仅作市场观察和投资知识解释，不构成买卖建议。
```

## 14. 前端改造

第一阶段前端只增加一个聊天面板，不改变现有看板主结构。

新增区域：

```text
Agent 对话
  - 消息列表
  - 输入框
  - 发送按钮
  - trace_id 小字显示
  - 证据折叠区
  - 下一步观察清单
```

交互：

- 用户输入问题，调用 `/api/agent/chat`。
- 回复展示正文、证据、风险标记和下一步观察。
- 点击证据可展开来源摘要。
- 保留现有 “DeepSeek AI 复盘”，后续可合并为 briefing。

## 15. 实施顺序

建议按以下顺序实现：

1. 数据目录统一。
2. 新建 `market/signals.py`，迁移前端市场信号逻辑。
3. 新建 `agent/schemas.py`、`memory.py`、`trace.py`。
4. 新建最小 `wiki/` 和 `search_wiki`。
5. 新建 `planner.py`，实现规则版任务识别。
6. 新建 `executor.py`，复用 DeepSeek 调用生成回答。
7. 新建 `reflector.py`，实现硬规则合规校验。
8. 新建 `runtime.py`，串起完整 loop。
9. 在 `server.py` 增加 `/api/agent/chat`。
10. 前端增加聊天面板。
11. 增加 `/api/agent/briefing`，替代旧的单次 recap。

## 16. 第一版验收标准

功能验收：

- 用户能在页面提问：“今天市场怎么样？”
- 用户能问：“AI 硬件为什么热？”
- 用户能问：“我的自选股有没有进入热榜？”
- 用户问“能买吗”时，系统能拒绝买卖建议并转为观察指标。
- 每次回答都有 trace_id。
- trace 文件记录 plan、工具结果、证据和 review。
- memory 文件会更新关注主题或下一步观察点。

质量验收：

- 回答必须引用当前市场数据或 Wiki section。
- 回答必须包含风险或观察清单。
- 不出现直接买卖建议。
- 前端和 Agent 对同一市场的主线判断一致。

## 17. 未来扩展

第二阶段：

- SQLite 替代 JSON 文件。
- 多用户。
- 更完整的新闻、公告、财报数据。
- 定时任务和主动触达。
- 评估脚本和模拟用户对抗演练。

第三阶段：

- TTS 语音。
- 口播字幕。
- 数字人头像。
- 多风格复盘。
- 人工审核台。

第四阶段：

- 配置化业务模板。
- 可插拔 Wiki。
- 可视化 trace。
- 自动生成改进建议，但上线前人工确认。
