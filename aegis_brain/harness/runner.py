"""Expanding-window walk-forward harness (the honest loop).

Timeline convention (one-month embargo is structural, not optional):
  - features are computed at formation month m (info through month-end m)
  - target is the return of month m+1
  - predicting for test month T uses a model trained ONLY on samples whose
    target month m+1 <= T-1, i.e. formation months m <= T-2

The result of ONE run of this harness is one trial. Re-running with tweaked
parameters because you didn't like the number is the overfitting machine —
register a new trial or walk away.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from aegis_brain.combiner.ranker import make_ranker
from aegis_brain.config import COST_BPS_ONE_WAY
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.signals.base import Signal

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardConfig:
    min_train_months: int = 24
    refit_every: int = 3               # retrain cadence (months)
    top_frac: float = 0.10             # long decile
    long_short: bool = False           # False = long-only vs EW universe
    cost_bps_one_way: float = COST_BPS_ONE_WAY
    ranker_kind: str = "gbm"
    ranker_kwargs: dict = field(default_factory=dict)
    min_names_per_month: int = 50      # skip months with a too-thin cross-section
    largest_n_by_dollar_vol: int | None = None  # survivorship-bound subset runs
    # For survivorship-bound runs: train ONLY on formation rows that were
    # eligible at their formation month, so the subset run is a genuinely
    # independent pipeline rather than full-universe training in disguise.
    restrict_training_to_eligible: bool = False


def _rank_standardize(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-month cross-sectional rank mapped to [-0.5, 0.5] (GKX standard)."""
    return frame.rank(axis=1, pct=True) - 0.5


def build_design(panel: Panel, signals: list[Signal]) -> pd.DataFrame:
    """Stacked design matrix: index (month, symbol), signal columns + fwd_ret.

    fwd_ret at formation month m is the month m+1 return. Rows require ALL
    signals present plus a realized forward return (or delisting stamp).
    """
    feats = {s.name: _rank_standardize(s.compute(panel)) for s in signals}
    fwd = panel.monthly_ret.shift(-1)

    stacked = pd.concat(
        {name: f.stack() for name, f in feats.items()}, axis=1
    )
    stacked["fwd_ret"] = fwd.stack()
    stacked = stacked.dropna()
    stacked.index.names = ["month", "symbol"]
    return stacked


def run_walk_forward(
    panel: Panel,
    signals: list[Signal],
    cfg: WalkForwardConfig | None = None,
) -> dict:
    """One walk-forward run. Returns {'monthly': DataFrame, 'summary': dict}."""
    cfg = cfg or WalkForwardConfig()

    eligible = panel.eligible()
    if cfg.largest_n_by_dollar_vol:
        dv = panel.monthly_dollar_vol
        topn = dv.rank(axis=1, ascending=False) <= cfg.largest_n_by_dollar_vol
        eligible = eligible & topn

    design = build_design(panel, signals)
    if cfg.restrict_training_to_eligible:
        elig_stack = eligible.stack()
        elig_stack.index.names = ["month", "symbol"]
        keep = elig_stack.reindex(design.index).fillna(False).astype(bool)
        design = design.loc[keep]
    months = design.index.get_level_values("month").unique().sort_values()
    if len(months) <= cfg.min_train_months + 1:
        raise ValueError("not enough months for walk-forward")

    feature_cols = [s.name for s in signals]
    model = None
    records: list[dict] = []
    prev_w: pd.Series = pd.Series(dtype=float)

    test_months = months[cfg.min_train_months + 1:]
    for i, test_m in enumerate(test_months):
        formation_m = months[months.get_loc(test_m) - 1]
        # training cutoff: formation months <= T-2 (targets realized before T)
        cutoff = months[months.get_loc(test_m) - 2]
        train = design.loc[design.index.get_level_values("month") <= cutoff]
        if train.shape[0] < 500:
            continue

        if model is None or i % cfg.refit_every == 0:
            model = make_ranker(cfg.ranker_kind, **cfg.ranker_kwargs)
            model.fit(train[feature_cols], train["fwd_ret"])

        try:
            cross = design.xs(formation_m, level="month")
        except KeyError:
            continue
        elig_syms = eligible.loc[formation_m]
        cross = cross[cross.index.isin(elig_syms[elig_syms].index)]
        if cross.shape[0] < cfg.min_names_per_month:
            continue

        scores = pd.Series(model.predict(cross[feature_cols]), index=cross.index)
        n_top = max(int(len(scores) * cfg.top_frac), 10)
        long_syms = scores.nlargest(n_top).index

        w = pd.Series(0.0, index=scores.index)
        w.loc[long_syms] = 1.0 / n_top
        if cfg.long_short:
            short_syms = scores.nsmallest(n_top).index
            w.loc[short_syms] = -1.0 / n_top

        realized = panel.monthly_ret.loc[test_m]
        gross = float((w * realized.reindex(w.index)).sum())
        universe_ew = float(realized.reindex(scores.index).mean())

        # traded value = Σ|Δw|; cost charged one-way bps on every dollar traded
        aligned_prev = prev_w.reindex(w.index.union(prev_w.index), fill_value=0.0)
        aligned_new = w.reindex(aligned_prev.index, fill_value=0.0)
        traded = float((aligned_new - aligned_prev).abs().sum())
        cost = traded * cfg.cost_bps_one_way / 1e4
        net = gross - cost

        records.append({
            "month": test_m, "gross": gross, "net": net,
            "universe_ew": universe_ew, "excess_net": net - universe_ew,
            "traded": traded, "cost": cost,
            "n_universe": len(scores), "n_long": n_top,
        })
        prev_w = w

    monthly = pd.DataFrame(records).set_index("month")
    if monthly.empty:
        raise ValueError("walk-forward produced no test months")

    summary = summarize(monthly, cfg)
    logger.info("walk-forward: %s", summary)
    return {"monthly": monthly, "summary": summary, "config": cfg}


def summarize(monthly: pd.DataFrame, cfg: WalkForwardConfig) -> dict:
    net = monthly["net"]
    n = len(net)
    ann = 12
    sharpe = float(net.mean() / net.std(ddof=1) * np.sqrt(ann)) if net.std(ddof=1) > 0 else 0.0
    cum = (1 + net).cumprod()
    max_dd = float((cum / cum.cummax() - 1).min())
    excess = monthly["excess_net"]
    t_excess = float(excess.mean() / excess.std(ddof=1) * np.sqrt(n)) if excess.std(ddof=1) > 0 else 0.0
    # Gross excess is the LEAK metric: a leak inflates gross performance, while
    # net excess of even a random book is expected-negative by its cost drag
    # (the TRIAL-BRAIN-001 lesson). Leak bar: |t_stat_excess_gross| >= 3.
    excess_g = monthly["gross"] - monthly["universe_ew"]
    t_excess_g = float(excess_g.mean() / excess_g.std(ddof=1) * np.sqrt(n)) if excess_g.std(ddof=1) > 0 else 0.0
    return {
        "months": n,
        "cagr_net": float(cum.iloc[-1] ** (ann / n) - 1),
        "sharpe_net_ann": round(sharpe, 3),
        "max_drawdown": round(max_dd, 3),
        "mean_monthly_traded": round(float(monthly["traded"].mean()), 3),
        "mean_excess_vs_universe_ew": round(float(excess.mean()), 5),
        "t_stat_excess": round(t_excess, 2),
        "mean_excess_gross": round(float(excess_g.mean()), 5),
        "t_stat_excess_gross": round(t_excess_g, 2),
        "long_short": cfg.long_short,
        "cost_bps_one_way": cfg.cost_bps_one_way,
    }
