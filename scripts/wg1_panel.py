"""WINNER-GENOME-1 — stage 1: build the daily panel cache.

CRSP daily stock file 2002-2024, already restricted at the source pull to
`shrcd in (10,11)` and `exchcd in (1,2,3)` (see `scripts/fetch_wrds_p0.py`), so
the panel is common US stock on NYSE/AMEX/NASDAQ and nothing else.

The one thing that has to be right here is DEATH. A tournament simulation whose
universe is "names that were still trading at the end" is a machine for
manufacturing skill. So every permno gets a `last_obs` index, and every real
delisting (`dlstcd >= 200` — code 100 means STILL ACTIVE and liquidating those
would invent a price, per `daily_sim.py`) gets its delisting return written into
the return matrix on the first trading day AFTER the last quote. Performance
delists (400-591) with no `dlret` get the Shumway (1997) −0.30. After that day
the position is cash. `assert_delisting_reached` in the runner refuses to report
a result if this path never fired.

    python -m scripts.wg1_panel        # writes data/factory/wg1_panel.npz
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

RAW = MODULE_ROOT / "data" / "wrds_raw"
DSF_DIR = RAW / "dsf_full"
OUT = MODULE_ROOT / "data" / "factory" / "wg1_panel.npz"
OUT_META = MODULE_ROOT / "data" / "factory" / "wg1_panel_meta.json"

YEARS = range(2002, 2025)
FIRST_REAL_DELIST_CODE = 200
PERF_DELIST_LO, PERF_DELIST_HI = 400, 591
SHUMWAY = -0.30


def build() -> dict:
    t0 = time.time()
    frames = []
    for yr in YEARS:
        f = DSF_DIR / f"dsf_{yr}.parquet"
        if not f.exists():
            raise SystemExit(f"missing {f}")
        df = pd.read_parquet(f, columns=["permno", "date", "ret", "prc",
                                         "vol", "shrout"])
        frames.append(df)
        print(f"  {yr}: {len(df):,} rows", flush=True)
    df = pd.concat(frames, ignore_index=True)
    del frames
    df["permno"] = df["permno"].astype("int64")
    for c in ("ret", "prc", "vol", "shrout"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    print(f"concat {len(df):,} rows in {time.time()-t0:.0f}s", flush=True)

    dates = np.sort(df["date"].unique())
    permnos = np.sort(df["permno"].unique())
    d_ix = pd.Index(dates)
    p_ix = pd.Index(permnos)
    di = d_ix.get_indexer(df["date"].values)
    pi = p_ix.get_indexer(df["permno"].values)
    nD, nP = len(dates), len(permnos)
    print(f"grid {nD} dates x {nP} permnos = {nD*nP/1e6:.0f}M cells",
          flush=True)

    def mat(vals: np.ndarray) -> np.ndarray:
        m = np.full((nD, nP), np.nan, dtype=np.float32)
        m[di, pi] = vals.astype(np.float32)
        return m

    prc = np.abs(df["prc"].values)
    RET = mat(df["ret"].values)
    PRC = mat(prc)
    DOLVOL = mat(prc * df["vol"].values)
    MCAP = mat(prc * df["shrout"].values * 1e3)     # shrout is in thousands
    del df, di, pi, prc

    alive = np.isfinite(PRC)
    has_any = alive.any(axis=0)
    if not has_any.all():
        keep = np.where(has_any)[0]
        RET, PRC, DOLVOL, MCAP = (m[:, keep] for m in (RET, PRC, DOLVOL, MCAP))
        permnos = permnos[keep]
        alive = alive[:, keep]
        nP = len(permnos)
    first_obs = alive.argmax(axis=0)
    last_obs = nD - 1 - alive[::-1].argmax(axis=0)

    # ── delisting splice ────────────────────────────────────────────────
    dl = pd.read_parquet(RAW / "crsp_dsedelist.parquet",
                         columns=["permno", "dlstdt", "dlstcd", "dlret"])
    dl = dl[dl["dlstcd"] >= FIRST_REAL_DELIST_CODE]
    dl = dl.sort_values("dlstdt").drop_duplicates("permno", keep="last")
    dl_map = {int(r.permno): (int(r.dlstcd),
                              float(r.dlret) if pd.notna(r.dlret) else np.nan)
              for r in dl.itertuples()}

    delist_ret = np.zeros(nP, dtype=np.float32)
    delist_day = np.full(nP, -1, dtype=np.int32)
    n_spliced = n_shumway = 0
    for j, p in enumerate(permnos):
        rec = dl_map.get(int(p))
        if rec is None:
            continue
        lo = int(last_obs[j])
        if lo >= nD - 1:                       # still trading at sample end
            continue
        code, r = rec
        if not np.isfinite(r):
            if PERF_DELIST_LO <= code <= PERF_DELIST_HI:
                r = SHUMWAY
                n_shumway += 1
            else:
                r = 0.0
        delist_ret[j] = r
        delist_day[j] = lo + 1
        n_spliced += 1

    # write the delisting return into RET on the day after the last quote
    valid = delist_day >= 0
    RET[delist_day[valid], np.where(valid)[0]] = delist_ret[valid]

    meta = {
        "n_dates": int(nD), "n_permnos": int(nP),
        "date_min": str(pd.Timestamp(dates[0]).date()),
        "date_max": str(pd.Timestamp(dates[-1]).date()),
        "delistings_spliced": int(n_spliced),
        "delistings_shumway_imputed": int(n_shumway),
        "build_seconds": round(time.time() - t0, 1),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT,
        dates=dates.astype("datetime64[D]"), permnos=permnos,
        RET=RET, PRC=PRC, DOLVOL=DOLVOL, MCAP=MCAP,
        first_obs=first_obs.astype(np.int32), last_obs=last_obs.astype(np.int32),
        delist_ret=delist_ret, delist_day=delist_day,
    )
    OUT_META.write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    build()
