from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MB = 1024 * 1024

TRACE_LINE_THRESHOLD = 10_000
TRACE_SIZE_THRESHOLD_BYTES = 50 * MB
WATCH_RATIO = 0.8
HISTORY_WATCH_SIZE_BYTES = 50 * MB

RUNTIME_FILES = [
    {
        "path": "data/xueqiu_radar_latest.json",
        "kind": "latest_snapshot",
        "jsonl": False,
    },
    {
        "path": "data/xueqiu_radar_history.jsonl",
        "kind": "market_history",
        "jsonl": True,
    },
    {
        "path": "data/user_memory.json",
        "kind": "user_memory",
        "jsonl": False,
    },
    {
        "path": "data/agent_traces.jsonl",
        "kind": "agent_traces",
        "jsonl": True,
    },
]


def size_mb(size_bytes: int) -> float:
    return round(size_bytes / MB, 3)


def count_jsonl_lines(path: Path) -> int:
    line_count = 0
    last_byte = b""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            line_count += chunk.count(b"\n")
            last_byte = chunk[-1:]
    if path.stat().st_size > 0 and last_byte != b"\n":
        line_count += 1
    return line_count


def trace_status(size_bytes: int, line_count: int | None) -> tuple[str, str]:
    lines = line_count or 0
    if lines >= TRACE_LINE_THRESHOLD or size_bytes >= TRACE_SIZE_THRESHOLD_BYTES:
        return (
            "exceeds",
            "Trace file is at or above the policy observation threshold; use this for manual judgment only. No cleanup is triggered.",
        )
    if lines >= int(TRACE_LINE_THRESHOLD * WATCH_RATIO) or size_bytes >= int(TRACE_SIZE_THRESHOLD_BYTES * WATCH_RATIO):
        return (
            "watch",
            "Trace file is approaching the policy observation threshold; use this for manual judgment only. No cleanup is triggered.",
        )
    return (
        "ok",
        "Trace file is below the policy observation threshold. This read-only check does not trigger cleanup.",
    )


def history_status(size_bytes: int) -> tuple[str, str]:
    if size_bytes >= HISTORY_WATCH_SIZE_BYTES:
        return (
            "watch",
            "Market history is large enough to watch manually. A single run cannot prove sustained growth and no cleanup is triggered.",
        )
    return (
        "ok",
        "Market history is below the watch size used by this inspector. Compare repeated runs manually if growth is suspected.",
    )


def generic_status(kind: str) -> tuple[str, str]:
    if kind == "latest_snapshot":
        return (
            "ok",
            "Latest snapshot is a regenerable current snapshot, not an audit history. This inspector does not modify it.",
        )
    if kind == "user_memory":
        return (
            "ok",
            "User memory is protected local state. This inspector only reports existence and size, never content.",
        )
    return (
        "ok",
        "Read-only inspection completed. No cleanup is triggered.",
    )


def inspect_file(config: dict[str, Any]) -> dict[str, Any]:
    rel_path = str(config["path"])
    path = REPO_ROOT / rel_path
    is_jsonl = bool(config["jsonl"])
    kind = str(config["kind"])

    result: dict[str, Any] = {
        "file_path": rel_path,
        "exists": path.exists(),
        "size_bytes": 0,
        "size_mb": 0.0,
        "line_count": None,
        "threshold_status": "ok",
        "note": "File is missing; no threshold check was applied and no cleanup is triggered.",
    }

    if not path.exists():
        return result

    stat_result = path.stat()
    result["size_bytes"] = stat_result.st_size
    result["size_mb"] = size_mb(stat_result.st_size)

    line_count: int | None = None
    if is_jsonl:
        line_count = count_jsonl_lines(path)
        result["line_count"] = line_count

    if kind == "agent_traces":
        status, note = trace_status(stat_result.st_size, line_count)
    elif kind == "market_history":
        status, note = history_status(stat_result.st_size)
    else:
        status, note = generic_status(kind)

    result["threshold_status"] = status
    result["note"] = note
    return result


def main() -> int:
    if len(sys.argv) != 1:
        print("Usage: python scripts/inspect_runtime_data.py", file=sys.stderr)
        return 2

    report = [inspect_file(config) for config in RUNTIME_FILES]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
