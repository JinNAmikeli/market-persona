from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"


def load_local_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def is_configured() -> bool:
    load_local_env()
    return bool(os.environ.get("DEEPSEEK_API_KEY"))


def _compact_stock(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": item.get("rank"),
        "symbol": item.get("symbol"),
        "name": item.get("name"),
        "current": item.get("current"),
        "percent": item.get("percent"),
    }


def _compact_post(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": item.get("title"),
        "author": item.get("author"),
        "likes": item.get("likes"),
        "text": (item.get("text") or "")[:180],
        "url": item.get("url"),
    }


def build_prompt(radar: dict[str, Any], history: list[dict[str, Any]]) -> str:
    payload = {
        "generated_at": radar.get("generated_at"),
        "indices": radar.get("indices", []),
        "hot_popularity": [_compact_stock(item) for item in radar.get("hot_popularity", [])[:20]],
        "hot_watchlist": [_compact_stock(item) for item in radar.get("hot_watchlist", [])[:20]],
        "hot_posts": [_compact_post(item) for item in radar.get("hot_posts", [])[:12]],
        "history_tail": history[-20:],
    }

    return (
        "你是一个面向金融小白的A股市场观察助理。"
        "请基于输入的雪球市场雷达数据输出一份中文复盘。"
        "严格遵守：不提供买卖指令，不使用'必须买入/卖出'，不预测确定收益；"
        "只输出观察结论、证据、风险和下一步观察清单。\n\n"
        "输出格式：\n"
        "1. 一句话市场状态\n"
        "2. 主线热度排序（说明证据）\n"
        "3. 情绪与拥挤度\n"
        "4. 风险点\n"
        "5. 明日/下一次刷新重点观察\n"
        "6. 小白解释（把专业词讲成人话）\n\n"
        f"市场数据JSON：\n{json.dumps(payload, ensure_ascii=False)}"
    )


def generate_recap(radar: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    load_local_env()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY. Add it to .env and restart the app.")

    model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL)
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    url = f"{base_url}/chat/completions"
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是谨慎、证据驱动的市场观察助手。"
                    "你帮助新手理解市场，不提供个股买卖建议。"
                ),
            },
            {"role": "user", "content": build_prompt(radar, history)},
        ],
        "temperature": 0.2,
        "max_tokens": 1800,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"DeepSeek API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"DeepSeek network error: {exc}") from exc

    content = (
        (result.get("choices") or [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not content:
        raise RuntimeError("DeepSeek returned an empty response.")

    usage = result.get("usage") or {}
    return {
        "model": model,
        "generated_at": radar.get("generated_at"),
        "content": content,
        "usage": usage,
    }
