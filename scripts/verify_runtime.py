from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPO_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from market_radar.agent.memory import load_memory, set_memory_fields
from market_radar.agent.llm import get_config, normalize_provider
from market_radar.agent.planner import plan
from market_radar.agent.prompts import build_execution_prompt, build_reflection_prompt
from market_radar.agent.reflector import repair, review
from market_radar.agent.runtime import run_agent_briefing, run_agent_turn
from market_radar.agent.schemas import AgentRequest
from market_radar.agent.tools import TOOL_REGISTRY, run_tools, tool_data
from market_radar.agent.trace import find_trace, read_traces, summarize_trace
from market_radar.agent.wiki import search_wiki
from market_radar.market.data_store import read_latest
from market_radar.market.signals import derive_market, get_theme_signals
from market_radar.market.watchlist import watchlist_status


def check(name: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return condition


def require_keys(payload: dict[str, Any], keys: list[str]) -> bool:
    return all(key in payload for key in keys)


def load_schema(rel_path: str) -> dict[str, Any]:
    return json.loads((REPO_ROOT / "schemas" / rel_path).read_text(encoding="utf-8"))


def schema_required_ok(payload: dict[str, Any], rel_path: str) -> tuple[bool, list[str]]:
    schema = load_schema(rel_path)
    missing = [key for key in schema.get("required", []) if key not in payload]
    return not missing, missing


def check_schema(name: str, payload: dict[str, Any], rel_path: str) -> bool:
    ok, missing = schema_required_ok(payload, rel_path)
    return check(name, ok, f"missing={missing}" if missing else "")


def load_wiki_pages() -> list[dict[str, Any]]:
    index = json.loads((REPO_ROOT / "wiki" / "index.json").read_text(encoding="utf-8"))
    pages = []
    for rel_path in index.get("pages") or []:
        pages.append(json.loads((REPO_ROOT / "wiki" / rel_path).read_text(encoding="utf-8")))
    return pages


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
    failures += not check_schema("schema market signals", signals, "market/market_signals.schema.json")

    wiki_hits = search_wiki(["AI硬件为什么热", "拥挤度"], top_k=3)
    failures += not check("wiki search", len(wiki_hits) > 0, f"hits={len(wiki_hits)}")
    wiki_pages = load_wiki_pages()
    failures += not check(
        "schema wiki pages",
        all(schema_required_ok(page, "wiki/wiki_page.schema.json")[0] for page in wiki_pages),
        f"pages={len(wiki_pages)}",
    )

    theme_signals = get_theme_signals(radar, "AI硬件/光通信")
    failures += not check(
        "theme signals",
        theme_signals["name"] == "AI硬件/光通信" and len(theme_signals["stocks"]) > 0,
        f"stocks={len(theme_signals.get('stocks') or [])}",
    )

    watch_rows = watchlist_status(radar, ["中际旭创", "宁德时代"])
    failures += not check(
        "watchlist tool",
        len(watch_rows) == 2 and watch_rows[0].get("stock"),
        f"rows={len(watch_rows)}",
    )

    tool_results = run_tools(
        ["get_market_snapshot", "get_market_signals", "get_theme_signals"],
        {"radar": radar, "history": [], "signals": signals, "watchlist": []},
    )
    failures += not check(
        "tool runner",
        len(tool_results) == 3
        and all(item.get("ok") for item in tool_results)
        and tool_data(tool_results, "get_theme_signals", {}).get("name"),
        f"registered={len(TOOL_REGISTRY)}",
    )
    failures += not check(
        "schema tool results",
        all(schema_required_ok(item, "runtime/tool_result.schema.json")[0] for item in tool_results),
        f"results={len(tool_results)}",
    )
    sample_plan = plan(AgentRequest(user_id="verify_script", message="AI硬件为什么热？"))
    execution_prompt = build_execution_prompt(
        message="AI硬件为什么热？",
        plan=sample_plan,
        memory={"watchlist": ["中际旭创"]},
        tool_results=tool_results,
        wiki_hits=wiki_hits,
    )
    reflection_prompt = build_reflection_prompt(
        plan=sample_plan,
        evidence=[{"type": "market_signal", "summary": "验证证据"}],
        content="验证回复",
    )
    failures += not check(
        "prompt builders",
        "AI硬件为什么热？" in execution_prompt
        and "工具结果" in execution_prompt
        and "待审查回复" in reflection_prompt,
    )
    failures += not check(
        "llm config optional",
        normalize_provider("a") == "anthropic" and (get_config() is None or bool(get_config().api_key)),
    )

    overview = run_agent_turn({"user_id": "verify_script", "message": "今天市场怎么样？"})
    failures += not check(
        "chat market overview",
        overview["task_type"] == "market_overview"
        and overview["review"]["passed"]
        and overview.get("execution", {}).get("mode") in ("template", "llm", "llm_fallback"),
        f"task={overview.get('task_type')} execution={overview.get('execution')}",
    )
    review_layers = overview["review"].get("layers") or []
    failures += not check(
        "reflection layers",
        [item.get("name") for item in review_layers] == ["hard_rules", "factuality_rules", "llm_reflection"]
        and review_layers[0].get("mode") == "rules"
        and review_layers[1].get("mode") == "rules"
        and review_layers[2].get("mode") in ("skipped", "llm", "llm_fallback"),
        f"layers={review_layers}",
    )
    factuality = overview["review"].get("factuality") or {}
    failures += not check(
        "factuality structure",
        factuality.get("status") == "supported"
        and "coverage" in factuality
        and isinstance(factuality.get("unsupported_claims"), list)
        and isinstance(factuality.get("conflicting_claims"), list),
        f"factuality={factuality}",
    )
    bad_review = review("这只股票可以买，目标价很明确。")
    repair_result = repair("这只股票可以买，目标价很明确。", bad_review, plan=sample_plan, evidence=[])
    failures += not check(
        "structured repair",
        bad_review.passed is False
        and repair_result["changed"]
        and repair_result["pre_repair_content"] != repair_result["post_repair_content"]
        and len(repair_result["replacements"]) >= 2
        and "可以买" not in repair_result["post_repair_content"],
        f"repair={repair_result}",
    )
    insufficient = review("这段结论会继续扩散并带来更强趋势。", evidence=[], tool_results=[], wiki_hits=[])
    failures += not check(
        "factuality insufficient",
        insufficient.passed is False and (insufficient.factuality or {}).get("status") == "insufficient_evidence",
        f"review={insufficient}",
    )
    conflicting = review(
        "当前市场情绪分 99/100，拥挤度为「低」。",
        evidence=[{"type": "market_signal", "title": "市场信号", "summary": "情绪分 49/100。"}],
        tool_results=[{"name": "get_market_signals", "ok": True, "data": {"sentiment_score": 49, "crowding": "中", "positive_count": 3, "themes": []}}],
        wiki_hits=[],
    )
    failures += not check(
        "factuality conflict",
        conflicting.passed is False and (conflicting.factuality or {}).get("status") == "evidence_conflict",
        f"review={conflicting}",
    )
    failures += not check_schema("schema chat response", overview, "api/agent_chat_response.schema.json")

    refusal = run_agent_turn({"user_id": "verify_script", "message": "AI硬件现在能买吗？"})
    failures += not check(
        "chat refusal redirect",
        refusal["task_type"] == "refusal_or_redirect"
        and refusal["review"]["passed"]
        and refusal["repair"]["mode"] == "none"
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

    trace = find_trace(briefing["trace_id"])
    failures += not check(
        "trace lookup",
        trace is not None
        and trace.get("trace_id") == briefing["trace_id"]
        and bool(trace.get("created_at"))
        and bool(trace.get("draft")),
        f"trace_id={briefing.get('trace_id')}",
    )
    if trace:
        failures += not check_schema("schema agent trace", trace, "runtime/agent_trace.schema.json")

    trace_rows = read_traces(limit=5)
    trace_summaries = [summarize_trace(item) for item in trace_rows]
    failures += not check(
        "trace list",
        len(trace_summaries) > 0
        and "task_type" in trace_summaries[0]
        and "execution_mode" in trace_summaries[0]
        and "factuality_status" in trace_summaries[0]
        and "repair_changed" in trace_summaries[0],
        f"rows={len(trace_summaries)}",
    )
    filtered_traces = read_traces(
        limit=10,
        filters={
            "task_type": "briefing_script",
            "review_passed": "true",
            "repair_changed": "false",
        },
    )
    failures += not check(
        "trace filters",
        len(filtered_traces) > 0
        and all((item.get("plan") or {}).get("task_type") == "briefing_script" for item in filtered_traces),
        f"rows={len(filtered_traces)}",
    )

    if failures:
        print(f"\n{failures} verification check(s) failed.")
        return 1

    print("\nAll verification checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
