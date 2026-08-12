"""EXIT-LAB-1 — the counterfactual decision factory.

    python -m scripts.run_exit_lab_1 --stage factory     # generate the rows
    python -m scripts.run_exit_lab_1 --stage perturb     # no-lookahead proof
    python -m scripts.run_exit_lab_1 --stage all

Pre-registered in `TRIALS/PREREG_EXIT_LAB_1.md` (`lint_prereg` PASS) BEFORE a
single row existed. Read `scripts/exit_lab_core.py` for the accounting
convention and the action space; this file is the driver and the checkpointer.

Checkpointing is per YEAR: `data/factory/exit_lab_1_states_YYYY.parquet` and
`..._outcomes_YYYY.parquet`. A crash at hour four resumes at the first year
whose pair of files is missing.
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
from scripts.exit_lab_core import (
    A, ACTIONS, COHORTS, EXTRA_BPS, FEATURE_COLS, HORIZONS, REPLACE_ARMS,
    TGT_CLIP, apply_actions, build_position_factors, cohort_stats, cum_series,
    eligible_at, hret, hscalar, trailing_stats,
)

FACT = MODULE_ROOT / "data" / "factory"
PANEL = FACT / "wg1_panel.npz"
AUX = FACT / "exit_lab_1_aux.npz"
SEED = 20260812


# ──────────────────────────────────────────────────────────────────────────
class Lab:
    def __init__(self, corrupt_after: int | None = None, quiet: bool = False):
        t0 = time.time()
        z = np.load(PANEL, allow_pickle=False)
        self.dates = z["dates"].astype("datetime64[ns]")
        self.permnos = z["permnos"].astype(np.int64)
        RET = z["RET"]
        self.PRC = z["PRC"]
        self.DOLVOL = z["DOLVOL"]
        self.MCAP = z["MCAP"]
        first_obs = z["first_obs"].astype(np.int64)
        last_obs = z["last_obs"].astype(np.int64)
        delist_day = z["delist_day"].astype(np.int64)
        del z

        ff = pd.read_parquet(MODULE_ROOT / "data" / "wrds_raw"
                             / "ff_factors_daily.parquet",
                             columns=["date", "mktrf", "rf"])
        ff = ff.set_index("date").reindex(pd.DatetimeIndex(self.dates))
        rf = ff["rf"].astype("float64").fillna(0.0).to_numpy()
        mkt = (ff["mktrf"].astype("float64").fillna(0.0).to_numpy() + rf)
        if ff["mktrf"].isna().mean() > 0.02:
            raise SystemExit("FF daily market series does not cover the panel")

        # ── the no-lookahead perturbation: garbage every cell after T0 ─────
        if corrupt_after is not None:
            rng = np.random.default_rng(999)
            k = corrupt_after + 1
            RET = RET.copy()
            RET[k:] = rng.normal(0.5, 1.0, RET[k:].shape).astype(np.float32)
            self.PRC = self.PRC.copy(); self.PRC[k:] = 1e6
            self.DOLVOL = self.DOLVOL.copy(); self.DOLVOL[k:] = 1e15
            self.MCAP = self.MCAP.copy(); self.MCAP[k:] = 1e15
            rf = rf.copy(); rf[k:] = 0.5
            mkt = mkt.copy(); mkt[k:] = 0.5

        self.LC, self.term, self.pdiag = build_position_factors(
            RET, first_obs, last_obs, delist_day, rf)
        del RET
        self.first_obs = first_obs
        self.RFC = cum_series(rf)
        self.MKC = cum_series(mkt)
        self.mkt_log = self.MKC

        a = np.load(AUX, allow_pickle=False)
        self.dec_ix = a["dec_ix"].astype(np.int64)
        self.dec_dates = pd.DatetimeIndex(a["dec_dates"].astype("datetime64[ns]"))
        self.HS, self.REV, self.NEST = a["HS"], a["REV"], a["NEST"]
        self.SUE, self.AGE, self.TGT, self.FF12 = (a["SUE"], a["AGE"],
                                                   a["TGT"], a["FF12"])
        del a
        if not quiet:
            print(f"panel loaded in {time.time()-t0:.0f}s  "
                  f"{self.LC.shape[0]} dates x {self.LC.shape[1]} names  "
                  f"{len(self.dec_ix)} decision dates", flush=True)
        self.counts = {"terminated_in_horizon": {str(h): 0 for h in HORIZONS},
                       "eligible_names": 0, "dates_skipped_thin": 0,
                       "basket_substitution_events": 0,
                       "candidate_pool_short": 0, "tgt_upside_clipped": 0,
                       "hs_imputed_p90": 0, "hs_cells": 0,
                       "feature_nonnull": {c: 0 for c in FEATURE_COLS}}

    # ── the candidate baskets ────────────────────────────────────────────
    def _basket(self, ranked, start, size):
        """Members and the substitute rank for one replacement arm.

        A held name may itself sit inside the basket it would be replaced by;
        substituting the next unused rank is the only PIT-honest fix (dropping
        it would shrink the basket for exactly the best-ranked holders).
        """
        if len(ranked) < start + size + 1:
            self.counts["candidate_pool_short"] += 1
            return None
        return {"members": ranked[start:start + size], "sub": ranked[start + size]}

    def _basket_outcomes(self, b, idx, t, h, k):
        """(ret, cost) per state for one basket arm at one horizon."""
        n = len(idx)
        if b is None:
            return (np.full(n, np.nan), np.full(n, np.nan))
        m, sub = b["members"], b["sub"]
        r_m = hret(self.LC, t, h, m)
        c_m = self.HS[k, m].astype(np.float64) + EXTRA_BPS
        r_sub = float(hret(self.LC, t, h, np.array([sub]))[0])
        c_sub = float(self.HS[k, sub]) + EXTRA_BPS
        size = len(m)
        base_r = np.nanmean(r_m)
        base_c = np.nanmean(c_m) / 1e4
        ret = np.full(n, base_r)
        cost = np.full(n, base_c)
        pos = {int(p): q for q, p in enumerate(idx)}
        for q, p in enumerate(m):
            s = pos.get(int(p))
            if s is None:
                continue
            self.counts["basket_substitution_events"] += 1
            keep = np.delete(r_m, q)
            ret[s] = np.nanmean(np.append(keep, r_sub))
            keepc = np.delete(c_m, q)
            cost[s] = np.nanmean(np.append(keepc, c_sub)) / 1e4
        return ret, cost

    # ── one decision date ────────────────────────────────────────────────
    def date_states(self, k: int, rng: np.random.Generator):
        t = int(self.dec_ix[k])
        idx = eligible_at(t, self.PRC, self.DOLVOL, self.first_obs, self.term)
        if len(idx) < 100:
            self.counts["dates_skipped_thin"] += 1
            return None
        n = len(idx)
        ts = trailing_stats(self.LC, t, idx, self.mkt_log)
        lc_t = self.LC[t, idx].astype(np.float64)
        mom_12_1 = np.expm1(self.LC[t - 21, idx].astype(np.float64)
                            - self.LC[t - 252, idx].astype(np.float64))
        mom_63 = np.expm1(lc_t - self.LC[t - 63, idx].astype(np.float64))
        mom_21 = np.expm1(lc_t - self.LC[t - 21, idx].astype(np.float64))
        hi252 = np.nanmax(self.LC[t - 252:t + 1, idx].astype(np.float64), axis=0)
        dist_hi = np.expm1(lc_t - hi252)

        mk = np.expm1(self.MKC[t] - self.MKC[t - 63])
        mk_vol = float(np.std(np.diff(self.MKC[t - 63:t + 1])) * np.sqrt(252.0))
        mk_dd = float(np.expm1(self.MKC[t] - np.max(self.MKC[t - 252:t + 1])))

        px = self.PRC[t, idx].astype(np.float64)
        mcap = self.MCAP[t, idx].astype(np.float64)
        dv = np.nanmedian(self.DOLVOL[t - 62:t + 1, idx], axis=0)
        hs = self.HS[k, idx].astype(np.float64)
        # a name with no CS estimate is charged the cross-sectional 90th
        # percentile of that day, never zero: an unpriceable spread is an
        # EXPENSIVE spread, and a silent 0 would make trading look free
        hs_fill = np.nanpercentile(hs, 90) if np.isfinite(hs).any() else 50.0
        self.counts["hs_imputed_p90"] += int((~np.isfinite(hs)).sum())
        self.counts["hs_cells"] += n
        hs = np.where(np.isfinite(hs), hs, hs_fill)
        tgt = self.TGT[k, idx].astype(np.float64)
        self.counts["tgt_upside_clipped"] += int(
            np.nansum((tgt < TGT_CLIP[0]) | (tgt > TGT_CLIP[1])))
        tgt = np.clip(tgt, *TGT_CLIP)

        base = {
            "price": px, "log_mcap": np.log(np.where(mcap > 0, mcap, np.nan)),
            "log_dv": np.log(np.where(dv > 0, dv, np.nan)),
            "turnover": dv / np.where(mcap > 0, mcap, np.nan),
            "hs_bps": hs,
            "vol_63": ts["vol_63"], "vol_252": ts["vol_252"],
            "beta_252": ts["beta_252"], "ivol_252": ts["ivol_252"],
            "mom_12_1": mom_12_1, "mom_63": mom_63, "mom_21": mom_21,
            "dist_252high": dist_hi,
            "mkt_ret_63": np.full(n, mk), "mkt_vol_63": np.full(n, mk_vol),
            "mkt_dd_252": np.full(n, mk_dd),
            "rev_score": self.REV[k, idx].astype(np.float64),
            "numest": self.NEST[k, idx].astype(np.float64),
            "sue": self.SUE[k, idx].astype(np.float64),
            "days_since_rdq": self.AGE[k, idx].astype(np.float64),
            "tgt_upside": tgt,
            "ff12": self.FF12[k, idx].astype(np.float64),
        }

        # ── candidate rankings, PIT and unfitted ──────────────────────────
        def rank_desc(v):
            o = np.argsort(np.where(np.isfinite(v), -v, np.inf), kind="mergesort")
            return idx[o]
        ranked = {"mom": rank_desc(mom_12_1), "rev": rank_desc(base["rev_score"]),
                  "rnd": rng.permutation(idx)}
        baskets = {name: self._basket(ranked[src], start, size)
                   for name, (src, start, size) in REPLACE_ARMS.items()}

        cost_i = (hs + EXTRA_BPS) / 1e4
        with np.errstate(divide="ignore", invalid="ignore"):
            f_beta = np.clip(1.0 / ts["beta_252"], 0.0, 1.0)
        f_beta = np.where(np.isfinite(f_beta), f_beta, 1.0)

        # ── outcomes, per horizon ─────────────────────────────────────────
        out = np.full((n, len(ACTIONS), len(HORIZONS)), np.nan, dtype=np.float32)
        for hi, h in enumerate(HORIZONS):
            if t + h >= self.LC.shape[0]:
                continue
            R_i = hret(self.LC, t, h, idx)
            R_cash = hscalar(self.RFC, t, h)
            R_bm = hscalar(self.MKC, t, h)
            R_c, C_c = {}, {}
            for name, b in baskets.items():
                r, c = self._basket_outcomes(b, idx, t, h, k)
                R_c[name], C_c[name] = r, c
            out[:, :, hi] = apply_actions(R_i, R_cash, R_bm, R_c, cost_i, C_c,
                                          f_beta).astype(np.float32)
            self.counts["terminated_in_horizon"][str(h)] += int(
                ((self.term[idx] >= t) & (self.term[idx] < t + h)).sum())

        # ── cohort-conditioned state features ─────────────────────────────
        frames = []
        for E in COHORTS:
            cs = cohort_stats(self.LC, t, idx, E)
            d = {"date_ix": np.full(n, k, dtype=np.int32),
                 "permno": self.permnos[idx].astype(np.int32),
                 "cohort": np.full(n, E, dtype=np.int16)}
            for c in FEATURE_COLS:
                if c in base:
                    d[c] = base[c].astype(np.float32)
                elif c in cs:
                    d[c] = cs[c].astype(np.float32)
                elif c == "cohort_days":
                    d[c] = np.full(n, float(E), dtype=np.float32)
            frames.append(pd.DataFrame(d))
        states = pd.concat(frames, ignore_index=True)
        self.counts["eligible_names"] += n
        for c in FEATURE_COLS:
            self.counts["feature_nonnull"][c] += int(
                np.isfinite(states[c].to_numpy()).sum())
        return states, out, n


def run_factory(resume: bool = True) -> dict:
    lab = Lab()
    years = sorted({int(d.year) for d in lab.dec_dates})
    sid0 = 0
    t_start = time.time()
    written = {"states": 0, "outcome_rows": 0, "years": []}
    # sid must be globally stable across a resume, so it is derived from the
    # year's position in the calendar, not from a running counter
    per_year_k = {y: [k for k, d in enumerate(lab.dec_dates) if d.year == y]
                  for y in years}
    for y in years:
        sf = FACT / f"exit_lab_1_states_{y}.parquet"
        of = FACT / f"exit_lab_1_outcomes_{y}.parquet"
        ks = per_year_k[y]
        if resume and sf.exists() and of.exists():
            n = pd.read_parquet(sf, columns=["permno"]).shape[0]
            sid0 += n
            written["states"] += n
            written["outcome_rows"] += n * len(ACTIONS)
            print(f"  {y}: resume, {n:,} states already on disk", flush=True)
            continue
        rng = np.random.default_rng(SEED + y)
        S, O = [], []
        for k in ks:
            r = lab.date_states(k, rng)
            if r is None:
                continue
            st, out, n = r
            S.append(st)
            # the outcome block is per (date, name); the four cohorts share it
            O.append(np.tile(out, (len(COHORTS), 1, 1)))
        if not S:
            continue
        st = pd.concat(S, ignore_index=True)
        out = np.concatenate(O, axis=0)
        assert len(st) == out.shape[0], "state/outcome row misalignment"
        st.insert(0, "sid", np.arange(sid0, sid0 + len(st), dtype=np.int64))
        st.to_parquet(sf, index=False, compression="zstd")

        nrow = out.shape[0]
        long = {
            "sid": np.repeat(st["sid"].to_numpy(), len(ACTIONS)),
            "action": np.tile(np.arange(len(ACTIONS), dtype=np.int8), nrow),
        }
        flat = out.reshape(nrow * len(ACTIONS), len(HORIZONS))
        for hi, h in enumerate(HORIZONS):
            long[f"r{h}"] = flat[:, hi]
        pd.DataFrame(long).to_parquet(of, index=False, compression="zstd")

        sid0 += len(st)
        written["states"] += len(st)
        written["outcome_rows"] += nrow * len(ACTIONS)
        written["years"].append(y)
        print(f"  {y}: {len(st):,} states  {nrow*len(ACTIONS):,} state-action "
              f"rows  ({written['states']:,} cum)  "
              f"{time.time()-t_start:.0f}s", flush=True)

    written["state_action_horizon_cells"] = (written["outcome_rows"]
                                             * len(HORIZONS))
    written["counts"] = lab.counts
    written["panel_diag"] = lab.pdiag
    written["seconds"] = round(time.time() - t_start, 1)
    (FACT / "exit_lab_1_factory.json").write_text(json.dumps(written, indent=2))
    print(json.dumps({k: v for k, v in written.items() if k != "years"},
                     indent=2))
    return written


def perturbation_proof() -> dict:
    """Corrupt every cell after T0; the state table must come back identical."""
    lab = Lab(quiet=True)
    k = len(lab.dec_dates) // 2
    t = int(lab.dec_ix[k])
    clean, _, _ = lab.date_states(k, np.random.default_rng(1))
    del lab
    lab2 = Lab(corrupt_after=t, quiet=True)
    dirty, _, _ = lab2.date_states(k, np.random.default_rng(1))
    cols = [c for c in clean.columns]
    same = True
    bad = []
    for c in cols:
        a, b = clean[c].to_numpy(), dirty[c].to_numpy()
        eq = np.array_equal(a, b, equal_nan=True) if a.dtype.kind == "f" \
            else np.array_equal(a, b)
        if not eq:
            same = False
            bad.append(c)
    res = {"decision_date": str(lab2.dec_dates[k].date()),
           "n_states": int(len(clean)), "columns_checked": len(cols),
           "mismatched_columns": bad,
           "perturbation_proof": "PASS" if same else "FAIL"}
    (FACT / "exit_lab_1_perturbation.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["factory", "perturb", "all"])
    ap.add_argument("--no-resume", action="store_true")
    a = ap.parse_args()
    if a.stage in ("perturb", "all"):
        perturbation_proof()
    if a.stage in ("factory", "all"):
        run_factory(resume=not a.no_resume)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
