from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from market_radar.market.data_store import append_history, write_latest


INDICES = {
    "SH000001": "上证指数",
    "SZ399001": "深证成指",
    "SZ399006": "创业板指",
    "SH000300": "沪深300",
    "SH000905": "中证500",
    "SH000688": "科创50",
}


def collect() -> dict[str, Any]:
    from agent_reach.channels.xueqiu import XueqiuChannel

    channel = XueqiuChannel()
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "agent_reach.channels.xueqiu.XueqiuChannel",
        "indices": [
            {"label": label, **channel.get_stock_quote(symbol)}
            for symbol, label in INDICES.items()
        ],
        "hot_popularity": channel.get_hot_stocks(limit=20, stock_type=10),
        "hot_watchlist": channel.get_hot_stocks(limit=20, stock_type=12),
        "hot_posts": channel.get_hot_posts(limit=20),
    }


def build_history_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    indices = payload.get("indices") or []
    hot_popularity = payload.get("hot_popularity") or []
    hot_watchlist = payload.get("hot_watchlist") or []
    popularity_symbols = {item.get("symbol") for item in hot_popularity}
    overlap = sum(1 for item in hot_watchlist if item.get("symbol") in popularity_symbols)
    limit_like = len(
        {
            item.get("symbol")
            for item in [*hot_popularity, *hot_watchlist]
            if (item.get("percent") or 0) >= 9.8
        }
    )

    return {
        "generated_at": payload.get("generated_at"),
        "indices": [
            {
                "label": item.get("label") or item.get("name"),
                "symbol": item.get("symbol"),
                "current": item.get("current"),
                "percent": item.get("percent"),
                "amount": item.get("amount"),
            }
            for item in indices
        ],
        "hot_top": [item.get("name") for item in hot_popularity[:5]],
        "watch_top": [item.get("name") for item in hot_watchlist[:5]],
        "overlap": overlap,
        "limit_like_count": limit_like,
    }


def save_payload(payload: dict[str, Any]) -> Path:
    out_path = write_latest(payload)
    append_history(build_history_snapshot(payload))
    return out_path


def collect_and_save() -> Path:
    return save_payload(collect())


def main() -> None:
    out_path = collect_and_save()
    print(json.dumps({"path": str(out_path.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
