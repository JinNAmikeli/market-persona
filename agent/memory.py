from __future__ import annotations

import json
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
