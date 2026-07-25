"""TRIAL-BRAIN-011 — FDA daily-CAR successor. ONE run, frozen spec.

Pre-registered in TRIALS/TRIAL-BRAIN-011-fda-daily-car.md (committed BEFORE
this runs). Explore events 2002-07..2018-12; confirm 2019-01..2024-11 is
read ONLY if the explore bar passes (gate implemented below, frozen).

Usage:  .venv\\Scripts\\python -m scripts.run_trial_011
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("t011")

RAW = MODULE_ROOT / "data" / "wrds_raw"
EV = MODULE_ROOT / "data" / "events"
OUT = MODULE_ROOT / "data" / "factory"

EST_LO, EST_HI = -120, -30          # estimation window (trading days)
CAR_LO, CAR_HI = 1, 20              # primary drift window
MIN_EST_OBS = 60


def _t(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return np.nan
    return float(x.mean() / x.std(ddof=1) * np.sqrt(len(x)))


def car_study(events: pd.DataFrame, px: dict, spy: pd.Series) -> pd.DataFrame:
    """Per-event market-model CARs. px: permno -> DataFrame(date-indexed)."""
    rows, drop_no_data, drop_est = 0, 0, 0
    out = []
    for ev in events.itertuples():
        d = px.get(ev.permno)
        if d is None:
            drop_no_data += 1
            continue
        idx = d.index.searchsorted(pd.Timestamp(ev.approval_date))
        if idx + CAR_HI >= len(d.index) or idx + EST_LO < 0:
            drop_no_data += 1
            continue
        est = d.iloc[idx + EST_LO: idx + EST_HI]
        pair = pd.DataFrame({"r": est["ret"], "m": spy.reindex(est.index)}).dropna()
        if len(pair) < MIN_EST_OBS:
            drop_est += 1
            continue
        beta, alpha = np.polyfit(pair["m"], pair["r"], 1)
        win = d.iloc[idx + EST_LO: idx + CAR_HI + 1]
        m = spy.reindex(win.index)
        ar = win["ret"] - (alpha + beta * m)
        rel = np.arange(EST_LO, EST_LO + len(win))
        ar_rel = pd.Series(ar.to_numpy(), index=rel)
        dv = (win["prc"].abs() * win["vol"]).reindex(win.index)
        dv_rel = pd.Series(dv.to_numpy(), index=rel)
        vol_rel = pd.Series(win["vol"].to_numpy(), index=rel)
        att_num = vol_rel.loc[-5:-1].mean()
        att_den = vol_rel.loc[-60:-11].mean()
        out.append({
            "permno": ev.permno, "date": ev.approval_date,
            "priority": ev.review_priority == "PRIORITY",
            "car_1_20": float(ar_rel.loc[CAR_LO:CAR_HI].sum()),
            "car_1_5": float(ar_rel.loc[1:5].sum()),
            "car_m1_2": float(ar_rel.loc[-1:2].sum()),
            "ar_0": float(ar_rel.loc[0]) if 0 in ar_rel.index else np.nan,
            "attention": float(att_num / att_den) if att_den and att_den > 0 else np.nan,
            "dollar_vol": float(dv_rel.loc[-60:-11].mean()),
            "beta": float(beta),
        })
        rows += 1
    log.info("events used %d | dropped: no_data/window %d, est_obs %d",
             rows, drop_no_data, drop_est)
    return pd.DataFrame(out)


def summarize(df: pd.DataFrame, label: str) -> dict:
    s = {"label": label, "n": int(len(df))}
    for c in ("car_1_20", "car_1_5", "car_m1_2", "ar_0"):
        v = df[c].to_numpy(dtype=float)
        s[c] = {"mean_pct": round(float(np.nanmean(v)) * 100, 2), "t": round(_t(v), 2)}
    med_att = df["attention"].median()
    lo, hi = df[df["attention"] <= med_att], df[df["attention"] > med_att]
    s["attention_low"] = {"n": len(lo), "car_1_20_pct": round(float(lo["car_1_20"].mean()) * 100, 2),
                          "t": round(_t(lo["car_1_20"].to_numpy(dtype=float)), 2)}
    s["attention_high"] = {"n": len(hi), "car_1_20_pct": round(float(hi["car_1_20"].mean()) * 100, 2),
                           "t": round(_t(hi["car_1_20"].to_numpy(dtype=float)), 2)}
    pri, std = df[df["priority"]], df[~df["priority"]]
    s["priority"] = {"n": len(pri), "car_1_20_pct": round(float(pri["car_1_20"].mean()) * 100, 2),
                     "t": round(_t(pri["car_1_20"].to_numpy(dtype=float)), 2)}
    s["standard"] = {"n": len(std), "car_1_20_pct": round(float(std["car_1_20"].mean()) * 100, 2),
                     "t": round(_t(std["car_1_20"].to_numpy(dtype=float)), 2)}
    med_dv = df["dollar_vol"].median()
    sm, lg = df[df["dollar_vol"] <= med_dv], df[df["dollar_vol"] > med_dv]
    s["small_half"] = {"n": len(sm), "car_1_20_pct": round(float(sm["car_1_20"].mean()) * 100, 2),
                       "t": round(_t(sm["car_1_20"].to_numpy(dtype=float)), 2)}
    s["large_half"] = {"n": len(lg), "car_1_20_pct": round(float(lg["car_1_20"].mean()) * 100, 2),
                       "t": round(_t(lg["car_1_20"].to_numpy(dtype=float)), 2)}
    return s


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    xw = pd.read_parquet(EV / "fda_crosswalk.parquet")
    ev = xw.dropna(subset=["permno"]).copy()
    ev["permno"] = ev["permno"].astype(int)
    ev["approval_date"] = pd.to_datetime(ev["approval_date"])
    ev = ev.sort_values("approval_date")
    # dedupe: one event per permno per 30 calendar days (earliest kept)
    keep, last = [], {}
    for r in ev.itertuples():
        if r.permno in last and (r.approval_date - last[r.permno]).days <= 30:
            continue
        keep.append(r.Index)
        last[r.permno] = r.approval_date
    n_dropped_dedupe = len(ev) - len(keep)
    ev = ev.loc[keep]

    dsf = pd.read_parquet(RAW / "dsf_pharma_2002.parquet")
    dsf["date"] = pd.to_datetime(dsf["date"])
    px = {p: g.set_index("date").sort_index()
          for p, g in dsf.groupby("permno")}
    spy = pd.read_parquet(MODULE_ROOT / "data" / "macro" / "etf_daily_close.parquet")
    spy = spy["SPY"].sort_index().pct_change()

    explore_ev = ev[(ev["approval_date"] >= "2002-07-01")
                    & (ev["approval_date"] <= "2018-12-31")]
    log.info("events: %d total after dedupe (-%d), %d explore",
             len(ev), n_dropped_dedupe, len(explore_ev))

    exp_df = car_study(explore_ev, px, spy)
    exp = summarize(exp_df, "explore 2002-07..2018-12")
    exp_pass = (exp["car_1_20"]["mean_pct"] > 0 and exp["car_1_20"]["t"] >= 2.0)
    out = {"trial": "TRIAL-BRAIN-011", "n_dedupe_dropped": n_dropped_dedupe,
           "explore": exp,
           "explore_verdict": "PASS -> confirm runs" if exp_pass else "REJECT (bar: mean>0 AND t>=2.0)"}

    if exp_pass:  # frozen gate — confirm events read ONLY here
        confirm_ev = ev[(ev["approval_date"] >= "2019-01-01")
                        & (ev["approval_date"] <= "2024-11-30")]
        cf_df = car_study(confirm_ev, px, spy)
        cf = summarize(cf_df, "confirm 2019-01..2024-11 (held out)")
        out["confirm"] = cf
        out["confirm_verdict"] = ("PASS" if (cf["car_1_20"]["mean_pct"] > 0
                                             and cf["car_1_20"]["t"] >= 1.0)
                                  else "REJECT (bar: mean>0 AND t>=1.0)")
        cf_df.to_parquet(OUT / "trial011_confirm_events.parquet")

    exp_df.to_parquet(OUT / "trial011_explore_events.parquet")
    with open(OUT / "trial011_fda_daily_car.json", "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
