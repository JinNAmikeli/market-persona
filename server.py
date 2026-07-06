from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


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
        if path == "/api/agent/status":
            self._handle_agent_status()
            return
        if path == "/api/agent/memory":
            self._handle_agent_memory()
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
                    "hint": "Run POST /api/refresh or python tools/xueqiu_radar_collect.py",
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
        self._json_response(
            {
                "configured": configured,
                "provider": "deepseek",
                "model_env": "DEEPSEEK_MODEL",
                "default_model": "deepseek-v4-flash",
                "runtime": {
                    "memory": True,
                    "trace": True,
                    "wiki": False,
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
            from tools.xueqiu_radar_collect import collect, save_payload

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
