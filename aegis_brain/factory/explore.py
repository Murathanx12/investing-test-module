"""Explore-tier decile scan: one signal, no model, honest costs.

Same economics as harness/runner.py (top-decile long book, 30% hold-band
incumbency, one-way bps costs on traded value, EW-universe benchmark) but the
signal IS the score — nothing is fitted, so a scan is cheap enough to run by
the dozen. The scan hard-stops at the explore/confirm boundary; confirm months
are readable only by a pre-registered confirm trial.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.signals import FactorySignal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScanConfig:
    """Frozen in docs/STRATEGY_FACTORY.md — do not tune per-signal."""

    top_frac: float = 0.10
    hold_band_frac: float = 0.30
    cost_bps_one_way: float = 25.0
    min_names_per_month: int = 100
    first_test_month: str = "2004-01-31"
    last_test_month: str = "2018-12-31"   # explore/confirm boundary (inclusive)


def segment_mask(panel: Panel, segment: str) -> pd.DataFrame:
    """Formation-month membership by dollar-volume rank (PIT: uses month m only)."""
    rank = panel.monthly_dollar_vol.rank(axis=1, ascending=False)
    if segment == "largemid":
        return rank <= 1000
    if segment == "small":
        return (rank > 1000) & (rank <= 3000)
    raise ValueError(f"unknown segment {segment!r}")


def scan_signal(
    panel: Panel,
    sig: FactorySignal,
    segment: str,
    cfg: ScanConfig | None = None,
) -> dict:
    """One explore scan. Returns {'summary': dict, 'monthly': DataFrame}."""
    cfg = cfg or ScanConfig()
    score = sig.compute(panel) * float(sig.direction)  # higher = better, always
    eligible = panel.eligible() & segment_mask(panel, segment)

    months = panel.monthly_ret.index
    lo = pd.Timestamp(cfg.first_test_month)
    hi = pd.Timestamp(cfg.last_test_month)
    test_months = [m for m in months if lo <= m <= hi]

    prev_w: pd.Series = pd.Series(dtype=float)
    records: list[dict] = []
    for test_m in test_months:
        pos = months.get_loc(test_m)
        if pos == 0:
            continue
        formation_m = months[pos - 1]

        elig = eligible.loc[formation_m]
        s = score.loc[formation_m].dropna()
        s = s[s.index.isin(elig[elig].index)]
        if len(s) < cfg.min_names_per_month:
            continue

        realized = panel.monthly_ret.loc[test_m]
        n_top = max(int(len(s) * cfg.top_frac), 10)
        band_n = max(int(len(s) * cfg.hold_band_frac), n_top)
        band = set(s.nlargest(band_n).index)
        prev_held = prev_w[prev_w > 0].index
        kept = s.reindex([x for x in prev_held if x in band]).dropna()
        kept = kept.sort_values(ascending=False).index[:n_top].tolist()
        fresh = [x for x in s.sort_values(ascending=False).index
                 if x not in kept][: n_top - len(kept)]
        long_syms = pd.Index(kept + fresh)

        w = pd.Series(0.0, index=s.index)
        w.loc[long_syms] = 1.0 / n_top

        gross = float((w * realized.reindex(w.index)).sum())
        universe_ew = float(realized.reindex(s.index).mean())

        aligned_prev = prev_w.reindex(w.index.union(prev_w.index), fill_value=0.0)
        aligned_new = w.reindex(aligned_prev.index, fill_value=0.0)
        traded = float((aligned_new - aligned_prev).abs().sum())
        net = gross - traded * cfg.cost_bps_one_way / 1e4

        fwd = realized.reindex(s.index)
        ok = fwd.notna()
        ic = float(s[ok].rank().corr(fwd[ok].rank())) if ok.sum() >= 30 else np.nan

        records.append({
            "month": test_m, "gross": gross, "net": net,
            "universe_ew": universe_ew, "excess_net": net - universe_ew,
            "excess_gross": gross - universe_ew,
            "traded": traded, "ic": ic, "n_universe": len(s),
        })
        prev_w = w

    monthly = pd.DataFrame(records).set_index("month")
    if monthly.empty:
        raise ValueError(f"scan produced no months for {sig.name}/{segment}")

    def _t(x: pd.Series) -> float:
        x = x.dropna()
        sd = x.std(ddof=1)
        return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else 0.0

    net = monthly["net"]
    cum = (1 + net).cumprod()
    summary = {
        "signal": sig.name, "segment": segment,
        "contaminated": sig.contaminated,
        "months": len(monthly),
        "mean_excess_net_bps": round(float(monthly["excess_net"].mean()) * 1e4, 1),
        "t_excess_net": round(_t(monthly["excess_net"]), 2),
        "t_excess_gross": round(_t(monthly["excess_gross"]), 2),
        "ic_mean": round(float(monthly["ic"].mean()), 4),
        "t_ic": round(_t(monthly["ic"]), 2),
        "turnover_1way": round(float(monthly["traded"].mean()) / 2, 3),
        "cagr_net": round(float(cum.iloc[-1] ** (12 / len(net)) - 1), 4),
        "max_dd": round(float((cum / cum.cummax() - 1).min()), 3),
    }
    return {"summary": summary, "monthly": monthly}


def run_batch(panel: Panel, signals: list[FactorySignal],
              segments: tuple[str, ...] = ("largemid", "small"),
              cfg: ScanConfig | None = None) -> pd.DataFrame:
    """Scan every signal × segment; ranked summary table (t_excess_net desc)."""
    rows = []
    for sig in signals:
        for seg in segments:
            try:
                rows.append(scan_signal(panel, sig, seg, cfg)["summary"])
            except Exception:
                logger.exception("scan failed: %s/%s", sig.name, seg)
                rows.append({"signal": sig.name, "segment": seg, "months": 0,
                             "contaminated": sig.contaminated})
    out = pd.DataFrame(rows)
    return out.sort_values("t_excess_net", ascending=False, na_position="last")
