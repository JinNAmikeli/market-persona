from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPO_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from market_radar.agent.memory import load_memory, set_memory_fields
from market_radar.agent.runtime import run_agent_briefing, run_agent_turn
from market_radar.agent.wiki import search_wiki
from market_radar.market.data_store import read_latest
from market_radar.market.signals import derive_market


def check(name: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return condition


def require_keys(payload: dict[str, Any], keys: list[str]) -> bool:
    return all(key in payload for key in keys)


def main() -> int:
    failures = 0

    radar = read_latest()
    signals = derive_market(radar)
    failures += not check(
        "market signals",
        require_keys(signals, ["tone", "sentiment_score", "crowding", "themes"])
        and isinstance(signals["themes"], list),
        f"tone={signals.get('tone')} score={signals.get('sentiment_score')}",
    )

    wiki_hits = search_wiki(["AI硬件为什么热", "拥挤度"], top_k=3)
    failures += not check("wiki search", len(wiki_hits) > 0, f"hits={len(wiki_hits)}")

    overview = run_agent_turn({"user_id": "verify_script", "message": "今天市场怎么样？"})
    failures += not check(
        "chat market overview",
        overview["task_type"] == "market_overview" and overview["review"]["passed"],
        f"task={overview.get('task_type')}",
    )

    refusal = run_agent_turn({"user_id": "verify_script", "message": "AI硬件现在能买吗？"})
    failures += not check(
        "chat refusal redirect",
        refusal["task_type"] == "refusal_or_redirect"
        and refusal["review"]["passed"]
        and "不构成买卖建议" in refusal["content"],
        f"task={refusal.get('task_type')}",
    )

    set_memory_fields("verify_script", {"watchlist": ["中际旭创", "宁德时代"]})
    watchlist = run_agent_turn({"user_id": "verify_script", "message": "我的自选股怎么样？"})
    failures += not check(
        "watchlist from memory",
        watchlist["task_type"] == "watchlist_review" and "中际旭创" in watchlist["content"],
        f"task={watchlist.get('task_type')}",
    )

    memory = load_memory("verify_script")
    failures += not check(
        "memory persisted",
        memory.get("watchlist") == ["中际旭创", "宁德时代"],
        f"watchlist={memory.get('watchlist')}",
    )

    briefing = run_agent_briefing({"user_id": "verify_script", "briefing_type": "close"})
    failures += not check(
        "briefing",
        briefing["review"]["passed"] and briefing["title"] == "收盘市场复盘",
        f"title={briefing.get('title')}",
    )

    if failures:
        print(f"\n{failures} verification check(s) failed.")
        return 1

    print("\nAll verification checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
