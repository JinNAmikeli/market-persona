from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from market_radar.market.data_store import DATA_DIR, ensure_data_dir


TRACE_PATH = DATA_DIR / "agent_traces.jsonl"


def make_trace_id(user_id: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return f"{stamp}-{user_id}"


def append_trace(trace: dict[str, Any]) -> None:
    ensure_data_dir()
    with TRACE_PATH.open("a", encoding="utf-8") as trace_file:
        trace_file.write(json.dumps(trace, ensure_ascii=False))
        trace_file.write("\n")


def read_traces(limit: int = 20, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if not TRACE_PATH.exists():
        return []
    rows = []
    for line in TRACE_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            trace = json.loads(line)
        except json.JSONDecodeError:
            continue
        if _matches_filters(trace, filters or {}):
            rows.append(trace)
    return rows[-max(1, min(limit, 200)) :][::-1]


def find_trace(trace_id: str) -> dict[str, Any] | None:
    if not trace_id or not TRACE_PATH.exists():
        return None
    for line in reversed(TRACE_PATH.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            trace = json.loads(line)
        except json.JSONDecodeError:
            continue
        if trace.get("trace_id") == trace_id:
            return trace
    return None


def summarize_trace(trace: dict[str, Any]) -> dict[str, Any]:
    request = trace.get("request") or {}
    plan = trace.get("plan") or {}
    review = trace.get("review") or {}
    response = trace.get("final_response") or {}
    execution = trace.get("execution") or response.get("execution") or {}
    repair = trace.get("repair") or response.get("repair") or {}
    factuality = review.get("factuality") or {}
    if isinstance(factuality, str):
        factuality = {"status": factuality}
    return {
        "trace_id": trace.get("trace_id"),
        "created_at": trace.get("created_at"),
        "user_id": request.get("user_id"),
        "message": request.get("message"),
        "mode": request.get("mode"),
        "task_type": plan.get("task_type") or response.get("task_type"),
        "execution_mode": execution.get("mode"),
        "llm_provider": execution.get("provider"),
        "llm_model": execution.get("model"),
        "factuality_status": factuality.get("status"),
        "factuality_coverage": factuality.get("coverage"),
        "repair_mode": repair.get("mode"),
        "repair_changed": repair.get("changed"),
        "review_passed": review.get("passed"),
        "evidence_count": len(response.get("evidence") or []),
        "risk_flags": response.get("risk_flags") or [],
        "memory_patch_keys": sorted((trace.get("memory_patch") or {}).keys()),
        "generated_at": (trace.get("state_summary") or {}).get("generated_at"),
    }


def _matches_filters(trace: dict[str, Any], filters: dict[str, Any]) -> bool:
    summary = summarize_trace(trace)
    query = str(filters.get("query") or "").strip().lower()
    if query:
        haystack = " ".join(
            [
                str(summary.get("trace_id") or ""),
                str(summary.get("message") or ""),
                str(summary.get("task_type") or ""),
                str(summary.get("execution_mode") or ""),
                str(summary.get("user_id") or ""),
            ]
        ).lower()
        if query not in haystack:
            return False

    if filters.get("task_type") and summary.get("task_type") != filters["task_type"]:
        return False
    if filters.get("execution_mode") and summary.get("execution_mode") != filters["execution_mode"]:
        return False

    review_passed = _parse_bool(filters.get("review_passed"))
    if review_passed is not None and summary.get("review_passed") is not review_passed:
        return False

    repair_changed = _parse_bool(filters.get("repair_changed"))
    if repair_changed is not None and summary.get("repair_changed") is not repair_changed:
        return False

    created_at = _parse_trace_datetime(summary.get("created_at"))
    if created_at is None:
        return False
    date_from = _parse_filter_datetime(filters.get("date_from"), is_end=False)
    if date_from and created_at < date_from:
        return False
    date_to = _parse_filter_datetime(filters.get("date_to"), is_end=True)
    if date_to and created_at > date_to:
        return False
    return True


def _parse_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    normalized = str(value).strip().lower()
    if normalized in ("1", "true", "yes", "y", "passed", "changed"):
        return True
    if normalized in ("0", "false", "no", "n", "failed", "unchanged"):
        return False
    return None


def _parse_trace_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _parse_filter_datetime(value: Any, *, is_end: bool) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        if len(raw) == 10:
            date_value = datetime.strptime(raw, "%Y-%m-%d")
            if is_end:
                return date_value + timedelta(days=1) - timedelta(microseconds=1)
            return date_value
        return datetime.fromisoformat(raw)
    except ValueError:
        return None
