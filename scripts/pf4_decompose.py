"""TRIAL-PF4-DECOMPOSITION-1 — the runner.

Registered in TRIALS/PREREG_PF4_DECOMPOSITION.md and committed BEFORE this file
executed (commit 12d8540, 2026-08-09T18:58:02+08:00). The decision rule lives
there; nothing here adjudicates.

    python scripts/pf4_decompose.py --stage A     # decompositions, fast-ish
    python scripts/pf4_decompose.py --stage B     # characteristic-matched placebo
    python scripts/pf4_decompose.py --stage C     # product benchmark

Every stage writes its own JSON under runs/PF4/ and prints its own numbers, so a
stage that dies takes only itself down.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf.engine import buy_and_hold_universe, run_book
from aegis_brain.pf.panel63 import annualize, eligibility, max_drawdown
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import SignalLibrary, composite_score
from aegis_brain.pf.spec import StrategySpec

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pf4")

OUT = MODULE_ROOT / "runs" / "PF4"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
DELIST = MODULE_ROOT / "data" / "wrds_raw" / "crsp_dsedelist.parquet"
SEED = 20260809

# Shumway (1997): CRSP DLRET is missing disproportionately for performance
# delists, and the missing truth averages about -30%. Codes 400-591 are
# liquidations and "dropped" (performance) delists. Mergers and exchanges
# (200-399) pay out and are correctly treated as 0.
PERF_CODE_LO, PERF_CODE_HI = 400, 591
IMPUTE_PRIMARY = -0.30
IMPUTE_STRESS = -0.55


def spec_of(card: dict, **changes) -> StrategySpec:
    d = dict(card["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = tuple(d.get("tags", ()))
    d.update(changes)
    return StrategySpec(**d)


def dump(name: str, obj: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=2, default=str),
                            encoding="utf-8")
    log.info("wrote runs/PF4/%s", name)


# ── delisting ───────────────────────────────────────────────────────────────
def delist_events() -> pd.DataFrame:
    d = pd.read_parquet(DELIST, columns=["permno", "dlstdt", "dlstcd", "dlret"])
    d = d.dropna(subset=["permno", "dlstcd"])
    d["sym"] = d["permno"].astype("int64").astype(str)
    d["code"] = d["dlstcd"].astype("int64")
    d["has_dlret"] = d["dlret"].notna()
    d["perf"] = d["code"].between(PERF_CODE_LO, PERF_CODE_HI)
    return d[["sym", "code", "has_dlret", "perf"]].drop_duplicates("sym")


def delist_stub_frame(panel, events: pd.DataFrame, value: float
                      ) -> tuple[pd.DataFrame, dict]:
    """Stub returns for the month a held name's return first goes permanently NaN.

    Only the TERMINAL gap is imputed. A name that goes missing mid-series and
    comes back is a data hole, not a delisting, and imputing -30% there would be
    inventing losses.
    """
    ret = panel.monthly_ret
    months = ret.index
    pos = {m: i for i, m in enumerate(months)}
    ev = events.set_index("sym")
    stub = pd.DataFrame(0.0, index=months, columns=ret.columns, dtype=np.float32)
    n_imputed = 0
    counts = {"perf_no_dlret": 0, "perf_with_dlret": 0, "nonperf": 0,
              "no_delist_record": 0, "still_trading_at_panel_end": 0}
    last_month = months[-1]
    for sym in ret.columns:
        lv = ret[sym].last_valid_index()
        if lv is None or lv == last_month:
            counts["still_trading_at_panel_end"] += 1
            continue
        nxt = months[pos[lv] + 1]
        if sym not in ev.index:
            counts["no_delist_record"] += 1
            continue
        row = ev.loc[sym]
        if not bool(row["perf"]):
            counts["nonperf"] += 1
            continue
        if bool(row["has_dlret"]):
            counts["perf_with_dlret"] += 1
            continue
        counts["perf_no_dlret"] += 1
        stub.loc[nxt, sym] = value
        n_imputed += 1
    return stub, {"names_imputed": n_imputed, "impute_value": value, **counts}


# ── stage A ─────────────────────────────────────────────────────────────────
def stage_a(f: Factory, banked: dict) -> dict:
    t0 = time.time()
    base = spec_of(banked)
    elig = f.eligible(base.segment)
    score, _ = composite_score(f.lib, base.signals, elig)
    panel, rf, mkt = f.spine.panel, f.spine.rf, f.spine.mkt
    factors = f.factors

    holdings: list[dict] = []
    out = run_book(panel, score, elig, base, rf, None, None, None, holdings)
    net = out["monthly"]["net"].dropna()
    idx = net.index
    bench = mkt.reindex(idx)
    ew = buy_and_hold_universe(panel, elig, base, rf).reindex(idx)
    log.info("base book %d months, EW universe covers %d", len(net), ew.notna().sum())

    res: dict = {
        "trial": "TRIAL-PF4-DECOMPOSITION-1",
        "prereg": "TRIALS/PREREG_PF4_DECOMPOSITION.md (commit 12d8540)",
        "strategy": base.name, "spec_hash": base.spec_hash(),
        "window": {"first": str(idx.min().date()), "last": str(idx.max().date()),
                   "months": len(idx)},
        "holdout_read": bool(f.spine.provenance["holdout_read"]),
        "banked_headline": banked["headline"],
    }

    # ── PRIMARY METRIC ──────────────────────────────────────────────────────
    d = (net - ew).dropna()
    res["PRIMARY_incremental_signal_contribution"] = {
        "definition": "FF5+UMD alpha of (book net - equal-weight eligible "
                      "universe), Newey-West(12)",
        "self_financing_cagr_gap": round(annualize(net) - annualize(ew.dropna()), 4),
        "mean_monthly": round(float(d.mean()), 5),
        "t_raw_nw": D.nw_t(d),
        "mde_at_t2_annualized": D.mde_annualized(d),
        "alpha_ff5_umd": D.alpha_report(d, factors, D.FF6),
        "alpha_capm": D.alpha_report(d, factors, ["mktrf"]),
    }

    # ── the legs the reviewers name ─────────────────────────────────────────
    ewd = ew.dropna()
    res["leg_ew_universe"] = {
        "note": "the equal-weight, monthly-rebalanced eligible universe itself, "
                "no selection and no costs — the rebalancing/size/illiquidity "
                "premium leg",
        "cagr": round(annualize(ewd), 4),
        "excess_cagr_vs_benchmark": round(annualize(ewd) - annualize(bench), 4),
        "alpha_ff5_umd": D.alpha_report(ewd, factors, D.FF6, rf=rf),
        "alpha_capm": D.alpha_report(ewd, factors, ["mktrf"], rf=rf),
    }

    smallprof = D.long_short_factor(score, elig, panel.monthly_ret).reindex(idx)
    fac7 = factors.copy()
    fac7["smallprof"] = smallprof
    res["leg_smallcap_profitability_factor"] = {
        "construction": "EW top-30% minus bottom-30% of the same composite "
                        "inside the same eligible small universe, formation m -> "
                        "realized m+1",
        "months": int(smallprof.notna().sum()),
        "cagr_of_factor": round(annualize(smallprof.dropna()), 4),
        "t_factor_nw": D.nw_t(smallprof),
        "book_alpha_vs_ff5_umd_plus_smallprof": D.alpha_report(
            net, fac7, D.FF6 + ["smallprof"], rf=rf),
        "self_financing_alpha_vs_ff5_umd_plus_smallprof": D.alpha_report(
            d, fac7, D.FF6 + ["smallprof"]),
        "why": "RMW is value-weighted and large-cap dominated; a low RMW loading "
               "on an EW microcap book is mechanically expected and is not "
               "evidence of non-spanning. This factor is the fair benchmark.",
    }

    ami = D.amihud(panel)
    ami_l = D.long_short_factor(-ami, elig, panel.monthly_ret).reindex(idx)
    facA = factors.copy()
    facA["illiq"] = ami_l
    res["leg_illiquidity"] = {
        "construction": "EW least-illiquid-30% minus most-illiquid-30% (Amihud, "
                        "12m) inside the same universe; sign is liquid-minus-"
                        "illiquid, so a NEGATIVE loading means the book tilts "
                        "illiquid",
        "book_alpha_vs_ff5_umd_plus_illiq": D.alpha_report(
            net, facA, D.FF6 + ["illiq"], rf=rf),
        "self_financing_alpha_vs_ff5_umd_plus_illiq": D.alpha_report(
            d, facA, D.FF6 + ["illiq"]),
    }

    res["calendar"] = D.calendar_split(net, bench)
    res["event_time_membership"] = D.event_time_profile(
        holdings, panel.monthly_ret, mkt)

    # ── delisting ───────────────────────────────────────────────────────────
    ev = delist_events()
    dead_events = []
    for h in holdings:
        r = panel.monthly_ret.loc[h["test"]]
        dead = [n for n in h["weights"].index if pd.isna(r.get(n, np.nan))]
        for n in dead:
            dead_events.append({"month": h["test"], "sym": n,
                                "w": float(h["weights"][n])})
    de = pd.DataFrame(dead_events)
    evi = ev.set_index("sym")
    if len(de):
        de = de.join(evi, on="sym")
        de["perf"] = de["perf"].fillna(False)
        de["has_dlret"] = de["has_dlret"].fillna(False)
    audit = {
        "forced_liquidation_events": int(len(de)),
        "banked_count_for_cross_check": banked["implementation"]["forced_liquidations"],
        "with_delist_record": int(de["code"].notna().sum()) if len(de) else 0,
        "performance_code_400_591": int(de["perf"].sum()) if len(de) else 0,
        "performance_and_missing_dlret": (
            int((de["perf"] & ~de["has_dlret"]).sum()) if len(de) else 0),
        "weight_exposed_performance_missing_dlret": (
            round(float(de.loc[de["perf"] & ~de["has_dlret"], "w"].sum()), 4)
            if len(de) else 0.0),
        "note": "'forced liquidation events' counts name-months the engine had "
                "to liquidate; the banked figure counts the same events. Only "
                "performance-coded delists with NO CRSP dlret are imputed - a "
                "merger pays out and a recorded dlret is already in the panel.",
    }
    for label, val in (("shumway_-30pct", IMPUTE_PRIMARY),
                       ("shumway_warther_-55pct", IMPUTE_STRESS)):
        stub, sdiag = delist_stub_frame(panel, ev, val)
        o = run_book(panel, score, elig, base, rf, None, None, stub)
        n2 = o["monthly"]["net"].dropna()
        b2 = mkt.reindex(n2.index)
        audit[label] = {
            **sdiag,
            "excess_cagr_net": round(annualize(n2) - annualize(b2), 4),
            "delta_vs_banked": round(
                (annualize(n2) - annualize(b2))
                - banked["headline"]["excess_cagr_net"], 4),
            "max_drawdown": round(max_drawdown(n2), 4),
        }
        log.info("delist %s -> excess %.4f", label, audit[label]["excess_cagr_net"])
    res["delisting_audit"] = audit

    # ── era-appropriate costs ───────────────────────────────────────────────
    ko = f.cost_frame()
    cost_arms = {}
    for label, frame in (("tick_floor_over_flat25", D.era_cost_frame(panel, 25.0)),
                         ("tick_floor_over_ko", D.era_cost_frame(panel, 25.0, ko))):
        sp = spec_of(banked, cost_model="ko", name=f"{base.name}__{label}")
        o = run_book(panel, score, elig, sp, rf, frame)
        n2 = o["monthly"]["net"].dropna()
        b2 = mkt.reindex(n2.index)
        half = n2.index[len(n2) // 2]
        cost_arms[label] = {
            "excess_cagr_net": round(annualize(n2) - annualize(b2), 4),
            "delta_vs_flat25": round((annualize(n2) - annualize(b2))
                                     - banked["headline"]["excess_cagr_net"], 4),
            "cost_drag_annual_bps": o["diag"]["cost_drag_annual_bps"],
            "excess_pre_2001": round(
                annualize(n2[n2.index <= "2001-03-31"])
                - annualize(b2[b2.index <= "2001-03-31"]), 4),
            "excess_post_2001": round(
                annualize(n2[n2.index > "2001-03-31"])
                - annualize(b2[b2.index > "2001-03-31"]), 4),
            "t_excess_nw": D.nw_t(n2 - b2),
        }
        log.info("cost arm %s -> excess %.4f", label,
                 cost_arms[label]["excess_cagr_net"])
    tf = D.tick_floor_bps(panel)
    cost_arms["_tick_floor_bps_median_by_era"] = {
        era: round(float(np.nanmedian(
            tf.loc[(tf.index > lo) & (tf.index <= hi)].to_numpy())), 1)
        for era, lo, hi in (("pre-1997", "1900-01-01", "1997-06-30"),
                            ("1997-2001", "1997-06-30", "2001-03-31"),
                            ("post-2001", "2001-03-31", "2100-01-01"))}
    cost_arms["_limitation"] = (
        "no daily high/low on this spine, so Corwin-Schultz and Abdi-Ranaldo "
        "are not computable. The tick floor is a mechanical LOWER bound, so "
        "these arms understate cost and any surviving excess is an upper bound.")
    res["era_costs"] = cost_arms

    # ── construction grids ──────────────────────────────────────────────────
    grids: dict = {"buy_hold_band": {}, "rebalance_months": {}}
    for mult in (1.0, 2.0, 3.0, 5.0, 10.0):
        sp = spec_of(banked, hold_band_mult=mult)
        o = run_book(panel, score, elig, sp, rf)
        n2 = o["monthly"]["net"].dropna()
        b2 = mkt.reindex(n2.index)
        grids["buy_hold_band"][f"mult_{mult:g}"] = {
            "buy_rank": sp.top_n, "hold_until_rank": int(mult * sp.top_n),
            "excess_cagr_net": round(annualize(n2) - annualize(b2), 4),
            "turnover_1way_annual": o["diag"]["turnover_1way_annual"],
            "t_excess_nw": D.nw_t(n2 - b2)}
    for reb in (1, 3, 6, 12):
        sp = spec_of(banked, rebalance_months=reb)
        o = run_book(panel, score, elig, sp, rf)
        n2 = o["monthly"]["net"].dropna()
        b2 = mkt.reindex(n2.index)
        grids["rebalance_months"][str(reb)] = {
            "excess_cagr_net": round(annualize(n2) - annualize(b2), 4),
            "turnover_1way_annual": o["diag"]["turnover_1way_annual"],
            "t_excess_nw": D.nw_t(n2 - b2)}
    res["construction_grids"] = grids
    res["construction_grids"]["_note"] = (
        "the live spec already runs hold_band_mult=3.0, i.e. buy at rank <=150 "
        "and hold until rank >450. The Novy-Marx-Velikov buy/hold spread the "
        "reviewer proposed (buy <=150, hold to >300) is mult_2 and is TIGHTER "
        "than what production already does.")

    # ── marginal rank windows (R-5) ─────────────────────────────────────────
    marg = {}
    for lo in range(1, 150, 10):
        hi = lo + 9
        sc = D.rank_window_score(score, elig, lo, hi)
        sp = spec_of(banked, top_n=10, hold_band_mult=1.0, min_names=10,
                     name=f"{base.name}__rank{lo}_{hi}")
        try:
            o = run_book(panel, sc, elig, sp, rf)
        except RuntimeError as exc:
            marg[f"{lo}-{hi}"] = {"error": str(exc)[:120]}
            continue
        n2 = o["monthly"]["net"].dropna()
        b2 = mkt.reindex(n2.index)
        marg[f"{lo}-{hi}"] = {
            "months": len(n2),
            "excess_cagr_net": round(annualize(n2) - annualize(b2), 4),
            "alpha_ff5_umd": D.alpha_report(n2, factors, D.FF6, rf=rf),
        }
        log.info("rank window %d-%d done", lo, hi)
    res["marginal_rank_windows"] = marg
    res["marginal_rank_windows"]["_note"] = (
        "R-5: if ordering inside the selected set is informationless, the "
        "ALPHAS are flat. Raw excess is not the test - deeper ranks are smaller "
        "and less liquid, so falling signal quality offset by rising size and "
        "illiquidity premia produces a flat raw curve either way.")

    # ── liquidity shift: drop the bottom 30% of the universe by ADV ─────────
    dv = panel.monthly_dollar_vol.where(elig)
    keep = dv.rank(axis=1, pct=True) > 0.30
    elig_liq = (elig & keep.fillna(False)).astype(bool)
    score_liq, _ = composite_score(f.lib, base.signals, elig_liq)
    sp = spec_of(banked, min_names=70, name=f"{base.name}__drop_bottom30_adv")
    o = run_book(panel, score_liq, elig_liq, sp, rf)
    n2 = o["monthly"]["net"].dropna()
    b2 = mkt.reindex(n2.index)
    ew2 = buy_and_hold_universe(panel, elig_liq, sp, rf).reindex(n2.index)
    d2 = (n2 - ew2).dropna()
    res["liquidity_shift_drop_bottom30_adv"] = {
        "months": len(n2),
        "excess_cagr_net": round(annualize(n2) - annualize(b2), 4),
        "delta_vs_banked": round((annualize(n2) - annualize(b2))
                                 - banked["headline"]["excess_cagr_net"], 4),
        "incremental_alpha_ff5_umd": D.alpha_report(d2, factors, D.FF6),
        "t_excess_nw": D.nw_t(n2 - b2),
    }

    res["runtime_secs"] = round(time.time() - t0, 1)
    dump("STAGE_A.json", res)
    return res


# ── stage A2: the pre-1982 block ────────────────────────────────────────────
def stage_a2(f: Factory, banked: dict) -> dict:
    """1963-1982, made computable by indexing the nominal liquidity floor.

    REPORTED, NEVER DECIDING - the deflator uses a future-dated anchor and is
    therefore not point-in-time. It cannot promote anything.
    """
    t0 = time.time()
    base = spec_of(banked)
    panel, rf, mkt = f.spine.panel, f.spine.rf, f.spine.mkt
    from aegis_brain.pf.panel63 import segment_mask
    res = {"status": "REPORTED-NEVER-DECIDING",
           "why": "the dollar-volume floor deflator is anchored on a future "
                  "month, so this block is not PIT and may not gate anything"}

    ok = D.indexed_eligibility(panel, 200_000.0, anchor="2010-12-31")
    elig = (ok & segment_mask(panel, "small")).fillna(False).astype(bool)
    res["eligible_names_by_decade"] = {
        str(k.year): round(float(v), 1) for k, v in
        elig.sum(axis=1).resample("10YE").mean().items()}
    try:
        score, _ = composite_score(f.lib, base.signals, elig)
    except RuntimeError as exc:
        res["error"] = str(exc)
        dump("STAGE_A2_PRE1982.json", res)
        return res
    res["scored_names_by_decade"] = {
        str(k.year): round(float(v), 1) for k, v in
        score.notna().sum(axis=1).resample("10YE").mean().items()}
    sp = spec_of(banked, min_names=60, name=f"{base.name}__indexed_floor")
    try:
        o = run_book(panel, score, elig, sp, rf)
    except RuntimeError as exc:
        res["error"] = str(exc)
        dump("STAGE_A2_PRE1982.json", res)
        return res
    net = o["monthly"]["net"].dropna()
    bench = mkt.reindex(net.index)
    res["full_window"] = {
        "first": str(net.index.min().date()), "last": str(net.index.max().date()),
        "months": len(net),
        "excess_cagr_net": round(annualize(net) - annualize(bench), 4),
        "t_excess_nw": D.nw_t(net - bench)}
    pre = net[net.index <= "1982-10-31"]
    if len(pre) >= 24:
        bp = bench.reindex(pre.index)
        ewp = buy_and_hold_universe(panel, elig, sp, rf).reindex(pre.index)
        res["block_1963_1982"] = {
            "months": len(pre),
            "excess_cagr_net": round(annualize(pre) - annualize(bp), 4),
            "t_excess_nw": D.nw_t(pre - bp),
            "mde_at_t2": D.mde_annualized(pre - bp),
            "incremental_alpha_ff5_umd": D.alpha_report(
                (pre - ewp).dropna(), f.factors, D.FF6),
        }
    else:
        res["block_1963_1982"] = {"months": len(pre),
                                  "note": "still too thin to report"}
    res["runtime_secs"] = round(time.time() - t0, 1)
    dump("STAGE_A2_PRE1982.json", res)
    return res


# ── stage B: characteristic-matched placebo ─────────────────────────────────
def stage_b(f: Factory, banked: dict, n_draws: int) -> dict:
    t0 = time.time()
    base = spec_of(banked)
    elig = f.eligible(base.segment)
    score, _ = composite_score(f.lib, base.signals, elig)
    panel, rf, mkt = f.spine.panel, f.spine.rf, f.spine.mkt
    holdings: list[dict] = []
    out = run_book(panel, score, elig, base, rf, None, None, None, holdings)
    m = out["monthly"]
    bench = mkt.reindex(m.index)
    strat = {"net": annualize(m["net"]) - annualize(bench),
             "gross": annualize(m["gross"]) - annualize(bench)}

    f.lib.preload(["native:mom_12_1", "osap:BM"])
    cell, cdiag = D.build_cells(panel, f.lib, elig)
    log.info("cells: %s", cdiag)
    band = D.char_matched_placebo(panel, elig, base, rf, None, mkt, holdings,
                                  cell, n_draws=n_draws, seed=SEED)
    verdicts = {}
    for basis in ("gross", "net"):
        ex = np.asarray(band[f"draws_{basis}"], dtype=float)
        n = len(ex)
        s = strat[basis]
        verdicts[basis] = {
            "strategy_excess_cagr": round(float(s), 4),
            "empirical_p_value": round((n - int((ex < s).sum()) + 1) / (n + 1), 4),
            "beats_placebo_max": bool(s > band[f"excess_cagr_{basis}"]["max"]),
            "beats_placebo_p95": bool(s > band[f"excess_cagr_{basis}"]["p95"]),
        }
    res = {
        "trial": "TRIAL-PF4-DECOMPOSITION-1", "arm": "characteristic-matched placebo",
        "primary_basis": "gross (see band.turnover_caveat)",
        "cells": cdiag, "band": band, "verdict_by_basis": verdicts,
        "banked_turnover_matched_p_for_comparison": 0.0099,
        "why_this_replaces_the_old_gate": (
            "the turnover-matched placebo draws random names, which differ from "
            "a profitability-selected 150 in size and liquidity; it is therefore "
            "not exchangeable with the book. This one randomizes ONLY the "
            "profitability dimension."),
        "runtime_secs": round(time.time() - t0, 1),
    }
    dump("STAGE_B_CHAR_PLACEBO.json", res)
    return res


# ── stage C: product benchmark ──────────────────────────────────────────────
def stage_c(f: Factory, banked: dict) -> dict:
    """Is there a buyable thing that already does this?

    The dossier compared the book to the market and never to the products that
    implement small-cap profitability screening in one ticker. Ken French's
    size x operating-profitability portfolios are the long-history proxy;
    AVUV/DFSV from 2019-09 need a PIT-clean price source this repo does not
    have, and are named as deferred rather than quietly dropped.
    """
    t0 = time.time()
    res = {"trial": "TRIAL-PF4-DECOMPOSITION-1", "arm": "product benchmark",
           "avuv_dfsv": {"status": "DEFERRED - NOT RUN",
                         "reason": "requires a PIT-clean price source; yfinance "
                                   "is forbidden for money claims and no ETF "
                                   "price feed is wired into this repo",
                         "needed_from_murat": "one clean ETF price source "
                                              "(Polygon or FMP) for AVUV, DFSV, "
                                              "IJS, VBR from 2019-09"}}
    url = ("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
           "25_Portfolios_ME_OP_5x5_CSV.zip")
    try:
        import io
        import urllib.request
        import zipfile
        req = urllib.request.Request(url, headers={"User-Agent": "aegis-research"})
        raw = urllib.request.urlopen(req, timeout=60).read()
        z = zipfile.ZipFile(io.BytesIO(raw))
        txt = z.read(z.namelist()[0]).decode("latin-1")
        lines = txt.splitlines()
        start = next(i for i, l in enumerate(lines)
                     if l.strip().startswith("SMALL") or "LoOP" in l)
        rows, hdr = [], [c.strip() for c in lines[start].split(",")]
        for l in lines[start + 1:]:
            p = [c.strip() for c in l.split(",")]
            if len(p) != len(hdr) + 1 or not p[0].isdigit() or len(p[0]) != 6:
                if rows:
                    break
                continue
            rows.append(p)
        df = pd.DataFrame(rows)
        df[0] = pd.to_datetime(df[0], format="%Y%m") + pd.offsets.MonthEnd(0)
        df = df.set_index(0).astype(float) / 100.0
        df.columns = hdr
        small_robust = [c for c in df.columns
                        if c.upper().startswith("SMALL") and "HI" in c.upper()]
        col = small_robust[0] if small_robust else df.columns[4]
        banked_card = banked
        s = df[col]
        idx = pd.date_range(banked_card["window"]["first"],
                            banked_card["window"]["last"], freq="ME")
        s = s.reindex(idx).dropna()
        b = f.spine.mkt.reindex(s.index)
        res["french_small_robust"] = {
            "portfolio_column": col, "months": len(s),
            "cagr": round(annualize(s), 4),
            "excess_cagr_vs_benchmark": round(annualize(s) - annualize(b), 4),
            "book_excess_over_this_product": round(
                banked_card["headline"]["cagr_net"] - annualize(s), 4),
            "note": "French portfolios are GROSS of costs and of any fund "
                    "expense ratio; the book's number is net of 25bps trading. "
                    "This comparison flatters the product, not the book.",
        }
    except Exception as exc:
        res["french_small_robust"] = {"status": "NOT RUN", "error": str(exc)[:200]}
    res["runtime_secs"] = round(time.time() - t0, 1)
    dump("STAGE_C_PRODUCT_BENCHMARK.json", res)
    return res


# ── stage D: the configurations a person could actually hold ────────────────
def stage_d(f: Factory, banked: dict) -> dict:
    """Combinations of arms already registered as reported-never-deciding.

    Nothing new is introduced here: era-appropriate costs (5.3), the rebalance
    grid (5.7) and the liquidity shift (5.2) are each registered, and this stage
    only runs them TOGETHER, because the product question is what survives all
    of them at once rather than one at a time. Still reported, still never
    deciding — the primary metric is unaffected by anything in this function.
    """
    t0 = time.time()
    base = spec_of(banked)
    panel, rf, mkt = f.spine.panel, f.spine.rf, f.spine.mkt
    elig = f.eligible(base.segment)
    score, _ = composite_score(f.lib, base.signals, elig)
    ko = f.cost_frame()
    era = D.era_cost_frame(panel, 25.0, ko)

    dv = panel.monthly_dollar_vol.where(elig)
    elig_liq = (elig & (dv.rank(axis=1, pct=True) > 0.30).fillna(False)).astype(bool)
    score_liq, _ = composite_score(f.lib, base.signals, elig_liq)

    configs = {
        "as_registered_monthly_flat25": (base, score, elig, None),
        "annual_rebalance_era_costs": (
            spec_of(banked, rebalance_months=12, cost_model="ko",
                    name=f"{base.name}__ann_era"), score, elig, era),
        "quarterly_rebalance_era_costs": (
            spec_of(banked, rebalance_months=3, cost_model="ko",
                    name=f"{base.name}__q_era"), score, elig, era),
        "annual_era_costs_liquid_two_thirds": (
            spec_of(banked, rebalance_months=12, cost_model="ko", min_names=70,
                    name=f"{base.name}__ann_era_liq"), score_liq, elig_liq, era),
        "annual_era_costs_no_incumbency_band": (
            spec_of(banked, rebalance_months=12, cost_model="ko",
                    hold_band_mult=1.0, name=f"{base.name}__ann_era_nb"),
            score, elig, era),
    }
    out: dict = {"trial": "TRIAL-PF4-DECOMPOSITION-1",
                 "arm": "product configurations",
                 "status": "REPORTED-NEVER-DECIDING",
                 "why": "combinations of already-registered reported arms; the "
                        "primary metric and the verdict do not depend on any of "
                        "these"}
    for label, (sp, sc, el, cf) in configs.items():
        o = run_book(panel, sc, el, sp, rf, cf)
        net = o["monthly"]["net"].dropna()
        b = mkt.reindex(net.index)
        ew = buy_and_hold_universe(panel, el, sp, rf).reindex(net.index)
        post = net.index > "2001-03-31"
        row = {
            "months": len(net),
            "excess_cagr_net": round(annualize(net) - annualize(b), 4),
            "t_excess_nw": D.nw_t(net - b),
            "turnover_1way_annual": o["diag"]["turnover_1way_annual"],
            "cost_drag_annual_bps": o["diag"]["cost_drag_annual_bps"],
            "max_drawdown": round(max_drawdown(net), 4),
            "excess_pre_2001": round(annualize(net[~post])
                                     - annualize(b[~post]), 4),
            "excess_post_2001": round(annualize(net[post])
                                      - annualize(b[post]), 4),
            "t_excess_post_2001_nw": D.nw_t((net - b)[post]),
            "incremental_alpha_ff5_umd": D.alpha_report(
                (net - ew).dropna(), f.factors, D.FF6),
        }
        out[label] = row
        log.info("stage D %s -> excess %.4f (post-2001 %.4f) turnover %.2f",
                 label, row["excess_cagr_net"], row["excess_post_2001"],
                 row["turnover_1way_annual"])
    out["runtime_secs"] = round(time.time() - t0, 1)
    dump("STAGE_D_PRODUCT_CONFIGS.json", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="A",
                    choices=["A", "A2", "B", "C", "D", "all"])
    ap.add_argument("--draws", type=int, default=100)
    args = ap.parse_args()
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    f = Factory()
    if args.stage in ("A", "all"):
        stage_a(f, banked)
    if args.stage in ("A2", "all"):
        stage_a2(f, banked)
    if args.stage in ("B", "all"):
        stage_b(f, banked, args.draws)
    if args.stage in ("C", "all"):
        stage_c(f, banked)
    if args.stage in ("D", "all"):
        stage_d(f, banked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
