"""TRIAL-EVENT-8K-FILTER — one execution, results final.

Frozen spec + the 2026-07-28 pre-run addendum (monthly measurement resolution).

Deciding metric: mean 3-calendar-month market-adjusted return of the flagged
cohort, measured from the first month-end on/after the filing date (the filing
month is excluded outright, so no pre-filing return can leak in). Bar: t <= -2.0.

Arm A = pseudo-events, same names, filing dates shifted -12 months (+12 where -12
falls before the panel). Arm B = the true flagged cohort.

Secondary, NOT deciding: a calendar-time cohort portfolio, because event-time
t-stats overstate significance when events cluster and bankruptcies cluster hard
in 2008-09.

Usage: .venv\\Scripts\\python -m scripts.run_trial_8k_filter [--confirm]
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
from aegis_brain.events.name_link import link_filings_by_cik
from aegis_brain.factory.explore import segment_mask

ITEMS = {"1.03", "2.04", "5.01"}          # frozen at registration
HORIZONS = (1, 3, 6)                       # months; DECIDING = 3
DECIDING_H = 3
EXPLORE = ("2004-01-01", "2018-12-31")
CONFIRM = ("2019-01-01", "2024-12-31")
EVENTS_DIR = MODULE_ROOT / "data" / "events"


def _t(x: pd.Series | np.ndarray) -> float:
    x = pd.Series(x).dropna()
    if len(x) < 2:
        return float("nan")
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else float("nan")


def load_flagged_events() -> tuple[pd.DataFrame, dict]:
    """Daily-index 8-K rows INTERSECTED with submission-header item codes."""
    idx = pd.read_parquet(EVENTS_DIR / "edgar_8k_daily_index.parquet")
    idx = idx[~idx["is_amendment"]]                       # originals only
    subs = pd.read_parquet(EVENTS_DIR / "sec_submissions.parquet")
    subs = subs[subs["form"].str.startswith("8-K")][["accession", "items_raw"]]

    ev = idx.merge(subs, on="accession", how="inner")     # the intersection
    ev["item_list"] = ev["items_raw"].str.split(",")
    ev = ev.explode("item_list")
    ev["item"] = ev["item_list"].str.strip()
    flagged = ev[ev["item"].isin(ITEMS)].copy()

    audit = {
        "n_daily_index_8k_originals": int(len(idx)),
        "n_with_item_metadata": int(ev["accession"].nunique()),
        "n_flagged_filings": int(flagged["accession"].nunique()),
        "item_mix": {k: int(v) for k, v in flagged["item"].value_counts().items()},
    }
    keep = (flagged.sort_values("item")
            .groupby("accession")
            .agg(cik=("cik", "first"), date_filed=("date_filed", "first"),
                 company=("company", "first"), items=("item", lambda s: "+".join(sorted(set(s)))))
            .reset_index())
    return keep, audit


def forward_market_adjusted(panel, events: pd.DataFrame, horizon: int) -> pd.Series:
    """Compounded stock return minus compounded segment-EW return over the
    `horizon` months FOLLOWING the filing month.

    A name that delists inside the window compounds its realised returns (CRSP
    delisting return included) and then sits in cash; the benchmark keeps running.
    That is what a holder actually experiences, and it is the convention that does
    NOT quietly delete the worst outcomes from a distress cohort.
    """
    ret = panel.monthly_ret
    months = ret.index
    lm, sm = segment_mask(panel, "largemid"), segment_mask(panel, "small")

    seg_ew: dict[str, pd.Series] = {}
    for name, mask in (("largemid", lm), ("small", sm)):
        m = ret.where(mask)
        seg_ew[name] = m.mean(axis=1)

    out = []
    for _, r in events.iterrows():
        p = str(int(r["permno"]))
        if p not in ret.columns:
            out.append(np.nan)
            continue
        fm = pd.Timestamp(r["date_filed"]).to_period("M").to_timestamp("M")
        if fm not in months:
            out.append(np.nan)
            continue
        pos = months.get_loc(fm)
        win = months[pos + 1: pos + 1 + horizon]
        if len(win) < horizon:
            out.append(np.nan)
            continue

        seg = "largemid" if bool(lm.loc[fm, p]) else ("small" if bool(sm.loc[fm, p]) else None)
        if seg is None:
            out.append(np.nan)
            continue

        stock = ret.loc[win, p]
        if stock.isna().all():
            out.append(np.nan)
            continue
        stock_cum = float(np.prod(1.0 + stock.fillna(0.0).values) - 1.0)
        bench_cum = float(np.prod(1.0 + seg_ew[seg].loc[win].fillna(0.0).values) - 1.0)
        out.append(stock_cum - bench_cum)
    return pd.Series(out, index=events.index, dtype=float)


def calendar_time_excess(panel, events: pd.DataFrame, hold: int = 3) -> dict:
    """Secondary arm: EW cohort portfolio, names held `hold` months post-filing."""
    ret = panel.monthly_ret
    months = ret.index
    lm, sm = segment_mask(panel, "largemid"), segment_mask(panel, "small")
    uni_ew = ret.where(lm | sm).mean(axis=1)

    flags: dict[pd.Timestamp, set[str]] = {}
    for _, r in events.iterrows():
        fm = pd.Timestamp(r["date_filed"]).to_period("M").to_timestamp("M")
        if fm in months:
            flags.setdefault(fm, set()).add(str(int(r["permno"])))

    rows = []
    for i, m in enumerate(months):
        held: set[str] = set()
        for k in range(1, hold + 1):
            if i - k >= 0:
                held |= flags.get(months[i - k], set())
        held &= set(ret.columns)
        if len(held) < 5:
            continue
        r_m = ret.loc[m, list(held)].dropna()
        if r_m.empty:
            continue
        rows.append({"month": m, "cohort": float(r_m.mean()),
                     "universe": float(uni_ew.loc[m]), "n": int(len(r_m))})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"months": 0}
    df["excess"] = df["cohort"] - df["universe"]
    return {"months": int(len(df)),
            "mean_excess_bps_per_mo": round(float(df["excess"].mean()) * 1e4, 1),
            "t_excess": round(_t(df["excess"]), 2),
            "median_n_names": int(df["n"].median())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true",
                    help="run the HELD-OUT 2019-2024 window (explore graduates only)")
    args = ap.parse_args()
    lo, hi = CONFIRM if args.confirm else EXPLORE
    tag = "confirm" if args.confirm else "explore"

    t0 = time.time()
    out_dir = MODULE_ROOT / "runs" / "TRIAL-EVENT-8K-FILTER"
    out_dir.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")

    flagged, audit = load_flagged_events()
    linked, link_report = link_filings_by_cik(flagged, "cik", "date_filed")
    linked = linked[(linked["date_filed"] >= lo) & (linked["date_filed"] <= hi)].copy()
    linked = linked.reset_index(drop=True)

    # Arm A: same names, dates shifted -12m (+12m where -12 leaves the panel).
    panel_lo = panel.monthly_ret.index.min()
    arm_a = linked.copy()
    shifted = arm_a["date_filed"] - pd.DateOffset(months=12)
    fallback = arm_a["date_filed"] + pd.DateOffset(months=12)
    arm_a["date_filed"] = np.where(shifted >= panel_lo, shifted, fallback)
    arm_a["date_filed"] = pd.to_datetime(arm_a["date_filed"])

    res = {}
    for arm_name, ev in (("A_pseudo", arm_a), ("B_flagged", linked)):
        arm = {}
        for h in HORIZONS:
            x = forward_market_adjusted(panel, ev, h).dropna()
            arm[f"h{h}m"] = {
                "n_events": int(len(x)),
                "mean_pct": round(float(x.mean()) * 100, 2),
                "median_pct": round(float(x.median()) * 100, 2),
                "t": round(_t(x), 2),
            }
        arm["calendar_time"] = calendar_time_excess(panel, ev)
        res[arm_name] = arm

    dec = res["B_flagged"][f"h{DECIDING_H}m"]
    passed = (dec["mean_pct"] < 0) and (dec["t"] <= (-1.5 if args.confirm else -2.0))

    out = {
        "trial": "TRIAL-EVENT-8K-FILTER",
        "window": tag, "range": [lo, hi],
        "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "items_frozen": sorted(ITEMS),
        "deciding": {"horizon_months": DECIDING_H,
                     "bar_t": -1.5 if args.confirm else -2.0,
                     **dec, "PASS": bool(passed)},
        "acquisition_audit": audit,
        "link_report": link_report,
        "n_events_in_window": int(len(linked)),
        "item_mix_in_window": {k: int(v) for k, v in
                               linked["items"].value_counts().items()},
        "arms": res,
        "elapsed_s": round(time.time() - t0, 1),
    }
    (out_dir / f"results_{tag}.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
