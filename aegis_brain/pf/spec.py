"""StrategySpec — the frozen, hashable description of one portfolio.

A spec is the unit of pre-registration. Its hash goes in the registry BEFORE
the run; changing any field is a new strategy with a new ID, never a retry
(CANON §6). Nothing in the spec is fitted at run time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import MISSING, asdict, dataclass, field, fields


def _is_default(key: str, value, defaults: dict) -> bool:
    d = defaults.get(key, MISSING)
    return d is not MISSING and value == d


@dataclass(frozen=True)
class StrategySpec:
    name: str
    signals: tuple[tuple[str, float], ...]
    # ── universe ────────────────────────────────────────────────────────────
    segment: str = "small"                 # small | largemid | all
    min_names: int = 100                   # months with fewer eligible names skip
    # ── construction ────────────────────────────────────────────────────────
    top_n: int = 25                        # names held (fixed count, not a frac)
    weighting: str = "ew"                  # ew | score
    hold_band_mult: float = 3.0            # incumbency band = mult × top_n
    max_weight: float = 1.0                # per-name cap after weighting
    # ── trading ─────────────────────────────────────────────────────────────
    rebalance_months: int = 1              # 1 monthly, 3 quarterly
    cost_model: str = "flat25"             # flat25 | ko | flat0
    # ── window ──────────────────────────────────────────────────────────────
    first_month: str = "1963-07-31"
    last_month: str = "2022-12-31"
    # ── regime conditioning (walk-forward only; see engine) ─────────────────
    regime_rule: str = ""                  # "" | "bull_risk_on"
    # ── core-satellite blend (PF-2; fixed fraction, NOT a timing rule) ──────
    blend_market: float = 0.0              # constant share held in the market
    blend_fee_bps: float = 3.0             # index-fund expense on that sleeve
    # ── bookkeeping ─────────────────────────────────────────────────────────
    seed: int = 20260808
    family: str = "PF"
    hypothesis: str = ""
    notes: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.segment not in ("small", "largemid", "all"):
            raise ValueError(f"bad segment {self.segment!r}")
        if self.weighting not in ("ew", "score"):
            raise ValueError(f"bad weighting {self.weighting!r}")
        if self.cost_model not in ("flat25", "ko", "flat0"):
            raise ValueError(f"bad cost_model {self.cost_model!r}")
        if self.top_n < 5:
            raise ValueError("top_n < 5 is a lottery ticket, not a portfolio")
        if not self.signals:
            raise ValueError("a strategy needs at least one signal")
        tw = sum(abs(w) for _, w in self.signals)
        if tw <= 0:
            raise ValueError("signal weights sum to zero")
        if not 0.0 <= self.blend_market < 1.0:
            raise ValueError("blend_market must be in [0, 1) — a book that is "
                             "100% market is the benchmark, not a strategy")

    def as_dict(self) -> dict:
        d = asdict(self)
        d["signals"] = [list(s) for s in self.signals]
        d["tags"] = list(self.tags)
        return d

    def spec_hash(self) -> str:
        """Identity hash — v2 (PF-2 onward).

        Fields sitting at their default are OMITTED from the payload. That is
        what makes the hash stable when a later campaign adds a new optional
        knob: PF-2's `blend_market` did not exist during PF-1, and without this
        rule its mere existence would have silently renamed every PF-1
        artifact. Two specs that differ only in explicitly restating a default
        ARE the same portfolio, so collapsing them is correct, not a shortcut.

        Consequence, recorded rather than hidden: PF-1 hashes were computed
        under v1 (all fields included) and reproduce only at commit c01388f.
        The PF-1 receipts on disk keep their v1 names.
        """
        defaults = {f.name: f.default for f in fields(self)}
        payload = {k: v for k, v in self.as_dict().items()
                   if k not in ("hypothesis", "notes")
                   and not _is_default(k, getattr(self, k), defaults)}
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:12]

    def variant(self, **changes) -> "StrategySpec":
        """A NEW registered strategy, not an edit of this one."""
        d = {k: v for k, v in self.__dict__.items()}
        d.update(changes)
        if "name" not in changes:
            tag = "_".join(f"{k}-{v}" for k, v in sorted(changes.items()))
            d["name"] = f"{self.name}__{tag}"
        return StrategySpec(**d)
