"""StrategySpec — the frozen, hashable description of one portfolio.

A spec is the unit of pre-registration. Its hash goes in the registry BEFORE
the run; changing any field is a new strategy with a new ID, never a retry
(CANON §6). Nothing in the spec is fitted at run time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field


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

    def as_dict(self) -> dict:
        d = asdict(self)
        d["signals"] = [list(s) for s in self.signals]
        d["tags"] = list(self.tags)
        return d

    def spec_hash(self) -> str:
        payload = {k: v for k, v in self.as_dict().items()
                   if k not in ("hypothesis", "notes")}
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
