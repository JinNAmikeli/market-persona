from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from market_radar.market.data_store import DATA_DIR, ensure_data_dir


MEMORY_PATH = DATA_DIR / "user_memory.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_memory(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "watchlist": [],
        "focus_themes": [],
        "knowledge_level": "beginner",
        "risk_preferences": {"needs_stronger_risk_warning": False},
        "last_questions": [],
        "last_next_watch": [],
        "updated_at": _now(),
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
    return payload.get(user_id) or default_memory(user_id)


def set_memory_fields(user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    payload = load_all()
    memory = payload.get(user_id) or default_memory(user_id)

    if "watchlist" in fields:
        watchlist = fields.get("watchlist") or []
        memory["watchlist"] = list(dict.fromkeys(item for item in watchlist if item))
    if "focus_themes" in fields:
        themes = fields.get("focus_themes") or []
        memory["focus_themes"] = list(dict.fromkeys(item for item in themes if item))
    if "knowledge_level" in fields:
        memory["knowledge_level"] = fields["knowledge_level"]

    memory["updated_at"] = _now()
    payload[user_id] = memory
    save_all(payload)
    return memory


def apply_patch(user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    payload = load_all()
    memory = payload.get(user_id) or default_memory(user_id)

    for key in ("watchlist", "focus_themes", "last_next_watch"):
        if key in patch:
            merged = [*memory.get(key, []), *patch.get(key, [])]
            memory[key] = list(dict.fromkeys(item for item in merged if item))

    if "knowledge_level" in patch:
        memory["knowledge_level"] = patch["knowledge_level"]
    if "needs_stronger_risk_warning" in patch:
        memory.setdefault("risk_preferences", {})["needs_stronger_risk_warning"] = bool(
            patch["needs_stronger_risk_warning"]
        )
    if "question" in patch:
        memory["last_questions"] = [patch["question"], *memory.get("last_questions", [])][:10]

    memory["updated_at"] = _now()
    payload[user_id] = memory
    save_all(payload)
    return memory
