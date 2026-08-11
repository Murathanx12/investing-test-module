"""The scorecard — every number EXECUTION_STANDARD §3 asks for, computed once.

Design rules:
  * Nothing here chooses a winner. It reports; adjudication is a separate,
    pre-registered decision rule.
  * The headline is NET EXCESS CAGR vs the benchmark, plus the per-regime
    table. Sharpe is reported, never maximized (the standard ranks by excess
    terminal wealth under a ruin constraint).
  * Tail risk is estimated by PAIRED stationary block bootstrap: strategy and
    benchmark months are resampled together, so the excess-wealth distribution
    keeps their co-movement instead of pretending they are independent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.harness.benchmark import factor_alpha, newey_west_tstat
from aegis_brain.pf.panel63 import (FULL_BLOCKS, GATE_BLOCKS, HOLDOUT_BLOCK,
                                    annualize, block_slice, max_drawdown)

RUIN_DD = 0.60          # "catastrophic impairment" threshold from the standard
BOOT_PATHS = 5000
BLOCK_MONTHS = 12


def _t(x: pd.Series) -> float:
    x = pd.Series(x).dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 and len(x) > 1 else 0.0


def _time_underwater(monthly: pd.Series) -> dict:
    cum = (1.0 + monthly.dropna()).cumprod()
    dd = cum / cum.cummax() - 1.0
    under = dd < -1e-9
    # longest consecutive run of underwater months
    longest = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    return {"frac_months_underwater": round(float(under.mean()), 3),
            "longest_underwater_months": int(longest)}


def _annual_table(net: pd.Series, bench: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"net": net, "bench": bench}).dropna()
    g = df.groupby(df.index.year)
    out = g.apply(lambda x: pd.Series({
        "strategy": float((1 + x["net"]).prod() - 1),
        "benchmark": float((1 + x["bench"]).prod() - 1),
        "months": len(x)}))
    out["excess"] = out["strategy"] - out["benchmark"]
    return out


def _paired_block_bootstrap(net: np.ndarray, bench: np.ndarray, *,
                            paths: int, block: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n = len(net)
    if n < block * 2:
        return {"note": f"series too short ({n} months) for block bootstrap"}
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block, size=(paths, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(paths, -1)[:, :n]
    s_paths = net[idx]
    b_paths = bench[idx]

    s_wealth = np.cumprod(1.0 + s_paths, axis=1)
    b_wealth = np.cumprod(1.0 + b_paths, axis=1)
    run_max = np.maximum.accumulate(s_wealth, axis=1)
    dd = (s_wealth / run_max - 1.0).min(axis=1)
    yrs = n / 12.0
    s_cagr = s_wealth[:, -1] ** (1 / yrs) - 1
    b_cagr = b_wealth[:, -1] ** (1 / yrs) - 1

    q = lambda a, p: float(np.percentile(a, p))  # noqa: E731
    return {
        "paths": paths, "block_months": block, "horizon_months": n,
        "p_maxdd_worse_than_60pct": round(float((dd < -RUIN_DD).mean()), 4),
        "p_maxdd_worse_than_40pct": round(float((dd < -0.40).mean()), 4),
        "p_underperform_benchmark": round(float((s_wealth[:, -1]
                                                 < b_wealth[:, -1]).mean()), 4),
        "terminal_wealth_strategy": {
            "p05": round(q(s_wealth[:, -1], 5), 3),
            "p25": round(q(s_wealth[:, -1], 25), 3),
            "median": round(q(s_wealth[:, -1], 50), 3),
            "p75": round(q(s_wealth[:, -1], 75), 3),
            "p95": round(q(s_wealth[:, -1], 95), 3)},
        "terminal_wealth_benchmark_median": round(q(b_wealth[:, -1], 50), 3),
        "excess_cagr": {"p05": round(q(s_cagr - b_cagr, 5), 4),
                        "median": round(q(s_cagr - b_cagr, 50), 4),
                        "p95": round(q(s_cagr - b_cagr, 95), 4)},
    }



#: z(0.975) + z(0.80) — the two-sided 80%-power constant. An effect below
#: `MDE_Z` standard errors was unlikely to be found even if it were real.
MDE_Z = 2.8
SIG_Z = 1.96


def _power_block(excess: pd.Series, gross_excess: pd.Series | None = None) -> dict:
    """CANON §19 — every arm reports its own 80%-power MDE beside its effect.

    NIGHT-10 measured 21 configurations across two independent audits and found
    that NOT ONE reported an effect above its own detection threshold: the
    standard shape (EW top-50, monthly, 2002-2022) resolves 6.3 to 19.9 %/yr,
    roughly double the largest credible equity anomaly. A kill from such a
    design is absence of evidence, and this programme recorded it identically to
    evidence of absence for 195 experiments.

    Making that a rule was not enough — the corpse check only started working
    when it became `lint_prereg.py`. So the number is computed here, on every
    card, whether or not anyone remembers to ask for it.

    The effect compared against the MDE is the ARITHMETIC annualised mean of the
    monthly excess series, because that is the quantity whose standard error is
    being estimated. The headline `excess_cagr_net` is geometric and is NOT the
    same functional; both are reported so the comparison cannot be made in the
    wrong units by accident.
    """
    e = excess.dropna()
    n = len(e)
    if n < 12:
        return {"status": "TOO_SHORT", "n_months": n,
                "reading": f"{n} months is too few to estimate a standard error"}
    sd_m = float(e.std(ddof=1))
    se_ann = 12.0 * sd_m / np.sqrt(n)
    eff_ann = 12.0 * float(e.mean())
    mde = MDE_Z * se_ann
    sig = SIG_Z * se_ann
    detectable = bool(abs(eff_ann) >= mde)
    significant = bool(abs(eff_ann) >= sig)
    out = {
        "status": "OK",
        "n_months": n,
        "arithmetic_excess_annual": round(eff_ann, 5),
        "se_annual": round(se_ann, 5),
        "sig_threshold_annual": round(sig, 5),
        "mde_80pct_power_annual": round(mde, 5),
        "significant_at_5pct": significant,
        "above_80pct_power_mde": detectable,
        "effect_over_mde": round(abs(eff_ann) / mde, 3) if mde > 0 else None,
    }
    if gross_excess is not None:
        g = gross_excess.dropna()
        if len(g) >= 12:
            out["gross_arithmetic_excess_annual"] = round(
                12.0 * float(g.mean()), 5)
    if detectable:
        out["reading"] = (
            f"this design detects {100*mde:.1f}%/yr at 80% power and the arm "
            f"shows {100*eff_ann:+.1f}%/yr — large enough for this design to "
            f"have found it reliably")
    else:
        out["reading"] = (
            f"NOT RELIABLY DETECTABLE BY THIS DESIGN: it resolves "
            f"{100*mde:.1f}%/yr at 80% power and the arm shows "
            f"{100*eff_ann:+.1f}%/yr"
            + (" — significant, but in the region where significant findings "
               "systematically overstate their effects (CANON §19)"
               if significant else
               " — a null here is NOT evidence of absence (CANON §19)"))
    return out


def scorecard(monthly: pd.DataFrame, bench: pd.Series, *, diag: dict,
              spec_dict: dict, ew_universe: pd.Series | None = None,
              factors: pd.DataFrame | None = None, rf: pd.Series | None = None,
              seed: int = 20260808) -> dict:
    """Full scorecard for one strategy run."""
    net = monthly["net"].dropna()
    gross = monthly["gross"].reindex(net.index)
    b = bench.reindex(net.index)
    if b.isna().any():
        raise RuntimeError("benchmark has gaps over the strategy window")
    excess = net - b

    yrs = len(net) / 12.0
    cum_s = float((1 + net).prod())
    cum_b = float((1 + b).prod())
    ann_vol = float(net.std(ddof=1) * np.sqrt(12))
    downside = net[net < 0]
    sortino_den = float(downside.std(ddof=1) * np.sqrt(12)) if len(downside) > 1 else np.nan
    mdd = max_drawdown(net)
    cagr = annualize(net)
    bench_cagr = annualize(b)
    rf_ann = annualize(rf.reindex(net.index)) if rf is not None else 0.0

    ann = _annual_table(net, b)
    wins = net > 0

    card = {
        "spec": spec_dict,
        "window": {"first": str(net.index.min().date()),
                   "last": str(net.index.max().date()),
                   "months": len(net), "years": round(yrs, 1)},
        "headline": {
            "cagr_net": round(cagr, 4),
            "benchmark_cagr": round(bench_cagr, 4),
            "excess_cagr_net": round(cagr - bench_cagr, 4),
            "cum_return_strategy": round(cum_s - 1, 3),
            "cum_return_benchmark": round(cum_b - 1, 3),
            "terminal_wealth_multiple_vs_benchmark": round(cum_s / cum_b, 3),
            "t_excess_monthly": round(_t(excess), 2),
            "t_excess_newey_west": (
                round(newey_west_tstat(excess, lags=12)["t"], 2)
                if newey_west_tstat(excess, lags=12)["t"] is not None else None),
        },
        "risk": {
            "ann_vol": round(ann_vol, 4),
            "max_drawdown": round(mdd, 4),
            "sharpe_net": round((cagr - rf_ann) / ann_vol, 3) if ann_vol > 0 else None,
            "sortino_net": (round((cagr - rf_ann) / sortino_den, 3)
                            if sortino_den and sortino_den > 0 else None),
            "calmar": round(cagr / abs(mdd), 3) if mdd < 0 else None,
            "benchmark_max_drawdown": round(max_drawdown(b), 4),
            "benchmark_ann_vol": round(float(b.std(ddof=1) * np.sqrt(12)), 4),
            **_time_underwater(net),
        },
        "distribution": {
            "monthly_win_rate": round(float(wins.mean()), 3),
            "avg_win": round(float(net[wins].mean()), 4),
            "avg_loss": round(float(net[~wins].mean()), 4),
            "worst_month": round(float(net.min()), 4),
            "best_month": round(float(net.max()), 4),
            "skew": round(float(net.skew()), 3),
            "kurtosis": round(float(net.kurtosis()), 3),
            "best_year": {"year": int(ann["strategy"].idxmax()),
                          "ret": round(float(ann["strategy"].max()), 3)},
            "worst_year": {"year": int(ann["strategy"].idxmin()),
                           "ret": round(float(ann["strategy"].min()), 3)},
            "years_beating_benchmark": (
                f"{int((ann['excess'] > 0).sum())}/{len(ann)}"),
        },
        "implementation": {
            **diag,
            "gross_cagr": round(annualize(gross), 4),
            "cost_drag_cagr": round(annualize(gross) - cagr, 4),
        },
        "power": _power_block(excess, gross.reindex(net.index) - b),
        "robustness": _robustness(net, b),
        "regimes_gate": _regime_table(net, b, GATE_BLOCKS),
        "regimes_full": _regime_table(net, b, FULL_BLOCKS),
        "tail": _paired_block_bootstrap(net.to_numpy(), b.to_numpy(),
                                        paths=BOOT_PATHS, block=BLOCK_MONTHS,
                                        seed=seed),
        "annual_table": {int(y): {k: round(float(v), 4) for k, v in row.items()}
                         for y, row in ann.iterrows()},
    }

    if ew_universe is not None:
        ew = ew_universe.reindex(net.index)
        if ew.notna().sum() > 12:
            card["controls"] = {
                "ew_universe_cagr": round(annualize(ew.dropna()), 4),
                "excess_vs_ew_universe_cagr": round(
                    annualize(net.reindex(ew.dropna().index)) - annualize(ew.dropna()), 4),
                "t_excess_vs_ew_universe": round(_t((net - ew).dropna()), 2),
            }
    if factors is not None and rf is not None:
        pe = (net - rf.reindex(net.index)).dropna()
        f = factors.reindex(pe.index)
        for label, cols in (("capm", ["mktrf"]),
                            ("ff5_umd", ["mktrf", "smb", "hml", "rmw", "cma", "umd"])):
            if set(cols).issubset(f.columns) and f[cols].notna().all().all():
                a = factor_alpha(pe, f, cols, lags=12)
                card.setdefault("factor_alpha", {})[label] = {
                    "ann_alpha": (round(a["ann_alpha"], 4)
                                  if a.get("ann_alpha") is not None else None),
                    "t_alpha": (round(a["t_alpha"], 2)
                                if a.get("t_alpha") is not None else None),
                    "betas": {k: round(v, 3) for k, v in a.get("betas", {}).items()},
                }
    return card


def _robustness(net: pd.Series, bench: pd.Series) -> dict:
    """G6: is the edge one year, one month, or one lucky tail?

    Each variant DROPS the named months from BOTH series and recomputes excess
    CAGR on what is left. Frozen before any PF-1 run.
    """
    full = annualize(net) - annualize(bench)
    ann = pd.DataFrame({"net": net, "bench": bench})
    ann["excess"] = ann["net"] - ann["bench"]
    by_year = ann.groupby(ann.index.year)["excess"].mean()
    best_year = int(by_year.idxmax())
    worst_year = int(by_year.idxmin())

    def ex(mask: pd.Series) -> float:
        s, b = net[mask], bench[mask]
        return round(annualize(s) - annualize(b), 4)

    top_months = ann["excess"].nlargest(max(int(0.01 * len(ann)), 1)).index
    return {
        "excess_cagr_full": round(full, 4),
        "best_excess_year": best_year,
        "excess_cagr_ex_best_year": ex(net.index.year != best_year),
        "excess_cagr_ex_worst_year": ex(net.index.year != worst_year),
        "excess_cagr_ex_top_1pct_months": ex(~net.index.isin(top_months)),
        "excess_cagr_first_half": ex(net.index <= net.index[len(net) // 2]),
        "excess_cagr_second_half": ex(net.index > net.index[len(net) // 2]),
    }


def _regime_table(net: pd.Series, bench: pd.Series,
                  blocks: tuple[tuple[str, str, str], ...]) -> dict:
    out = {}
    for name, first, last in blocks:
        s = block_slice(net, first, last)
        b = block_slice(bench, first, last)
        if len(s) < 6:
            out[name] = {"months": len(s),
                         "status": ("HOLDOUT — not evaluated"
                                    if name == HOLDOUT_BLOCK else "insufficient")}
            continue
        out[name] = {
            "months": len(s),
            "strategy_cagr": round(annualize(s), 4),
            "benchmark_cagr": round(annualize(b), 4),
            "excess_cagr": round(annualize(s) - annualize(b), 4),
            "max_dd": round(max_drawdown(s), 4),
            "positive_excess": bool(annualize(s) > annualize(b)),
        }
    evaluable = [v for k, v in out.items()
                 if "excess_cagr" in v and k != HOLDOUT_BLOCK]
    if evaluable:
        out["_summary"] = {
            "blocks_evaluated": len(evaluable),
            "blocks_positive_excess": sum(v["positive_excess"] for v in evaluable),
            "worst_block_excess": round(min(v["excess_cagr"] for v in evaluable), 4),
        }
    return out
