"""WINNER-GENOME-1 — the runner.

Pre-registered at TRIALS/PREREG_WINNER_GENOME_1.md, committed BEFORE this file
produced a number (git 4aa03aa). Nothing here may be tuned: every constant
below appears in §8 of the prereg.

    python -m scripts.run_winner_genome_1              # full run
    python -m scripts.run_winner_genome_1 --windows 6  # smoke test

What it does, in order:
  1. tiles the CRSP trading calendar 2002-2024 into non-overlapping 25-day
     blocks (no window is chosen by hand);
  2. for each block, builds the eligible universe and the five family pools
     from data strictly before the formation date;
  3. runs 2,600 simulated teams per arm under the tournament rules;
  4. re-runs each family's SELECTIONS under six sizing rules;
  5. aggregates with the WINDOW as the sampling unit and prints a measured
     80%-power MDE beside every difference (CANON §19).

The verdict is decided by ONE number per family — Delta-median vs that
family's own volatility-matched random control — and by nothing else.
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
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from scripts import wg1_sim as S
from scripts.wg1_features import (SicResolver, QualityResolver, ff12_of,
                                  is_biotech, pct_rank, FF12_NAMES)

RAW = MODULE_ROOT / "data" / "wrds_raw"
FAC = MODULE_ROOT / "data" / "factory"
PANEL = FAC / "wg1_panel.npz"

# ── frozen parameters (prereg §8) ───────────────────────────────────────
WINDOW = 25
N_TEAMS = 2600
K_MIN, K_MAX = 5, 25
CAP_TOURNAMENT = 0.20
REBAL_EVERY = 5
COST_DECIDES = 10.0
COST_LEVELS = (0.0, 10.0, 25.0)
MIN_PRICE = 5.0
MIN_DOLVOL = 1_000_000.0
UNIVERSE_TOP = 1500
HIST_DAYS = 252
LB_MOM, LB_TREND, LB_VOL_SHORT, LB_VOL_LONG = 126, 63, 21, 252
VOL_BUCKETS = 20                       # 5-percentile buckets
SEED_BASE = 20260812
REGIMES = [("2002-2003", 2002, 2003), ("2004-2006", 2004, 2006),
           ("2007-2009", 2007, 2009), ("2010-2012", 2010, 2012),
           ("2013-2015", 2013, 2015), ("2016-2018", 2016, 2018),
           ("2019-2021", 2019, 2021), ("2022-2024", 2022, 2024)]
HALF_SPLIT = np.datetime64("2014-01-01")
FAMILIES = ["F1_momentum_volume", "F2_volatility", "F3_quality_momentum",
            "F4_sector_concentrated", "F5_speculative_underdogs"]
SIZINGS = ["S1_cap20_tournament", "S2_cap10", "S3_cap5", "S4_inverse_vol",
           "S5_risk_parity_erc", "S6_half_kelly"]
RUIN_LEVEL = 0.50                      # career NAV below half of start


# ── helpers ─────────────────────────────────────────────────────────────
def nw_se(x: np.ndarray, lag: int = 1) -> float:
    """Newey-West SE of the mean. NIGHT-11 rule: the reported SE is
    max(HAC, IID), so a HAC correction can only ever widen the ruler."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    e = x - x.mean()
    g0 = float(e @ e) / n
    s = g0
    for l in range(1, min(lag, n - 1) + 1):
        gl = float(e[l:] @ e[:-l]) / n
        s += 2.0 * (1.0 - l / (lag + 1.0)) * gl
    hac = float(np.sqrt(max(s, 0.0) / n))
    iid = float(x.std(ddof=1) / np.sqrt(n))
    return max(hac, iid)


def paired_stat(deltas: np.ndarray) -> dict:
    """Mean of a per-window difference series with its measured 80%-power
    MDE. n is the number of WINDOWS — teams inside a window share a market
    factor and are not independent observations."""
    d = np.asarray(deltas, dtype=float)
    d = d[np.isfinite(d)]
    se = nw_se(d)
    m = float(d.mean()) if len(d) else float("nan")
    mde = 2.80 * se                                    # (1.96 + 0.84) * SE
    return {"mean": m, "se": se, "mde_80pct_power": mde,
            "t": float(m / se) if se and np.isfinite(se) and se > 0 else float("nan"),
            "n_windows": int(len(d)),
            "detectable": bool(np.isfinite(mde) and abs(m) >= mde)}


def summarise(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {}
    m, sd = float(x.mean()), float(x.std(ddof=1))
    sk = float(((x - m) ** 3).mean() / sd ** 3) if sd > 0 else float("nan")
    return {"mean": m, "median": float(np.median(x)), "sd": sd, "skew": sk,
            "p5": float(np.percentile(x, 5)), "p95": float(np.percentile(x, 95)),
            "max": float(x.max()), "min": float(x.min()), "n": int(len(x))}


def _pct(d: dict) -> dict:
    """Percent-scale a summary. `skew` is dimensionless and `n` is a count —
    scaling either would be a silently wrong number on every dashboard."""
    return {k: (v if k in ("skew", "n") else 100 * v) for k, v in d.items()}


class Recorder:
    """Per-arm (n_windows x n_teams) net-return matrices, NaN where the arm
    could not run in that window. Every key ever written is the search
    denominator."""

    def __init__(self, n_windows, n_teams):
        self.nW, self.nT = n_windows, n_teams
        self.mats: dict[str, np.ndarray] = {}
        self.skipped: dict[str, int] = {}

    def put(self, key, wi, vals):
        m = self.mats.get(key)
        if m is None:
            m = np.full((self.nW, self.nT), np.nan, dtype=np.float32)
            self.mats[key] = m
        v = np.asarray(vals, dtype=np.float32)
        m[wi, :len(v)] = v

    def skip(self, key):
        self.skipped[key] = self.skipped.get(key, 0) + 1
        self.mats.setdefault(key, np.full((self.nW, self.nT), np.nan,
                                          dtype=np.float32))


# ── main ────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", type=int, default=0,
                    help="smoke test: only the first N evaluable windows")
    ap.add_argument("--teams", type=int, default=N_TEAMS)
    ap.add_argument("--out", default="winner_genome_1_results.json")
    a = ap.parse_args()
    t_start = time.time()

    print("loading panel ...", flush=True)
    z = np.load(PANEL, allow_pickle=False)
    dates = z["dates"].astype("datetime64[D]")
    permnos = z["permnos"]
    RET, PRC, DOLVOL, MCAP = z["RET"], z["PRC"], z["DOLVOL"], z["MCAP"]
    first_obs, last_obs = z["first_obs"], z["last_obs"]
    delist_day = z["delist_day"]
    nD, nP = RET.shape
    print(f"  {nD} dates x {nP} permnos", flush=True)

    sic = SicResolver(RAW / "crsp_stocknames.parquet")
    qual = QualityResolver(RAW / "comp_funda.parquet", RAW / "ccm_link.parquet")

    ff = pd.read_parquet(RAW / "ff_factors_daily.parquet",
                         columns=["date", "rf"])
    rf_map = pd.Series(ff["rf"].values,
                       index=ff["date"].values.astype("datetime64[D]"))
    rf_daily = rf_map.reindex(dates).fillna(0.0).values.astype(float)

    dsi = pd.read_parquet(RAW / "crsp_dsi.parquet", columns=["date", "vwretd"])
    vw = pd.Series(dsi["vwretd"].values,
                   index=dsi["date"].values.astype("datetime64[D]"))
    vw_daily = vw.reindex(dates).fillna(0.0).values.astype(float)

    # ── window tiling (mechanical, prereg §3) ───────────────────────────
    n_blocks = nD // WINDOW
    all_starts = [i * WINDOW for i in range(n_blocks)]
    starts = [s for s in all_starts if s - 1 >= HIST_DAYS]
    if a.windows:
        starts = starts[:a.windows]
    nW, nT = len(starts), a.teams
    print(f"tiling: {n_blocks} blocks, {len(starts)} evaluable "
          f"(the first {n_blocks - len([s for s in all_starts if s-1>=HIST_DAYS])}"
          f" lack the {HIST_DAYS}-day formation history)", flush=True)

    rec = Recorder(nW, nT)
    diag = {"windows": [], "vol_match_gap": [], "delist_terminations": 0,
            "silent_terminations": 0, "cap_violations": 0,
            "cap_infeasible_S2": 0, "cap_infeasible_S3": 0,
            "f3_coverage": [], "universe_size": [], "pool_sizes": {},
            "arms_skipped": {}}
    cost_summary: dict[str, list] = {}
    winner_counts = {}
    det = {"C1_equal_weight_universe": np.full(nW, np.nan),
           "C2_largecap_top100": np.full(nW, np.nan),
           "CRSP_vwretd": np.full(nW, np.nan)}
    window_meta = []

    for wi, s0 in enumerate(starts):
        t0 = s0 - 1                                  # formation date index
        wsl = slice(s0, s0 + WINDOW)
        rng = np.random.default_rng(SEED_BASE + wi * 1000)

        # ── eligible universe ───────────────────────────────────────────
        alive = (first_obs <= t0 - HIST_DAYS + 1) & (last_obs >= t0)
        price = PRC[t0]
        with np.errstate(invalid="ignore"):
            elig = alive & np.isfinite(price) & (price >= MIN_PRICE)
        cand = np.where(elig)[0]
        if len(cand) < 200:
            continue
        dv63 = np.nanmedian(DOLVOL[t0 - LB_TREND + 1:t0 + 1, cand], axis=0)
        ok = np.isfinite(dv63) & (dv63 >= MIN_DOLVOL)
        cand, dv63 = cand[ok], dv63[ok]
        if len(cand) > UNIVERSE_TOP:
            keep = np.argsort(-dv63)[:UNIVERSE_TOP]
            cand, dv63 = cand[keep], dv63[keep]
        nU = len(cand)
        if nU < 300:
            continue
        diag["universe_size"].append(int(nU))

        # ── features, strictly pre-T0 ───────────────────────────────────
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
        ind12 = ff12_of(siccd)
        bio = is_biotech(siccd)
        roe, de = qual.at(dates[t0], permnos[cand])

        # ── window returns actually earned ──────────────────────────────
        Rwin = np.nan_to_num(RET[wsl, cand].astype(np.float64)).T   # (nU, 25)
        dead = (delist_day[cand] >= s0) & (delist_day[cand] < s0 + WINDOW)
        diag["delist_terminations"] += int(dead.sum())
        gone = (last_obs[cand] < s0 + WINDOW - 1) & ~dead
        diag["silent_terminations"] += int(gone.sum())
        rf_win = rf_daily[wsl]

        # ── deterministic controls ──────────────────────────────────────
        for key, w_det in (("C1_equal_weight_universe",
                            np.full((1, nU), 1.0 / nU)),
                           ("C2_largecap_top100", None)):
            if key == "C2_largecap_top100":
                top = np.argsort(-np.nan_to_num(mcap))[:100]
                w_det = np.zeros((1, nU))
                w_det[0, top] = 1.0 / len(top)
            p, _ = S.simulate(Rwin[None, :, :], w_det,
                              np.ones((1, nU), dtype=bool),
                              np.zeros(1, dtype=bool), rf_win, COST_DECIDES)
            det[key][wi] = p[0, -1] - 1.0
        det["CRSP_vwretd"][wi] = float(np.prod(1.0 + vw_daily[wsl]) - 1.0)

        # ── pools ───────────────────────────────────────────────────────
        r_mom, r_va, r_tq = pct_rank(ret126), pct_rank(volacc), pct_rank(trendq)
        f1_score = np.nanmean(np.vstack([r_mom, r_va, r_tq]), axis=0)
        pools: dict[str, np.ndarray] = {}
        pools["F1_momentum_volume"] = np.where(
            f1_score >= np.nanpercentile(f1_score, 80))[0]
        pools["F2_volatility"] = np.where(
            vol126 >= np.nanpercentile(vol126, 80))[0]

        cov_q = np.isfinite(roe) & np.isfinite(de)
        diag["f3_coverage"].append(float(cov_q.mean()))
        if cov_q.sum() >= 100:
            roe_med = np.nanmedian(roe[cov_q])
            de_med = np.nanmedian(de[cov_q])
            f3 = np.where(cov_q & (ret126 >= np.nanpercentile(ret126, 66.667))
                          & (roe > 0) & (roe >= roe_med) & (de <= de_med))[0]
        else:
            f3 = np.zeros(0, dtype=int)
        pools["F3_quality_momentum"] = f3

        small = mcap <= np.nanpercentile(mcap, 25)
        cheap = px <= np.nanpercentile(px, 25)
        pools["F5_speculative_underdogs"] = np.where(small & cheap)[0]

        sector_pools = [np.where(ind12 == k)[0] for k in range(12)]
        sector_ok = [k for k in range(12) if len(sector_pools[k]) >= K_MAX]
        bio_pool = np.where(bio)[0]

        # ── volatility buckets for the matched control ──────────────────
        vr = pct_rank(vol126)
        vbucket = np.clip((np.nan_to_num(vr, nan=0.5) * VOL_BUCKETS)
                          .astype(int), 0, VOL_BUCKETS - 1)
        bucket_lists = [np.where(vbucket == b)[0] for b in range(VOL_BUCKETS)]
        nonempty = np.array([len(x) > 0 for x in bucket_lists])
        bstart_v, bcount_v, bflat_v = S.flat_buckets(
            [x if len(x) else np.array([0]) for x in bucket_lists])

        # ── team scaffolding, shared by a family and its matched control ─
        kvec = rng.integers(K_MIN, K_MAX + 1, size=nT)
        kmask = np.arange(K_MAX)[None, :] < kvec[:, None]
        w_tour = S.dirichlet_weights(rng, kmask, CAP_TOURNAMENT)
        rebal = rng.random(nT) < 0.5
        if w_tour.max() > CAP_TOURNAMENT + 1e-6 or (w_tour.sum(1) > 1.0 + 1e-6).any():
            diag["cap_violations"] += 1

        pre = np.nan_to_num(RET[t0 - LB_MOM + 1:t0 + 1, cand].astype(np.float64))

        def run_arm(key, sel, do_sizing):
            """sel (nT,K_MAX) universe positions; runs the three cost levels
            and, when asked, the six sizing rules."""
            Rsel = Rwin[sel]                                     # (nT,K,25)
            for cb in COST_LEVELS:
                p, turn = S.simulate(Rsel, w_tour, kmask, rebal, rf_win, cb)
                r, dd, vol = S.path_stats(p)
                if cb == COST_DECIDES:
                    rec.put(key, wi, r)
                    rec.put(key + "|dd", wi, dd)
                    rec.put(key + "|vol", wi, vol)
                cost_summary.setdefault(f"{key}@{cb:g}bps", []).append(
                    (float(np.median(r)), float(np.mean(r)), float(r.max())))
            if not do_sizing:
                return
            X = pre[:, sel].transpose(1, 2, 0)                   # (nT,K,126)
            Xc = X - X.mean(axis=2, keepdims=True)
            cov = np.einsum("bkt,bjt->bkj", Xc, Xc) / (X.shape[2] - 1)
            mu = X.mean(axis=2)
            vol_sel = np.sqrt(np.maximum(np.einsum("bii->bi", cov), 1e-12))
            k_ = kmask.sum(axis=1)
            w10 = np.where((k_ >= 10)[:, None],
                           S.cap_project(w_tour, kmask, 0.10),
                           S.equal_weights(kmask))
            diag["cap_infeasible_S2"] += int((k_ < 10).sum())
            w5 = np.where((k_ >= 20)[:, None],
                          S.cap_project(w_tour, kmask, 0.05),
                          S.equal_weights(kmask))
            diag["cap_infeasible_S3"] += int((k_ < 20).sum())
            wsz = {
                "S1_cap20_tournament": w_tour,
                "S2_cap10": w10,
                "S3_cap5": w5,
                "S4_inverse_vol": S.inverse_vol_weights(vol_sel, kmask,
                                                        CAP_TOURNAMENT),
                "S5_risk_parity_erc": S.erc_weights(cov, kmask, CAP_TOURNAMENT),
                "S6_half_kelly": S.half_kelly_weights(cov, mu, kmask,
                                                      CAP_TOURNAMENT),
            }
            for sname, ww in wsz.items():
                p, turn = S.simulate(Rsel, ww, kmask, rebal, rf_win,
                                     COST_DECIDES)
                r, dd, vol = S.path_stats(p)
                rec.put(f"{key}~{sname}", wi, r)
                rec.put(f"{key}~{sname}|dd", wi, dd)
                rec.put(f"{key}~{sname}|vol", wi, vol)

        # ── the five families + their matched controls ──────────────────
        for fam in FAMILIES:
            if fam == "F4_sector_concentrated":
                if len(sector_ok) < 3:
                    rec.skip(fam)
                    diag["arms_skipped"][fam] = diag["arms_skipped"].get(fam, 0) + 1
                    continue
                pick = rng.choice(sector_ok, size=nT)
                bstart_s, bcount_s, bflat_s = S.flat_buckets(
                    [sector_pools[k] if len(sector_pools[k]) else np.array([0])
                     for k in range(12)])
                pos = S.draw_names(rng, np.repeat(pick[:, None], K_MAX, 1),
                                   bstart_s, bcount_s, kmask)
                sel = bflat_s[pos]
                diag["pool_sizes"].setdefault(fam, []).append(
                    float(np.mean([len(sector_pools[k]) for k in sector_ok])))
            else:
                pool = pools[fam]
                if len(pool) < K_MAX:
                    rec.skip(fam)
                    diag["arms_skipped"][fam] = diag["arms_skipped"].get(fam, 0) + 1
                    continue
                bstart_p, bcount_p, bflat_p = S.flat_buckets([pool])
                pos = S.draw_names(rng, np.zeros((nT, K_MAX), dtype=int),
                                   bstart_p, bcount_p, kmask)
                sel = bflat_p[pos]
                diag["pool_sizes"].setdefault(fam, []).append(float(len(pool)))

            run_arm(fam, sel, do_sizing=True)

            # C3: same k / weights / rebalance, names redrawn to reproduce
            # THIS family's own realised volatility-bucket histogram.
            fam_buckets = vbucket[sel][kmask]
            hist = np.bincount(fam_buckets, minlength=VOL_BUCKETS).astype(float)
            hist = np.where(nonempty, hist, 0.0)
            p_b = hist / max(hist.sum(), 1.0)
            if p_b.sum() <= 0:
                rec.skip(f"C3_volmatched~{fam}")
                continue
            p_b = p_b / p_b.sum()
            bk = rng.choice(VOL_BUCKETS, size=(nT, K_MAX), p=p_b)
            pos3 = S.draw_names(rng, bk, bstart_v, bcount_v, kmask)
            sel3 = bflat_v[pos3]
            c3_buckets = vbucket[sel3][kmask]
            h1 = np.bincount(fam_buckets, minlength=VOL_BUCKETS) / len(fam_buckets)
            h2 = np.bincount(c3_buckets, minlength=VOL_BUCKETS) / len(c3_buckets)
            diag["vol_match_gap"].append(float(np.abs(h1 - h2).mean()))
            run_arm(f"C3_volmatched~{fam}", sel3, do_sizing=True)

        # ── F4 biotech sub-arm (Drexel 2025), reported separately ───────
        if len(bio_pool) >= K_MAX:
            bstart_b, bcount_b, bflat_b = S.flat_buckets([bio_pool])
            posb = S.draw_names(rng, np.zeros((nT, K_MAX), dtype=int),
                                bstart_b, bcount_b, kmask)
            run_arm("F4b_biotech_only", bflat_b[posb], do_sizing=False)
        else:
            rec.skip("F4b_biotech_only")

        # ── C4: random at market volatility ─────────────────────────────
        bstart_u, bcount_u, bflat_u = S.flat_buckets([np.arange(nU)])
        posu = S.draw_names(rng, np.zeros((nT, K_MAX), dtype=int),
                            bstart_u, bcount_u, kmask)
        run_arm("C4_random_market_vol", bflat_u[posu], do_sizing=False)

        window_meta.append({
            "i": wi, "t0": str(dates[t0]), "start": str(dates[s0]),
            "end": str(dates[s0 + WINDOW - 1]), "universe": int(nU)})
        if wi % 10 == 0:
            print(f"  window {wi+1}/{nW} {dates[s0]}..{dates[s0+WINDOW-1]} "
                  f"U={nU} ({time.time()-t_start:.0f}s)", flush=True)

    print(f"simulation done in {time.time()-t_start:.0f}s", flush=True)
    base_keys = [k for k in rec.mats if "|" not in k and "~S" not in k]
    np.savez_compressed(FAC / "wg1_arm_matrices.npz",
                        **{k.replace("~", "__"): rec.mats[k] for k in base_keys})
    out = aggregate(rec, det, diag, window_meta, cost_summary, starts, dates,
                    nW, nT)
    out["runtime_seconds"] = round(time.time() - t_start, 1)
    path = FAC / a.out
    path.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nreceipt -> {path}", flush=True)
    print(json.dumps(out["headline"], indent=1, default=float))
    return 0


# ── aggregation, MDEs, verdicts ─────────────────────────────────────────
def aggregate(rec, det, diag, window_meta, cost_summary, starts, dates, nW, nT):
    wstart = np.array([dates[s] for s in starts])
    years = np.array([int(str(d)[:4]) for d in wstart])
    first_half = wstart < HALF_SPLIT

    def med_by_window(key):
        m = rec.mats.get(key)
        return np.full(nW, np.nan) if m is None else np.nanmedian(m, axis=1)

    def q_by_window(key, q):
        m = rec.mats.get(key)
        return (np.full(nW, np.nan) if m is None
                else np.nanpercentile(m, q, axis=1))

    def max_by_window(key):
        m = rec.mats.get(key)
        if m is None:
            return np.full(nW, np.nan)
        with np.errstate(all="ignore"):
            return np.where(np.isfinite(m).any(axis=1),
                            np.nanmax(np.where(np.isfinite(m), m, -np.inf),
                                      axis=1), np.nan)

    def min_by_window(key):
        m = rec.mats.get(key)
        if m is None:
            return np.full(nW, np.nan)
        with np.errstate(all="ignore"):
            return np.where(np.isfinite(m).any(axis=1),
                            np.nanmin(np.where(np.isfinite(m), m, np.inf),
                                      axis=1), np.nan)

    fams = {}
    for fam in FAMILIES:
        c3 = f"C3_volmatched~{fam}"
        f_med, c_med = med_by_window(fam), med_by_window(c3)
        d_med = f_med - c_med
        st = paired_stat(d_med)
        d_p95 = q_by_window(fam, 95) - q_by_window(c3, 95)
        st95 = paired_stat(d_p95)
        d_p5 = q_by_window(fam, 5) - q_by_window(c3, 5)
        st5 = paired_stat(d_p5)
        d_c4 = f_med - med_by_window("C4_random_market_vol")
        st_c4 = paired_stat(d_c4)

        blocks = {}
        for name, y0, y1 in REGIMES:
            sel = (years >= y0) & (years <= y1)
            v = d_med[sel]
            v = v[np.isfinite(v)]
            blocks[name] = {"n": int(len(v)),
                            "mean_delta_pp": float(100 * v.mean()) if len(v) else None}
        pos_blocks = sum(1 for b in blocks.values()
                         if b["mean_delta_pp"] is not None
                         and np.sign(b["mean_delta_pp"]) == np.sign(st["mean"]))
        h1 = paired_stat(d_med[first_half])
        h2 = paired_stat(d_med[~first_half])
        halves_agree = (np.isfinite(h1["mean"]) and np.isfinite(h2["mean"])
                        and np.sign(h1["mean"]) == np.sign(h2["mean"])
                        == np.sign(st["mean"]))

        if st["detectable"] and st["mean"] > 0 and pos_blocks >= 5 and halves_agree:
            verdict = "SELECTION_DETECTED"
        elif st["detectable"] and st["mean"] > 0:
            verdict = "UNRESOLVED_UNSTABLE"
        elif st["detectable"] and st["mean"] < 0:
            verdict = "SELECTION_HARMFUL"
        elif st95["detectable"] and st95["mean"] > 0:
            verdict = "DISPERSION_ONLY"
        else:
            verdict = "UNRESOLVED"

        allr = rec.mats.get(fam)
        c3r = rec.mats.get(c3)
        fmax, cmax = max_by_window(fam), max_by_window(c3)
        fmin = min_by_window(fam)
        st_max = paired_stat(fmax - cmax)
        fams[fam] = {
            "verdict": verdict,
            "delta_median_pp": 100 * st["mean"],
            "delta_median_mde_pp": 100 * st["mde_80pct_power"],
            "delta_median_t": st["t"],
            "delta_median_n_windows": st["n_windows"],
            "delta_p95_pp": 100 * st95["mean"],
            "delta_p95_mde_pp": 100 * st95["mde_80pct_power"],
            "delta_p5_pp": 100 * st5["mean"],
            "delta_p5_mde_pp": 100 * st5["mde_80pct_power"],
            "delta_median_vs_C4_pp": 100 * st_c4["mean"],
            "delta_median_vs_C4_mde_pp": 100 * st_c4["mde_80pct_power"],
            "regime_blocks": blocks,
            "regime_blocks_same_sign": pos_blocks,
            "half1_delta_pp": 100 * h1["mean"], "half2_delta_pp": 100 * h2["mean"],
            "halves_agree": bool(halves_agree),
            "dist": _pct(summarise(allr[np.isfinite(allr)])) if allr is not None else {},
            "dist_c3": _pct(summarise(c3r[np.isfinite(c3r)])) if c3r is not None else {},
            "max_over_teams_pct": 100 * float(np.nanmax(allr)) if allr is not None else None,
            "max_over_teams_pct_c3": 100 * float(np.nanmax(c3r)) if c3r is not None else None,
            "p5_pct": 100 * float(np.nanpercentile(allr, 5)) if allr is not None else None,
            "worst_team_pct": 100 * float(np.nanmin(allr)) if allr is not None else None,
            "leaderboard_max_over_2600_per_window": {
                "mean_pct": 100 * float(np.nanmean(fmax)),
                "median_pct": 100 * float(np.nanmedian(fmax)),
                "p90_pct": 100 * float(np.nanpercentile(fmax[np.isfinite(fmax)], 90)),
                "best_window_pct": 100 * float(np.nanmax(fmax)),
                "worst_team_in_that_window_pct":
                    100 * float(fmin[int(np.nanargmax(fmax))]),
                "best_window_dates": window_meta[int(np.nanargmax(fmax))]
                if int(np.nanargmax(fmax)) < len(window_meta) else None,
            },
            "leaderboard_max_c3_median_pct": 100 * float(np.nanmedian(cmax)),
            "delta_max_pp": 100 * st_max["mean"],
            "delta_max_mde_pp": 100 * st_max["mde_80pct_power"],
            "delta_max_t": st_max["t"],
            "delta_max_detectable": st_max["detectable"],
            "mean_realised_ann_vol": float(np.nanmean(rec.mats.get(fam + "|vol", np.array([np.nan])))),
            "mean_realised_ann_vol_c3": float(np.nanmean(rec.mats.get(c3 + "|vol", np.array([np.nan])))),
        }

    # ── P(arm produces the field winner) ────────────────────────────────
    groups = FAMILIES + ["C3_volmatched_pooled", "C4_random_market_vol"]
    per_group = 2600 // len(groups)
    rng = np.random.default_rng(SEED_BASE + 777)
    wins = {g: 0 for g in groups}
    wins["C1_equal_weight_universe"] = 0
    wins["C2_largecap_top100"] = 0
    trials = 0
    c3_stack = [rec.mats.get(f"C3_volmatched~{f}") for f in FAMILIES]
    for wi in range(nW):
        pools_w = {}
        for g in FAMILIES + ["C4_random_market_vol"]:
            m = rec.mats.get(g)
            if m is None:
                continue
            v = m[wi][np.isfinite(m[wi])]
            if len(v):
                pools_w[g] = v
        c3v = np.concatenate([m[wi][np.isfinite(m[wi])] for m in c3_stack
                              if m is not None and np.isfinite(m[wi]).any()]) \
            if any(m is not None for m in c3_stack) else np.zeros(0)
        if len(c3v):
            pools_w["C3_volmatched_pooled"] = c3v
        if len(pools_w) < 4:
            continue
        dets = {k: det[k][wi] for k in
                ("C1_equal_weight_universe", "C2_largecap_top100")
                if np.isfinite(det[k][wi])}
        for _ in range(200):
            best, who = -np.inf, None
            for g, v in pools_w.items():
                x = v[rng.integers(0, len(v), per_group)].max()
                if x > best:
                    best, who = x, g
            for g, x in dets.items():
                if x > best:
                    best, who = x, g
            wins[who] += 1
            trials += 1
    p_win = {g: (wins[g] / trials if trials else float("nan")) for g in wins}
    field_max = np.full(nW, np.nan)
    field_min = np.full(nW, np.nan)
    all_arm_keys = FAMILIES + ["C4_random_market_vol"] +         [f"C3_volmatched~{f}" for f in FAMILIES]
    for wi in range(nW):
        vs = [rec.mats[k][wi][np.isfinite(rec.mats[k][wi])]
              for k in all_arm_keys if k in rec.mats
              and np.isfinite(rec.mats[k][wi]).any()]
        if vs:
            cat = np.concatenate(vs)
            field_max[wi], field_min[wi] = float(cat.max()), float(cat.min())
    for fam in FAMILIES:
        fams[fam]["p_produces_winner"] = p_win.get(fam, 0.0)

    # ── selection vs sizing ─────────────────────────────────────────────
    sizing = {}
    for base in FAMILIES + [f"C3_volmatched~{f}" for f in FAMILIES]:
        for sname in SIZINGS:
            key = f"{base}~{sname}"
            m = rec.mats.get(key)
            if m is None:
                continue
            dd = rec.mats.get(key + "|dd")
            vol = rec.mats.get(key + "|vol")
            careers = np.nancumprod(np.where(np.isfinite(m), 1.0 + m, 1.0),
                                    axis=0)
            terminal = careers[-1]
            peak = np.maximum.accumulate(careers, axis=0)
            career_dd = (careers / peak - 1.0).min(axis=0)
            ruin = float((careers.min(axis=0) < RUIN_LEVEL).mean())
            nwin = int(np.isfinite(m).any(axis=1).sum())
            yrs = nwin * WINDOW / 252.0
            cagr = np.sign(terminal) * (np.abs(terminal) ** (1.0 / max(yrs, 1e-9))) - 1.0
            r_flat = m[np.isfinite(m)]
            sizing[key] = {
                "median_window_return_pct": 100 * float(np.median(r_flat)),
                "mean_window_return_pct": 100 * float(r_flat.mean()),
                "career_terminal_median": float(np.median(terminal)),
                "career_cagr_median_pct": 100 * float(np.median(cagr)),
                "career_maxdd_median_pct": 100 * float(np.median(career_dd)),
                "career_maxdd_p95_worst_pct": 100 * float(np.percentile(career_dd, 5)),
                "within_window_maxdd_mean_pct":
                    100 * float(np.nanmean(dd)) if dd is not None else None,
                "realised_ann_vol_mean_pct":
                    100 * float(np.nanmean(vol)) if vol is not None else None,
                "return_per_unit_vol":
                    float(np.nanmean(r_flat) * (252.0 / WINDOW) /
                          max(float(np.nanmean(vol)), 1e-9))
                    if vol is not None else None,
                "ruin_probability": ruin,
                "years_of_career": round(yrs, 1),
            }
    # paired family-minus-control at each sizing rule
    sizing_paired = {}
    for fam in FAMILIES:
        for sname in SIZINGS:
            a_, b_ = rec.mats.get(f"{fam}~{sname}"), \
                rec.mats.get(f"C3_volmatched~{fam}~{sname}")
            if a_ is None or b_ is None:
                continue
            d = np.nanmedian(a_, axis=1) - np.nanmedian(b_, axis=1)
            st = paired_stat(d)
            sizing_paired[f"{fam}~{sname}"] = {
                "delta_median_pp": 100 * st["mean"],
                "mde_pp": 100 * st["mde_80pct_power"],
                "t": st["t"], "detectable": st["detectable"]}

    # ── controls, diagnostics, denominators ─────────────────────────────
    ctrl = {k: {"mean_window_return_pct": 100 * float(np.nanmean(v)),
                "median_window_return_pct": 100 * float(np.nanmedian(v)),
                "sd_pct": 100 * float(np.nanstd(v))}
            for k, v in det.items()}
    for k in ("C4_random_market_vol",):
        m = rec.mats.get(k)
        if m is not None:
            ctrl[k] = _pct(summarise(m[np.isfinite(m)]))

    assertions = {
        "delist_terminations": diag["delist_terminations"],
        "delist_path_fired": diag["delist_terminations"] > 0,
        "silent_terminations": diag["silent_terminations"],
        "vol_match_mean_abs_gap_pp":
            100 * float(np.mean(diag["vol_match_gap"])) if diag["vol_match_gap"] else None,
        "vol_match_within_2pp":
            bool(np.mean(diag["vol_match_gap"]) * 100 <= 2.0) if diag["vol_match_gap"] else False,
        "cap_violations": diag["cap_violations"],
        "cap_legal": diag["cap_violations"] == 0,
        "f3_compustat_coverage_mean":
            float(np.mean(diag["f3_coverage"])) if diag["f3_coverage"] else None,
        "f3_compustat_coverage_median":
            float(np.median(diag["f3_coverage"])) if diag["f3_coverage"] else None,
        "f3_compustat_coverage_last20_mean":
            float(np.mean(diag["f3_coverage"][-20:])) if diag["f3_coverage"] else None,
        "f3_windows_below_40pct_coverage":
            int(sum(1 for c in diag["f3_coverage"] if c < 0.40)),
        "arms_skipped": diag["arms_skipped"],
    }

    field = {
        "note": ("max over the pooled simulated field in each window — the "
                 "order statistic a leaderboard reports, and its same-window "
                 "cousin that nobody interviewed"),
        "winner_mean_pct": 100 * float(np.nanmean(field_max)),
        "winner_median_pct": 100 * float(np.nanmedian(field_max)),
        "winner_p90_pct": 100 * float(np.nanpercentile(
            field_max[np.isfinite(field_max)], 90)),
        "winner_best_window_pct": 100 * float(np.nanmax(field_max)),
        "loser_median_pct": 100 * float(np.nanmedian(field_min)),
        "loser_worst_window_pct": 100 * float(np.nanmin(field_min)),
        "field_size_per_window": int(len(all_arm_keys)) * nT,
    }

    verdicts = {f: fams[f]["verdict"] for f in FAMILIES}
    if "SELECTION_DETECTED" in verdicts.values():
        trial_verdict = "MIXED — at least one family clears its own MDE on the median"
    elif "DISPERSION_ONLY" in verdicts.values():
        trial_verdict = "DISPERSION_ONLY (no family shifts the median above its MDE)"
    else:
        trial_verdict = "UNRESOLVED (no family detectable on median or p95)"

    search_keys = sorted(rec.mats.keys())
    n_configs = len([k for k in search_keys if "|" not in k])

    return {
        "trial": "WINNER-GENOME-1",
        "prereg": "TRIALS/PREREG_WINNER_GENOME_1.md @ 4aa03aa",
        "trial_verdict": trial_verdict,
        "headline": {f: {"verdict": fams[f]["verdict"],
                         "delta_median_pp": round(fams[f]["delta_median_pp"], 3),
                         "mde_pp": round(fams[f]["delta_median_mde_pp"], 3),
                         "max_over_2600_pct": round(fams[f]["max_over_teams_pct"], 1)
                         if fams[f]["max_over_teams_pct"] is not None else None,
                         "p5_pct": round(fams[f]["p5_pct"], 1)
                         if fams[f]["p5_pct"] is not None else None,
                         "p_win": round(fams[f]["p_produces_winner"], 3)}
                     for f in FAMILIES},
        "families": fams,
        "controls": ctrl,
        "p_produces_winner": p_win,
        "field_order_statistics": field,
        "sizing": sizing,
        "sizing_paired_vs_control": sizing_paired,
        "assertions": assertions,
        "n_windows": nW,
        "n_teams": nT,
        "universe_median_size": float(np.median(diag["universe_size"]))
        if diag["universe_size"] else None,
        "pool_sizes_mean": {k: float(np.mean(v))
                            for k, v in diag["pool_sizes"].items()},
        "search_denominator": n_configs,
        "search_denominator_failed": int(sum(diag["arms_skipped"].values())),
        "cost_sensitivity": {k: {"median_pct": 100 * float(np.mean([x[0] for x in v])),
                                 "mean_pct": 100 * float(np.mean([x[1] for x in v])),
                                 "max_pct": 100 * float(np.max([x[2] for x in v]))}
                             for k, v in cost_summary.items()},
        "windows": window_meta[:5] + window_meta[-5:],
        "ruin_definition": ("career NAV < 0.50 of its start at any window-end "
                            "mark, where a career plays the same arm and sizing "
                            "rule in every consecutive window with an "
                            "independent team draw each time"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
