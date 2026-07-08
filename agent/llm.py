from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: str
    model: str
    base_url: str
    timeout: int = 45
    max_tokens: int = 1200
    temperature: float = 0.2


@dataclass(frozen=True)
class LLMResult:
    provider: str
    model: str
    content: str
    usage: dict[str, Any]


PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4.1-mini",
        "key_env": "OPENAI_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "key_env": "DEEPSEEK_API_KEY",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-5-haiku-latest",
        "key_env": "ANTHROPIC_API_KEY",
    },
}


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


def normalize_provider(provider: str) -> str:
    value = (provider or "").strip().lower()
    aliases = {
        "a": "anthropic",
        "claude": "anthropic",
        "anthropic": "anthropic",
        "openai": "openai",
        "oai": "openai",
        "deepseek": "deepseek",
        "ds": "deepseek",
    }
    return aliases.get(value, value)


def get_config() -> LLMConfig | None:
    load_local_env()
    provider = normalize_provider(os.environ.get("MARKET_AGENT_LLM_PROVIDER") or "")
    if not provider:
        return None

    defaults = PROVIDER_DEFAULTS.get(provider)
    if not defaults:
        raise RuntimeError(f"Unsupported MARKET_AGENT_LLM_PROVIDER: {provider}")

    api_key = os.environ.get("MARKET_AGENT_LLM_API_KEY") or os.environ.get(defaults["key_env"]) or ""
    if not api_key:
        return None

    model = os.environ.get("MARKET_AGENT_LLM_MODEL") or defaults["model"]
    base_url = (os.environ.get("MARKET_AGENT_LLM_BASE_URL") or defaults["base_url"]).rstrip("/")
    timeout = int(os.environ.get("MARKET_AGENT_LLM_TIMEOUT") or "45")
    max_tokens = int(os.environ.get("MARKET_AGENT_LLM_MAX_TOKENS") or "1200")
    temperature = float(os.environ.get("MARKET_AGENT_LLM_TEMPERATURE") or "0.2")
    return LLMConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout=timeout,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def is_configured() -> bool:
    return get_config() is not None


def complete_chat(system_prompt: str, user_prompt: str, config: LLMConfig | None = None) -> LLMResult | None:
    config = config or get_config()
    if config is None:
        return None
    if config.provider == "anthropic":
        return _complete_anthropic(system_prompt, user_prompt, config)
    return _complete_openai_compatible(system_prompt, user_prompt, config)


def _complete_openai_compatible(system_prompt: str, user_prompt: str, config: LLMConfig) -> LLMResult:
    body = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    result = _post_json(
        f"{config.base_url}/chat/completions",
        body,
        {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        config.timeout,
        config.provider,
    )
    content = (
        (result.get("choices") or [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not content:
        raise RuntimeError(f"{config.provider} returned an empty response.")
    return LLMResult(
        provider=config.provider,
        model=config.model,
        content=content,
        usage=result.get("usage") or {},
    )


def _complete_anthropic(system_prompt: str, user_prompt: str, config: LLMConfig) -> LLMResult:
    body = {
        "model": config.model,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    result = _post_json(
        f"{config.base_url}/messages",
        body,
        {
            "x-api-key": config.api_key,
            "anthropic-version": os.environ.get("ANTHROPIC_VERSION") or "2023-06-01",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        config.timeout,
        config.provider,
    )
    chunks = result.get("content") or []
    content = "\n".join(
        item.get("text", "").strip()
        for item in chunks
        if item.get("type") == "text" and item.get("text")
    ).strip()
    if not content:
        raise RuntimeError("anthropic returned an empty response.")
    return LLMResult(
        provider=config.provider,
        model=config.model,
        content=content,
        usage=result.get("usage") or {},
    )


def _post_json(
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
    provider: str,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"{provider} API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{provider} network error: {exc}") from exc
