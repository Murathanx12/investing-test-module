"""DGP-A and DGP-B null-panel generators (design §2).

DGP-A **v6** (primary):
    r*[i,t] = rf[π(t)] + beta[i]·(f[π(t)] − f̄) + c[t]·sigma[i,t]·z*[i,t]

Version history — every rejection was an F8 catch, kept here as the record:
  v1 REJECTED (13/20 signals leaked, |IC| to 0.014): factor-premium channel
     (real E[f]>0 × real betas) + delist-stamp death channel.
  v2 REJECTED (worse, 18/20, |IC| to 0.057): sigma-stratification
     concentrated per-firm alpha left inside z (intercept bug).
  v3 REJECTED: alpha fix barely moved it. Payoff diagnostic split the leak:
     sigma-family ICs carry NO money (rank/skew artifact — zero-alpha does
     NOT imply zero-rank-IC under heteroskedastic skew), but time-series
     signals harvested REAL factor autocorrelation (st_reversal -37bps/mo
     t=-3.6). Consequences: factor months are permuted per rep (π), and F8
     gates on the PAYOFF null (mean decile excess), rank-IC demoted to a
     reported diagnostic.
  v4: adds time-varying rolling sigma[i,t] (pooled kurtosis was 105 vs real
     494 with flat sigma — the tail lives in vol regimes).
  v5: sigma[i,t] LAGGED (.shift(1)) — v4's contemporaneous rolling window let
     "high sigma_t stratum" condition on |resid_t|, and right-skewed residuals
     made magnitude-selecting signals collect the skew (momentum AND reversal
     both won ~+26bps). F8 payoff-null PASS at v5; F1 22.9% / F3 kurt 90%
     still out of tolerance.
  v6: PER-MONTH RE-STANDARDIZATION of the residual term (the F1/F3 close).
     The stratified permutation pairs sigma[i] with z[j] within a sigma
     DECILE, and a decile is wide — especially the top one, where sigma spans
     multiples. Real residuals carry positive within-stratum cov(sigma², z²)
     structure the pairing destroys: a fat z from a modest-sigma firm lands
     on the stratum's highest-sigma firm and mints a monster return that the
     real panel never printed. That inflates pooled tails (F3 kurtosis 939 vs
     real 494) and inflates idiosyncratic variance, which depresses pairwise
     correlation (F1, worst in the small tercile where within-stratum sigma
     dispersion is widest). Fix: scale month t's residual term by

         c[t] = RMS_cs(resid_real[t,:]) / sqrt(E_π[RMS²_cs(sigma[t,:]·z*[t,:])])

     i.e. divide the synthetic month-t residual cross-section by its own
     (expected) scale and multiply by the real month-t cross-sectional scale.
     Both numerator and denominator are functions of the REAL panel only —
     c[t] is DETERMINISTIC, never a function of the realized permutation.
     Neutrality: c[t]·sigma[i,t] is therefore just another deterministic vol
     surface, so the v5 null argument applies verbatim (z* exchangeable
     within lagged-sigma strata); and a constant shared by every firm in the
     month cannot create cross-sectional selection, so the v4 conditioning
     channel (which was per-firm, contemporaneous) cannot re-enter. We do
     NOT scale by contemporaneous rolling sigma and we do NOT match realized
     (permutation-dependent) dispersion — both would weaken the provable
     null. F8 re-verified empirically after this change.

The v2 changes (kept in v4), from the original design doc:

1. **Factors are DEMEANED for generation** (f − f̄ over the panel window).
   v1 kept real E[f] > 0, so real time-invariant betas created persistent
   cross-sectional expected-return differences — every beta-correlated
   signal (sharpe_12m, trend_ma10, consistency...) picked up the premium.
   The design's "E[rank-IC]=0 exactly" claim was wrong for the factor term.
   Demeaning equalizes E[r*] across firms while keeping factor co-movement
   and crisis months (dispersion) intact.
2. **No real-return delist stamp.** v1 stamped each dead firm's real final
   -month return; death is predictable from formation characteristics
   (price_level +0.014, dd_from_12m_high −0.011, amihud −0.012 = the death
   signature). v2 keeps the real truncation DATE (universe attrition
   preserved) but the final month is an ordinary synthetic return.
3. **Permutation is stratified by sigma decile within month.** v1's free
   cross-pairing destroyed the joint sigma×z tail: real pooled kurtosis 494
   vs synthetic 99 (F3 fail). Extreme residuals stay attached to high-vol
   slots; exchangeability within strata keeps the null exact.
4. **Real month_end_price is CARRIED, not regenerated** (like dollar_vol).
   v1's compounded prices drifted through the $-floor (F6: eligible names
   7.8% low). Carrying real prices makes eligibility and segment structure
   byte-identical to production (R4 exact). Price-based signals therefore
   see real formation histories — legitimate under the null because the
   synthetic future has no firm-linked component for them to predict.

DGP-B (fallback/cross-check): real panel, realized returns permuted across
firms within each month. Zero alpha by construction; supports FDR only.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from aegis_brain.calibration.config import FACTOR_SET, MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel

logger = logging.getLogger(__name__)

FF_PARQUET = MODULE_ROOT / "data" / "ff_factors.parquet"
FF_VINTAGE = MODULE_ROOT / "data" / "ff_factors_VINTAGE.json"

MIN_OBS_FOR_BETA = 24     # firms below this get market-only beta = 1
SIGMA_FLOOR = 1e-4        # a zero residual vol would freeze a firm's returns


N_SIGMA_STRATA = 10
SIGMA_ROLL_MONTHS = 12
SIGMA_ROLL_MIN = 6


@dataclass
class DGPAInputs:
    """Everything gen_null_panel needs, computed ONCE from the real panel."""

    months: pd.DatetimeIndex          # panel month index
    symbols: pd.Index                 # panel columns
    beta: np.ndarray                  # (n_sym, n_fac)
    sigma_t: np.ndarray               # (n_month, n_sym) rolling residual vol — v4:
                                      #   time-VARYING so vol clustering survives
    c_t: np.ndarray                   # (n_month,) v6 per-month re-standardization,
                                      #   deterministic (real panel only)
    z: np.ndarray                     # (n_month, n_sym) standardized residuals, NaN-preserving
    fac: np.ndarray                   # (n_month, n_fac) real factor returns (record)
    fac_centered: np.ndarray          # (n_month, n_fac) demeaned — the generator input
    rf: np.ndarray                    # (n_month,)
    real_ret: pd.DataFrame            # fidelity reference
    real_price: pd.DataFrame          # carried into synthetic panels (v2 §4)
    real_dollar_vol: pd.DataFrame
    delist_month: dict[str, pd.Timestamp]
    n_beta_defaulted: int             # firms that fell back to market-only beta
    vintage: dict


def load_factors(months: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray, dict]:
    """Real factor matrix + rf aligned to the panel months. Raises on any gap —
    a silently NaN-filled factor month would flow into every synthetic panel."""
    ff = pd.read_parquet(FF_PARQUET)
    vintage = json.loads(FF_VINTAGE.read_text(encoding="utf-8"))
    ff = ff.reindex(months)
    if ff[list(FACTOR_SET)].isna().any().any() or ff["rf"].isna().any():
        missing = ff.index[ff[list(FACTOR_SET)].isna().any(axis=1)]
        raise ValueError(f"factor vintage missing panel months: {list(missing[:5])}")
    return ff[list(FACTOR_SET)].to_numpy(), ff["rf"].to_numpy(), vintage


def _sigma_strata(sigma_row: np.ndarray, valid: np.ndarray) -> list[np.ndarray]:
    """Month-t sigma-decile strata over the valid columns. ONE definition,
    shared by the generator and by the c_t computation — if these ever
    diverged, c_t would re-standardize against the wrong expectation."""
    order = np.argsort(sigma_row[valid], kind="stable")
    return [g for g in np.array_split(valid[order],
                                      min(N_SIGMA_STRATA, valid.size)) if g.size]


def _restandardization_c(resid: np.ndarray, sigma_t: np.ndarray,
                         z: np.ndarray) -> np.ndarray:
    """v6: deterministic per-month residual re-standardization constants.

    c[t] = RMS of the real month-t residual cross-section, divided by the
    square root of the EXPECTED (over stratified permutations) mean square of
    the synthetic residual sigma[i]·z*[i]:  E[(sigma_i z_{π(i)})²] =
    sigma_i² · mean_{j∈stratum(i)}(z_j²). Every input is real-panel-only, so
    c is deterministic; months with no valid names keep c=1.
    """
    T = resid.shape[0]
    c = np.ones(T)
    for t in range(T):
        valid = np.flatnonzero(~np.isnan(z[t]))
        if not valid.size:
            continue
        v_real = np.nanmean(resid[t, valid] ** 2)
        v_exp = 0.0
        for grp in _sigma_strata(sigma_t[t], valid):
            v_exp += float((sigma_t[t, grp] ** 2).sum()) * float(
                np.mean(z[t, grp] ** 2))
        v_exp /= valid.size
        if v_exp > 0 and v_real > 0:
            c[t] = np.sqrt(v_real / v_exp)
    return c


def build_dgpa_inputs(panel: Panel) -> DGPAInputs:
    """One-time decomposition of the real panel into factor + residual parts."""
    months = panel.monthly_ret.index
    symbols = panel.monthly_ret.columns
    fac, rf, vintage = load_factors(months)

    R = panel.monthly_ret.astype("float64").to_numpy()   # (T, N)
    excess = R - rf[:, None]
    T, N = R.shape
    K = fac.shape[1]

    beta = np.zeros((N, K))
    alpha = np.zeros(N)
    sigma = np.full(N, np.nan)
    n_defaulted = 0
    X_full = np.column_stack([np.ones(T), fac])
    for j in range(N):
        y = excess[:, j]
        ok = ~np.isnan(y)
        if ok.sum() >= MIN_OBS_FOR_BETA:
            coef, *_ = np.linalg.lstsq(X_full[ok], y[ok], rcond=None)
            alpha[j] = coef[0]
            beta[j] = coef[1:]
            resid = y[ok] - X_full[ok] @ coef
            sigma[j] = resid.std(ddof=K + 1) if ok.sum() > K + 1 else resid.std()
        else:
            beta[j, 0] = 1.0                        # market-only fallback
            n_defaulted += 1
            resid = y[ok] - fac[ok, 0]
            alpha[j] = resid.mean() if ok.sum() else 0.0
            resid = resid - alpha[j]
            sigma[j] = resid.std(ddof=1) if ok.sum() >= 3 else np.nan
    # a firm with no measurable residual vol gets the cross-sectional median —
    # freezing it at zero would create a synthetic firm with deterministic returns
    med = np.nanmedian(sigma)
    sigma = np.where(np.isnan(sigma) | (sigma < SIGMA_FLOOR), med, sigma)

    # The intercept MUST be inside the fitted part: leaving each firm's alpha
    # in z gave every firm a persistent alpha-flavored mean residual, which
    # sigma-stratified permutation then concentrated into the strata — the
    # 2026-08-04 F8 blow-up (vol_12m_low IC 0.057). The null is alpha-free by
    # construction: real alphas (real anomalies) do not enter synthetic panels.
    fitted = alpha[None, :] + fac @ beta.T          # (T, N)
    resid = excess - fitted
    resid[np.isnan(R)] = np.nan

    # v4: TIME-VARYING sigma. Full-sample sigma flattened the joint tail
    # (pooled kurtosis 105 vs real 494) because real extreme months come from
    # firms in high-vol REGIMES. Rolling residual vol restores vol clustering;
    # leading months take the firm's first estimate (bfill), the floor and a
    # cross-median fallback keep every valid cell strictly positive.
    resid_df = pd.DataFrame(resid, index=months, columns=symbols)
    # .shift(1): month t's sigma must use months <= t-1 ONLY. With t inside
    # its own window, "high sigma_t stratum" conditions on |resid_t| large,
    # and right-skewed residuals make those disproportionately POSITIVE — v4's
    # F8 kill (momentum AND reversal both won ~+26bps: anything selecting on
    # magnitude collected the skew). Lagging removes the conditioning.
    sig_df = (resid_df.rolling(SIGMA_ROLL_MONTHS, min_periods=SIGMA_ROLL_MIN)
              .std().shift(1))
    sig_df = sig_df.bfill().ffill()
    med = float(np.nanmedian(sig_df.to_numpy()))
    sig_df = sig_df.clip(lower=SIGMA_FLOOR).fillna(med)
    sigma_t = sig_df.to_numpy()

    z = resid / sigma_t
    z[np.isnan(R)] = np.nan                         # preserve the NaN mask exactly

    c_t = _restandardization_c(resid, sigma_t, z)

    return DGPAInputs(
        months=months, symbols=symbols, beta=beta, sigma_t=sigma_t, c_t=c_t, z=z,
        fac=fac, fac_centered=fac - fac.mean(axis=0, keepdims=True), rf=rf,
        real_ret=panel.monthly_ret, real_price=panel.month_end_price,
        real_dollar_vol=panel.monthly_dollar_vol,
        delist_month=dict(panel.delist_month),
        n_beta_defaulted=n_defaulted, vintage=vintage,
    )


def gen_null_panel(inputs: DGPAInputs, rng: np.random.Generator) -> Panel:
    """One DGP-A v4 null replication.

    - Residuals permuted across firms within (month, per-month sigma_t decile)
      — exchangeable within strata, joint sigma-z tail preserved.
    - Factor MONTHS permuted per replication: every real month appears exactly
      once (crises preserved as units) but serial correlation is destroyed —
      v3's F8 payoff diagnostic showed real factor autocorrelation paying
      st_reversal -37bps/mo (t -3.6) in the "null"; a null may not contain
      harvestable structure.
    - No delist stamp; real prices and dollar volumes carried.
    """
    z = inputs.z
    sigma_t = inputs.sigma_t
    T, N = z.shape
    z_star = np.full_like(z, np.nan)
    for t in range(T):
        valid = np.flatnonzero(~np.isnan(z[t]))
        if not valid.size:
            continue
        for grp in _sigma_strata(sigma_t[t], valid):
            z_star[t, grp] = z[t, grp[rng.permutation(grp.size)]]

    perm = rng.permutation(T)                       # factor-calendar permutation
    fac_used = inputs.fac_centered[perm]
    rf_used = inputs.rf[perm]

    r_star = (rf_used[:, None] + fac_used @ inputs.beta.T
              + (inputs.c_t[:, None] * sigma_t) * z_star)
    r_star[np.isnan(z)] = np.nan
    ret = pd.DataFrame(r_star, index=inputs.months, columns=inputs.symbols)

    return Panel(
        monthly_ret=ret,
        month_end_price=inputs.real_price,           # carried real (v2 §4)
        monthly_dollar_vol=inputs.real_dollar_vol,   # carried real (design §2.3)
        delist_month=dict(inputs.delist_month),
    )


def gen_dgpb_null(panel: Panel, rng: np.random.Generator) -> Panel:
    """DGP-B: real panel with realized returns permuted across firms within
    each month. Formation-side data stays fully real; alpha is exactly zero."""
    R = panel.monthly_ret.astype("float64").to_numpy().copy()
    for t in range(R.shape[0]):
        valid = np.flatnonzero(~np.isnan(R[t]))
        if valid.size:
            R[t, valid] = R[t, valid[rng.permutation(valid.size)]]
    return Panel(
        monthly_ret=pd.DataFrame(R, index=panel.monthly_ret.index,
                                 columns=panel.monthly_ret.columns),
        month_end_price=panel.month_end_price,
        monthly_dollar_vol=panel.monthly_dollar_vol,
        delist_month=dict(panel.delist_month),
    )
