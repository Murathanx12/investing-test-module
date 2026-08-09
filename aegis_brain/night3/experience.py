"""EXPERIENCE — the canonical unit of learning, and the episodic memory over it.

Design authority: `aegis-finance/docs/DESIGN_MEMORY_TAXONOMY_2026-08-09.md` §1-2.

One record per GRADED DECISION. Not per event, not per claim: the thing worth
learning from is a decision that had a consequence. Free text exists only in
`lesson_text`, which the engine never parses — every field the engine acts on
is an enum or a number, because free text is ungradeable and invites the model
to narrate instead of commit.

Two properties this module enforces rather than documents:

  * **Loud failure.** A missing or out-of-range required field raises. A silent
    default here would poison every downstream posterior with a number nobody
    chose, which is the house failure mode.
  * **Append-only + write-once.** `ExperienceStore.append` refuses to rewrite an
    existing experience_id with different content. History does not get edited.

The episodic memory (`retrieve`) is deterministic engine code: kNN over
standardized fingerprints, with an absolute **outcome embargo** — an experience
is visible at time t only if its outcome resolved strictly before t. There is no
model-specific logic anywhere in this file; swapping the LLM changes `model_id`
and nothing else.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

BRAIN_VERSION = "night3-1.0"

# ── frozen enums (the engine acts on these; lesson_text is for humans only) ──
DIRECTIONS = ("BUY", "HOLD", "SELL")

THESES = ("value", "profitability", "momentum", "low_volatility",
          "reversal", "quality_at_price", "insufficient_information")

ATTRIBUTIONS = ("thesis_played_out", "thesis_wrong", "regime_dominated",
                "idiosyncratic_shock", "too_early", "costs_ate_it",
                "unattributed")

OUTCOME_CLASSES = ("big_win", "win", "flat", "loss", "big_loss")

# fingerprint feature order is FROZEN — kNN distance is meaningless if the
# vector layout can drift between writer and reader
FINGERPRINT_FEATURES = ("pct_ret_12m", "pct_vol_12m", "pct_gross_profit",
                        "pct_book_to_market", "pct_mom_12_1", "pct_size")

_REQUIRED_NUMERIC = ("confidence", "expected_return", "horizon_months",
                     "realized_return", "benchmark_return", "abnormal_return",
                     "error")


@dataclass(frozen=True)
class Experience:
    """One graded decision. Every field is required; there are no silent defaults."""

    # ── what was known, and by whom ─────────────────────────────────────────
    ts: str                                # decision timestamp (simulated clock)
    information_state_hash: str            # hash of everything the decider saw
    market_regime: str                     # WALK-FORWARD label only
    event_class: str                       # decision class (e.g. monthly_slate)
    fingerprint: tuple[float, ...]         # FINGERPRINT_FEATURES order
    model_id: str
    brain_version: str
    # ── what was decided ────────────────────────────────────────────────────
    thesis: str                            # THESES
    direction: str                         # DIRECTIONS
    confidence: float                      # elicited, PRE-calibration, [0,1]
    expected_return: float                 # the falsifiable part
    horizon_months: int
    target: float                          # exit-up condition, declared up front
    invalidation: float                    # exit-down condition
    # ── what happened ───────────────────────────────────────────────────────
    resolved_ts: str                       # when the outcome became knowable
    realized_return: float
    benchmark_return: float
    abnormal_return: float                 # realized − benchmark
    error: float                           # realized − expected
    attribution: str                       # ATTRIBUTIONS
    outcome_class: str                     # OUTCOME_CLASSES
    lesson_text: str                       # humans read this; the engine never parses it
    entity_key: str = ""                   # permno — never a ticker string (KTD-Fin)

    def __post_init__(self) -> None:
        if self.direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of {DIRECTIONS}, got {self.direction!r}")
        if self.thesis not in THESES:
            raise ValueError(f"thesis must be one of {THESES}, got {self.thesis!r}")
        if self.attribution not in ATTRIBUTIONS:
            raise ValueError(f"attribution must be one of {ATTRIBUTIONS}, got {self.attribution!r}")
        if self.outcome_class not in OUTCOME_CLASSES:
            raise ValueError(f"outcome_class must be one of {OUTCOME_CLASSES}, "
                             f"got {self.outcome_class!r}")
        if len(self.fingerprint) != len(FINGERPRINT_FEATURES):
            raise ValueError(f"fingerprint must have {len(FINGERPRINT_FEATURES)} "
                             f"features in {FINGERPRINT_FEATURES} order, "
                             f"got {len(self.fingerprint)}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence out of [0,1]: {self.confidence}")
        if self.horizon_months <= 0:
            raise ValueError("horizon_months must be positive")
        if self.resolved_ts <= self.ts:
            raise ValueError("resolved_ts must be strictly after ts — an "
                             "experience that resolves at or before its own "
                             "decision is a look-ahead bug, not an experience")
        for name in _REQUIRED_NUMERIC:
            v = getattr(self, name)
            if v is None or not np.isfinite(float(v)):
                raise ValueError(f"{name} must be a finite number, got {v!r}")
        for name in ("ts", "information_state_hash", "market_regime",
                     "event_class", "model_id", "brain_version", "resolved_ts"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required and must be non-empty")

    @property
    def experience_id(self) -> str:
        """Stable hash of (information_state, decision, model_id) — per design §1."""
        payload = json.dumps(
            {"information_state_hash": self.information_state_hash,
             "direction": self.direction, "ts": self.ts,
             "entity_key": self.entity_key, "model_id": self.model_id},
            sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["fingerprint"] = list(self.fingerprint)
        d["experience_id"] = self.experience_id
        return d


def classify_outcome(abnormal_return: float) -> str:
    """Deterministic outcome class. Thresholds frozen here, not per-caller."""
    if abnormal_return >= 0.10:
        return "big_win"
    if abnormal_return >= 0.02:
        return "win"
    if abnormal_return > -0.02:
        return "flat"
    if abnormal_return > -0.10:
        return "loss"
    return "big_loss"


def attribute(direction: str, abnormal_return: float, expected_return: float,
              regime_abnormal: float) -> str:
    """Deterministic attribution enum.

    `regime_abnormal` is how the whole slate did versus the benchmark that
    month: if everything moved together, the regime dominated and the individual
    thesis explains little. Attribution is computed by the engine, never
    elicited from the model — a model grading its own reasons is not evidence.
    """
    intended = 1.0 if direction == "BUY" else (-1.0 if direction == "SELL" else 0.0)
    signed = intended * abnormal_return
    if abs(regime_abnormal) >= 0.05 and abs(abnormal_return - regime_abnormal) < 0.02:
        return "regime_dominated"
    if intended == 0.0:
        return "unattributed"
    if signed > 0.02:
        return "thesis_played_out"
    if signed < -0.10:
        return "idiosyncratic_shock"
    if signed < -0.02:
        return "thesis_wrong"
    if abs(expected_return) > 0.05 and abs(abnormal_return) < 0.01:
        return "too_early"
    return "unattributed"


class ExperienceStore:
    """Append-only JSONL store with write-once semantics and kNN retrieval."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rows: list[dict] = []
        self._ids: set[str] = set()
        # retrieval fast path: experiences are appended in decision order, so
        # resolved_ts is non-decreasing and the embargo cutoff is a bisect
        # rather than a scan of every row on every one of ~8k queries
        self._fp: np.ndarray | None = None
        self._resolved: list[str] = []
        self._sorted = True
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    self._rows.append(r)
                    self._ids.add(r["experience_id"])
            self._reindex()

    def _reindex(self) -> None:
        self._fp = (np.array([r["fingerprint"] for r in self._rows], dtype=float)
                    if self._rows else None)
        self._resolved = [r["resolved_ts"] for r in self._rows]
        self._sorted = all(a <= b for a, b in zip(self._resolved, self._resolved[1:]))
        if not self._sorted:
            logger.warning("experience store is not in resolution order — "
                           "falling back to a full scan for the embargo "
                           "(correct, just slower)")

    def _cutoff(self, ts: str) -> int | None:
        """Index of the first row with resolved_ts >= ts, or None if unsorted."""
        if not self._sorted:
            return None
        import bisect
        return bisect.bisect_left(self._resolved, ts)

    def __len__(self) -> int:
        return len(self._rows)

    def append(self, exp: Experience) -> bool:
        """Write one experience. Returns False if already present (idempotent).

        Raises if the same id arrives with different content — that means two
        different things are claiming the same identity, which is a bug worth
        stopping for, not a collision worth tolerating.
        """
        d = exp.as_dict()
        eid = d["experience_id"]
        if eid in self._ids:
            existing = next(r for r in self._rows if r["experience_id"] == eid)
            if {k: v for k, v in existing.items() if k != "lesson_text"} != \
               {k: v for k, v in d.items() if k != "lesson_text"}:
                raise ValueError(f"experience_id {eid} already exists with "
                                 "different content — refusing to overwrite")
            return False
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(d, separators=(",", ":"), default=str) + "\n")
        self._rows.append(d)
        self._ids.add(eid)
        if self._sorted and self._resolved and d["resolved_ts"] < self._resolved[-1]:
            self._sorted = False
        self._resolved.append(d["resolved_ts"])
        self._fp = None                      # invalidate; rebuilt on next query
        return True

    def extend(self, exps: list[Experience]) -> int:
        return sum(self.append(e) for e in exps)

    def _matrix(self) -> np.ndarray:
        if self._fp is None:
            self._fp = (np.array([r["fingerprint"] for r in self._rows], dtype=float)
                        if self._rows else np.zeros((0, len(FINGERPRINT_FEATURES))))
        return self._fp

    # ── episodic retrieval ──────────────────────────────────────────────────
    def available_at(self, ts: str) -> list[dict]:
        """OUTCOME EMBARGO: only experiences resolved strictly before ts."""
        cut = self._cutoff(ts)
        if cut is None:
            return [r for r in self._rows if r["resolved_ts"] < ts]
        return self._rows[:cut]

    def retrieve(self, fingerprint: tuple[float, ...], ts: str, k: int = 8,
                 event_class: str | None = None) -> list[dict]:
        """k nearest resolved experiences by Euclidean distance on the
        standardized fingerprint. Deterministic, model-agnostic, ties broken by
        experience_id so the same query always returns the same neighbours."""
        cut = self._cutoff(ts)
        if cut is None:                      # unsorted store: correct, slower
            idx = [i for i, r in enumerate(self._rows) if r["resolved_ts"] < ts]
        else:
            idx = list(range(cut))
        if event_class is not None:
            idx = [i for i in idx if self._rows[i]["event_class"] == event_class]
        if not idx:
            return []
        q = np.asarray(fingerprint, dtype=float)
        M = self._matrix()
        if M.shape[1] != q.shape[0]:
            raise ValueError("fingerprint width mismatch between query and store")
        sub = M[idx] if len(idx) != len(self._rows) else M
        # percentiles are already on a common 0-100 scale; dividing by 100 keeps
        # the distance interpretable without fitting anything to the pool
        d = np.linalg.norm((sub - q) / 100.0, axis=1)
        take = min(k, len(idx))
        cand = np.argpartition(d, take - 1)[:take] if take < len(idx) else np.arange(len(idx))
        order = sorted(cand, key=lambda i: (float(d[i]),
                                            self._rows[idx[i]]["experience_id"]))
        out = []
        for i in order[:k]:
            r = dict(self._rows[idx[i]])
            r["_distance"] = round(float(d[i]), 4)
            out.append(r)
        return out

    def summarize_neighbours(self, neighbours: list[dict]) -> dict:
        """Aggregate a retrieval into the few numbers a decider can act on.

        This is the ONLY thing shown to the model from episodic memory: base
        rates and mean outcomes with their n. A generalization without its n is
        rejected by design (taxonomy §2), so n travels with every number.
        """
        if not neighbours:
            return {"n": 0}
        buys = [r for r in neighbours if r["direction"] == "BUY"]
        ab = [float(r["abnormal_return"]) for r in neighbours]
        out = {
            "n": len(neighbours),
            "mean_abnormal_return": round(float(np.mean(ab)), 4),
            "frac_beat_benchmark": round(float(np.mean([a > 0 for a in ab])), 3),
            "mean_error": round(float(np.mean([r["error"] for r in neighbours])), 4),
        }
        if buys:
            bab = [float(r["abnormal_return"]) for r in buys]
            out["n_buy"] = len(buys)
            out["buy_frac_beat_benchmark"] = round(float(np.mean([a > 0 for a in bab])), 3)
            out["buy_mean_abnormal_return"] = round(float(np.mean(bab)), 4)
        cls: dict[str, int] = {}
        att: dict[str, int] = {}
        for r in neighbours:
            cls[r["outcome_class"]] = cls.get(r["outcome_class"], 0) + 1
            att[r["attribution"]] = att.get(r["attribution"], 0) + 1
        out["outcome_classes"] = dict(sorted(cls.items(), key=lambda kv: -kv[1]))
        out["attributions"] = dict(sorted(att.items(), key=lambda kv: -kv[1]))
        return out


def required_fields() -> tuple[str, ...]:
    return tuple(f.name for f in fields(Experience))
