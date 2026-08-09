"""Immutable response cache + spend guard.

Murat's complaint, stated exactly: *"sometimes llms have noise and they give
different answers to same question."* This module is half the answer — the same
question, to the same model, can never be silently re-rolled, because the answer
is written once and read forever after. (The other half is decision persistence:
showing the model its own prior claim and grading the delta, in `persistence.py`.)

The cache key is `(model_id, sha256(system + user))`. Nothing else. Not an event
id, not an arm name — so if two arms happen to construct byte-identical prompts
they share one answer, which is correct: they asked the same question.

Write-once is enforced, not assumed: a second call that produces different text
for an existing key raises rather than overwriting. Spend is checked BEFORE each
call against a hard cap and the campaign halts on breach rather than degrading
into a silently truncated sample.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# DeepSeek list price, USD per 1M tokens (deepseek-chat, cache-miss input).
# Used only for the spend guard's estimate; the true bill is the provider's.
PRICE_IN_PER_1M = 0.27
PRICE_OUT_PER_1M = 1.10


def prompt_hash(system: str, user: str) -> str:
    return hashlib.sha256(f"{system}\x00{user}".encode()).hexdigest()


class SpendGuard:
    """Hard-cap spend tracker. Raises rather than letting a campaign overrun."""

    def __init__(self, cap_usd: float) -> None:
        self.cap_usd = float(cap_usd)
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.calls = 0
        self._lock = threading.Lock()

    @property
    def spent_usd(self) -> float:
        return (self.prompt_tokens * PRICE_IN_PER_1M
                + self.completion_tokens * PRICE_OUT_PER_1M) / 1e6

    def check(self) -> None:
        if self.spent_usd >= self.cap_usd:
            raise RuntimeError(
                f"SPEND CAP REACHED: ${self.spent_usd:.2f} >= ${self.cap_usd:.2f} "
                f"after {self.calls} calls. Halting — a truncated sample must be "
                "visible, never silent.")

    def record(self, usage: dict | None) -> None:
        with self._lock:
            self.calls += 1
            u = usage or {}
            self.prompt_tokens += int(u.get("prompt_tokens", 0) or 0)
            self.completion_tokens += int(u.get("completion_tokens", 0) or 0)

    def as_dict(self) -> dict:
        return {"calls": self.calls, "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "estimated_usd": round(self.spent_usd, 4),
                "cap_usd": self.cap_usd}


class LLMCache:
    """Write-once response store keyed by (model_id, prompt hash)."""

    def __init__(self, root: Path | str, model_id: str, guard: SpendGuard) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.model_id = model_id
        self.guard = guard
        self.hits = 0
        self.misses = 0
        self.failures = 0
        self._lock = threading.Lock()

    def _path(self, key: str) -> Path:
        # shard so a directory never holds tens of thousands of entries
        d = self.root / key[:2]
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{key}.json"

    def get(self, system: str, user: str, *, nonce: str = "") -> dict | None:
        key = prompt_hash(system, user + nonce)
        p = self._path(f"{self.model_id}_{key}"[:64].replace("/", "_"))
        if p.exists():
            with self._lock:
                self.hits += 1
            return json.loads(p.read_text(encoding="utf-8"))
        return None

    def call(self, system: str, user: str, *, temperature: float = 0.0,
             max_tokens: int = 1500, nonce: str = "", retries: int = 3,
             tag: str = "") -> dict:
        """Cached completion. Returns the stored record (may carry ok=False)."""
        from aegis_brain.llm.client import chat

        key = prompt_hash(system, user + nonce)
        p = self._path(f"{self.model_id}_{key}"[:64].replace("/", "_"))
        if p.exists():
            with self._lock:
                self.hits += 1
            return json.loads(p.read_text(encoding="utf-8"))

        self.guard.check()
        rec = {"model_id": self.model_id, "prompt_sha256": key, "tag": tag,
               "temperature": temperature, "nonce": nonce,
               "system": system, "user": user}
        for attempt in range(retries):
            try:
                out = chat(user, system=system, model=self.model_id,
                           temperature=temperature, max_tokens=max_tokens,
                           response_json=True, timeout=120)
                rec["raw"] = out["text"]
                rec["usage"] = out.get("usage")
                rec["ok"] = True
                self.guard.record(out.get("usage"))
                break
            except Exception as exc:            # noqa: BLE001 — loud, then retry
                rec["error"] = f"{type(exc).__name__}: {exc}"
                rec["ok"] = False
                if attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))
        with self._lock:
            self.misses += 1
            if not rec.get("ok"):
                self.failures += 1
        # write-once: a differing answer for an existing key is a contract
        # violation, not a cache update
        if p.exists():
            prior = json.loads(p.read_text(encoding="utf-8"))
            if prior.get("raw") != rec.get("raw"):
                raise RuntimeError(f"cache key {key[:12]} already holds a "
                                   "different answer — refusing to overwrite")
            return prior
        p.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
        return rec

    def stats(self) -> dict:
        return {"hits": self.hits, "misses": self.misses,
                "failures": self.failures, "model_id": self.model_id}


def parse_json(text: str) -> dict:
    """Tolerant JSON extraction — models sometimes wrap output in fences."""
    t = (text or "").strip()
    if t.startswith("```"):
        parts = t.split("```")
        t = parts[1] if len(parts) > 1 else t
        if t.lower().startswith("json"):
            t = t[4:]
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        raise ValueError(f"no JSON object in response: {(text or '')[:120]!r}")
    return json.loads(t[i:j + 1])
