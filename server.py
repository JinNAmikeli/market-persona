from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"


def ensure_project_path() -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))


class RadarHandler(BaseHTTPRequestHandler):
    server_version = "MarketRadar/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/radar":
            self._handle_get_radar()
            return
        if path == "/api/history":
            self._handle_get_history()
            return
        if path == "/api/signals":
            self._handle_get_signals()
            return
        if path == "/api/agent/status":
            self._handle_agent_status()
            return
        if path == "/api/agent/memory":
            self._handle_agent_memory()
            return
        if path == "/api/agent/traces":
            self._handle_agent_traces()
            return
        self._serve_static(path)

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/radar":
            ensure_project_path()
            from market_radar.market.data_store import latest_path

            if latest_path().exists():
                self._head_response("application/json; charset=utf-8")
            else:
                self._head_response("application/json; charset=utf-8", status=404)
            return
        if path == "/api/history":
            ensure_project_path()
            from market_radar.market.data_store import history_path

            if history_path().exists():
                self._head_response("application/json; charset=utf-8")
            else:
                self._head_response("application/json; charset=utf-8", status=404)
            return
        if path == "/api/signals":
            ensure_project_path()
            from market_radar.market.data_store import latest_path

            if latest_path().exists():
                self._head_response("application/json; charset=utf-8")
            else:
                self._head_response("application/json; charset=utf-8", status=404)
            return
        self._serve_static(path, head_only=True)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/refresh":
            self._handle_refresh()
            return
        if path == "/api/agent/recap":
            self._handle_agent_recap()
            return
        if path == "/api/agent/chat":
            self._handle_agent_chat()
            return
        if path == "/api/agent/briefing":
            self._handle_agent_briefing()
            return
        if path == "/api/agent/memory":
            self._handle_agent_memory_update()
            return
        self._json_response({"error": "Not found"}, status=404)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def _handle_get_radar(self) -> None:
        ensure_project_path()
        from market_radar.market.data_store import latest_path, read_latest

        if not latest_path().exists():
            self._json_response(
                {
                    "error": "No radar data yet",
                    "hint": "Run POST /api/refresh or python scripts/refresh_xueqiu.py",
                },
                status=404,
            )
            return
        try:
            self._json_response(read_latest())
        except json.JSONDecodeError as exc:
            self._json_response({"error": f"Invalid radar JSON: {exc}"}, status=500)

    def _handle_get_history(self) -> None:
        self._json_response(self._read_history())

    def _handle_get_signals(self) -> None:
        try:
            ensure_project_path()
            from market_radar.market.signals import derive_market

            radar = self._read_radar()
            self._json_response(
                {
                    "generated_at": radar.get("generated_at"),
                    "signals": derive_market(radar),
                }
            )
        except Exception as exc:
            self._json_response(
                {
                    "error": "Signals failed",
                    "detail": str(exc),
                },
                status=500,
            )

    def _read_history(self) -> list[dict]:
        ensure_project_path()
        from market_radar.market.data_store import read_history

        return read_history(limit=120)

    def _read_radar(self) -> dict:
        ensure_project_path()
        from market_radar.market.data_store import read_latest

        return read_latest()

    def _handle_agent_status(self) -> None:
        try:
            ensure_project_path()
            from market_radar.deepseek_agent import is_configured

            configured = is_configured()
        except Exception:
            configured = False
        try:
            ensure_project_path()
            from market_radar.agent.llm import get_config, normalize_provider

            agent_llm_config = get_config()
            agent_provider = normalize_provider(agent_llm_config.provider if agent_llm_config else "")
            agent_llm = {
                "configured": agent_llm_config is not None,
                "provider": agent_provider or None,
                "model": agent_llm_config.model if agent_llm_config else None,
            }
        except Exception as exc:
            agent_llm = {
                "configured": False,
                "provider": None,
                "model": None,
                "error": str(exc),
            }
        self._json_response(
            {
                "configured": configured,
                "provider": "deepseek",
                "model_env": "DEEPSEEK_MODEL",
                "default_model": "deepseek-v4-flash",
                "agent_llm": agent_llm,
                "runtime": {
                    "memory": True,
                    "trace": True,
                    "wiki": True,
                    "reflection": True,
                },
            }
        )

    def _handle_agent_recap(self) -> None:
        try:
            ensure_project_path()
            from market_radar.deepseek_agent import generate_recap

            payload = generate_recap(self._read_radar(), self._read_history())
            self._json_response(payload)
        except Exception as exc:
            self._json_response(
                {
                    "error": "Agent recap failed",
                    "detail": str(exc),
                    "hint": "Add DEEPSEEK_API_KEY to .env and restart the app.",
                },
                status=500,
            )

    def _handle_agent_memory(self) -> None:
        try:
            ensure_project_path()
            from market_radar.agent.memory import load_memory

            self._json_response(load_memory("local"))
        except Exception as exc:
            self._json_response(
                {
                    "error": "Agent memory failed",
                    "detail": str(exc),
                },
                status=500,
            )

    def _handle_agent_traces(self) -> None:
        try:
            params = {
                key: values[-1]
                for key, values in parse_qs(urlparse(self.path).query, keep_blank_values=False).items()
                if values
            }
            ensure_project_path()
            from market_radar.agent.trace import find_trace, read_traces, summarize_trace

            trace_id = params.get("id") or params.get("trace_id")
            if trace_id:
                trace = find_trace(trace_id)
                if not trace:
                    self._json_response({"error": "Trace not found", "trace_id": trace_id}, status=404)
                    return
                self._json_response(trace)
                return

            try:
                limit = int(params.get("limit", "20"))
            except ValueError:
                limit = 20
            filters = {
                key: params.get(key)
                for key in ("query", "task_type", "execution_mode", "review_passed", "repair_changed", "date_from", "date_to")
                if params.get(key) not in (None, "")
            }
            traces = read_traces(limit=limit, filters=filters)
            self._json_response(
                {
                    "count": len(traces),
                    "limit": limit,
                    "filters": filters,
                    "traces": [summarize_trace(trace) for trace in traces],
                }
            )
        except Exception as exc:
            self._json_response(
                {
                    "error": "Agent traces failed",
                    "detail": str(exc),
                },
                status=500,
            )

    def _handle_agent_memory_update(self) -> None:
        try:
            payload = self._read_json_body()
            ensure_project_path()
            from market_radar.agent.memory import set_memory_fields

            user_id = payload.get("user_id") or "local"
            fields = {
                key: payload[key]
                for key in ("watchlist", "focus_themes", "knowledge_level")
                if key in payload
            }
            self._json_response(set_memory_fields(user_id, fields))
        except json.JSONDecodeError as exc:
            self._json_response({"error": f"Invalid JSON: {exc}"}, status=400)
        except Exception as exc:
            self._json_response(
                {
                    "error": "Agent memory update failed",
                    "detail": str(exc),
                },
                status=500,
            )

    def _handle_agent_chat(self) -> None:
        try:
            payload = self._read_json_body()
            ensure_project_path()
            from market_radar.agent.runtime import run_agent_turn

            self._json_response(run_agent_turn(payload))
        except json.JSONDecodeError as exc:
            self._json_response({"error": f"Invalid JSON: {exc}"}, status=400)
        except Exception as exc:
            self._json_response(
                {
                    "error": "Agent chat failed",
                    "detail": str(exc),
                },
                status=500,
            )

    def _handle_agent_briefing(self) -> None:
        try:
            payload = self._read_json_body()
            ensure_project_path()
            from market_radar.agent.runtime import run_agent_briefing

            self._json_response(run_agent_briefing(payload))
        except json.JSONDecodeError as exc:
            self._json_response({"error": f"Invalid JSON: {exc}"}, status=400)
        except Exception as exc:
            self._json_response(
                {
                    "error": "Agent briefing failed",
                    "detail": str(exc),
                },
                status=500,
            )

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw_body = self.rfile.read(length) if length else b"{}"
        return json.loads(raw_body.decode("utf-8"))

    def _handle_refresh(self) -> None:
        try:
            ensure_project_path()
            from market_radar.market.collector import collect, save_payload

            payload = collect()
            save_payload(payload)
            self._json_response(payload)
        except Exception as exc:
            self._json_response(
                {
                    "error": "Refresh failed",
                    "detail": str(exc),
                },
                status=500,
            )

    def _serve_static(self, path: str, head_only: bool = False) -> None:
        if path in ("", "/"):
            path = "/index.html"
        rel_path = unquote(path).lstrip("/")
        target = (STATIC_DIR / rel_path).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            self._json_response({"error": "Not found"}, status=404)
            return

        content_type, _ = mimetypes.guess_type(str(target))
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(target.stat().st_size))
        self.end_headers()
        if head_only:
            return
        self.wfile.write(target.read_bytes())

    def _json_response(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _head_response(self, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local A-share market radar app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8787, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), RadarHandler)
    print(f"Market Radar running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
