from __future__ import annotations

from market_radar.agent.schemas import AgentPlan, AgentRequest


BUY_SELL_WORDS = ["能买吗", "可以买", "要不要买", "要不要卖", "卖吗", "目标价", "会涨吗", "满仓", "梭哈"]


def plan(request: AgentRequest) -> AgentPlan:
    message = request.message.strip()
    lower = message.lower()

    if any(word in message for word in BUY_SELL_WORDS):
        return AgentPlan(
            task_type="refusal_or_redirect",
            intent="用户请求买卖或确定性判断，转为观察维度",
            required_tools=["get_market_snapshot", "get_market_signals"],
            knowledge_queries=["风险提示", "追热点", "观察指标"],
        )
    if any(word in message for word in ["自选", "我的股票", "关注"]):
        return AgentPlan(
            task_type="watchlist_review",
            intent="检查用户自选股在热榜和热门帖中的状态",
            required_tools=["get_market_snapshot", "get_watchlist_status"],
            knowledge_queries=["自选股观察", "风险提示"],
        )
    if any(word in message for word in ["为什么", "主线", "热点", "板块", "ai", "AI", "光模块", "半导体"]):
        return AgentPlan(
            task_type="theme_explanation",
            intent="解释市场主题热度和证据",
            required_tools=["get_market_snapshot", "get_market_signals"],
            knowledge_queries=[message, "主题热度", "拥挤度"],
        )
    if any(word in message for word in ["解释", "什么意思", "什么是"]):
        return AgentPlan(
            task_type="term_explanation",
            intent="解释金融术语",
            required_tools=["get_market_signals"],
            knowledge_queries=[message],
        )
    if any(word in message for word in ["口播", "脚本", "复盘"]):
        return AgentPlan(
            task_type="briefing_script",
            intent="生成市场复盘或口播稿",
            required_tools=["get_market_snapshot", "get_market_signals"],
            knowledge_queries=["市场复盘", "风险提示"],
        )
    if any(word in message for word in ["今天", "市场", "行情", "指数", "大盘"]) or not lower:
        return AgentPlan(
            task_type="market_overview",
            intent="解释当前市场状态",
            required_tools=["get_market_snapshot", "get_market_signals"],
            knowledge_queries=["市场情绪", "结构分化", "拥挤度"],
        )
    return AgentPlan(
        task_type="market_overview",
        intent="按市场观察问题处理",
        required_tools=["get_market_snapshot", "get_market_signals"],
        knowledge_queries=[message],
    )
