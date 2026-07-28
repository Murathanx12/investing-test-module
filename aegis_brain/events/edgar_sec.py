"""ONE choke-point for every SEC HTTP request this module ever makes.

The prod postmortem applies to research pulls too: `insider_form4` once made raw
unpaced `requests.get` calls that bypassed the process-wide limiter and 403'd on
100% of Archives fetches in prod (aegis-finance, 2026-06-17, NEGATIVE_RESULTS §5).
SEC's cap is 10 req/s and it actively 403s default fetcher user-agents. A research
pull that walks 21 years of daily indexes is exactly the high-volume shape that
tripped it.

Rules enforced here, nowhere else:
  * every request passes `_RATE_LIMITER.wait()` (8/s, process-wide, with headroom)
  * every request carries a declared User-Agent with a contact address
  * 403/429/5xx get bounded retries with backoff; anything else fails loud
"""

from __future__ import annotations

import logging
import os
import threading
import time

import requests

logger = logging.getLogger(__name__)

USER_AGENT = os.environ.get(
    "SEC_USER_AGENT", "Aegis Research (mrthnabdullaev@gmail.com)"
)

_MAX_PER_SEC = 8.0
_MAX_RETRIES = 3


class _RateLimiter:
    def __init__(self, max_per_sec: float) -> None:
        self._min_interval = 1.0 / max_per_sec
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            delta = time.monotonic() - self._last
            if delta < self._min_interval:
                time.sleep(self._min_interval - delta)
            self._last = time.monotonic()


_RATE_LIMITER = _RateLimiter(_MAX_PER_SEC)
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
})

# Observability: a silent-fragility guard. A pull that returns "no events" because
# every fetch 403'd must be distinguishable from a pull that found nothing.
STATS = {"ok": 0, "retried": 0, "failed": 0, "missing": 0}


def sec_get(url: str, *, accept: str = "*/*", timeout: int = 30,
            allow_404: bool = False) -> requests.Response | None:
    """Paced, identified GET. Returns None only when allow_404 and the object is
    genuinely absent (many trading-day index files do not exist)."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        _RATE_LIMITER.wait()
        try:
            resp = _SESSION.get(url, headers={"Accept": accept}, timeout=timeout)
        except requests.RequestException as exc:      # transport-level
            last_exc = exc
            STATS["retried"] += 1
            time.sleep(2.0 * (attempt + 1))
            continue
        if resp.status_code == 404 and allow_404:
            STATS["missing"] += 1
            return None
        if resp.status_code in (403, 429) or resp.status_code >= 500:
            last_exc = requests.HTTPError(f"{resp.status_code} for {url}")
            STATS["retried"] += 1
            logger.warning("SEC %s on %s — backing off (attempt %d/%d)",
                           resp.status_code, url, attempt + 1, _MAX_RETRIES)
            time.sleep(3.0 * (attempt + 1))
            continue
        resp.raise_for_status()
        STATS["ok"] += 1
        return resp
    STATS["failed"] += 1
    raise RuntimeError(f"SEC fetch failed after {_MAX_RETRIES} attempts: {url}") from last_exc
