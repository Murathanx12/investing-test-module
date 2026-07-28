"""TRIAL-TEXT-LAZY — one execution, results final.

Frozen spec + the 2026-07-28 pre-run addendum (coverage: 10-K only).

Arm B: text_cos(+) / text_jac(+) — YoY same-firm 10-K similarity.
Arm A: ctl_cos / ctl_jac — the SAME filing scored against a randomly drawn
       different firm's filing from the same year. Pipeline validation; a control
       arm that shows signal means the plumbing, not the hypothesis, is talking.

Byte-identical house factory scan (top decile, 30% hold band, standard costs,
explore ends 2018-12-31). The departure from CMN's monthly quintiles is declared
in the registration.

Also reported unconditionally (pre-declared in the kill condition, so it is NOT
post-hoc): the CHANGER cohort's forward market-adjusted return. A changer t<=-2.0
would license a NEW filter registration; it can never rescue this one.

Usage: .venv\\Scripts\\python -m scripts.run_trial_lazy [--confirm]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal, segment_mask
from aegis_brain.factory.signals import FactorySignal

STALENESS_MONTHS = 15          # frozen
EVENTS_DIR = MODULE_ROOT / "data" / "events"


def _t(x) -> float:
    x = pd.Series(x).dropna()
    if len(x) < 2:
        return float("nan")
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else float("nan")


def build_frames(panel) -> dict[str, pd.DataFrame]:
    """[month x permno] signal frames, PIT by filing month-end, ffilled 15 months."""
    sig = pd.read_parquet(EVENTS_DIR / "lazy_text_signals.parquet")
    sig["month"] = pd.to_datetime(sig["filing_date"]).dt.to_period("M").dt.to_timestamp("M")
    sig["sym"] = sig["permno"].astype(int).astype(str)

    months, cols = panel.monthly_ret.index, panel.monthly_ret.columns
    out = {}
    for col in ("text_cos", "text_jac", "ctl_cos", "ctl_jac"):
        # last observation within the month wins (a firm files one 10-K a year)
        wide = (sig.sort_values("filing_date")
                .groupby(["month", "sym"])[col].last().unstack())
        wide = wide.reindex(index=months, columns=cols)
        out[col] = wide.ffill(limit=STALENESS_MONTHS)
    return out


def changer_cohort(panel, frames: pd.DataFrame, lo: str, hi: str) -> dict:
    """Bottom-decile (most-changed) names: forward 3m market-adjusted return.

    Pre-declared in the kill condition — reported whatever the picker does.
    """
    ret = panel.monthly_ret
    months = ret.index
    lm, sm = segment_mask(panel, "largemid"), segment_mask(panel, "small")
    seg_ew = {"largemid": ret.where(lm).mean(axis=1), "small": ret.where(sm).mean(axis=1)}
    elig = panel.eligible() & (lm | sm)

    out = {}
    for seg_name, mask in (("largemid", lm), ("small", sm)):
        vals = []
        for i, m in enumerate(months):
            if not (pd.Timestamp(lo) <= m <= pd.Timestamp(hi)) or i + 3 >= len(months):
                continue
            s = frames.loc[m].dropna()
            s = s[s.index.isin(elig.loc[m][elig.loc[m]].index)]
            s = s[s.index.isin(mask.loc[m][mask.loc[m]].index)]
            if len(s) < 100:
                continue
            worst = s.nsmallest(max(int(len(s) * 0.10), 10)).index
            win = months[i + 1: i + 4]
            r = ret.loc[win, list(worst)]
            cum = (1.0 + r.fillna(0.0)).prod(axis=0) - 1.0
            bench = float(np.prod(1.0 + seg_ew[seg_name].loc[win].fillna(0.0).values) - 1.0)
            vals.append(float(cum.mean()) - bench)
        out[seg_name] = {"n_months": len(vals),
                         "mean_3m_excess_pct": round(float(np.mean(vals)) * 100, 2) if vals else None,
                         "t": round(_t(vals), 2) if vals else None}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()
    tag = "confirm" if args.confirm else "explore"
    cfg = ScanConfig()
    if args.confirm:            # EXPLORE_END mutation pattern
        cfg = ScanConfig(first_test_month="2019-01-31", last_test_month="2024-12-31")

    t0 = time.time()
    out_dir = MODULE_ROOT / "runs" / "TRIAL-TEXT-LAZY"
    out_dir.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    frames = build_frames(panel)

    cov = {k: {"n_obs": int(v.notna().sum().sum()),
               "mean_names_per_month": int(v.notna().sum(axis=1).loc[
                   cfg.first_test_month:cfg.last_test_month].mean())}
           for k, v in frames.items()}

    rows = []
    for name in ("text_cos", "text_jac", "ctl_cos", "ctl_jac"):
        frame = frames[name]
        sig = FactorySignal(name=name,
                            hypothesis="Lazy Prices (CMN 2020): non-changers outperform",
                            compute=lambda p, _f=frame: _f, direction=+1)
        for seg in ("largemid", "small"):
            try:
                rows.append(scan_signal(panel, sig, seg, cfg)["summary"])
            except Exception as exc:                      # fail loud, never silent
                rows.append({"signal": name, "segment": seg, "months": 0,
                             "error": repr(exc)})

    table = pd.DataFrame(rows)
    lo = cfg.first_test_month
    hi = cfg.last_test_month
    out = {
        "trial": "TRIAL-TEXT-LAZY", "window": tag, "range": [lo, hi],
        "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "coverage": "10-K only (declared shrink)",
        "signal_coverage": cov,
        "scans": table.to_dict(orient="records"),
        "changer_cohort_text_cos": changer_cohort(panel, frames["text_cos"], lo, hi),
        "elapsed_s": round(time.time() - t0, 1),
    }
    (out_dir / f"results_{tag}.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
