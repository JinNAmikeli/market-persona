from __future__ import annotations

from typing import Any, Callable

from market_radar.market.signals import derive_market, get_theme_signals
from market_radar.market.watchlist import watchlist_status


ToolContext = dict[str, Any]
ToolResult = dict[str, Any]
ToolHandler = Callable[[ToolContext], Any]


def _market_snapshot(context: ToolContext) -> dict[str, Any]:
    radar = context["radar"]
    return {
        "generated_at": radar.get("generated_at"),
        "index_count": len(radar.get("indices") or []),
        "hot_popularity_count": len(radar.get("hot_popularity") or []),
        "hot_watchlist_count": len(radar.get("hot_watchlist") or []),
        "hot_posts_count": len(radar.get("hot_posts") or []),
    }


def _history_tail(context: ToolContext) -> list[dict[str, Any]]:
    return context.get("history") or []


def _market_signals(context: ToolContext) -> dict[str, Any]:
    return context.get("signals") or derive_market(context["radar"])


def _theme_signals(context: ToolContext) -> dict[str, Any]:
    signals = _market_signals(context)
    theme_name = context.get("theme_name") or (signals.get("themes") or [{}])[0].get("name") or ""
    return get_theme_signals(context["radar"], theme_name, context.get("history") or [])


def _watchlist_status(context: ToolContext) -> list[dict[str, Any]]:
    watchlist = context.get("watchlist") or []
    return watchlist_status(context["radar"], watchlist)


TOOL_REGISTRY: dict[str, ToolHandler] = {
    "get_market_snapshot": _market_snapshot,
    "get_history_tail": _history_tail,
    "get_market_signals": _market_signals,
    "get_theme_signals": _theme_signals,
    "get_watchlist_status": _watchlist_status,
}


def run_tools(tool_names: list[str], context: ToolContext) -> list[ToolResult]:
    results = []
    for name in tool_names:
        handler = TOOL_REGISTRY.get(name)
        if not handler:
            results.append({"name": name, "ok": False, "error": "Unknown tool"})
            continue
        try:
            results.append({"name": name, "ok": True, "data": handler(context)})
        except Exception as exc:
            results.append({"name": name, "ok": False, "error": str(exc)})
    return results


def tool_data(tool_results: list[ToolResult], name: str, default: Any = None) -> Any:
    for result in tool_results:
        if result.get("name") == name and result.get("ok"):
            return result.get("data")
    return default
