from __future__ import annotations

from typing import Any


THEME_RULES = [
    {
        "name": "AI硬件/光通信",
        "words": ["中际旭创", "新易盛", "天孚通信", "亨通光电", "中天科技", "长飞光纤", "光通信", "光模块", "CPO", "NPO", "算力", "Token", "AI"],
    },
    {
        "name": "PCB/电子材料",
        "words": ["胜宏科技", "沪电股份", "东山精密", "生益科技", "宏和科", "沃格光电", "国瓷材料", "风华高科", "MLCC", "电容", "电子材料", "玻纤"],
    },
    {
        "name": "锂矿/新能源",
        "words": ["赣锋锂业", "盛新锂能", "天齐锂业", "比亚迪", "宁德时代", "锂", "锂电池", "新能源"],
    },
    {
        "name": "半导体/存储",
        "words": ["兆易创新", "美光科技", "TCL中环", "半导体", "存储", "硅片", "芯片"],
    },
    {
        "name": "消费白马",
        "words": ["五粮液", "贵州茅台", "伊利", "白酒", "消费", "蓝筹", "分红"],
    },
    {
        "name": "资源/周期",
        "words": ["中国石油", "紫金矿业", "黄金", "铜", "油气", "原油", "集运", "煤炭"],
    },
]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def classify_text(text: str) -> str:
    source = str(text or "").lower()
    for rule in THEME_RULES:
        if any(word.lower() in source for word in rule["words"]):
            return rule["name"]
    return "其他"


def all_hot_stocks(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [*(data.get("hot_popularity") or []), *(data.get("hot_watchlist") or [])]


def unique_by_symbol(stocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for stock in stocks:
        symbol = stock.get("symbol") or stock.get("name")
        if symbol and symbol not in seen:
            seen[str(symbol)] = stock
    return list(seen.values())


def get_theme_stats(data: dict[str, Any]) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}

    def bump(name: str, stock: str | None = None, post: bool = False) -> None:
        if name not in stats:
            stats[name] = {"name": name, "score": 0, "stocks": set(), "posts": 0}
        item = stats[name]
        item["score"] += 1
        if stock:
            item["stocks"].add(stock)
        if post:
            item["posts"] += 1

    for stock in all_hot_stocks(data):
        theme = classify_text(f"{stock.get('name', '')} {stock.get('symbol', '')}")
        bump(theme, stock.get("name"))

    for post in data.get("hot_posts") or []:
        theme = classify_text(f"{post.get('title', '')} {post.get('text', '')}")
        bump(theme, post=True)

    result = []
    for item in stats.values():
        if item["name"] == "其他":
            continue
        result.append({**item, "stocks": sorted(item["stocks"])})
    return sorted(result, key=lambda item: item["score"], reverse=True)


def derive_market(data: dict[str, Any]) -> dict[str, Any]:
    indices = data.get("indices") or []
    by_label = {item.get("label") or item.get("name"): item for item in indices}

    def avg(labels: list[str]) -> float:
        values = []
        for label in labels:
            value = by_label.get(label, {}).get("percent")
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
        return sum(values) / len(values) if values else 0.0

    growth_avg = avg(["深证成指", "创业板指", "科创50"])
    broad_avg = avg(["上证指数", "沪深300", "中证500"])
    positive_count = sum(1 for item in indices if float(item.get("percent") or 0) > 0)
    avg_pct = sum(float(item.get("percent") or 0) for item in indices) / max(len(indices), 1)
    popularity_symbols = {item.get("symbol") for item in data.get("hot_popularity") or []}
    duplicate_count = sum(
        1 for item in data.get("hot_watchlist") or [] if item.get("symbol") in popularity_symbols
    )
    limit_like_count = sum(
        1 for item in unique_by_symbol(all_hot_stocks(data)) if float(item.get("percent") or 0) >= 9.8
    )
    themes = get_theme_stats(data)

    tone = "结构分化"
    if positive_count == len(indices) and growth_avg > broad_avg + 1:
        tone = "成长进攻"
    elif positive_count == len(indices) and broad_avg >= growth_avg:
        tone = "权重修复"
    elif positive_count >= 4 and avg_pct > 0:
        tone = "震荡偏强"
    elif positive_count <= 2:
        tone = "风险降温"

    sentiment_score = int(
        clamp(
            round(positive_count * 9 + avg_pct * 10 + limit_like_count * 3 + duplicate_count * 1.5),
            0,
            100,
        )
    )
    crowding = "高" if duplicate_count >= 16 else "中" if duplicate_count >= 10 else "低"
    return {
        "tone": tone,
        "growth_avg": growth_avg,
        "broad_avg": broad_avg,
        "positive_count": positive_count,
        "avg_pct": avg_pct,
        "duplicate_count": duplicate_count,
        "limit_like_count": limit_like_count,
        "sentiment_score": sentiment_score,
        "crowding": crowding,
        "themes": themes,
    }


def watchlist_status(data: dict[str, Any], watchlist: list[str]) -> list[dict[str, Any]]:
    stocks = unique_by_symbol(all_hot_stocks(data))
    posts = data.get("hot_posts") or []
    rows = []
    for term in watchlist:
        query = term.lower()
        stock = next(
            (item for item in stocks if query in f"{item.get('name', '')} {item.get('symbol', '')}".lower()),
            None,
        )
        mentioned_posts = [
            post for post in posts if query in f"{post.get('title', '')} {post.get('text', '')}".lower()
        ]
        rows.append(
            {
                "term": term,
                "stock": stock,
                "mentioned_posts": len(mentioned_posts),
                "theme": classify_text(
                    f"{stock.get('name', '')} {stock.get('symbol', '')}"
                    if stock
                    else f"{mentioned_posts[0].get('title', '')} {mentioned_posts[0].get('text', '')}"
                    if mentioned_posts
                    else term
                ),
            }
        )
    return rows
