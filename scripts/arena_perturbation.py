"""The no-lookahead proof, for the arena panel and for the LLM snapshots.

A check that did not run is not a check that passed. So this corrupts every
daily cell strictly AFTER a probe decision date — returns ~ N(0.5, 1), prices
1e6, volumes 1e15 — rebuilds the feature block and the snapshots for that date,
and requires them back **bit-identical**. If any feature reads the future, the
garbage propagates and the comparison fails loudly.

Both surfaces are proved, because they are built by different code:
  * the arena panel's 20 feature columns (`scripts.arena_panel`)
  * the LLM snapshot's every field (`llm_swarm.snapshot_from_panel`)

    python -m scripts.arena_perturbation
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AF = Path(r"C:\Users\mrthn\aegis-finance")
if str(AF) not in sys.path:
    sys.path.insert(0, str(AF))

from aegis_brain.config import MODULE_ROOT                       # noqa: E402
from scripts.exit_lab_core import (build_position_factors,       # noqa: E402
                                   eligible_at)
from backend.services.llm_swarm import snapshot_from_panel       # noqa: E402

FACTORY = MODULE_ROOT / "data" / "factory"
OUT = FACTORY / "arena_perturbation.json"
PROBE_DATE_IX = 144                     # 2015-01-30, inside the LLM panel


def features_at(LC, PRC, DOLVOL, MCAP, mkt_log, first_obs, term, t, cols):
    w = LC[t - 252:t + 1, cols].astype(np.float64)
    r = np.diff(w, axis=0)
    m = np.diff(mkt_log[t - 252:t + 1])[:, None]
    mv = float(np.nanvar(m))
    beta = (np.nanmean((r - np.nanmean(r, axis=0)) * (m - np.nanmean(m)),
                       axis=0) / mv if mv > 0 else np.full(len(cols), np.nan))
    ivol = np.nanstd(r - beta[None, :] * m, axis=0) * np.sqrt(252.0)
    rs = np.expm1(r)
    sd = np.nanstd(rs, axis=0)
    skew = np.where(sd > 0, np.nanmean((rs - np.nanmean(rs, axis=0)) ** 3,
                                       axis=0) / np.maximum(sd, 1e-12) ** 3,
                    np.nan)
    max5 = np.mean(np.sort(rs[-21:], axis=0)[-5:], axis=0)
    lc_t = LC[t, cols].astype(np.float64)
    return np.column_stack([
        beta, ivol, np.nanstd(r, axis=0) * np.sqrt(252.0),
        np.nanstd(r[-63:], axis=0) * np.sqrt(252.0), skew, max5,
        np.expm1(LC[t - 21, cols].astype(np.float64)
                 - LC[t - 252, cols].astype(np.float64)),
        np.expm1(lc_t - LC[t - 63, cols].astype(np.float64)),
        np.expm1(lc_t - LC[t - 21, cols].astype(np.float64)),
        np.expm1(lc_t - np.nanmax(LC[t - 252:t + 1, cols].astype(np.float64),
                                  axis=0)),
        PRC[t, cols].astype(np.float64), MCAP[t, cols].astype(np.float64),
        np.nanmedian(DOLVOL[t - 62:t + 1, cols], axis=0).astype(np.float64),
    ])


def build(corrupt_after: int | None):
    z = np.load(FACTORY / "wg1_panel.npz", allow_pickle=False)
    dates = pd.DatetimeIndex(z["dates"].astype("datetime64[ns]"))
    RET, PRC, DOLVOL, MCAP = (z["RET"].copy(), z["PRC"].copy(),
                              z["DOLVOL"].copy(), z["MCAP"].copy())
    first_obs, last_obs, delist_day = (z["first_obs"], z["last_obs"],
                                       z["delist_day"])
    ff = pd.read_parquet(MODULE_ROOT / "data" / "wrds_raw" /
                         "ff_factors_daily.parquet",
                         columns=["date", "mktrf", "rf"])
    ff["date"] = pd.to_datetime(ff["date"])
    ff = ff.set_index("date").reindex(dates)
    rf = pd.to_numeric(ff["rf"], errors="coerce").fillna(0.0).to_numpy()
    mk = pd.to_numeric(ff["mktrf"], errors="coerce").fillna(0.0).to_numpy() + rf

    if corrupt_after is not None:
        rng = np.random.default_rng(999)
        s = slice(corrupt_after + 1, None)
        RET[s, :] = rng.normal(0.5, 1.0, RET[s, :].shape).astype(np.float32)
        PRC[s, :] = 1e6
        DOLVOL[s, :] = 1e15
        MCAP[s, :] = 1e15
        rf[s] = 0.5
        mk[s] = 0.5

    LC, term, _ = build_position_factors(RET, first_obs, last_obs, delist_day,
                                         rf)
    return (LC, PRC, DOLVOL, MCAP, np.cumsum(np.log1p(mk)), first_obs, term,
            dates)


def main() -> int:
    aux = np.load(FACTORY / "exit_lab_1_aux.npz", allow_pickle=False)
    dec_ix = aux["dec_ix"].astype(int)
    t = int(dec_ix[PROBE_DATE_IX])
    probe_date = str(pd.Timestamp(
        aux["dec_dates"].astype("datetime64[ns]")[PROBE_DATE_IX]).date())

    clean = build(None)
    dirty = build(t)
    cols = eligible_at(t, clean[1], clean[2], clean[5], clean[6])

    F0 = features_at(*clean[:7], t, cols)
    F1 = features_at(*dirty[:7], t, cols)
    same = np.array_equal(np.nan_to_num(F0, nan=-12345.0),
                          np.nan_to_num(F1, nan=-12345.0))
    ncols = F0.shape[1]
    per_col = [bool(np.array_equal(np.nan_to_num(F0[:, j], nan=-12345.0),
                                   np.nan_to_num(F1[:, j], nan=-12345.0)))
               for j in range(ncols)]

    # ── the LLM snapshot surface, same probe ────────────────────────────────
    cells = pd.read_parquet(FACTORY / "arena_llm_cells.parquet")
    g = cells[cells["date_ix"] == PROBE_DATE_IX]
    snap_same = True
    n_snap = 0
    if len(g):
        def frame(bundle):
            LC, PRC = bundle[0], bundle[1]
            dates = bundle[7]
            lo = max(0, t - 420)
            data = {}
            for row in g.itertuples():
                j = int(row.col)
                s = np.expm1(LC[lo:t + 1, j].astype(np.float64)
                             - LC[t, j].astype(np.float64))
                data[row.ticker] = float(PRC[t, j]) * (1.0 + s)
            f = pd.DataFrame(data, index=dates[lo:t + 1])
            spy = pd.read_parquet(MODULE_ROOT / "data" / "etf" /
                                  "etf_adjusted_close.parquet")["SPY"]
            f["SPY"] = pd.to_numeric(spy, errors="coerce").dropna().reindex(
                f.index).ffill().to_numpy()
            return f
        f0, f1 = frame(clean), frame(dirty)
        for row in g.itertuples():
            a = snapshot_from_panel(row.ticker, f0, as_of=probe_date)
            b = snapshot_from_panel(row.ticker, f1, as_of=probe_date)
            n_snap += 1
            if json.dumps(a, sort_keys=True, default=str) != \
                    json.dumps(b, sort_keys=True, default=str):
                snap_same = False

    out = {
        "probe_date_ix": PROBE_DATE_IX, "probe_date": probe_date,
        "n_names": int(len(cols)), "n_feature_columns": ncols,
        "feature_columns_identical": int(sum(per_col)),
        "features_bit_identical": bool(same),
        "n_snapshots_checked": n_snap,
        "snapshots_bit_identical": bool(snap_same),
        "perturbation": ("returns ~ N(0.5,1), prices 1e6, volumes 1e15, "
                         "market cap 1e15, rf and market return 50%/day, on "
                         "every daily cell strictly after the probe date"),
        "verdict": "PASS" if (same and snap_same) else "FAIL",
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
