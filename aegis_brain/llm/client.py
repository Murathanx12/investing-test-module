"""DeepSeek client (OpenAI-compatible) — reads the key from aegis-finance's .env
at runtime and NEVER copies the secret into this repo or logs it.

DeepSeek exposes an OpenAI-compatible endpoint. We use plain `requests` to avoid a
hard SDK dependency. Temperature is pinned low and the model id is logged with every
call so a stored call is reproducible (model version is part of the experiment).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests

# The key lives in the parent project's env file; we read it, we do not vendor it.
AEGIS_FINANCE_ENV = Path(r"C:\Users\mrthn\aegis-finance\.env")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def _load_key(var: str = "DEEPSEEK_API_KEY") -> str:
    """Read a single key from the aegis-finance .env without importing anything
    from that repo. Env var overrides the file if already set."""
    if os.environ.get(var):
        return os.environ[var]
    if not AEGIS_FINANCE_ENV.exists():
        raise FileNotFoundError(f"{AEGIS_FINANCE_ENV} not found — cannot load {var}")
    for line in AEGIS_FINANCE_ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == var:
            return v.strip().strip('"').strip("'")
    raise LookupError(f"{var} not found in {AEGIS_FINANCE_ENV}")


def chat(
    prompt: str,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    timeout: int = 60,
    response_json: bool = False,
) -> dict:
    """One chat completion. Returns {text, model, usage}. Raises on HTTP error so
    callers fail loud (never silently fabricate a call)."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_json:
        body["response_format"] = {"type": "json_object"}
    r = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {_load_key()}", "Content-Type": "application/json"},
        data=json.dumps(body),
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "text": data["choices"][0]["message"]["content"],
        "model": data.get("model", model),
        "usage": data.get("usage", {}),
    }


def ping() -> dict:
    """Minimal connectivity check. Returns the model's reply to a trivial prompt."""
    return chat("Reply with exactly the word: pong", max_tokens=8)
