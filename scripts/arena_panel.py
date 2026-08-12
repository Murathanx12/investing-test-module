"""PORTFOLIO-ARENA-1 / ABLATION-1 — stage 1: the one panel every system shares.

Every one of the fifteen systems in `TRIALS/PREREG_PORTFOLIO_ARENA_1.md` must
see the SAME names, at the SAME dates, with the SAME information and the SAME
cost inputs. If each system built its own universe the arena would be measuring
universes, not systems. So the eligible set, the features, the forward returns
and the half-spread are all built ONCE, here, from the same CRSP spine
`data/factory/wg1_panel.npz` that WINNER-GENOME-1 and EXIT-LAB-1 used, and the
auxiliary cache `exit_lab_1_aux.npz` is REUSED rather than rebuilt — it is
already stamped at exactly these 264 decision dates.

WHAT IS PIT AND WHY
-------------------
Every feature is computed from rows strictly at or before the decision date.
The forward return runs from the decision date to the next one, so it is
disjoint from every feature by construction. `assert_no_lookahead` in the runner
corrupts every cell after a probe date and requires the feature block to come
back bit-identical.

DEATH IS MODELLED, NOT DROPPED
------------------------------
`LC` is the cumulative log value of one dollar in each name, carrying the CRSP
delisting return on the first day after the last quote and then sitting in cash
at `rf`. A name that dies inside a month resolves at its real delisting return.
A universe of "names that were still trading at the end" is a machine for
manufacturing skill.

    python -m scripts.arena_panel
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
from scripts.exit_lab_core import (MIN_HISTORY, MIN_MED_DV, MIN_PRICE, TOP_N,
                                   build_position_factors, cum_series,
                                   eligible_at, hret)

FACTORY = MODULE_ROOT / "data" / "factory"
PANEL = FACTORY / "wg1_panel.npz"
AUX = FACTORY / "exit_lab_1_aux.npz"
RAW = MODULE_ROOT / "data" / "wrds_raw"
OUT = FACTORY / "arena_panel.parquet"
OUT_MKT = FACTORY / "arena_market.parquet"
OUT_META = FACTORY / "arena_panel_meta.json"

#: the ablation's LLM panel — declared in PREREG_ABLATION_1 section 5 before any call
LLM_FIRST_DATE = "2015-01-01"
LLM_N_NAMES = 40
LLM_QUINTILES = 5
LLM_SEED = 20260812
OUT_LLM = FACTORY / "arena_llm_cells.parquet"


def load_ff(dates: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Daily rf and CRSP VW market total return, aligned to the panel's dates."""
    ff = pd.read_parquet(RAW / "ff_factors_daily.parquet",
                         columns=["date", "mktrf", "rf"])
    ff["date"] = pd.to_datetime(ff["date"])
    ff = ff.set_index("date").sort_index()
    ff = ff.reindex(pd.DatetimeIndex(dates))
    rf = pd.to_numeric(ff["rf"], errors="coerce").astype("float64").fillna(0.0)
    mkt = (pd.to_numeric(ff["mktrf"], errors="coerce").astype("float64")
           .fillna(0.0) + rf)
    n_missing = int(pd.isna(ff["mktrf"]).sum())
    if n_missing:
        print(f"  FF: {n_missing} panel dates with no factor row -> 0.0 "
              f"(they are holidays in one calendar and not the other)")
    return rf.to_numpy(), mkt.to_numpy()


def load_tickers(permnos: np.ndarray, dec_dates: pd.DatetimeIndex) -> dict:
    """PIT ticker per (decision date, permno) — the name valid ON that date.

    A ticker is not a permanent property of a security. Showing a language
    model the ticker a company has TODAY for a decision made in 2015 leaks the
    company's later identity, which is exactly the contamination channel the
    swarm's snapshot truncation exists to close.
    """
    sn = pd.read_parquet(RAW / "crsp_stocknames.parquet",
                         columns=["permno", "namedt", "nameenddt", "ticker",
                                  "comnam"])
    sn["permno"] = sn["permno"].astype("int64")
    sn["namedt"] = pd.to_datetime(sn["namedt"])
    sn["nameenddt"] = pd.to_datetime(sn["nameenddt"])
    keep = set(int(p) for p in permnos)
    sn = sn[sn["permno"].isin(keep)]
    out: dict[tuple[int, int], tuple[str, str]] = {}
    for k, t in enumerate(dec_dates):
        v = sn[(sn["namedt"] <= t) & (sn["nameenddt"] >= t)]
        v = v.drop_duplicates("permno", keep="last")
        for p, tk, cn in zip(v["permno"].to_numpy(), v["ticker"].to_numpy(),
                             v["comnam"].to_numpy()):
            if isinstance(tk, str) and tk.strip():
                out[(k, int(p))] = (tk.strip().upper(),
                                    str(cn).strip() if isinstance(cn, str) else "")
    return out


def build() -> dict:
    t0 = time.time()
    z = np.load(PANEL, allow_pickle=False)
    dates = z["dates"].astype("datetime64[ns]")
    permnos = z["permnos"]
    RET, PRC, DOLVOL, MCAP = z["RET"], z["PRC"], z["DOLVOL"], z["MCAP"]
    first_obs, last_obs, delist_day = (z["first_obs"], z["last_obs"],
                                       z["delist_day"])
    print(f"panel {RET.shape} loaded in {time.time()-t0:.0f}s", flush=True)

    rf, mkt = load_ff(dates)
    LC, term, ddiag = build_position_factors(RET, first_obs, last_obs,
                                             delist_day, rf)
    del RET
    mkt_log = cum_series(mkt)
    cash_log = cum_series(rf)
    print(f"LC built in {time.time()-t0:.0f}s  {ddiag}", flush=True)

    aux = np.load(AUX, allow_pickle=False)
    dec_ix = aux["dec_ix"].astype(int)
    dec_dates = pd.DatetimeIndex(aux["dec_dates"].astype("datetime64[ns]"))
    HS, REV, NEST, SUE, AGE, TGT, FF12 = (aux["HS"], aux["REV"], aux["NEST"],
                                          aux["SUE"], aux["AGE"], aux["TGT"],
                                          aux["FF12"])
    nT = len(dec_ix)

    rows: list[pd.DataFrame] = []
    n_states = 0
    for k in range(nT - 1):                    # last date has no forward month
        t = int(dec_ix[k])
        t_next = int(dec_ix[k + 1])
        h = t_next - t
        cols = eligible_at(t, PRC, DOLVOL, first_obs, term)
        if len(cols) == 0:
            continue
        w = LC[t - 252:t + 1, cols].astype(np.float64)
        r = np.diff(w, axis=0)                             # 252 daily log rets
        m = np.diff(mkt_log[t - 252:t + 1])[:, None]
        mv = float(np.nanvar(m))
        with np.errstate(invalid="ignore", divide="ignore"):
            beta = (np.nanmean((r - np.nanmean(r, axis=0)) * (m - np.nanmean(m)),
                               axis=0) / mv if mv > 0
                    else np.full(len(cols), np.nan))
            ivol = np.nanstd(r - beta[None, :] * m, axis=0) * np.sqrt(252.0)
        vol252 = np.nanstd(r, axis=0) * np.sqrt(252.0)
        vol63 = np.nanstd(r[-63:], axis=0) * np.sqrt(252.0)
        rs = np.expm1(r)                                   # simple daily
        sd = np.nanstd(rs, axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            skew252 = np.where(sd > 0,
                               np.nanmean((rs - np.nanmean(rs, axis=0)) ** 3,
                                          axis=0) / np.maximum(sd, 1e-12) ** 3,
                               np.nan)
        # Bali-Cakici-Whitelaw MAX: mean of the five largest daily returns in
        # the last month. The canonical lottery-demand proxy.
        max5 = np.mean(np.sort(rs[-21:], axis=0)[-5:], axis=0)

        lc_t = LC[t, cols].astype(np.float64)
        mom_12_1 = np.expm1(LC[t - 21, cols].astype(np.float64)
                            - LC[t - 252, cols].astype(np.float64))
        mom_63 = np.expm1(lc_t - LC[t - 63, cols].astype(np.float64))
        mom_21 = np.expm1(lc_t - LC[t - 21, cols].astype(np.float64))
        hi252 = np.nanmax(LC[t - 252:t + 1, cols].astype(np.float64), axis=0)
        dist_hi = np.expm1(lc_t - hi252)

        px = PRC[t, cols].astype(np.float64)
        mcap = MCAP[t, cols].astype(np.float64)
        dv = np.nanmedian(DOLVOL[t - 62:t + 1, cols], axis=0).astype(np.float64)

        fwd = hret(LC, t, h, cols)
        adv = dv                                    # 63-day median dollar volume

        rows.append(pd.DataFrame({
            "date_ix": np.int32(k), "col": cols.astype(np.int32),
            "permno": permnos[cols].astype(np.int64),
            "price": px.astype(np.float32),
            "mcap": mcap.astype(np.float64),
            "adv": adv.astype(np.float64),
            "hs_bps": HS[k, cols].astype(np.float32),
            "vol_63": vol63.astype(np.float32),
            "vol_252": vol252.astype(np.float32),
            "beta_252": beta.astype(np.float32),
            "ivol_252": ivol.astype(np.float32),
            "skew_252": skew252.astype(np.float32),
            "max5": max5.astype(np.float32),
            "mom_12_1": mom_12_1.astype(np.float32),
            "mom_63": mom_63.astype(np.float32),
            "mom_21": mom_21.astype(np.float32),
            "dist_252high": dist_hi.astype(np.float32),
            "rev_score": REV[k, cols].astype(np.float32),
            "numest": NEST[k, cols].astype(np.float32),
            "sue": SUE[k, cols].astype(np.float32),
            "days_since_rdq": AGE[k, cols].astype(np.float32),
            "tgt_upside": TGT[k, cols].astype(np.float32),
            "ff12": FF12[k, cols].astype(np.int8),
            "fwd_ret_1m": fwd.astype(np.float32),
            "h_days": np.int16(h),
        }))
        n_states += len(cols)
        if k % 24 == 0:
            print(f"  {dec_dates[k].date()}  {len(cols)} names  "
                  f"({time.time()-t0:.0f}s)", flush=True)

    panel = pd.concat(rows, ignore_index=True)
    del rows

    # ── market-level series at the decision grid ────────────────────────────
    mrows = []
    for k in range(nT - 1):
        t, t_next = int(dec_ix[k]), int(dec_ix[k + 1])
        h = t_next - t
        mrows.append({
            "date_ix": k, "date": dec_dates[k],
            "mkt_fwd_1m": float(np.expm1(mkt_log[t + h] - mkt_log[t])),
            "cash_fwd_1m": float(np.expm1(cash_log[t + h] - cash_log[t])),
            "mkt_vol_252": float(np.std(np.diff(mkt_log[t - 252:t + 1]))
                                 * np.sqrt(252.0)),
            "mkt_vol_63": float(np.std(np.diff(mkt_log[t - 63:t + 1]))
                                * np.sqrt(252.0)),
            "mkt_ret_63": float(np.expm1(mkt_log[t] - mkt_log[t - 63])),
            "mkt_ret_252": float(np.expm1(mkt_log[t] - mkt_log[t - 252])),
            "mkt_dd_252": float(np.expm1(mkt_log[t]
                                         - np.max(mkt_log[t - 252:t + 1]))),
            "h_days": h,
        })
    mkt_df = pd.DataFrame(mrows)

    # buyable index funds, from the EODHD spine
    etf = pd.read_parquet(MODULE_ROOT / "data" / "etf" / "etf_adjusted_close.parquet")
    qqq = pd.read_parquet(MODULE_ROOT / "data" / "etf" /
                          "etf_QQQ_adjusted_close.parquet")
    etf = etf.join(qqq, how="outer").sort_index()
    for tk in ("SPY", "QQQ"):
        s = pd.to_numeric(etf[tk], errors="coerce").dropna()
        v = []
        for k in range(nT - 1):
            a, b = dec_dates[k], dec_dates[k + 1]
            sa = s.loc[:a]
            sb = s.loc[:b]
            v.append(float(sb.iloc[-1] / sa.iloc[-1] - 1.0)
                     if len(sa) and len(sb) else np.nan)
        mkt_df[f"{tk.lower()}_fwd_1m"] = v

    # ── the ablation's declared LLM cells ───────────────────────────────────
    rng = np.random.default_rng(LLM_SEED)
    lo = pd.Timestamp(LLM_FIRST_DATE)
    llm_rows = []
    for k in range(nT - 1):
        if dec_dates[k] < lo:
            continue
        d = panel[panel["date_ix"] == k]
        d = d[np.isfinite(d["mcap"]) & (d["mcap"] > 0)]
        if len(d) < LLM_N_NAMES:
            continue
        q = pd.qcut(d["mcap"].rank(method="first"), LLM_QUINTILES,
                    labels=False)
        per = LLM_N_NAMES // LLM_QUINTILES
        pick = []
        for g in range(LLM_QUINTILES):
            idx = d.index[q.to_numpy() == g].to_numpy()
            take = rng.choice(idx, size=min(per, len(idx)), replace=False)
            pick.extend(take.tolist())
        llm_rows.append(d.loc[sorted(pick)].assign(date_ix=k))
    llm = pd.concat(llm_rows, ignore_index=True)

    tick = load_tickers(np.unique(llm["permno"].to_numpy()), dec_dates)
    llm["ticker"] = [tick.get((int(k), int(p)), ("", ""))[0]
                     for k, p in zip(llm["date_ix"], llm["permno"])]
    llm["comnam"] = [tick.get((int(k), int(p)), ("", ""))[1]
                     for k, p in zip(llm["date_ix"], llm["permno"])]
    llm["date"] = [dec_dates[int(k)] for k in llm["date_ix"]]
    n_no_ticker = int((llm["ticker"] == "").sum())
    llm = llm[llm["ticker"] != ""].reset_index(drop=True)

    FACTORY.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT, index=False)
    mkt_df.to_parquet(OUT_MKT, index=False)
    llm.to_parquet(OUT_LLM, index=False)

    meta = {
        "n_decision_dates": int(nT - 1),
        "first_decision": str(dec_dates[0].date()),
        "last_decision": str(dec_dates[nT - 2].date()),
        "n_state_rows": int(n_states),
        "names_per_date_min": int(panel.groupby("date_ix").size().min()),
        "names_per_date_max": int(panel.groupby("date_ix").size().max()),
        "eligibility": {"min_price": MIN_PRICE, "min_history": MIN_HISTORY,
                        "min_median_dollar_volume": MIN_MED_DV, "top_n": TOP_N},
        "delisting": ddiag,
        "fwd_ret_finite_share": float(np.isfinite(panel["fwd_ret_1m"]).mean()),
        "llm_cells": {
            "n_dates": int(llm["date_ix"].nunique()),
            "n_cells": int(len(llm)),
            "first": str(llm["date"].min().date()),
            "last": str(llm["date"].max().date()),
            "dropped_no_pit_ticker": n_no_ticker,
            "seed": LLM_SEED, "names_per_date": LLM_N_NAMES,
            "strata": "market-cap quintiles, 8 per quintile",
        },
        "build_seconds": round(time.time() - t0, 1),
    }
    OUT_META.write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    build()
