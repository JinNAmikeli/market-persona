from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from market_radar.agent import executor, planner, reflector
from market_radar.agent.memory import apply_patch, load_memory
from market_radar.agent.schemas import AgentRequest, AgentResponse
from market_radar.agent.tools import run_tools, tool_data
from market_radar.agent.trace import append_trace, make_trace_id
from market_radar.agent.wiki import search_wiki
from market_radar.market.data_store import read_history, read_latest
from market_radar.market.signals import derive_market


def run_agent_turn(payload: dict[str, Any]) -> dict[str, Any]:
    request = AgentRequest(
        user_id=payload.get("user_id") or "local",
        message=(payload.get("message") or "").strip(),
        mode=payload.get("mode") or "passive",
        context=payload.get("context") or {},
    )
    trace_id = make_trace_id(request.user_id)
    memory = load_memory(request.user_id)
    radar = read_latest()
    history = read_history(limit=20)
    plan = planner.plan(request)
    signals = derive_market(radar)
    watchlist = request.context.get("watchlist") or memory.get("watchlist") or []
    tool_context = {
        "request": request,
        "radar": radar,
        "history": history,
        "signals": signals,
        "memory": memory,
        "watchlist": watchlist,
    }
    tool_results = run_tools(plan.required_tools, tool_context)
    watch_rows = tool_data(tool_results, "get_watchlist_status", [])
    wiki_hits = search_wiki(plan.knowledge_queries, top_k=5)

    content, evidence, risk_flags, next_watch, memory_patch, execution = executor.generate(
        request.message,
        plan,
        memory,
        radar,
        history,
        signals,
        watch_rows,
        wiki_hits,
        tool_results,
    )
    draft = {
        "task_type": plan.task_type,
        "content": content,
        "evidence": evidence,
        "risk_flags": risk_flags,
        "next_watch": next_watch,
        "execution": execution,
    }
    review = reflector.review(
        content,
        plan=plan,
        evidence=evidence,
        tool_results=tool_results,
        wiki_hits=wiki_hits,
    )
    repair_result: dict[str, Any] = {
        "mode": "none",
        "changed": False,
        "pre_repair_content": None,
        "post_repair_content": None,
        "issues": [],
        "repair_suggestions": [],
        "replacements": [],
    }
    if not review.passed:
        repair_result = reflector.repair(content, review, plan=plan, evidence=evidence)
        content = repair_result["post_repair_content"]
        review = reflector.review(
            content,
            plan=plan,
            evidence=evidence,
            tool_results=tool_results,
            wiki_hits=wiki_hits,
        )

    updated_memory = apply_patch(request.user_id, memory_patch)
    response = AgentResponse(
        trace_id=trace_id,
        task_type=plan.task_type,
        content=content,
        evidence=evidence,
        risk_flags=risk_flags,
        next_watch=next_watch,
        review=review,
        execution=execution,
        repair=repair_result,
    )
    trace = {
        "trace_id": trace_id,
        "created_at": datetime.now().isoformat(timespec="microseconds"),
        "request": asdict(request),
        "state_summary": {
            "generated_at": radar.get("generated_at"),
            "history_count": len(history),
            "memory": {
                "watchlist": memory.get("watchlist", []),
                "focus_themes": memory.get("focus_themes", []),
                "knowledge_level": memory.get("knowledge_level"),
            },
        },
        "plan": asdict(plan),
        "tool_results": tool_results,
        "wiki_hits": wiki_hits,
        "execution": execution,
        "draft": draft,
        "repair": repair_result,
        "review": asdict(review),
        "memory_patch": memory_patch,
        "updated_memory": updated_memory,
        "final_response": {
            "task_type": response.task_type,
            "content": response.content,
            "evidence": response.evidence,
            "risk_flags": response.risk_flags,
            "next_watch": response.next_watch,
            "execution": response.execution,
            "repair": response.repair,
        },
    }
    append_trace(trace)
    result = asdict(response)
    result["review"] = asdict(response.review)
    return result


def run_agent_briefing(payload: dict[str, Any]) -> dict[str, Any]:
    briefing_type = payload.get("briefing_type") or "close"
    style = payload.get("style") or "plain_beginner"
    message_by_type = {
        "open": "生成一段早盘观察脚本",
        "midday": "生成一段午盘更新脚本",
        "close": "生成一段收盘复盘脚本",
        "weekly": "生成一段周末主题复盘脚本",
    }
    response = run_agent_turn(
        {
            "user_id": payload.get("user_id") or "local",
            "mode": "activate",
            "message": message_by_type.get(briefing_type, "生成一段市场复盘脚本"),
            "context": {
                **(payload.get("context") or {}),
                "briefing_type": briefing_type,
                "style": style,
            },
        }
    )
    sections = _briefing_sections(response["content"])
    return {
        "trace_id": response["trace_id"],
        "title": _briefing_title(briefing_type),
        "briefing_type": briefing_type,
        "style": style,
        "script": response["content"],
        "sections": sections,
        "evidence": response["evidence"],
        "risk_flags": response["risk_flags"],
        "next_watch": response["next_watch"],
        "review": response["review"],
    }


def _briefing_title(briefing_type: str) -> str:
    return {
        "open": "早盘市场观察",
        "midday": "午盘市场更新",
        "close": "收盘市场复盘",
        "weekly": "周末主题复盘",
    }.get(briefing_type, "市场复盘")


def _briefing_sections(content: str) -> list[dict[str, str]]:
    paragraphs = [item.strip() for item in content.split("\n\n") if item.strip()]
    titles = ["市场状态", "主线", "风险", "下一步观察", "边界"]
    return [
        {
            "title": titles[index] if index < len(titles) else f"段落 {index + 1}",
            "content": paragraph,
        }
        for index, paragraph in enumerate(paragraphs)
    ]
