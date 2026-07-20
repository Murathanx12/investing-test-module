"""Event ledger — pre-registered, forward-only, falsifiable event calls (L1a → L5).

This is the module's actual moat (ROADMAP §"revolutionary angle"): a calibration
track record that cannot be faked or overfit, because every call is registered
BEFORE its outcome window and scored mechanically at maturity.

A call is a probabilistic forecast attached to a catalyst:
    "event E on ticker T at date D → P(k-day forward return > 0) = p"
with a written rationale and a pre-committed kill condition.

Discipline enforced in code:
  - register_call() REFUSES a call whose registered_at is not strictly before the
    event date — you cannot pre-register an event after it is observable.
  - the store is append-only JSONL; scoring writes a separate scored file.
  - scoring needs a realized-return function INJECTED by the caller (CRSP/yfinance
    later, synthetic in tests) — the ledger itself has no market-data dependency,
    so its logic is provable in isolation.
  - a call cannot be scored before its maturity date (event_date + horizon).

Brier score is the headline metric (lower = better calibrated); the calibration
table (mean predicted p vs realized hit-rate per bucket) is what an allocator
would actually value.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

# realized_return_fn(ticker, event_date, horizon_days) -> float | None
#   returns the k-trading-day forward return starting after event_date, or None
#   if price data is unavailable (call stays pending, never silently scored 0).
RealizedReturnFn = Callable[[str, str, int], "float | None"]


@dataclass(frozen=True)
class EventCall:
    event_id: str            # stable unique id (e.g. "FDA-NDA212345-2023-04-15")
    ticker: str
    event_type: str          # "FDA_APPROVAL", "PDUFA", "LAUNCH", "MNA", ...
    event_date: str          # YYYY-MM-DD — when the catalyst resolves/is observable
    prob_up: float           # P(forward return > 0), the falsifiable forecast
    horizon_days: int        # forward window in trading days
    rationale: str           # the economic mechanism, in words
    kill_condition: str      # what realized pattern falsifies this call's thesis
    registered_at: str       # UTC iso — MUST be < event_date

    def maturity(self) -> date:
        # calendar-day proxy for "event_date + horizon trading days"; scoring
        # gate only needs a conservative lower bound on when the window closes.
        from datetime import timedelta
        return _as_date(self.event_date) + timedelta(days=self.horizon_days)


@dataclass(frozen=True)
class ScoredCall:
    event_id: str
    prob_up: float
    realized_return: float
    outcome: int             # 1 if realized_return > 0 else 0
    brier: float             # (prob_up - outcome)^2
    scored_at: str


def _as_date(s: str) -> date:
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventLedger:
    """Append-only JSONL ledger of calls + a scored sidecar file."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.scored_path = self.path.with_suffix(".scored.jsonl")

    # ── registration ────────────────────────────────────────────────────
    def register_call(self, call: EventCall) -> EventCall:
        """Append a call. Idempotent on event_id. Raises on look-ahead."""
        if not (0.0 <= call.prob_up <= 1.0):
            raise ValueError("prob_up must be in [0, 1]")
        if call.horizon_days < 1:
            raise ValueError("horizon_days must be >= 1")
        reg = _as_date(call.registered_at)
        if reg >= _as_date(call.event_date):
            raise ValueError(
                f"look-ahead: registered_at {call.registered_at} not before "
                f"event_date {call.event_date}"
            )
        for existing in self.calls():
            if existing.event_id == call.event_id:
                return existing
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(call)) + "\n")
        return call

    def calls(self) -> list[EventCall]:
        return [EventCall(**r) for r in _read_jsonl(self.path)]

    def scored(self) -> list[ScoredCall]:
        return [ScoredCall(**r) for r in _read_jsonl(self.scored_path)]

    # ── scoring ─────────────────────────────────────────────────────────
    def score_matured(
        self,
        realized_return_fn: RealizedReturnFn,
        as_of: str | None = None,
    ) -> list[ScoredCall]:
        """Score every unscored call whose maturity <= as_of and whose realized
        return is available. Returns the newly scored calls."""
        as_of_d = _as_date(as_of) if as_of else datetime.now(timezone.utc).date()
        done = {s.event_id for s in self.scored()}
        new: list[ScoredCall] = []
        for call in self.calls():
            if call.event_id in done or call.maturity() > as_of_d:
                continue
            r = realized_return_fn(call.ticker, call.event_date, call.horizon_days)
            if r is None:
                continue  # data not yet available — stays pending, never faux-0
            outcome = 1 if r > 0 else 0
            scored = ScoredCall(
                event_id=call.event_id, prob_up=round(call.prob_up, 4),
                realized_return=round(float(r), 6), outcome=outcome,
                brier=round((call.prob_up - outcome) ** 2, 6),
                scored_at=_utcnow_iso(),
            )
            _append_jsonl(self.scored_path, asdict(scored))
            new.append(scored)
        return new

    # ── calibration ─────────────────────────────────────────────────────
    def calibration_summary(self, n_buckets: int = 5) -> dict:
        scored = self.scored()
        return calibration_summary(scored, n_buckets=n_buckets)


def calibration_summary(scored: Iterable[ScoredCall], n_buckets: int = 5) -> dict:
    scored = list(scored)
    n = len(scored)
    if n == 0:
        return {"n": 0, "note": "no scored calls yet"}
    brier = sum(s.brier for s in scored) / n
    hit_rate = sum(s.outcome for s in scored) / n
    mean_prob = sum(s.prob_up for s in scored) / n
    # Brier of the always-predict-base-rate baseline; skill = 1 - brier/baseline
    base = hit_rate * (1 - hit_rate)
    brier_skill = (1 - brier / base) if base > 0 else 0.0

    buckets = []
    width = 1.0 / n_buckets
    for b in range(n_buckets):
        lo, hi = b * width, (b + 1) * width
        grp = [s for s in scored if (lo <= s.prob_up < hi) or (b == n_buckets - 1 and s.prob_up == 1.0)]
        if grp:
            buckets.append({
                "bucket": f"[{lo:.1f},{hi:.1f})",
                "n": len(grp),
                "mean_predicted": round(sum(s.prob_up for s in grp) / len(grp), 4),
                "realized_hit_rate": round(sum(s.outcome for s in grp) / len(grp), 4),
            })
    return {
        "n": n,
        "brier": round(brier, 5),
        "brier_skill_vs_baserate": round(brier_skill, 4),
        "mean_predicted_prob_up": round(mean_prob, 4),
        "realized_hit_rate": round(hit_rate, 4),
        "calibration_table": buckets,
        "note": ("brier_skill > 0 means the calls beat their own base-rate; "
                 "this forward, pre-registered record is the product, not a backtest."),
    }


def _read_jsonl(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _append_jsonl(path: Path, row: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
