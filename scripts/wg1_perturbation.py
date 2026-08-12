"""WINNER-GENOME-1 — prereg §7.3: the no-lookahead perturbation proof.

A backtest that reads the future does not announce itself; it just looks good.
The only cheap proof that a formation-date computation is causal is to destroy
every observation after the formation date and require the formed object to
come back bit-identical.

This rebuilds the eligible universe and all five family pools for a named
window twice — once on the real panel, once on a panel where every return,
price, volume and market-cap cell strictly after T0 has been replaced with
garbage — and compares them byte for byte.

    python -m scripts.wg1_perturbation
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from scripts.wg1_features import SicResolver, QualityResolver, ff12_of, pct_rank

RAW = MODULE_ROOT / "data" / "wrds_raw"
FAC = MODULE_ROOT / "data" / "factory"

WINDOW, HIST_DAYS, LB_MOM, LB_TREND = 25, 252, 126, 63
LB_VOL_SHORT, LB_VOL_LONG = 21, 252
MIN_PRICE, MIN_DOLVOL, UNIVERSE_TOP = 5.0, 1_000_000.0, 1500


def build_pools(RET, PRC, DOLVOL, MCAP, first_obs, last_obs, t0,
                permnos, dates, sic, qual):
    alive = (first_obs <= t0 - HIST_DAYS + 1) & (last_obs >= t0)
    price = PRC[t0]
    with np.errstate(invalid="ignore"):
        elig = alive & np.isfinite(price) & (price >= MIN_PRICE)
    cand = np.where(elig)[0]
    dv63 = np.nanmedian(DOLVOL[t0 - LB_TREND + 1:t0 + 1, cand], axis=0)
    ok = np.isfinite(dv63) & (dv63 >= MIN_DOLVOL)
    cand, dv63 = cand[ok], dv63[ok]
    if len(cand) > UNIVERSE_TOP:
        keep = np.argsort(-dv63)[:UNIVERSE_TOP]
        cand = cand[keep]
    Rm = np.nan_to_num(RET[t0 - LB_MOM + 1:t0 + 1, cand].astype(np.float64))
    ret126 = np.prod(1.0 + Rm, axis=0) - 1.0
    vol126 = Rm.std(axis=0, ddof=1)
    Rt = Rm[-LB_TREND:]
    ret63 = np.prod(1.0 + Rt, axis=0) - 1.0
    vol63 = Rt.std(axis=0, ddof=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        trendq = ret63 / np.maximum(vol63 * np.sqrt(LB_TREND), 1e-6)
    dv21 = np.nanmedian(DOLVOL[t0 - LB_VOL_SHORT + 1:t0 + 1, cand], axis=0)
    dv252 = np.nanmedian(DOLVOL[t0 - LB_VOL_LONG + 1:t0 + 1, cand], axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        volacc = dv21 / np.maximum(dv252, 1.0)
    mcap = MCAP[t0, cand].astype(np.float64)
    px = PRC[t0, cand].astype(np.float64)
    siccd = sic.at(dates[t0], permnos[cand])
    roe, de = qual.at(dates[t0], permnos[cand])

    f1 = np.nanmean(np.vstack([pct_rank(ret126), pct_rank(volacc),
                               pct_rank(trendq)]), axis=0)
    cov_q = np.isfinite(roe) & np.isfinite(de)
    pools = {
        "universe": permnos[cand],
        "F1": permnos[cand][f1 >= np.nanpercentile(f1, 80)],
        "F2": permnos[cand][vol126 >= np.nanpercentile(vol126, 80)],
        "F3": permnos[cand][cov_q
                            & (ret126 >= np.nanpercentile(ret126, 66.667))
                            & (roe > 0)
                            & (roe >= np.nanmedian(roe[cov_q]))
                            & (de <= np.nanmedian(de[cov_q]))],
        "F4_ind": ff12_of(siccd),
        "F5": permnos[cand][(mcap <= np.nanpercentile(mcap, 25))
                            & (px <= np.nanpercentile(px, 25))],
        "vol126": vol126,
    }
    return pools


def main() -> int:
    z = np.load(FAC / "wg1_panel.npz", allow_pickle=False)
    dates = z["dates"].astype("datetime64[D]")
    permnos = z["permnos"]
    RET, PRC, DOLVOL, MCAP = (z[k].copy() for k in
                              ("RET", "PRC", "DOLVOL", "MCAP"))
    first_obs, last_obs = z["first_obs"], z["last_obs"]
    sic = SicResolver(RAW / "crsp_stocknames.parquet")
    qual = QualityResolver(RAW / "comp_funda.parquet", RAW / "ccm_link.parquet")

    # a named window, chosen before running: block 120 of the tiling
    t0 = 120 * WINDOW - 1
    clean = build_pools(RET, PRC, DOLVOL, MCAP, first_obs, last_obs, t0,
                        permnos, dates, sic, qual)

    rng = np.random.default_rng(20260812)
    for M in (RET, PRC, DOLVOL, MCAP):
        M[t0 + 1:, :] = rng.normal(5.0, 9.0,
                                   size=M[t0 + 1:, :].shape).astype(M.dtype)
    dirty = build_pools(RET, PRC, DOLVOL, MCAP, first_obs, last_obs, t0,
                        permnos, dates, sic, qual)

    res = {"formation_date": str(dates[t0]), "block": 120}
    same = True
    for k in ("universe", "F1", "F2", "F3", "F5"):
        eq = (len(clean[k]) == len(dirty[k])
              and bool(np.array_equal(clean[k], dirty[k])))
        res[f"{k}_identical"] = eq
        res[f"{k}_n"] = int(len(clean[k]))
        same &= eq
    for k in ("F4_ind", "vol126"):
        eq = bool(np.array_equal(np.nan_to_num(clean[k]),
                                 np.nan_to_num(dirty[k])))
        res[f"{k}_identical"] = eq
        same &= eq
    res["perturbation_proof"] = "PASS" if same else "FAIL"
    out = FAC / "winner_genome_1_perturbation.json"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
