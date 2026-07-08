from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from market_radar.market.data_store import DATA_DIR, ensure_data_dir


MEMORY_PATH = DATA_DIR / "user_memory.json"
LIST_FIELDS = (
    "watchlist",
    "focus_themes",
    "open_questions",
    "blockers",
    "last_questions",
    "last_next_watch",
)
PATCH_SOURCES = {"user_message", "agent_response", "review"}
PATCH_CONFIDENCE = {"low", "medium", "high"}
LIST_PATCH_PATHS = set(LIST_FIELDS)
SCALAR_PATCH_PATHS = {
    "knowledge_level",
    "next_priority",
    "journey_state.stage",
    "journey_state.active_task",
    "journey_state.updated_from_task",
    "risk_preferences.needs_stronger_risk_warning",
}
THEME_HINTS = (
    "AI",
    "ai",
    "硬件",
    "光模块",
    "光通信",
    "半导体",
    "芯片",
    "算力",
    "新能源",
    "锂电",
    "机器人",
    "板块",
    "主题",
    "方向",
    "赛道",
    "产业链",
)
WATCHLIST_INTENT_WORDS = ("自选", "我的股票", "我的持仓", "加入", "添加", "加到", "加进")
FOCUS_INTENT_WORDS = ("关注", "跟踪", "观察", "盯")
STOCK_FOLLOW_INTENT_WORDS = ("关注", "跟踪", "盯")
GENERIC_MARKET_TERMS = {"市场", "行情", "大盘", "指数", "主线", "热点", "板块", "主题", "风险", "股票", "自选股"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_memory(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "watchlist": [],
        "focus_themes": [],
        "knowledge_level": "beginner",
        "risk_preferences": {"needs_stronger_risk_warning": False},
        "journey_state": {
            "stage": "observe_market",
            "active_task": None,
            "updated_from_task": None,
        },
        "open_questions": [],
        "blockers": [],
        "next_priority": "",
        "last_questions": [],
        "last_next_watch": [],
        "updated_at": _now(),
    }


def ensure_memory_shape(memory: dict[str, Any] | None, user_id: str) -> dict[str, Any]:
    base = default_memory(user_id)
    current = memory or {}
    normalized = {
        **base,
        **current,
        "risk_preferences": {
            **base["risk_preferences"],
            **(current.get("risk_preferences") or {}),
        },
        "journey_state": {
            **base["journey_state"],
            **(current.get("journey_state") or {}),
        },
    }

    for key in LIST_FIELDS:
        value = normalized.get(key) or []
        normalized[key] = list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))

    normalized["knowledge_level"] = str(normalized.get("knowledge_level") or "beginner")
    normalized["next_priority"] = str(normalized.get("next_priority") or "").strip()
    if not normalized["next_priority"] and normalized["last_next_watch"]:
        normalized["next_priority"] = normalized["last_next_watch"][0]
    normalized["updated_at"] = str(normalized.get("updated_at") or _now())
    normalized["user_id"] = user_id
    return normalized


def memory_snapshot(memory: dict[str, Any]) -> dict[str, Any]:
    normalized = ensure_memory_shape(memory, memory.get("user_id") or "local")
    return {
        "watchlist": normalized["watchlist"],
        "focus_themes": normalized["focus_themes"],
        "knowledge_level": normalized["knowledge_level"],
        "open_questions": normalized["open_questions"],
        "blockers": normalized["blockers"],
        "next_priority": normalized["next_priority"],
        "journey_state": normalized["journey_state"],
        "risk_preferences": normalized["risk_preferences"],
    }


def build_memory_patch(
    request: Any,
    plan: Any,
    draft: dict[str, Any],
    review: Any,
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build an auditable, rule-based memory patch from one agent turn."""
    message = str(getattr(request, "message", "") or "").strip()
    operations: list[dict[str, Any]] = []

    def add_operation(
        op: str,
        path: str,
        value: Any,
        *,
        source: str,
        reason: str,
        confidence: str,
    ) -> None:
        if source not in PATCH_SOURCES or confidence not in PATCH_CONFIDENCE:
            return
        if value in (None, "", []):
            return
        operations.append(
            {
                "op": op,
                "path": path,
                "value": value,
                "source": source,
                "reason": reason,
                "confidence": confidence,
            }
        )

    if message:
        add_operation(
            "prepend_unique",
            "last_questions",
            message,
            source="user_message",
            reason="保留最近用户问题，供后续连续复盘参考。",
            confidence="high",
        )

    explicit_memory = _extract_explicit_memory_updates(message)
    for theme in explicit_memory["focus_themes"]:
        add_operation(
            "append_unique",
            "focus_themes",
            theme,
            source="user_message",
            reason="用户明确表达关注、跟踪或观察该主题。",
            confidence="high",
        )
    for stock in explicit_memory["watchlist"]:
        add_operation(
            "append_unique",
            "watchlist",
            stock,
            source="user_message",
            reason="用户明确要求关注、添加或加入自选股。",
            confidence="high",
        )

    knowledge_level = _extract_knowledge_level(message)
    if knowledge_level:
        add_operation(
            "set",
            "knowledge_level",
            knowledge_level,
            source="user_message",
            reason="用户用明确自我描述表达投资知识水平。",
            confidence="medium",
        )

    if _requests_stronger_risk_warning(message):
        add_operation(
            "set",
            "risk_preferences.needs_stronger_risk_warning",
            True,
            source="user_message",
            reason="用户明确要求更保守或更强风险提示。",
            confidence="high",
        )
    elif getattr(plan, "task_type", "") == "refusal_or_redirect":
        add_operation(
            "set",
            "risk_preferences.needs_stronger_risk_warning",
            True,
            source="review",
            reason="本轮触发买卖、目标价或确定收益等硬规则拦截，后续回复应保持更强风险提示。",
            confidence="medium",
        )

    next_watch = draft.get("next_watch") or []
    if next_watch:
        add_operation(
            "set",
            "last_next_watch",
            next_watch,
            source="agent_response",
            reason="保留本轮生成的下一步观察清单。",
            confidence="high",
        )

    patch_confidence = _patch_confidence(operations)
    return {
        "version": 1,
        "source": _patch_source(operations),
        "reason": _patch_reason(operations),
        "confidence": patch_confidence,
        "operations": operations,
        "evidence_refs": [item.get("id") for item in evidence if item.get("id")],
    }


def _patch_source(operations: list[dict[str, Any]]) -> str:
    sources = {item.get("source") for item in operations}
    if "user_message" in sources:
        return "user_message"
    if "review" in sources:
        return "review"
    return "agent_response"


def _patch_confidence(operations: list[dict[str, Any]]) -> str:
    if any(item.get("confidence") == "low" for item in operations):
        return "low"
    if any(item.get("confidence") == "medium" for item in operations):
        return "medium"
    return "high"


def _patch_reason(operations: list[dict[str, Any]]) -> str:
    memory_ops = [item for item in operations if item.get("path") in ("watchlist", "focus_themes", "knowledge_level", "risk_preferences.needs_stronger_risk_warning")]
    if memory_ops:
        return "规则型 memory builder 识别到明确、低风险的用户记忆更新意图。"
    if operations:
        return "仅记录本轮问题和下一步观察清单，不更新用户偏好。"
    return "未识别到可安全写入 memory 的内容。"


def _extract_explicit_memory_updates(message: str) -> dict[str, list[str]]:
    if not message:
        return {"watchlist": [], "focus_themes": []}

    watchlist: list[str] = []
    focus_themes: list[str] = []

    for candidate in _watchlist_candidates(message):
        if _looks_like_theme(candidate):
            focus_themes.append(candidate)
        else:
            watchlist.append(candidate)

    for candidate in _focus_candidates(message):
        if _looks_like_theme(candidate):
            focus_themes.append(candidate)
        elif _has_watchlist_intent(message) or (
            _has_stock_follow_intent(message) and _looks_like_stock_candidate(candidate)
        ):
            watchlist.append(candidate)

    return {
        "watchlist": _dedupe(watchlist),
        "focus_themes": _dedupe(focus_themes),
    }


def _watchlist_candidates(message: str) -> list[str]:
    if not _has_watchlist_intent(message):
        return []
    patterns = [
        r"(?:把|将)(?P<value>[\u4e00-\u9fffA-Za-z0-9/·\-\s]{2,30})(?:加入|加进|加到|添加到|添加进|放进|放到)(?:我的)?(?:自选|股票|关注)",
        r"(?:加入|添加|加到|加进)(?:我的)?(?:自选|股票|关注)[:：\s]*(?P<value>[\u4e00-\u9fffA-Za-z0-9/·\-\s]{2,30})",
        r"(?:我的股票|我的自选股|我的自选)(?:是|有|包括|[:：])\s*(?P<value>[\u4e00-\u9fffA-Za-z0-9/·\-\s、，,和及与]{2,60})",
    ]
    return _extract_candidates(message, patterns)


def _focus_candidates(message: str) -> list[str]:
    if not _has_focus_intent(message):
        return []
    patterns = [
        r"(?:我)?(?:重点)?(?:关注|跟踪|观察|盯)(?!榜)(?P<value>[\u4e00-\u9fffA-Za-z0-9/·\-\s]{2,30})",
        r"(?:关注主题|关注方向|跟踪主题|跟踪方向|观察主题|观察方向)(?:是|包括)?[:：\s]*(?P<value>[\u4e00-\u9fffA-Za-z0-9/·\-\s、，,和及与]{2,60})",
    ]
    return _extract_candidates(message, patterns)


def _extract_candidates(message: str, patterns: list[str]) -> list[str]:
    candidates: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, message):
            raw_value = match.group("value")
            candidates.extend(_split_candidate_text(raw_value))
    return [item for item in (_clean_candidate(candidate) for candidate in candidates) if item]


def _split_candidate_text(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[、，,；;]|\s+和\s+|\s+及\s+|\s+与\s+", value) if item.strip()]


def _clean_candidate(value: str) -> str:
    candidate = value.strip(" ：:，,。；;！？? \t\r\n")
    candidate = re.sub(r"^(一下|一下子|这个|这些|那个|那些|的)", "", candidate)
    candidate = re.sub(r"(今天|现在|后续|最近)?(怎么样|如何|怎么看|什么情况|能买吗|可以买吗|要不要买|会涨吗).*$", "", candidate)
    candidate = re.sub(r"(这个)?(板块|主题|方向|赛道)$", "", candidate)
    candidate = candidate.strip(" ：:，,。；;！？? \t\r\n")
    if not candidate or candidate.startswith("榜"):
        return ""
    if len(candidate) > 20:
        return ""
    return candidate


def _looks_like_theme(candidate: str) -> bool:
    return any(hint in candidate for hint in THEME_HINTS)


def _has_watchlist_intent(message: str) -> bool:
    return any(word in message for word in WATCHLIST_INTENT_WORDS)


def _has_focus_intent(message: str) -> bool:
    return any(word in message for word in FOCUS_INTENT_WORDS)


def _has_stock_follow_intent(message: str) -> bool:
    return any(word in message for word in STOCK_FOLLOW_INTENT_WORDS)


def _looks_like_stock_candidate(candidate: str) -> bool:
    if candidate in GENERIC_MARKET_TERMS:
        return False
    if _looks_like_theme(candidate):
        return False
    if re.fullmatch(r"[0-9A-Za-z.]{2,12}", candidate):
        return True
    return bool(re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9·]{2,8}", candidate))


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in values if item))


def _extract_knowledge_level(message: str) -> str | None:
    beginner_patterns = ("我是小白", "我是新手", "我刚入门", "刚开始学", "我看不懂", "不太懂投资")
    intermediate_patterns = ("我有基础", "有一点基础", "我懂一点", "我有一些投资经验")
    if any(pattern in message for pattern in beginner_patterns):
        return "beginner"
    if any(pattern in message for pattern in intermediate_patterns):
        return "intermediate"
    return None


def _requests_stronger_risk_warning(message: str) -> bool:
    patterns = ("风险提示多一点", "多提醒风险", "我比较保守", "我是保守型", "风险偏好低", "怕亏")
    return any(pattern in message for pattern in patterns)


def load_all() -> dict[str, Any]:
    if not MEMORY_PATH.exists():
        return {}
    try:
        return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_all(payload: dict[str, Any]) -> None:
    ensure_data_dir()
    MEMORY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_memory(user_id: str) -> dict[str, Any]:
    payload = load_all()
    return ensure_memory_shape(payload.get(user_id), user_id)


def set_memory_fields(user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    payload = load_all()
    memory = ensure_memory_shape(payload.get(user_id), user_id)

    if "watchlist" in fields:
        watchlist = fields.get("watchlist") or []
        memory["watchlist"] = list(dict.fromkeys(item for item in watchlist if item))
    if "focus_themes" in fields:
        themes = fields.get("focus_themes") or []
        memory["focus_themes"] = list(dict.fromkeys(item for item in themes if item))
    if "knowledge_level" in fields:
        memory["knowledge_level"] = fields["knowledge_level"]
    if "open_questions" in fields:
        questions = fields.get("open_questions") or []
        memory["open_questions"] = list(dict.fromkeys(item for item in questions if item))
    if "blockers" in fields:
        blockers = fields.get("blockers") or []
        memory["blockers"] = list(dict.fromkeys(item for item in blockers if item))
    if "next_priority" in fields:
        memory["next_priority"] = str(fields.get("next_priority") or "").strip()
    if "journey_state" in fields and isinstance(fields.get("journey_state"), dict):
        memory["journey_state"] = {
            **memory.get("journey_state", {}),
            **fields["journey_state"],
        }

    memory["updated_at"] = _now()
    payload[user_id] = memory
    save_all(payload)
    return memory


def apply_patch(user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    payload = load_all()
    memory = ensure_memory_shape(payload.get(user_id), user_id)

    operations = patch.get("operations")
    if isinstance(operations, list):
        for operation in operations:
            if isinstance(operation, dict):
                _apply_operation(memory, operation)

    for key in ("watchlist", "focus_themes", "open_questions", "blockers", "last_next_watch"):
        if key in patch:
            merged = [*memory.get(key, []), *patch.get(key, [])]
            memory[key] = list(dict.fromkeys(item for item in merged if item))

    if "knowledge_level" in patch:
        memory["knowledge_level"] = patch["knowledge_level"]
    if "next_priority" in patch:
        memory["next_priority"] = str(patch.get("next_priority") or "").strip()
    elif patch.get("last_next_watch"):
        memory["next_priority"] = str((patch.get("last_next_watch") or [""])[0]).strip()
    if "journey_stage" in patch:
        memory.setdefault("journey_state", {})["stage"] = patch["journey_stage"]
    if "active_task" in patch:
        memory.setdefault("journey_state", {})["active_task"] = patch["active_task"]
    if "updated_from_task" in patch:
        memory.setdefault("journey_state", {})["updated_from_task"] = patch["updated_from_task"]
    if "needs_stronger_risk_warning" in patch:
        memory.setdefault("risk_preferences", {})["needs_stronger_risk_warning"] = bool(
            patch["needs_stronger_risk_warning"]
        )
    if "question" in patch:
        memory["last_questions"] = [patch["question"], *memory.get("last_questions", [])][:10]

    memory = ensure_memory_shape(memory, user_id)
    memory["updated_at"] = _now()
    payload[user_id] = memory
    save_all(payload)
    return memory


def _apply_operation(memory: dict[str, Any], operation: dict[str, Any]) -> None:
    op = operation.get("op")
    path = str(operation.get("path") or "")
    value = operation.get("value")
    if path not in LIST_PATCH_PATHS and path not in SCALAR_PATCH_PATHS:
        return

    if path in LIST_PATCH_PATHS:
        if op == "set":
            memory[path] = _list_values(value)
        elif op == "append_unique":
            memory[path] = _merge_unique(memory.get(path, []), _list_values(value))
        elif op == "prepend_unique":
            memory[path] = _merge_unique(_list_values(value), memory.get(path, []))
        return

    if op != "set":
        return
    if path == "knowledge_level":
        memory["knowledge_level"] = str(value or "beginner")
    elif path == "next_priority":
        memory["next_priority"] = str(value or "").strip()
    elif path.startswith("journey_state."):
        nested_key = path.split(".", 1)[1]
        memory.setdefault("journey_state", {})[nested_key] = value
    elif path == "risk_preferences.needs_stronger_risk_warning":
        memory.setdefault("risk_preferences", {})["needs_stronger_risk_warning"] = bool(value)


def _list_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


def _merge_unique(first: list[Any], second: list[Any]) -> list[str]:
    values = [*(_list_values(first)), *(_list_values(second))]
    return list(dict.fromkeys(item for item in values if item))
