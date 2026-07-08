from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from market_radar.market.data_store import append_history, write_latest


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
AGENT_REACH_ENV = "agent-reach"
INDICES = {
    "SH000001": "上证指数",
    "SZ399001": "深证成指",
    "SZ399006": "创业板指",
    "SH000300": "沪深300",
    "SH000905": "中证500",
    "SH000688": "科创50",
}


def collect() -> dict[str, Any]:
    try:
        return _collect_with_agent_reach()
    except ModuleNotFoundError as exc:
        if exc.name != "agent_reach":
            raise
        return _collect_via_agent_reach_env()


def _collect_with_agent_reach() -> dict[str, Any]:
    from agent_reach.channels.xueqiu import XueqiuChannel

    channel = XueqiuChannel()
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "agent_reach.channels.xueqiu.XueqiuChannel",
        "indices": [
            {"label": label, **channel.get_stock_quote(symbol)}
            for symbol, label in INDICES.items()
        ],
        "hot_popularity": channel.get_hot_stocks(limit=20, stock_type=10),
        "hot_watchlist": channel.get_hot_stocks(limit=20, stock_type=12),
        "hot_posts": channel.get_hot_posts(limit=20),
    }


def _collect_via_agent_reach_env() -> dict[str, Any]:
    conda_exe = _find_conda_executable()
    if not conda_exe:
        raise RuntimeError(
            "Refresh requires the 'agent-reach' conda environment, but conda was not found. "
            "Activate that environment before starting the server, or install conda on this machine."
        )

    script = (
        "import json, sys; "
        f"sys.path.insert(0, {json.dumps(str(WORKSPACE_ROOT))}); "
        "from market_radar.market.collector import _collect_with_agent_reach; "
        "print(json.dumps(_collect_with_agent_reach(), ensure_ascii=False))"
    )
    result = subprocess.run(
        [
            str(conda_exe),
            "run",
            "-n",
            AGENT_REACH_ENV,
            "python",
            "-c",
            script,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[:1200]
        raise RuntimeError(
            "Refresh could not collect from the agent-reach environment. "
            f"conda env={AGENT_REACH_ENV}; detail={detail or 'no error output'}"
        )

    stdout = (result.stdout or "").strip()
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("indices"):
            return payload
    raise RuntimeError("Refresh fallback ran, but no valid JSON payload was returned from agent-reach.")


def _find_conda_executable() -> Path | None:
    candidates = [
        os.environ.get("CONDA_EXE"),
        shutil.which("conda"),
    ]
    current_python = Path(sys.executable)
    candidates.append(str(current_python.with_name("conda")))

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists() and path.is_file():
            return path
    return None


def build_history_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    indices = payload.get("indices") or []
    hot_popularity = payload.get("hot_popularity") or []
    hot_watchlist = payload.get("hot_watchlist") or []
    popularity_symbols = {item.get("symbol") for item in hot_popularity}
    overlap = sum(1 for item in hot_watchlist if item.get("symbol") in popularity_symbols)
    limit_like = len(
        {
            item.get("symbol")
            for item in [*hot_popularity, *hot_watchlist]
            if (item.get("percent") or 0) >= 9.8
        }
    )

    return {
        "generated_at": payload.get("generated_at"),
        "indices": [
            {
                "label": item.get("label") or item.get("name"),
                "symbol": item.get("symbol"),
                "current": item.get("current"),
                "percent": item.get("percent"),
                "amount": item.get("amount"),
            }
            for item in indices
        ],
        "hot_top": [item.get("name") for item in hot_popularity[:5]],
        "watch_top": [item.get("name") for item in hot_watchlist[:5]],
        "overlap": overlap,
        "limit_like_count": limit_like,
    }


def save_payload(payload: dict[str, Any]) -> Path:
    out_path = write_latest(payload)
    append_history(build_history_snapshot(payload))
    return out_path


def collect_and_save() -> Path:
    return save_payload(collect())


def main() -> None:
    out_path = collect_and_save()
    print(json.dumps({"path": str(out_path.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
