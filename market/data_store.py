from __future__ import annotations

import json
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent
DATA_DIR = APP_DIR / "data"
LEGACY_DATA_DIR = REPO_ROOT / "data"

LATEST_PATH = DATA_DIR / "xueqiu_radar_latest.json"
HISTORY_PATH = DATA_DIR / "xueqiu_radar_history.jsonl"
LEGACY_LATEST_PATH = LEGACY_DATA_DIR / "xueqiu_radar_latest.json"
LEGACY_HISTORY_PATH = LEGACY_DATA_DIR / "xueqiu_radar_history.jsonl"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _first_existing(primary: Path, fallback: Path) -> Path:
    return primary if primary.exists() else fallback


def latest_path() -> Path:
    return _first_existing(LATEST_PATH, LEGACY_LATEST_PATH)


def history_path() -> Path:
    return _first_existing(HISTORY_PATH, LEGACY_HISTORY_PATH)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_latest() -> dict[str, Any]:
    path = latest_path()
    if not path.exists():
        raise FileNotFoundError("No radar data yet. Refresh data first.")
    return read_json(path)


def read_history(limit: int = 120) -> list[dict[str, Any]]:
    path = history_path()
    history: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                history.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    elif latest_path().exists():
        payload = read_latest()
        from market_radar.market.collector import build_history_snapshot

        history.append(build_history_snapshot(payload))
    return history[-limit:]


def write_latest(payload: dict[str, Any]) -> Path:
    ensure_data_dir()
    LATEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return LATEST_PATH


def append_history(snapshot: dict[str, Any]) -> Path:
    ensure_data_dir()
    with HISTORY_PATH.open("a", encoding="utf-8") as history_file:
        history_file.write(json.dumps(snapshot, ensure_ascii=False))
        history_file.write("\n")
    return HISTORY_PATH
