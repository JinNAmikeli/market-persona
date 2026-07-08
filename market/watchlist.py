from __future__ import annotations

from typing import Any

from market_radar.market.signals import all_hot_stocks, classify_text, unique_by_symbol


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
