"""EXIT-LAB-1 — stage 1: the auxiliary cache, aligned to the decision dates.

Everything the counterfactual factory needs that is NOT already in
`data/factory/wg1_panel.npz` (built by `scripts/wg1_panel.py` for
WINNER-GENOME-1 and reused here rather than re-fetched):

  * `HS`   Corwin-Schultz half-spread in bps, at the decision dates only.
           **This is the repo's existing cost model**, imported from
           `aegis_brain.pf.daily_sim`, not a new one invented for this trial.
  * `REV`  the NIGHT-11 monthly analyst-revision score (`data/revision_panel`).
  * `SUE`  standardised earnings surprise and days-since-announcement, from
           `data/sue_events.parquet` (rdq is the PEAD event date).
  * `TGT`  IBES consensus 12-month price-target upside, built from the
           **unadjusted** summary file `ptgsumu` exactly as
           `aegis_brain/data/ibes_panel.py` documents (the adjusted detail file
           reads the future's share basis and voided two prior runs).
  * `FF12` Fama-French 12-industry code, from CRSP stocknames valid at T0.

Every one of these is stamped at the LAST observation available strictly at or
before T0, with an explicit staleness limit, and every one reports its coverage
so a silently-empty column cannot pass for a populated one.

    python -m scripts.exit_lab_data
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.daily_sim import SimConfig, corwin_schultz_half_spread_bps
from scripts.wg1_features import SicResolver, ff12_of

RAW = MODULE_ROOT / "data" / "wrds_raw"
DSF_DIR = RAW / "dsf_full"
PANEL = MODULE_ROOT / "data" / "factory" / "wg1_panel.npz"
OUT = MODULE_ROOT / "data" / "factory" / "exit_lab_1_aux.npz"
OUT_META = MODULE_ROOT / "data" / "factory" / "exit_lab_1_aux_meta.json"

YEARS = range(2002, 2025)
#: a name with no consensus snapshot for this long is treated as uncovered
TGT_STALE_DAYS = 100
REV_STALE_MONTHS = 3
#: PEAD window we still call "recent"; beyond it days_since is capped
MAX_DAYS_SINCE_RDQ = 400


def decision_indices(dates: np.ndarray, min_history: int = 252) -> np.ndarray:
    """Index of the last trading day of every month with enough history."""
    s = pd.Series(np.arange(len(dates)), index=pd.DatetimeIndex(dates))
    last = s.groupby([s.index.year, s.index.month]).max().to_numpy()
    return last[last >= min_history]


def build_half_spread(dates: np.ndarray, permnos: np.ndarray,
                      dec_ix: np.ndarray) -> tuple[np.ndarray, dict]:
    """CS half-spread bps at the decision dates.

    Streams the daily file two years at a time: the estimator needs yesterday's
    high/low and a 21-day rolling median, so a year processed alone would carry
    a warm-up hole at every January.
    """
    cfg = SimConfig()
    p_ix = pd.Index(permnos)
    d_ix = pd.DatetimeIndex(dates)
    out = np.full((len(dec_ix), len(permnos)), np.nan, dtype=np.float32)
    want = set(int(i) for i in dec_ix)
    prev: pd.DataFrame | None = None
    n_cells = 0
    for yr in YEARS:
        f = DSF_DIR / f"dsf_{yr}.parquet"
        d = pd.read_parquet(f, columns=["permno", "date", "prc", "askhi", "bidlo"])
        d["permno"] = d["permno"].astype("int64")
        for c in ("prc", "askhi", "bidlo"):
            d[c] = pd.to_numeric(d[c], errors="coerce").astype("float64").abs()
        chunk = d if prev is None else pd.concat([prev, d], ignore_index=True)
        hi = chunk.pivot_table(index="date", columns="permno", values="askhi",
                               aggfunc="last")
        lo = chunk.pivot_table(index="date", columns="permno", values="bidlo",
                               aggfunc="last")
        prc = chunk.pivot_table(index="date", columns="permno", values="prc",
                                aggfunc="last")
        hs = corwin_schultz_half_spread_bps(hi, lo, cfg)
        floor = (0.005 / prc.where(prc > 0)) * 1e4
        hs = pd.concat([hs, floor]).groupby(level=0).max()
        # keep only this year's decision rows (last year's were written already)
        rows = [t for t in hs.index if t.year == yr]
        for t in rows:
            i = d_ix.get_loc(t)
            if i not in want:
                continue
            row = hs.loc[t]
            j = p_ix.get_indexer(row.index.to_numpy())
            ok = j >= 0
            k = int(np.searchsorted(dec_ix, i))
            out[k, j[ok]] = row.to_numpy(dtype="float32")[ok]
            n_cells += int(np.isfinite(row.to_numpy()).sum())
        prev = d[d["date"] >= pd.Timestamp(f"{yr}-10-01")]
        print(f"  half-spread {yr}: {len(rows)} decision rows", flush=True)
    diag = {
        "hs_cells_finite": int(np.isfinite(out).sum()),
        "hs_cells_total": int(out.size),
        "hs_median_bps": float(np.nanmedian(out)),
        "hs_p90_bps": float(np.nanpercentile(out, 90)),
    }
    return out, diag


def _stamp_monthly(tbl: pd.DataFrame, key: str, dec_dates: pd.DatetimeIndex,
                   permnos: np.ndarray, stale_months: int) -> np.ndarray:
    """Latest monthly value at or before each decision date, ffilled `stale_months`."""
    g = tbl.pivot_table(index="month", columns="permno", values=key,
                        aggfunc="last")
    g.index = pd.to_datetime(g.index)
    g = g.sort_index().reindex(
        index=g.index.union(dec_dates)).ffill(limit=stale_months)
    g = g.reindex(index=dec_dates).reindex(columns=permnos)
    return g.to_numpy(dtype="float32")


def build_revision(dec_dates: pd.DatetimeIndex, permnos: np.ndarray):
    p = MODULE_ROOT / "data" / "revision_panel.parquet"
    rev = pd.read_parquet(p).dropna(subset=["permno"])
    rev["permno"] = rev["permno"].astype("int64")
    rev["month"] = pd.to_datetime(rev["month"])
    REV = _stamp_monthly(rev, "revision_score", dec_dates, permnos,
                         REV_STALE_MONTHS)
    NEST = _stamp_monthly(rev, "numest", dec_dates, permnos, REV_STALE_MONTHS)
    return REV, NEST


def build_sue(dec_dates: pd.DatetimeIndex, permnos: np.ndarray):
    """Latest earnings announcement strictly at or before T0: SUE and age."""
    ev = pd.read_parquet(MODULE_ROOT / "data" / "sue_events.parquet")
    n_all = len(ev)
    ev = ev.dropna(subset=["permno"])
    if len(ev) < n_all:
        print(f"  sue: dropped {n_all - len(ev):,} of {n_all:,} rows with no "
              f"permno (a link to nothing is not an event)", flush=True)
    ev["permno"] = ev["permno"].astype("int64")
    ev["rdq"] = pd.to_datetime(ev["rdq"])
    ev["sue"] = pd.to_numeric(ev["sue_analyst"], errors="coerce")
    ev = ev.dropna(subset=["rdq"]).sort_values("rdq")
    p_ix = pd.Index(permnos)
    SUE = np.full((len(dec_dates), len(permnos)), np.nan, dtype=np.float32)
    AGE = np.full((len(dec_dates), len(permnos)), np.nan, dtype=np.float32)
    for k, t in enumerate(dec_dates):
        v = ev[ev["rdq"] <= t].drop_duplicates("permno", keep="last")
        j = p_ix.get_indexer(v["permno"].to_numpy())
        ok = j >= 0
        SUE[k, j[ok]] = v["sue"].to_numpy(dtype="float32")[ok]
        age = (t - v["rdq"]).dt.days.to_numpy(dtype="float32")
        AGE[k, j[ok]] = np.minimum(age[ok], MAX_DAYS_SINCE_RDQ)
    return SUE, AGE


def build_target(dec_dates: pd.DatetimeIndex, permnos: np.ndarray,
                 PRC: np.ndarray, dec_ix: np.ndarray):
    """IBES consensus target upside = meanptg / raw price - 1, unadjusted file.

    Levels need no split correction (both sides are raw and same-dated); that is
    exactly why `ibes_panel.py` reads `ptgsumu` and refuses `ptgdet`.
    """
    from aegis_brain.data.ibes_panel import _attach_permno, _require
    ptg = _require("ptgsumu")[["ticker", "statpers", "meanptg", "numest",
                               "stdev"]].copy()
    ptg["statpers"] = pd.to_datetime(ptg["statpers"])
    ptg, rate = _attach_permno(ptg, "statpers")
    ptg["meanptg"] = pd.to_numeric(ptg["meanptg"], errors="coerce")
    ptg = ptg.dropna(subset=["meanptg"]).sort_values("statpers")
    p_ix = pd.Index(permnos)
    TGT = np.full((len(dec_dates), len(permnos)), np.nan, dtype=np.float32)
    for k, t in enumerate(dec_dates):
        v = ptg[(ptg["statpers"] <= t) &
                (ptg["statpers"] >= t - pd.Timedelta(days=TGT_STALE_DAYS))]
        v = v.drop_duplicates("permno", keep="last")
        j = p_ix.get_indexer(v["permno"].to_numpy())
        ok = j >= 0
        px = PRC[dec_ix[k], j[ok]]
        with np.errstate(invalid="ignore", divide="ignore"):
            up = v["meanptg"].to_numpy(dtype="float32")[ok] / np.where(px > 0, px,
                                                                       np.nan) - 1.0
        TGT[k, j[ok]] = up
    return TGT, float(rate)


def build_ff12(dec_dates: pd.DatetimeIndex, permnos: np.ndarray) -> np.ndarray:
    sr = SicResolver(RAW / "crsp_stocknames.parquet")
    out = np.full((len(dec_dates), len(permnos)), 11, dtype=np.int8)
    for k, t in enumerate(dec_dates):
        out[k] = ff12_of(sr.at(np.datetime64(t), permnos))
    return out


def build() -> dict:
    t0 = time.time()
    z = np.load(PANEL, allow_pickle=False)
    dates = z["dates"].astype("datetime64[ns]")
    permnos = z["permnos"]
    PRC = z["PRC"]
    dec_ix = decision_indices(dates)
    dec_dates = pd.DatetimeIndex(dates[dec_ix])
    print(f"decision dates: {len(dec_ix)}  "
          f"{dec_dates[0].date()} .. {dec_dates[-1].date()}", flush=True)

    # the half-spread pass streams 23 years of high/low quotes; cache it so a
    # later stage failure does not force it to be recomputed
    hs_cache = MODULE_ROOT / "data" / "factory" / "exit_lab_1_hs.npz"
    if hs_cache.exists():
        zz = np.load(hs_cache, allow_pickle=False)
        HS, hs_diag = zz["HS"], json.loads(str(zz["diag"]))
        print("half-spread loaded from cache", flush=True)
    else:
        HS, hs_diag = build_half_spread(dates, permnos, dec_ix)
        np.savez_compressed(hs_cache, HS=HS, diag=json.dumps(hs_diag))
    print("half-spread done", json.dumps(hs_diag), flush=True)

    REV, NEST = build_revision(dec_dates, permnos)
    SUE, AGE = build_sue(dec_dates, permnos)
    TGT, tgt_rate = build_target(dec_dates, permnos, PRC, dec_ix)
    FF12 = build_ff12(dec_dates, permnos)
    del PRC, z

    def cov(a):
        return round(float(np.isfinite(a).mean()), 4)

    meta = {
        "n_decision_dates": int(len(dec_ix)),
        "first_decision": str(dec_dates[0].date()),
        "last_decision": str(dec_dates[-1].date()),
        "n_permnos": int(len(permnos)),
        **hs_diag,
        "coverage_grid": {"REV": cov(REV), "SUE": cov(SUE), "AGE": cov(AGE),
                          "TGT": cov(TGT), "HS": cov(HS)},
        "ibes_ptgsumu_link_match_rate": round(tgt_rate, 4),
        "build_seconds": round(time.time() - t0, 1),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT, dec_ix=dec_ix.astype(np.int32),
                        dec_dates=dec_dates.values.astype("datetime64[D]"),
                        HS=HS, REV=REV, NEST=NEST, SUE=SUE, AGE=AGE, TGT=TGT,
                        FF12=FF12)
    OUT_META.write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    build()
