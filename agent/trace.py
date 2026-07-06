from __future__ import annotations

import json
from datetime import datetime
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
