from __future__ import annotations

from typing import Any

from market_radar.agent.reflector import DISCLAIMER


def _fmt_pct(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "--"
    prefix = "+" if number > 0 else ""
    return f"{prefix}{number:.2f}%"


def _top_themes(signals: dict[str, Any], limit: int = 3) -> str:
    names = [item["name"] for item in signals.get("themes", [])[:limit]]
    return "、".join(names) if names else "暂无明确主线"


def generate(
    message: str,
    plan: Any,
    memory: dict[str, Any],
    radar: dict[str, Any],
    history: list[dict[str, Any]],
    signals: dict[str, Any],
    watchlist_rows: list[dict[str, Any]],
    wiki_hits: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], list[str], list[str], dict[str, Any]]:
    evidence = [
        {
            "type": "market_signal",
            "title": "市场信号",
            "summary": f"{len(radar.get('indices') or [])} 个指数中 {signals['positive_count']} 个上涨，情绪分 {signals['sentiment_score']}/100。",
        }
    ]
    risk_flags = []
    next_watch = [
        "观察主线是否从少数热门股扩散到更多同主题标的。",
        "观察创业板指、科创50与宽基指数的相对强弱。",
    ]
    memory_patch: dict[str, Any] = {"question": message}

    top_themes = _top_themes(signals)
    if signals.get("crowding") in ("中", "高"):
        risk_flags.append("theme_crowding")
    if history:
        evidence.append({"type": "history", "title": "历史快照", "summary": f"已读取最近 {len(history)} 条历史快照。"})
    for hit in wiki_hits[:2]:
        evidence.append(
            {
                "type": "wiki_section",
                "title": f"{hit.get('title')} / {hit.get('section_title')}",
                "summary": hit.get("content", "")[:90],
            }
        )

    if plan.task_type == "refusal_or_redirect":
        content = (
            "我不能给出买入、卖出、价格目标或确定收益判断，但可以把问题转成观察框架。\n\n"
            f"当前市场状态偏「{signals['tone']}」，情绪分 {signals['sentiment_score']}/100，"
            f"讨论较集中的方向是 {top_themes}。如果你关注某个标的，可以重点看三件事："
            "它是否进入热榜、所属主题是否继续扩散、以及高热度是否带来拥挤风险。\n\n"
            f"{DISCLAIMER}"
        )
        memory_patch["needs_stronger_risk_warning"] = True
    elif plan.task_type == "watchlist_review":
        if not watchlist_rows:
            content = (
                "我还没有读取到你的自选股。你可以先在页面的观察台里添加股票名或代码，"
                "之后我会检查它是否进入热榜、是否被热门帖提到，以及属于哪条主线。\n\n"
                f"当前市场主线集中在 {top_themes}，拥挤度为「{signals['crowding']}」。\n\n{DISCLAIMER}"
            )
        else:
            lines = []
            for row in watchlist_rows:
                stock = row.get("stock")
                if stock:
                    lines.append(
                        f"- {stock.get('name')}: 热榜排名 #{stock.get('rank')}，涨跌幅 {_fmt_pct(stock.get('percent'))}，主题 {row.get('theme')}。"
                    )
                elif row.get("mentioned_posts"):
                    lines.append(f"- {row['term']}: 未进热榜，但被 {row['mentioned_posts']} 篇热门帖提到，主题 {row.get('theme')}。")
                else:
                    lines.append(f"- {row['term']}: 当前未进入热榜，也未在热门帖中明显出现。")
            content = "你的自选股观察结果：\n\n" + "\n".join(lines) + f"\n\n{DISCLAIMER}"
    elif plan.task_type == "theme_explanation":
        theme = signals.get("themes", [{}])[0]
        evidence.append(
            {
                "type": "theme_signal",
                "title": theme.get("name", "主题信号"),
                "summary": f"信号数 {theme.get('score', 0)}，相关股票：{'、'.join(theme.get('stocks', [])[:6]) or '暂无'}。",
            }
        )
        content = (
            f"从当前雷达看，市场讨论最集中的方向是 {top_themes}。\n\n"
            f"证据上，热榜和热门帖共同给出主题信号；当前拥挤度为「{signals['crowding']}」，"
            f"人气榜和关注榜重合 {signals['duplicate_count']} 只，接近涨停的热榜股票有 {signals['limit_like_count']} 只。\n\n"
            "这说明它更像是一个需要继续跟踪的高热方向，而不是可以直接推出买卖结论的信号。"
            f"下一步重点看：{next_watch[0]}\n\n{DISCLAIMER}"
        )
        if theme.get("name"):
            memory_patch["focus_themes"] = [theme["name"]]
    elif plan.task_type == "briefing_script":
        content = (
            f"今天市场偏「{signals['tone']}」。核心指数中 {signals['positive_count']} 个上涨，"
            f"成长侧均值 {_fmt_pct(signals['growth_avg'])}，宽基侧均值 {_fmt_pct(signals['broad_avg'])}。\n\n"
            f"主线方面，当前讨论集中在 {top_themes}。情绪分 {signals['sentiment_score']}/100，"
            f"拥挤度为「{signals['crowding']}」。\n\n"
            "风险上，如果高热方向不能扩散，后续更容易从普涨转向分化。下一次刷新重点观察主题扩散和宽基跟随情况。\n\n"
            f"{DISCLAIMER}"
        )
    elif plan.task_type == "term_explanation":
        content = (
            "我先按小白视角解释：市场里的“拥挤度”，可以理解为很多人是否同时挤在同一批热门方向里。"
            f"在当前雷达里，人气榜和关注榜重合 {signals['duplicate_count']} 只，所以拥挤度被判为「{signals['crowding']}」。\n\n"
            "拥挤度高不等于马上会跌，但说明后续更要观察分化风险。\n\n"
            f"{DISCLAIMER}"
        )
    else:
        content = (
            f"当前市场偏「{signals['tone']}」。{len(radar.get('indices') or [])} 个核心指数中 "
            f"{signals['positive_count']} 个上涨；成长侧均值 {_fmt_pct(signals['growth_avg'])}，"
            f"宽基侧均值 {_fmt_pct(signals['broad_avg'])}。\n\n"
            f"主线集中在 {top_themes}，情绪分 {signals['sentiment_score']}/100，"
            f"拥挤度为「{signals['crowding']}」。\n\n"
            f"下一步观察：{next_watch[0]} {next_watch[1]}\n\n{DISCLAIMER}"
        )

    memory_patch["last_next_watch"] = next_watch
    return content, evidence, risk_flags, next_watch, memory_patch
