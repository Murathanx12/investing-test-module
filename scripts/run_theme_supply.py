"""TRIAL-THEME-SUPPLY-supplier-baskets — one execution, EXPLORE WINDOW ONLY.

Slow basket arm of the suppliers thesis: at each June month-end, score
suppliers by the salecs-weighted 12-1 momentum of their matched COMPANY
customers (same audited link construction as cust_mom in altstores2), take
the top decile WITHIN each dollar-volume segment, EW, hold 12 months via
hold-band. Arms: B top decile / A bottom decile / noise (random scored names,
same counts). Benchmark = scored-supplier coverage universe EW within segment.
Window hard-stops at 2018-12 — 2019+ is held out and untouched.
Usage: .venv\\Scripts\\python -m scripts.run_theme_supply
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.altstores2 import RAW, _gvkey_to_sym, _norm_name
from aegis_brain.harness.benchmark import newey_west_tstat
from aegis_brain.harness.flag_portfolio import hold_band, run_arms

START, END, HOLD, MIN_NAMES, Q = "2004-01-01", "2018-12-31", 12, 10, 0.1


def build_links() -> pd.DataFrame:
    """Identical construction to altstores2.load_customer_momentum (audited):
    COMPANY links, normalized-exact name match, PIT srcdate+6m..+30m validity."""
    seg = pd.read_parquet(RAW / "seg_customer.parquet")
    seg = seg[(seg["ctype"] == "COMPANY") & seg["cnms"].notna()].copy()
    funda = pd.read_parquet(RAW / "comp_funda.parquet")[["gvkey", "conm"]]
    names = funda.drop_duplicates()
    names["norm"] = _norm_name(names["conm"])
    names = names[names["norm"].str.len() > 2].drop_duplicates("norm", keep=False)
    seg["norm"] = _norm_name(seg["cnms"])
    m = seg.merge(names[["norm", "gvkey"]].rename(columns={"gvkey": "cust_gvkey"}),
                  on="norm", how="inner")
    gs = _gvkey_to_sym()
    m = m.merge(gs.rename(columns={"gvkey": "cust_gvkey", "sym": "cust_sym"})
                [["cust_gvkey", "cust_sym", "linkdt", "linkenddt"]], on="cust_gvkey")
    m = m[(m["srcdate"] >= m["linkdt"]) & (m["srcdate"] <= m["linkenddt"])]
    m = m.merge(gs.rename(columns={"sym": "supp_sym"})
                [["gvkey", "supp_sym", "linkdt", "linkenddt"]], on="gvkey",
                suffixes=("", "_s"))
    m = m[(m["srcdate"] >= m["linkdt_s"]) & (m["srcdate"] <= m["linkenddt_s"])]
    links = m[["supp_sym", "cust_sym", "salecs", "srcdate"]].copy()
    links["w"] = links["salecs"].clip(lower=0).fillna(0) + 1e-9
    links["valid_from"] = links["srcdate"] + pd.DateOffset(months=6)
    links["valid_to"] = links["srcdate"] + pd.DateOffset(months=30)
    return links[links["cust_sym"] != links["supp_sym"]]


def main() -> None:
    t0 = time.time()
    OUT = MODULE_ROOT / "runs" / "TRIAL-THEME-SUPPLY"; OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    ret = panel.monthly_ret
    months, cols = ret.index, ret.columns
    links = build_links()

    # customer 12-1 momentum: compounded t-12..t-2 (skip formation month t-1)
    mom = np.expm1(np.log1p(ret).shift(2).rolling(11, min_periods=8).sum())

    junes = [m for m in months if m.month == 6 and START <= str(m.date()) <= END]
    elig = panel.eligible()
    dvol = panel.monthly_dollar_vol

    F_B = pd.DataFrame(False, index=months, columns=cols)
    F_A = pd.DataFrame(False, index=months, columns=cols)
    F_C = pd.DataFrame(False, index=months, columns=cols)  # coverage (scored)
    rng = np.random.default_rng(20260724)
    F_N = pd.DataFrame(False, index=months, columns=cols)

    for jm in junes:
        sub = links[(links["valid_from"] <= jm) & (links["valid_to"] >= jm)]
        if sub.empty:
            continue
        cm = mom.loc[jm]
        sub = sub.assign(cmom=sub["cust_sym"].map(cm)).dropna(subset=["cmom"])
        if sub.empty:
            continue
        sub["wc"] = sub["w"] * sub["cmom"]
        agg = sub.groupby("supp_sym").agg(wc=("wc", "sum"), w=("w", "sum"))
        score = (agg["wc"] / agg["w"])
        score = score[score.index.isin(cols)]
        e = elig.loc[jm]
        score = score[e.reindex(score.index).fillna(False).values]
        if score.empty:
            continue
        # per-segment deciles (frozen: top decile WITHIN segment)
        dv = dvol.loc[jm].reindex(score.index)
        med = dv.median()
        for seg_mask in (dv >= med, dv < med):
            s = score[seg_mask.fillna(False)]
            if len(s) < MIN_NAMES:
                continue
            top = s[s >= s.quantile(1 - Q)].index
            bot = s[s <= s.quantile(Q)].index
            F_B.loc[jm, top] = True
            F_A.loc[jm, bot] = True
            F_N.loc[jm, rng.choice(s.index, size=min(len(top), len(s)), replace=False)] = True
        F_C.loc[jm, score.index] = True

    arms = {"B": hold_band(F_B, HOLD), "A": hold_band(F_A, HOLD), "noise": hold_band(F_N, HOLD)}
    coverage = hold_band(F_C, HOLD)
    res = run_arms(panel, arms, START, END, MODULE_ROOT / "data",
                   min_names=MIN_NAMES, factor_alpha_arms=("B", "A"), coverage=coverage)

    best = res["best_B_segment"]
    spread = (res["nets"][f"B_{best}"] - res["nets"][f"A_{best}"]).dropna()
    res["B_minus_A_spread_t"] = newey_west_tstat(spread)["t"] if len(spread) >= 12 else None
    res["B_minus_A_spread_bps"] = round(float(spread.mean()) * 1e4, 1) if len(spread) else None
    res.pop("nets", None)
    out = {"trial": "TRIAL-THEME-SUPPLY-supplier-baskets", "window": f"{START}..{END}",
           "explore_only": True, "formations": len(junes),
           "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           **res, "elapsed_s": round(time.time() - t0, 1)}
    (OUT / "results.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
