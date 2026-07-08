from __future__ import annotations

import json
import re
from typing import Any

from market_radar.agent import llm
from market_radar.agent.prompts import SYSTEM_PROMPT, build_reflection_prompt
from market_radar.agent.schemas import ReflectionResult


BLOCKED_TERMS = ["可以买", "必须买", "必须卖", "满仓", "梭哈", "稳赚", "一定涨", "确定上涨", "目标价", "翻倍", "无风险"]
DISCLAIMER = "以上仅作市场观察和投资知识解释，不构成买卖建议。"
EVIDENCE_MARKERS = ["情绪分", "拥挤度", "上涨", "均值", "重合", "涨停", "热榜", "热门帖", "主线", "方向", "主题", "排名"]
DISCLAIMER_MARKERS = ["不构成买卖建议", "修复说明：", "证据不足", "待验证", "继续观察"]
GUIDANCE_MARKERS = ["重点看", "下一步", "继续跟踪", "如果你关注", "可以理解为", "先按", "说明后续更要观察"]


def review(
    content: str,
    *,
    plan: Any | None = None,
    evidence: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
    wiki_hits: list[dict[str, Any]] | None = None,
) -> ReflectionResult:
    blocked = [term for term in BLOCKED_TERMS if term in content]
    layers = [
        {
            "name": "hard_rules",
            "mode": "rules",
            "passed": not blocked,
            "blocked_terms": blocked,
        }
    ]
    if blocked:
        return ReflectionResult(
            passed=False,
            compliance="failed",
            blocked_terms=blocked,
            repair_suggestions=["将买卖建议转写为观察维度", "补充风险提示和免责声明"],
            issues=[f"blocked_term:{term}" for term in blocked],
            layers=layers,
        )

    factuality = _rule_factuality_review(
        content,
        evidence=evidence or [],
        tool_results=tool_results or [],
        wiki_hits=wiki_hits or [],
    )
    layers.append(
        {
            "name": "factuality_rules",
            "mode": "rules",
            "passed": factuality["status"] == "supported",
            "factuality": factuality,
        }
    )
    if factuality["status"] != "supported":
        issues = [
            *[f"unsupported_claim:{item}" for item in factuality["unsupported_claims"]],
            *[f"conflicting_claim:{item}" for item in factuality["conflicting_claims"]],
        ]
        suggestions = _factuality_repair_suggestions(factuality)
        return ReflectionResult(
            passed=False,
            factuality=factuality,
            compliance="passed",
            clarity="passed",
            repair_suggestions=suggestions,
            issues=issues,
            layers=layers,
        )

    llm_layer = _llm_review(content, plan=plan, evidence=evidence or [], tool_results=tool_results or [], wiki_hits=wiki_hits or [])
    layers.append(llm_layer)
    if llm_layer["mode"] == "llm" and not llm_layer["passed"]:
        issues = [str(item) for item in llm_layer.get("issues") or []]
        suggestions = [str(item) for item in llm_layer.get("repair_suggestions") or []]
        llm_factuality = _merge_llm_factuality(factuality, llm_layer.get("factuality"))
        return ReflectionResult(
            passed=False,
            factuality=llm_factuality,
            compliance="failed" if _has_issue(issues, ["买卖", "目标价", "收益", "越界", "compliance"]) else "passed",
            clarity="failed" if _has_issue(issues, ["小白", "清晰", "clarity"]) else "passed",
            repair_suggestions=suggestions or ["根据 LLM 审查意见补充证据、风险或边界提示"],
            issues=issues,
            layers=layers,
        )

    if llm_layer["mode"] == "llm":
        factuality = _merge_llm_factuality(factuality, llm_layer.get("factuality"))

    return ReflectionResult(passed=True, factuality=factuality, layers=layers)


def _llm_review(
    content: str,
    *,
    plan: Any | None,
    evidence: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    wiki_hits: list[dict[str, Any]],
) -> dict[str, Any]:
    layer: dict[str, Any] = {
        "name": "llm_reflection",
        "mode": "skipped",
        "passed": True,
        "provider": None,
        "model": None,
        "issues": [],
        "repair_suggestions": [],
        "factuality": None,
        "fallback_reason": None,
        "error": None,
        "usage": {},
    }
    try:
        config = llm.get_config()
    except Exception as exc:
        layer["mode"] = "llm_fallback"
        layer["fallback_reason"] = "config_error"
        layer["error"] = str(exc)[:500]
        return layer
    if config is None:
        layer["fallback_reason"] = "llm_not_configured"
        return layer

    layer["provider"] = config.provider
    layer["model"] = config.model
    try:
        prompt = build_reflection_prompt(
            plan=plan or {},
            evidence=[
                *evidence,
                {"type": "tool_results", "summary": tool_results},
                {"type": "wiki_hits", "summary": wiki_hits},
            ],
            content=content,
        )
        result = llm.complete_chat(SYSTEM_PROMPT, prompt, config=config)
        if result is None or not result.content.strip():
            layer["mode"] = "llm_fallback"
            layer["fallback_reason"] = "empty_response"
            return layer
        payload = _parse_json_object(result.content)
    except Exception as exc:
        layer["mode"] = "llm_fallback"
        layer["fallback_reason"] = "llm_error"
        layer["error"] = str(exc)[:500]
        return layer

    layer["mode"] = "llm"
    layer["provider"] = result.provider
    layer["model"] = result.model
    layer["usage"] = result.usage
    layer["passed"] = bool(payload.get("passed"))
    layer["issues"] = _as_string_list(payload.get("issues"))
    layer["repair_suggestions"] = _as_string_list(payload.get("repair_suggestions"))
    layer["factuality"] = payload.get("factuality") if isinstance(payload.get("factuality"), dict) else None
    return layer


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("LLM reflection did not return a JSON object.")
    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("LLM reflection JSON is not an object.")
    return payload


def _as_string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _has_issue(issues: list[str], needles: list[str]) -> bool:
    text = " ".join(issues).lower()
    return any(needle.lower() in text for needle in needles)


def repair(
    content: str,
    review: ReflectionResult | None = None,
    *,
    plan: Any | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    repaired = content
    replacements_applied = []
    replacements = {
        "可以买": "可以继续观察",
        "必须买": "需要谨慎观察",
        "必须卖": "需要重新评估风险",
        "满仓": "提高仓位前应先评估风险",
        "梭哈": "集中暴露风险较高",
        "稳赚": "不存在确定收益",
        "一定涨": "存在多种走势可能",
        "确定上涨": "并不具备确定性",
        "目标价": "观察区间",
        "翻倍": "大幅波动",
        "无风险": "风险较低但并非无风险",
    }
    for source, target in replacements.items():
        if source in repaired:
            repaired = repaired.replace(source, target)
            replacements_applied.append({"source": source, "target": target})
    if DISCLAIMER not in repaired:
        repaired = f"{repaired}\n\n{DISCLAIMER}"

    issues = list((review.issues if review else []) or [])
    suggestions = list((review.repair_suggestions if review else []) or [])
    factuality = dict((review.factuality if review else {}) or {})
    repaired = _apply_factuality_repair(repaired, factuality)
    if suggestions and _needs_structured_footer(repaired):
        repaired = (
            f"{repaired}\n\n"
            "修复说明：已将原回答中的结论性表达转为观察框架，并保留风险边界。"
        )
    return {
        "mode": "structured_rules",
        "pre_repair_content": content,
        "post_repair_content": repaired,
        "changed": repaired != content,
        "issues": issues,
        "repair_suggestions": suggestions,
        "replacements": replacements_applied,
        "factuality_before": factuality,
        "plan_task_type": getattr(plan, "task_type", None),
        "evidence_count": len(evidence or []),
    }


def _needs_structured_footer(content: str) -> bool:
    return "修复说明：" not in content


def _rule_factuality_review(
    content: str,
    *,
    evidence: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    wiki_hits: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence_count = len(evidence) + len([item for item in tool_results if item.get("ok")]) + len(wiki_hits)
    facts = _canonical_facts(tool_results, evidence, wiki_hits)
    checked_claims = 0
    supported_claims = 0
    unsupported_claims: list[str] = []
    conflicting_claims: list[str] = []

    for sentence in _split_sentences(content):
        if _skip_factuality_sentence(sentence):
            continue
        analysis = _analyze_sentence(sentence, facts)
        if analysis is None:
            continue
        checked_claims += 1
        if analysis["status"] == "supported":
            supported_claims += 1
        elif analysis["status"] == "insufficient_evidence":
            unsupported_claims.append(sentence)
        elif analysis["status"] == "evidence_conflict":
            conflicting_claims.append(sentence)

    if conflicting_claims:
        status = "evidence_conflict"
        summary = "部分回复与当前工具结果或证据摘要不一致。"
    elif evidence_count == 0 or unsupported_claims:
        status = "insufficient_evidence"
        summary = "部分回复缺少足够证据支撑，需要改写成待验证观察。"
    else:
        status = "supported"
        summary = "回复中的关键事实已被当前证据覆盖。"

    if checked_claims == 0:
        coverage = "unknown"
    elif checked_claims == supported_claims:
        coverage = "high"
    elif supported_claims > 0:
        coverage = "medium"
    else:
        coverage = "low"

    return {
        "status": status,
        "summary": summary,
        "checked_claims": checked_claims,
        "supported_claims": supported_claims,
        "unsupported_claims": unsupported_claims,
        "conflicting_claims": conflicting_claims,
        "evidence_count": evidence_count,
        "coverage": coverage,
    }


def _canonical_facts(
    tool_results: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    wiki_hits: list[dict[str, Any]],
) -> dict[str, Any]:
    market_signals = _tool_data(tool_results, "get_market_signals") or {}
    theme_signals = _tool_data(tool_results, "get_theme_signals") or {}
    tool_payloads = [item.get("data") for item in tool_results if item.get("ok")]
    text_corpus = "\n".join(
        [
            *[str(item.get("title") or "") for item in evidence],
            *[str(item.get("summary") or "") for item in evidence],
            *[str(item.get("title") or "") for item in wiki_hits],
            *[str(item.get("section_title") or "") for item in wiki_hits],
            *[json.dumps(item, ensure_ascii=False) for item in tool_payloads],
            json.dumps(market_signals, ensure_ascii=False),
            json.dumps(theme_signals, ensure_ascii=False),
        ]
    )
    known_numbers = set(re.findall(r"\d+(?:\.\d+)?", text_corpus))
    known_terms = {
        *[str(item.get("title") or "") for item in evidence if item.get("title")],
        *[str(item.get("name") or "") for item in market_signals.get("themes", []) if item.get("name")],
        *[str(item) for item in theme_signals.get("stocks", []) if item],
        *[str(item.get("title") or "") for item in wiki_hits if item.get("title")],
    }
    for item in tool_payloads:
        known_terms.update(_extract_terms(item))
    return {
        "market_signals": market_signals,
        "known_numbers": {item for item in known_numbers if item},
        "known_terms": {item for item in known_terms if item},
    }


def _analyze_sentence(sentence: str, facts: dict[str, Any]) -> dict[str, str] | None:
    market = facts.get("market_signals") or {}
    if "情绪分" in sentence:
        expected = market.get("sentiment_score")
        if expected is not None:
            return {"status": "supported" if str(int(expected)) in sentence else "evidence_conflict"}
    if "拥挤度" in sentence:
        expected = market.get("crowding")
        if expected:
            return {"status": "supported" if str(expected) in sentence else "evidence_conflict"}
    if "个上涨" in sentence:
        expected = market.get("positive_count")
        if expected is not None:
            return {"status": "supported" if str(expected) in sentence else "evidence_conflict"}

    numbers = re.findall(r"\d+(?:\.\d+)?", sentence)
    known_numbers = facts.get("known_numbers") or set()
    if numbers:
        return {"status": "supported" if any(number in known_numbers for number in numbers) else "insufficient_evidence"}

    known_terms = facts.get("known_terms") or set()
    if any(term and term in sentence for term in known_terms):
        return {"status": "supported"}

    if any(marker in sentence for marker in EVIDENCE_MARKERS):
        return {"status": "insufficient_evidence"}
    return None


def _skip_factuality_sentence(sentence: str) -> bool:
    return not sentence or any(marker in sentence for marker in DISCLAIMER_MARKERS + GUIDANCE_MARKERS)


def _split_sentences(content: str) -> list[str]:
    raw_parts = re.split(r"[。！？\n]+", content)
    return [item.strip(" -:：；;，,") for item in raw_parts if item.strip()]


def _tool_data(tool_results: list[dict[str, Any]], name: str) -> Any:
    for result in tool_results:
        if result.get("name") == name and result.get("ok"):
            return result.get("data")
    return None


def _extract_terms(value: Any) -> set[str]:
    terms: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            terms.update(_extract_terms(item))
    elif isinstance(value, list):
        for item in value:
            terms.update(_extract_terms(item))
    elif isinstance(value, str) and value.strip():
        terms.add(value.strip())
    return terms


def _factuality_repair_suggestions(factuality: dict[str, Any]) -> list[str]:
    if factuality.get("status") == "evidence_conflict":
        return ["删除与工具结果冲突的表述，并明确以当前证据为准", "将冲突结论改写为待验证观察"]
    return ["删除缺少证据支撑的表述", "把无证据结论改写成保守观察框架"]


def _apply_factuality_repair(content: str, factuality: dict[str, Any]) -> str:
    status = factuality.get("status")
    if status not in ("insufficient_evidence", "evidence_conflict"):
        return content
    repaired = content
    for sentence in factuality.get("unsupported_claims") or []:
        repaired = repaired.replace(sentence, "这部分判断目前证据不足，先保留为待验证观察")
    for sentence in factuality.get("conflicting_claims") or []:
        repaired = repaired.replace(sentence, "这部分表述与当前证据不一致，应以最新工具结果为准并继续观察")
    factuality_note = (
        "事实边界：当前回答已移除证据不足或与工具结果冲突的表述，其余内容仅保留有依据的观察。"
    )
    if factuality_note not in repaired:
        repaired = f"{repaired}\n\n{factuality_note}"
    return repaired


def _merge_llm_factuality(rule_factuality: dict[str, Any], llm_factuality: Any) -> dict[str, Any]:
    if not isinstance(llm_factuality, dict):
        return rule_factuality
    merged = dict(rule_factuality)
    merged["llm_status"] = llm_factuality.get("status")
    merged["llm_summary"] = str(llm_factuality.get("summary") or "")
    merged["llm_coverage"] = str(llm_factuality.get("coverage") or "")
    merged["unsupported_claims"] = _merge_strings(merged.get("unsupported_claims"), llm_factuality.get("unsupported_claims"))
    merged["conflicting_claims"] = _merge_strings(merged.get("conflicting_claims"), llm_factuality.get("conflicting_claims"))
    if merged["conflicting_claims"]:
        merged["status"] = "evidence_conflict"
    elif merged["unsupported_claims"] and merged.get("status") == "supported":
        merged["status"] = "insufficient_evidence"
    return merged


def _merge_strings(left: Any, right: Any) -> list[str]:
    merged = []
    for item in _as_string_list(left) + _as_string_list(right):
        if item not in merged:
            merged.append(item)
    return merged
