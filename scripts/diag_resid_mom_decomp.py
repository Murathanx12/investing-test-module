"""DIAGNOSTIC (not a trial): why did residual momentum lose the IC?

INSTR-RESID-MOM rejected on 2026-07-30: small-cap rank IC t fell 3.05
(mom_12_1) -> 0.81 (resid_mom). Two competing explanations:

  H_tilt   The cross-sectional information in small-cap total momentum WAS the
           factor tilt. Residualising removes the tilt AND the information.
           (the write-up's conclusion)

  H_noise  A 36-month rolling OLS on illiquid small caps estimates betas so
           noisily that subtracting beta-hat * F injects sampling noise which
           swamps a real idiosyncratic signal.
           (external reviewer critique, 2026-07-30)

These make OPPOSITE, checkable predictions.

  Test A — decomposition. Score the SAME 11-month window three ways with an
  IDENTICAL functional form (mean/sd), using the SAME 36-month betas:
      total   = mean(excess)/sd(excess)
      fitted  = mean(beta'F)/sd(beta'F)      <- the tilt component
      resid   = mean(e)/sd(e)                 <- resid_mom itself
  H_tilt predicts the FITTED leg carries the IC. H_noise predicts it does not
  (under H_noise the information is idiosyncratic, so the tilt should be
  uninformative and the residual should merely be a noisy version of a real
  signal).

  Test B — estimation-error dose response. If the residual IC is destroyed by
  beta noise, then REDUCING beta noise must partially restore it. Two arms,
  each strictly less noisy than the frozen FF3/36m spec:
      capm_36   1 factor instead of 3 (fewer parameters -> less estimation error)
      ff3_60    60-month window instead of 36 (more observations -> less error)
  H_noise predicts IC rises monotonically as estimation error falls.
  H_tilt predicts IC stays near zero regardless.

⚠️ SCOPE. This is a POST-MORTEM on a REJECT that already stands. None of these
variants can graduate, be re-registered, or revive the family — the frozen kill
clause forbids parameter switching, and nothing here is scored against a bar.
The only question asked is WHY the null happened. Reported either way.

Usage:  python -m scripts.diag_resid_mom_decomp
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import segment_mask
from aegis_brain.factory.resid_mom import SIG_END, SIG_START, spliced_returns

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("resid_decomp")

EXPLORE_LO, EXPLORE_HI = pd.Timestamp("2004-01-31"), pd.Timestamp("2018-12-31")


def component_scores(panel, ff, factors: list[str], est_months: int) -> dict:
    """Return {'total','fitted','resid'} score frames for one model spec."""
    rets = spliced_returns(panel)
    ff = ff.reindex(rets.index)
    excess = rets.sub(ff["rf"], axis=0)
    X_all = np.column_stack([np.ones(len(ff)), ff[factors].to_numpy(float)])

    idx, cols = panel.monthly_ret.index, panel.monthly_ret.columns
    out = {k: pd.DataFrame(np.nan, index=idx, columns=cols, dtype=float)
           for k in ("total", "fitted", "resid")}
    pos = {m: i for i, m in enumerate(rets.index)}

    # signal window scales with the estimation window: always the last 11
    # months before the formation month (m-11..m-1), i.e. the 12-1 skip.
    sig_lo = est_months - 1 - (SIG_END - SIG_START) - 1
    sig_hi = est_months - 2

    for m in idx:
        i = pos[m]
        if i + 1 < est_months:
            continue
        sl = slice(i + 1 - est_months, i + 1)
        X = X_all[sl]
        if not np.isfinite(X).all():
            continue
        Y = excess.iloc[sl].to_numpy(float)
        ok = np.isfinite(Y).all(axis=0)
        if ok.sum() == 0:
            continue
        Yk = Y[:, ok]
        beta, *_ = np.linalg.lstsq(X, Yk, rcond=None)
        fit = X @ beta
        res = Yk - fit
        names = excess.columns[ok]
        for key, arr in (("total", Yk), ("fitted", fit), ("resid", res)):
            w = arr[sig_lo:sig_hi + 1]
            mu, sd = w.mean(axis=0), w.std(axis=0, ddof=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                out[key].loc[m, names] = np.where(sd > 0, mu / sd, np.nan)
    return out


def rank_ic(score: pd.DataFrame, panel, segment: str) -> tuple[float, float, int]:
    """Mean monthly Spearman IC vs next-month return + its t-stat, explore window."""
    elig = panel.eligible() & segment_mask(panel, segment)
    months = panel.monthly_ret.index
    ics = []
    for i, m in enumerate(months):
        if m < EXPLORE_LO or m > EXPLORE_HI or i + 1 >= len(months):
            continue
        s = score.loc[m].where(elig.loc[m]).dropna()
        fwd = panel.monthly_ret.loc[months[i + 1]].reindex(s.index)
        d = pd.concat([s, fwd], axis=1).dropna()
        if len(d) >= 100:
            ics.append(d.iloc[:, 0].corr(d.iloc[:, 1], method="spearman"))
    ic = pd.Series(ics)
    t = float(ic.mean() / ic.std(ddof=1) * np.sqrt(len(ic))) if len(ic) > 1 else np.nan
    return float(ic.mean()), t, len(ic)


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    ff = pd.read_parquet(MODULE_ROOT / "data" / "ff_factors.parquet")
    results: dict = {"scope": "DIAGNOSTIC post-mortem; verdict REJECT stands; nothing graduates"}

    # ---- Test A: decomposition under the frozen spec (FF3, 36m) --------------
    print("\n=== TEST A — decomposition, frozen spec (FF3, 36m), explore window ===")
    print(f"{'component':10s} {'segment':9s} {'mean_IC':>9s} {'t_IC':>7s} {'months':>7s}")
    comps = component_scores(panel, ff, ["mktrf", "smb", "hml"], 36)
    a_rows = []
    for seg in ("small", "largemid"):
        for key in ("total", "fitted", "resid"):
            ic, t, n = rank_ic(comps[key], panel, seg)
            print(f"{key:10s} {seg:9s} {ic:9.4f} {t:7.2f} {n:7d}")
            a_rows.append({"component": key, "segment": seg,
                           "mean_ic": round(ic, 4), "t_ic": round(t, 2), "months": n})
    results["test_a_decomposition"] = a_rows

    # ---- Test B: estimation-error dose response -----------------------------
    print("\n=== TEST B — does REDUCING beta estimation error restore the IC? ===")
    print(f"{'spec':12s} {'params':>7s} {'segment':9s} {'mean_IC':>9s} {'t_IC':>7s}")
    b_rows = []
    specs = [("ff3_36 (frozen)", ["mktrf", "smb", "hml"], 36, 4),
             ("capm_36", ["mktrf"], 36, 2),
             ("ff3_60", ["mktrf", "smb", "hml"], 60, 4)]
    for label, facs, est, k in specs:
        c = comps if label.startswith("ff3_36") else component_scores(panel, ff, facs, est)
        for seg in ("small", "largemid"):
            ic, t, n = rank_ic(c["resid"], panel, seg)
            print(f"{label:12s} {k:7d} {seg:9s} {ic:9.4f} {t:7.2f}")
            b_rows.append({"spec": label, "n_params": k, "segment": seg,
                           "mean_ic": round(ic, 4), "t_ic": round(t, 2), "months": n})
    results["test_b_estimation_error"] = b_rows

    # ---- variance share: how much of the score is tilt vs idiosyncratic -----
    elig = panel.eligible() & segment_mask(panel, "small")
    win = [m for m in panel.monthly_ret.index if EXPLORE_LO <= m <= EXPLORE_HI]
    shares = []
    for m in win:
        f = comps["fitted"].loc[m].where(elig.loc[m]).dropna()
        r = comps["resid"].loc[m].where(elig.loc[m]).dropna()
        common = f.index.intersection(r.index)
        if len(common) >= 100:
            vf, vr = f[common].var(), r[common].var()
            if vf + vr > 0:
                shares.append(vf / (vf + vr))
    results["small_cross_sectional_variance_share_fitted"] = round(
        float(pd.Series(shares).mean()), 4)
    print(f"\nsmall-cap cross-sectional variance share carried by the FITTED "
          f"(tilt) leg: {results['small_cross_sectional_variance_share_fitted']:.3f}")

    (MODULE_ROOT / "data" / "factory" / "diag_resid_mom_decomp.json").write_text(
        json.dumps(results, indent=2))
    print("\nwrote data/factory/diag_resid_mom_decomp.json")


if __name__ == "__main__":
    main()
