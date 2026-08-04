"""Alpha injection (design §3) — the 21st candidate's world.

The injected object is a latent characteristic X (AR(1), phi = 0.9, cross-
sectionally standardized per month). The factory never sees X; it sees a
library signal S_observed = rho·X + sqrt(1-rho²)·noise. The NOISE IS ALSO
AR(1) phi = 0.9 (a decision, recorded here): the library measures a
persistent characteristic imperfectly but is itself a persistent signal, like
every real library signal. IID noise would instead make S jump monthly and
turnover costs would eat the edge for a reason that has nothing to do with
measurement honesty — that channel is I2's job (decay), not rho's.

Return injection is GROSS (the pipeline's own cost model must be allowed to
eat its share — that erosion is part of what M1 measures):

    dr[i, m+1] = k_m · 2 · (pct_rank_m(X[i,m]) − 0.5)      for i in mask_m

    k_m = k_base · w_m,   k_base = S_ann · SIGMA_HAT / (0.9 · sqrt(12))
    w_m = 1                                    (I1, I3, I4)
    w_m = exp(−m/τ) / mean_m'(exp(−m'/τ))      (I2, τ = 60; normalized so the
                                                FULL-SAMPLE mean k equals
                                                k_base → full-sample Sharpe
                                                hits the target)

pct_rank uses (rank − 0.5)/n, so the injection is EXACTLY mean-zero across
the injected set every month — the segment EW benchmark is untouched by
construction; only within-segment spread is added.

Injection breadth per design (mask_m, all formation-month information):
    I1, I2 — eligible ∩ largemid          (the graduating segment)
    I3     — eligible ∩ small             (alpha the largemid gate cannot see)
    I4     — eligible                     (economy-wide, size-correlated X:
             X_I4 = 0.5·z_size + sqrt(0.75)·X_orth per month, z_size =
             cross-sectional z of log dollar volume)

Masks come from carried REAL price/dollar-volume, so they are identical for
every synthetic panel and are precomputed once.

CRN: one X and one noise draw per rep (seed = SEED_BASE + INJECT_SEED_OFFSET
+ rep), shared across every alpha level and design; only k_base and the
design transform differ. dr is applied only where the null panel has a
return (a dead firm cannot earn injected alpha); the S2 perfect-foresight
gate measures the realized mapping, skips included.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from aegis_brain.calibration.config import (
    AR1_PHI,
    I2_DECAY_TAU_MONTHS,
    I4_SIZE_CORR,
    SIGMA_HAT_MONTHLY,
)
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.explore import segment_mask
from aegis_brain.factory.signals import FactorySignal


def k_base_for(s_ann: float) -> float:
    """k = S_ann · sigma_hat / (0.9 · sqrt(12)) — design §3.2."""
    return s_ann * SIGMA_HAT_MONTHLY / (0.9 * np.sqrt(12.0))


def decay_weights(n_months: int, design: str) -> np.ndarray:
    """Per-formation-month multiplier w_m, mean exactly 1 over the panel."""
    if design == "I2":
        w = np.exp(-np.arange(n_months) / I2_DECAY_TAU_MONTHS)
        return w / w.mean()
    if design in ("I1", "I3", "I4"):
        return np.ones(n_months)
    raise ValueError(f"unknown design {design!r}")


def _ar1_matrix(shape: tuple[int, int], rng: np.random.Generator,
                phi: float = AR1_PHI) -> np.ndarray:
    """(T x N) AR(1) columns, unit marginal variance."""
    T, N = shape
    out = np.empty((T, N))
    out[0] = rng.standard_normal(N)
    innov_scale = np.sqrt(1.0 - phi * phi)
    for t in range(1, T):
        out[t] = phi * out[t - 1] + innov_scale * rng.standard_normal(N)
    return out


def _cs_standardize(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Standardize each row over its valid cells; invalid cells -> NaN."""
    out = np.full_like(a, np.nan)
    for t in range(a.shape[0]):
        v = valid[t]
        n = int(v.sum())
        if n < 2:
            continue
        row = a[t, v]
        sd = row.std()
        if sd <= 0:
            raise ValueError(f"degenerate characteristic cross-section at row {t}")
        out[t, v] = (row - row.mean()) / sd
    return out


@dataclass
class InjectionInputs:
    """Per-rep injection state, shared across all alpha levels and designs."""

    X: pd.DataFrame            # latent characteristic, cs-standardized
    S: pd.DataFrame            # observed library signal (rho-blended)
    rho: float
    masks: dict[str, pd.DataFrame]   # design -> injection mask (formation months)


def build_masks(panel: Panel) -> dict[str, pd.DataFrame]:
    """Injection breadth per design from carried-real price/volume (identical
    for every synthetic panel)."""
    elig = panel.eligible()
    return {
        "I1": elig & segment_mask(panel, "largemid"),
        "I2": elig & segment_mask(panel, "largemid"),
        "I3": elig & segment_mask(panel, "small"),
        "I4": elig,
    }


def build_injection_inputs(panel: Panel, rho: float,
                           rng: np.random.Generator) -> InjectionInputs:
    """X, S_observed and masks for one rep. `panel` supplies the calendar,
    the live-cell mask (real NaN structure) and real dollar volume."""
    ret = panel.monthly_ret
    valid = ret.notna().to_numpy()
    X_raw = _ar1_matrix(ret.shape, rng)
    noise_raw = _ar1_matrix(ret.shape, rng)
    X = _cs_standardize(X_raw, valid)
    noise = _cs_standardize(noise_raw, valid)
    S = rho * X + np.sqrt(1.0 - rho * rho) * noise
    return InjectionInputs(
        X=pd.DataFrame(X, index=ret.index, columns=ret.columns),
        S=pd.DataFrame(S, index=ret.index, columns=ret.columns),
        rho=rho,
        masks=build_masks(panel),
    )


def _design_X(inj: InjectionInputs, design: str, panel: Panel) -> pd.DataFrame:
    """The characteristic that actually earns alpha under this design."""
    if design != "I4":
        return inj.X
    dv = panel.monthly_dollar_vol.where(panel.monthly_dollar_vol > 0)
    logdv = np.log(dv)
    z_size = logdv.sub(logdv.mean(axis=1), axis=0).div(logdv.std(axis=1), axis=0)
    X4 = I4_SIZE_CORR * z_size + np.sqrt(1.0 - I4_SIZE_CORR**2) * inj.X
    return X4.where(inj.X.notna())


def _pct_ranks(x_row: pd.Series) -> pd.Series:
    """(rank − 0.5)/n over the given values — mean is exactly 0.5."""
    r = x_row.rank(method="average")
    return (r - 0.5) / len(x_row)


def delta_frame(panel_null: Panel, inj: InjectionInputs, design: str,
                s_ann: float) -> pd.DataFrame:
    """dr (months x symbols): the injected GROSS return increment.

    Zero everywhere except (m+1, i) with i in mask_m and a live null return.
    """
    ret = panel_null.monthly_ret
    months = ret.index
    k_base = k_base_for(s_ann)
    w = decay_weights(len(months), design)
    X = _design_X(inj, design, panel_null)
    mask = inj.masks[design]

    dr = pd.DataFrame(0.0, index=months, columns=ret.columns)
    if k_base == 0.0:
        return dr
    for m_pos in range(len(months) - 1):
        fm, tm = months[m_pos], months[m_pos + 1]
        in_mask = mask.loc[fm]
        x = X.loc[fm].dropna()
        x = x[x.index.isin(in_mask[in_mask].index)]
        if len(x) < 2:
            continue
        pct = _pct_ranks(x)
        d = k_base * w[m_pos] * 2.0 * (pct - 0.5)
        live = ret.loc[tm].reindex(d.index).notna()
        dr.loc[tm, d.index[live]] = d[live]
    return dr


def inject(panel_null: Panel, inj: InjectionInputs, design: str,
           s_ann: float) -> Panel:
    """Injected panel = null panel + dr. Prices/volumes/delistings carried."""
    dr = delta_frame(panel_null, inj, design, s_ann)
    return Panel(
        monthly_ret=panel_null.monthly_ret + dr,
        month_end_price=panel_null.month_end_price,
        monthly_dollar_vol=panel_null.monthly_dollar_vol,
        delist_month=dict(panel_null.delist_month),
    )


def injected_signal(inj: InjectionInputs) -> FactorySignal:
    """The 21st candidate: the library's imperfect view of X. Fresh
    (contaminated=False), direction +1, score independent of alpha level —
    CRN across the alpha grid is exact for the candidate's formation side."""
    S = inj.S

    def compute(panel: Panel) -> pd.DataFrame:
        return S

    return FactorySignal(
        name="injected_edge",
        hypothesis="M1 calibration: library signal rho-correlated with the "
                   "injected characteristic X",
        compute=compute,
        direction=+1,
    )
