"""The belief store — two timescales, uncertainty everywhere, no point estimates.

Frozen day-1 hyperparameters (RESEARCH_SYNTHESIS_2026-08-08_R1-R4 §D):

  FAST layer   hit-rate Beta per (claim_class, context_key); exponential
               forgetting with half-life 75 resolutions. Fast because
               calibration and attention drift; slow enough not to chase noise.
  SLOW layer   effect size, Normal-Normal, NO decay. Partial reset only on a
               changepoint signal (ESS x0.5, tau^2 x2 — never a hard reset).
  DEFLATION    resolutions that land together are not independent evidence.
               Tempered update with eta = 1/DEFF, DEFF = 1 + (m-1)*rho, rho=0.2.
               Six same-day resolutions therefore count as ~3.
  PRIORS       effect ~ N(0, (4 bps)^2)  (Chen-Velikov net-anomaly ceiling)
               sigma_theta = 0.75 in t-units (NOT the selection-filtered 3.0)
  IDENTIFIABILITY  per-cell effect estimates below n_eff 1000 are a category
               error at our resolution rate; the store REFUSES them and returns
               the pooled estimate with a flag.

The update signature takes a Resolution and nothing else. There is no method
that accepts a return, a P&L, or a portfolio value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aegis_brain.abn.core import Resolution

HALF_LIFE_RESOLUTIONS = 75.0
RHO_SAME_COHORT = 0.20
EFFECT_PRIOR_MEAN = 0.0
EFFECT_PRIOR_SD = 0.0004          # 4 bps
SIGMA_THETA_T_UNITS = 0.75
N_EFF_FOR_PER_CELL_EFFECT = 1000.0
PARTIAL_RESET_ESS = 0.5
PARTIAL_RESET_TAU2 = 2.0


def deff(m: int, rho: float = RHO_SAME_COHORT) -> float:
    """Design effect for m correlated resolutions in one cohort."""
    return 1.0 + max(m - 1, 0) * rho


@dataclass
class BetaHitRate:
    """Fast layer. Beta(a, b) with exponential forgetting per resolution."""

    a: float = 1.0
    b: float = 1.0
    n_updates: int = 0

    @property
    def decay(self) -> float:
        return 0.5 ** (1.0 / HALF_LIFE_RESOLUTIONS)

    def update(self, hit: bool, weight: float = 1.0) -> None:
        d = self.decay
        # forget toward the uniform prior, then add the tempered observation
        self.a = 1.0 + (self.a - 1.0) * d
        self.b = 1.0 + (self.b - 1.0) * d
        if hit:
            self.a += weight
        else:
            self.b += weight
        self.n_updates += 1

    @property
    def mean(self) -> float:
        return self.a / (self.a + self.b)

    @property
    def n_eff(self) -> float:
        return self.a + self.b - 2.0

    def interval(self, z: float = 1.96) -> tuple[float, float]:
        m, n = self.mean, self.a + self.b
        sd = math.sqrt(max(m * (1 - m) / (n + 1), 1e-12))
        return max(0.0, m - z * sd), min(1.0, m + z * sd)


@dataclass
class NormalEffect:
    """Slow layer. Normal-Normal conjugate on the effect size. No decay."""

    mean: float = EFFECT_PRIOR_MEAN
    var: float = EFFECT_PRIOR_SD ** 2
    n_eff: float = 0.0

    def update(self, observed: float, obs_sd: float, weight: float = 1.0) -> None:
        if obs_sd <= 0:
            raise ValueError("obs_sd must be positive — an effect with no "
                             "measurement error is not an observation")
        prec_prior = 1.0 / self.var
        prec_obs = weight / (obs_sd ** 2)
        new_var = 1.0 / (prec_prior + prec_obs)
        self.mean = new_var * (prec_prior * self.mean + prec_obs * observed)
        self.var = new_var
        self.n_eff += weight

    def partial_reset(self) -> None:
        """Changepoint response: widen, halve the evidence. NEVER a hard reset."""
        self.var *= PARTIAL_RESET_TAU2
        self.n_eff *= PARTIAL_RESET_ESS

    @property
    def sd(self) -> float:
        return math.sqrt(self.var)

    @property
    def t_stat(self) -> float:
        return self.mean / self.sd if self.sd > 0 else 0.0


@dataclass
class Cell:
    hits: BetaHitRate = field(default_factory=BetaHitRate)
    effect: NormalEffect = field(default_factory=NormalEffect)
    n_resolutions: int = 0


class PosteriorStore:
    """(claim_class, context_key) -> Cell, plus the pooled parent."""

    def __init__(self) -> None:
        self.cells: dict[tuple[str, str], Cell] = {}
        self.pooled: dict[str, Cell] = {}
        self.rejected_writes: list[str] = []

    def _cell(self, claim_class: str, context_key: str) -> Cell:
        k = (claim_class, context_key)
        if k not in self.cells:
            self.cells[k] = Cell()
        if claim_class not in self.pooled:
            self.pooled[claim_class] = Cell()
        return self.cells[k]

    # ── the ONLY write path ─────────────────────────────────────────────────
    def update(self, claim: dict, resolution: Resolution, *,
               cohort_size: int = 1, obs_sd: float | None = None) -> None:
        """Fold one RESOLVED claim into the beliefs. Resolutions only.

        `claim` is the ledger's stored claim dict; `resolution` must be a
        Resolution instance — a float, a P&L, or a dict is refused. That
        refusal is the D3 rule expressed as a type check.
        """
        if not isinstance(resolution, Resolution):
            self.rejected_writes.append(type(resolution).__name__)
            raise TypeError(
                "PosteriorStore.update accepts a Resolution and nothing else. "
                "Portfolio P&L may brake exposure; it has no write path into "
                "beliefs (D3).")
        if claim.get("abstain"):
            return                      # abstentions carry no evidence
        w = 1.0 / deff(cohort_size)
        cell = self._cell(claim["claim_class"], claim.get("context_key", "default"))
        pool = self.pooled[claim["claim_class"]]
        for c in (cell, pool):
            c.hits.update(bool(resolution.hit), weight=w)
            c.n_resolutions += 1
        if obs_sd:
            for c in (cell, pool):
                c.effect.update(float(resolution.realized), obs_sd, weight=w)

    # ── read ────────────────────────────────────────────────────────────────
    def hit_rate(self, claim_class: str, context_key: str = "default") -> dict:
        cell = self.cells.get((claim_class, context_key))
        pool = self.pooled.get(claim_class)
        if cell is None and pool is None:
            return {"available": False}
        src = cell if (cell and cell.hits.n_eff >= 10) else pool
        lo, hi = src.hits.interval()
        return {"available": True,
                "used": "cell" if src is cell else "pooled",
                "mean": round(src.hits.mean, 4),
                "ci95": [round(lo, 4), round(hi, 4)],
                "n_eff": round(src.hits.n_eff, 1),
                "n_resolutions": src.n_resolutions}

    def effect_size(self, claim_class: str, context_key: str = "default") -> dict:
        """Per-cell effect only where it is identified; pooled otherwise."""
        cell = self.cells.get((claim_class, context_key))
        pool = self.pooled.get(claim_class)
        if pool is None:
            return {"available": False}
        if cell and cell.effect.n_eff >= N_EFF_FOR_PER_CELL_EFFECT:
            src, used = cell.effect, "cell"
        else:
            src, used = pool.effect, "pooled"
        return {"available": True, "used": used,
                "mean": src.mean, "sd": src.sd, "t": round(src.t_stat, 3),
                "n_eff": round(src.n_eff, 1),
                "note": ("per-cell effect suppressed: n_eff below "
                         f"{N_EFF_FOR_PER_CELL_EFFECT:.0f} is unidentified at "
                         "our resolution rate" if used == "pooled" else "")}

    def changepoint(self, claim_class: str, context_key: str = "default") -> None:
        cell = self.cells.get((claim_class, context_key))
        if cell:
            cell.effect.partial_reset()

    def snapshot(self) -> dict:
        return {
            "cells": {f"{k[0]}|{k[1]}": {
                "hit_mean": round(v.hits.mean, 4),
                "hit_n_eff": round(v.hits.n_eff, 1),
                "n_resolutions": v.n_resolutions,
                "effect_mean": v.effect.mean, "effect_t": round(v.effect.t_stat, 3),
            } for k, v in self.cells.items()},
            "pooled": {k: {"hit_mean": round(v.hits.mean, 4),
                           "n_resolutions": v.n_resolutions}
                       for k, v in self.pooled.items()},
        }


class ExposureBrake:
    """P&L's ONLY legitimate role: it can cut exposure, never change a belief.

    Reads the posterior store (read-only) and a realized drawdown, and returns
    a multiplier in [0, 1]. It holds no reference that could write.
    """

    def __init__(self, store: PosteriorStore, *, dd_warn: float = 0.10,
                 dd_halt: float = 0.25) -> None:
        self._read_only_view = store.snapshot
        self.dd_warn, self.dd_halt = dd_warn, dd_halt

    def multiplier(self, drawdown: float) -> float:
        d = abs(min(drawdown, 0.0))
        if d >= self.dd_halt:
            return 0.0
        if d <= self.dd_warn:
            return 1.0
        span = self.dd_halt - self.dd_warn
        return round(1.0 - (d - self.dd_warn) / span, 3)
