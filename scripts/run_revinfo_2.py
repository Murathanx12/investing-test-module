"""REVINFO-2 — Layer 2: the decision boundary for a long-only revision book,
with G7 turnover in the SAME trial.

Registered TRIALS/PREREG_REVINFO_2_LAYER2.md at commit 7409bff, BEFORE any
Layer-2 statistic was computed. This trial ACCRUES ONE ARM. Frozen window
2002-01-31..2022-12-31; the holdout is unread and the daily spine is truncated
at 2022-12-31 for that reason (the sibling G7 script ran to 2024 — this one
may not).

WHAT IS MEASURED
================
H1  E[r_entrant − r_incumbent] at the book's own decision boundary, estimated
    on the paired per-rebalance difference with its own Newey-West SE (§18).
    Entrants/leavers are read off the SAME holdings the simulated book actually
    traded, so the boundary tested is the boundary traded. Delist-driven exits
    (NaN return in the test month) are excluded — a delisting is not a decision.
H2  The same book through `aegis_brain/pf/daily_sim.py` at impact_coef=0 (G7).
    Headline: NET excess CAGR vs the CRSP value-weighted benchmark, beside its
    own 80%-power MDE (max(HAC, IID), §19), plus the EXECUTION-STANDARD
    regime-block table (scorecard._regime_table on GATE_BLOCKS).
H3  Holding periods 1/3/6 months; claims about DIFFERENCES between ADJACENT
    frequencies, each estimated on the paired monthly G7 return difference with
    its own SE (§18) — never read off two levels.

BOOK SIZE — both, not the better one. The prereg says "50-100 names";
ANALYST-IBES-1 (the turnover prior) ran top-50. Both {50, 100} run and BOTH are
reported with their own MDEs. Nothing here selects between them.

TARGET TIMING — a discrepancy in the sibling, resolved toward the module's own
contract. `daily_sim`'s docstring: "the decision is made on the month-end close
and the trade happens on the NEXT trading day's open." `scripts/g7_daily_sim.py`
says the same in a comment and then passes `effective = test` — the month-end
of the month whose return the monthly harness already earned, i.e. a ~1-month
implementation lag. For an annual book that cost ~28 bps/yr (NIGHT-5); for a
monthly book on a signal whose information decays over ~6 months it would
systematically destroy the h=1 information and bias H2 toward the registered
NET_DEAD expectation — a silent thumb on the scale in the direction we said we
expected. So targets here go effective at formation month-end + 1 day, and the
sibling's convention is run as a SENSITIVITY arm on one cell so the gap is a
measured number rather than an argument.

CONTROLS (pre-specified)
========================
* `tgt_upside` corpse through the SAME pipeline, BOTH arms: cross-sectional
  (Layer-1 instrument) and tail-concentrated (top-50 book through run_book AND
  G7). Must reproduce its negative sign.
* Pure-noise signal (np.random.default_rng, seeded), turnover-matched via
  controls.match_rho, through the same construction and G7. Must earn ~nothing.
* Realised turnover reported per frequency, against the ANALYST-IBES-1 prior
  (eps_rev_breadth small top-50 monthly: 10.614x, receipts on disk). Below the
  prior is investigated before anything is reported.

    python -m scripts.run_revinfo_2

Writes runs/REVINFO_2/revinfo2.json plus per-book monthly/NAV/H1 checkpoints.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.harness.benchmark import newey_west_tstat
from aegis_brain.pf.controls import match_rho
from aegis_brain.pf.daily_sim import DailyData, SimConfig, load_daily, simulate
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.information import cross_sectional_information
from aegis_brain.pf.panel63 import GATE_BLOCKS, annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.scorecard import _power_block, _regime_table
from aegis_brain.pf.signals import composite_score, random_score
from aegis_brain.pf.spec import StrategySpec

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "REVINFO_2"

FIRST, LAST = "2002-01-31", "2022-12-31"
DAILY_FIRST, DAILY_LAST = "2002-01-01", "2022-12-31"   # holdout NOT loaded
SIGNAL = "ibes:eps_rev_breadth"
CORPSE = "ibes:tgt_upside"
SIZES = (50, 100)
CLOCKS = (1, 3, 6)

MDE_Z = 2.8
SIG_Z = 1.96
#: EXECUTION STANDARD economic threshold: net excess CAGR >= +3%/yr.
ECON_THRESHOLD_ANN = 0.03
NOISE_SEED = 20260811

#: Realised turnover for THIS signal at the incumbent construction, measured by
#: ANALYST-IBES-1 (runs/ARENA1/ANALYST_IBES_1/results.json). The "10x prior".
TURNOVER_PRIOR = {
    "source": "ANALYST-IBES-1 R1_eps_rev_breadth small top-50",
    "m1": 10.614, "m3": 3.150,
}


# ── small statistics helpers (same conventions as pf.information) ────────────

def series_stats(x: pd.Series, lags: int, ann: float) -> dict:
    """Mean, HAC t, and 80%-power MDE (max(HAC, IID) — an MDE licenses a null)."""
    s = pd.Series(x).dropna().astype(float)
    n = len(s)
    if n < 12:
        return {"mean_ann": float("nan"), "t": None, "se_hac_ann": float("nan"),
                "se_iid_ann": float("nan"), "mde_ann": float("nan"),
                "n": n, "hac_lags": lags}
    nw = newey_west_tstat(s, lags=lags)
    se_iid = float(s.std(ddof=1) / np.sqrt(n))
    se_hac = float(nw["se"]) if nw.get("se") else se_iid
    return {
        "mean_ann": float(s.mean()) * ann,
        "t": None if nw.get("t") is None else round(float(nw["t"]), 3),
        "se_hac_ann": se_hac * ann,
        "se_iid_ann": se_iid * ann,
        "mde_ann": MDE_Z * max(se_hac, se_iid) * ann,
        "n": n, "hac_lags": lags,
    }


def rnd(d, k=5):
    if isinstance(d, dict):
        return {a: rnd(b, k) for a, b in d.items()}
    if isinstance(d, float):
        return round(d, k) if np.isfinite(d) else None
    return d


# ── H1: the decision boundary, read off the traded book ─────────────────────

def h1_events(holdings: list[dict], ret: pd.DataFrame, h: int) -> pd.DataFrame:
    """One row per rebalance with both entrants and (decision) leavers.

    Returns the h-month EW compounded return of the entrants minus that of the
    incumbents they replaced, paired within the same rebalance. Missing months
    after a delisting compound at 0 — the engine's own stub convention, applied
    identically to both legs so it cannot favour either.
    """
    months = ret.index
    rows = []
    for prev, cur in zip(holdings, holdings[1:]):
        if not cur["rebalanced"]:
            continue
        test_m = cur["test"]
        prev_names = set(prev["weights"].index)
        cur_names = set(cur["weights"].index)
        entrants = sorted(cur_names - prev_names)
        leavers = sorted(prev_names - cur_names)
        realized = ret.loc[test_m]
        leavers = [x for x in leavers if pd.notna(realized.get(x))]
        if not entrants or not leavers:
            continue
        pos = months.get_loc(test_m)
        if pos + h > len(months):
            continue                      # partial forward window: dropped
        sub = ret.loc[months[pos:pos + h]]

        def comp(names: list) -> float:
            r = sub[names].fillna(0.0)
            return float(((1.0 + r).prod() - 1.0).mean())

        re_, ri = comp(entrants), comp(leavers)
        rows.append({"month": test_m, "n_entrants": len(entrants),
                     "n_leavers": len(leavers), "r_entrant": re_,
                     "r_incumbent": ri, "diff": re_ - ri})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("month")


# ── G7 plumbing ─────────────────────────────────────────────────────────────

def targets_from(holdings: list[dict], timing: str) -> list[dict]:
    """Monthly-harness holdings -> daily-sim targets (trade months only)."""
    tg = []
    for h in holdings:
        if not h.get("rebalanced"):
            continue
        w = h["weights"].astype(float)
        w = w[w > 0]
        if not len(w):
            continue
        if timing == "formation_plus_1":
            eff = (pd.Timestamp(h["formation"]) + pd.Timedelta(days=1)).normalize()
        elif timing == "test_monthend":   # the sibling script's convention
            eff = pd.Timestamp(h["test"]).normalize()
        else:
            raise ValueError(timing)
        wi = w.copy()
        wi.index = [int(x) for x in wi.index]
        tg.append({"effective": eff, "weights": wi})
    return tg


def slice_daily(data: DailyData, permnos: set[int]) -> DailyData:
    cols = [p for p in data.ret.columns if int(p) in permnos]
    return DailyData(
        ret=data.ret[cols], prc=data.prc[cols], opn=data.opn[cols],
        dvol=data.dvol[cols], half_spread=data.half_spread[cols],
        rf=data.rf,
        delist_ret={p: v for p, v in data.delist_ret.items() if p in permnos})


def g7_monthly(nav: pd.Series, start_nav: float) -> pd.Series:
    """Daily NAV -> monthly return series including the first (cash) month."""
    me = nav.resample("ME").last()
    seed = pd.Series([start_nav], index=[me.index[0] - pd.offsets.MonthEnd(1)])
    return pd.concat([seed, me]).pct_change().dropna()


def g7_block(name: str, targets: list[dict], data: DailyData,
             mkt: pd.Series, years: float) -> tuple[dict, pd.Series]:
    cfg = SimConfig(start_nav=1_000_000.0)          # impact_coef=0 -> G7
    sim = simulate(targets, data, cfg)
    nav = sim["nav"]
    nav.to_frame("nav").to_csv(OUT / f"g7_nav_{name}.csv")
    mret = g7_monthly(nav, cfg.start_nav)
    b = mkt.reindex(mret.index)
    if b.isna().any():
        raise RuntimeError(f"{name}: benchmark has gaps over the G7 window")
    excess = mret - b
    diag = sim["diag"]
    mean_nav = float(nav.mean())
    block = {
        "execution_model": diag["execution_model"],
        "months": int(len(mret)),
        "cagr_net": annualize(mret),
        "benchmark_cagr": annualize(b),
        "excess_cagr_net": annualize(mret) - annualize(b),
        "power": _power_block(excess),
        "regimes_gate": _regime_table(mret, b, GATE_BLOCKS),
        "turnover_1way_annual_g7": (diag["turnover_dollars"] / 2.0
                                    / mean_nav / years),
        "cost_bps_of_traded": diag["cost_bps_of_traded"],
        "max_drawdown_daily": diag["max_drawdown_daily"],
        "max_drawdown_monthend": diag["max_drawdown_monthend"],
        "days_with_capped_orders": diag["days_with_capped_orders"],
        "delistings_handled": diag["delistings_handled"],
        "stale_liquidations": diag["stale_liquidations"],
        "final_nav": diag["final_nav"],
    }
    mret.to_frame("g7_net").assign(bench=b, excess=excess).to_csv(
        OUT / f"g7_monthly_{name}.csv")
    return block, mret


# ── the frozen decision rule, verbatim from the prereg ──────────────────────

def cell_verdict(h1: dict | None, h2: dict) -> dict:
    p = h2["power"]
    eff = p.get("arithmetic_excess_annual")
    mde = p.get("mde_80pct_power_annual")
    se_hac = p.get("se_annual_hac", float("nan"))
    sm = h2["regimes_gate"].get("_summary", {})
    pos, ev = sm.get("blocks_positive_excess", 0), sm.get("blocks_evaluated", 0)
    h2_pass = bool(eff is not None and mde is not None and eff > 0
                   and eff >= mde and pos >= 4)
    h1_pass = bool(h1 is not None and np.isfinite(h1.get("mean_ann", np.nan))
                   and h1["mean_ann"] > 0)
    upper95 = (eff + SIG_Z * se_hac) if eff is not None else float("nan")
    if h2_pass and not h1_pass:
        v = "VOID"
        why = ("H1 failed while H2 passed — a book cannot earn from a boundary "
               "that does not exist; the run is investigated, not reported")
    elif h2_pass:
        v = "CANDIDATE"
        why = (f"net excess {100*eff:+.2f}%/yr >= its own MDE {100*mde:.2f} and "
               f"{pos}/{ev} regime blocks positive — eligible for a forward "
               f"shadow lane, ATTENDED decision only")
    elif eff is not None and eff > 0:
        v = "UNRESOLVED"
        why = (f"net excess {100*eff:+.2f}%/yr below its own MDE {100*mde:.2f} "
               f"— absence of evidence, NOT a kill (§19). No lane.")
    elif np.isfinite(upper95) and upper95 < ECON_THRESHOLD_ANN:
        v = "NET_DEAD"
        why = (f"net excess {100*eff:+.2f}%/yr <= 0 and the whole 95% interval "
               f"(upper {100*upper95:+.2f}) sits below the economic threshold "
               f"+{100*ECON_THRESHOLD_ANN:.0f}%/yr — the information cannot be "
               f"collected long-only at this turnover")
    else:
        v = "UNRESOLVED"
        why = (f"net excess {100*eff:+.2f}%/yr, but the 95% interval reaches "
               f"{100*upper95:+.2f}%/yr — an economically interesting effect "
               f"is not ruled out (§19)")
    return {"verdict": v, "why": why, "h1_pass": h1_pass, "h2_pass": h2_pass,
            "regime_blocks_positive": pos, "regime_blocks_evaluated": ev,
            "upper95_on_net_excess_ann": (round(upper95, 5)
                                          if np.isfinite(upper95) else None)}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    years = 21.0                                 # 2002-01..2022-12

    fac = Factory(FIRST, LAST, out_dir=OUT)
    panel = fac.spine.panel
    ret = panel.monthly_ret
    mkt, rf = fac.spine.mkt, fac.spine.rf
    elig = fac.eligible("small")                 # SAME universe as REVINFO-1
    frames = fac.lib._ibes()
    if SIGNAL not in frames or CORPSE not in frames:
        raise RuntimeError("IBES panel lacks a registered arm — refusing")

    # ── monthly-harness books (reference + holdings for H1/G7) ──────────────
    books: dict[str, dict] = {}

    def build_book(name: str, score: pd.DataFrame, spec: StrategySpec) -> dict:
        holdings: list[dict] = []
        out = run_book(panel, score, elig, spec, rf, holdings_out=holdings)
        net = out["monthly"]["net"].dropna()
        b = mkt.reindex(net.index)
        entry = {
            "spec": spec.as_dict(), "diag": out["diag"], "holdings": holdings,
            "monthly_net": net,
            "monthly_reference": {
                "months": int(len(net)),
                "cagr_net": annualize(net),
                "excess_cagr_net": annualize(net) - annualize(b),
                "gross_cagr": annualize(out["monthly"]["gross"].dropna()),
                "excess_cagr_gross": (annualize(out["monthly"]["gross"].dropna())
                                      - annualize(b)),
                "turnover_1way_annual": out["diag"]["turnover_1way_annual"],
                "cost_model": spec.cost_model,
            },
        }
        net.to_frame("net").to_csv(OUT / f"monthly_{name}.csv")
        print(f"  {name}: monthly net excess "
              f"{100*entry['monthly_reference']['excess_cagr_net']:+.2f}%/yr, "
              f"turnover {out['diag']['turnover_1way_annual']}x", flush=True)
        return entry

    sig_score, sig_diag = composite_score(fac.lib, ((SIGNAL, 1.0),), elig)
    for n in SIZES:
        for c in CLOCKS:
            name = f"eps_rev_breadth_small_n{n}_m{c}"
            spec = StrategySpec(
                name=f"REVINFO2_{name}", signals=((SIGNAL, 1.0),),
                segment="small", top_n=n, rebalance_months=c,
                cost_model="flat25", first_month=FIRST, last_month=LAST,
                family="REVINFO-2",
                hypothesis="H1/H2/H3 per TRIALS/PREREG_REVINFO_2_LAYER2.md")
            books[name] = build_book(name, sig_score, spec)

    # corpse tail-concentrated arm: the construction that killed it (top-50 1m)
    corpse_score, _ = composite_score(fac.lib, ((CORPSE, 1.0),), elig)
    corpse_spec = StrategySpec(
        name="REVINFO2_control_tgt_upside_n50_m1", signals=((CORPSE, 1.0),),
        segment="small", top_n=50, rebalance_months=1, cost_model="flat25",
        first_month=FIRST, last_month=LAST, family="REVINFO-2",
        hypothesis="CONTROL: PERVERSE/CLOSED corpse, must come back negative")
    books["control_tgt_upside_n50_m1"] = build_book(
        "control_tgt_upside_n50_m1", corpse_score, corpse_spec)

    # noise control, turnover-matched to the n50 m1 signal book
    target_turn = books["eps_rev_breadth_small_n50_m1"]["diag"][
        "turnover_1way_annual"]
    noise_spec = StrategySpec(
        name="REVINFO2_control_noise_n50_m1", signals=(("noise:rng", 1.0),),
        segment="small", top_n=50, rebalance_months=1, cost_model="flat25",
        first_month=FIRST, last_month=LAST, family="REVINFO-2", seed=NOISE_SEED,
        hypothesis="CONTROL: pure noise, must earn ~nothing")
    print("matching noise rho to signal turnover "
          f"{target_turn}x ...", flush=True)
    rho = match_rho(panel, elig, noise_spec, rf, None, target_turn)
    noise_score = random_score(panel, seed=NOISE_SEED, rho=rho)
    books["control_noise_n50_m1"] = build_book(
        "control_noise_n50_m1", noise_score, noise_spec)
    books["control_noise_n50_m1"]["noise_rho"] = rho

    # ── H1 per signal cell ──────────────────────────────────────────────────
    h1_out: dict[str, dict] = {}
    for n in SIZES:
        for c in CLOCKS:
            name = f"eps_rev_breadth_small_n{n}_m{c}"
            ev = h1_events(books[name]["holdings"], ret, c)
            if ev.empty:
                h1_out[name] = {"status": "NO_EVENTS"}
                continue
            ev.to_csv(OUT / f"h1_events_{name}.csv")
            st = series_stats(ev["diff"], lags=max(2, 12 // c), ann=12.0 / c)
            st.update({
                "n_events": int(len(ev)),
                "mean_entrants_per_event": round(float(ev["n_entrants"].mean()), 1),
                "mean_leavers_per_event": round(float(ev["n_leavers"].mean()), 1),
                "estimator": ("paired per-rebalance EW difference, h-month "
                              "compounded, Newey-West on the event series; "
                              "MDE = 2.8 x max(HAC, IID) (§18/§19)"),
            })
            h1_out[name] = st
            print(f"  H1 {name}: {100*st['mean_ann']:+.2f}%/yr "
                  f"(MDE {100*st['mde_ann']:.2f}, t {st['t']}, "
                  f"{st['n_events']} events)", flush=True)

    # ── daily spine, loaded ONCE over the union, truncated at the holdout ───
    all_targets: dict[str, list[dict]] = {}
    for name, bk in books.items():
        all_targets[name] = targets_from(bk["holdings"], "formation_plus_1")
    all_targets["eps_rev_breadth_small_n50_m1__sib_timing"] = targets_from(
        books["eps_rev_breadth_small_n50_m1"]["holdings"], "test_monthend")

    union: set[int] = set()
    for tg in all_targets.values():
        for t in tg:
            union |= set(int(x) for x in t["weights"].index)
    print(f"loading daily spine {DAILY_FIRST}..{DAILY_LAST} for "
          f"{len(union)} permnos ...", flush=True)
    data = load_daily(DAILY_FIRST, DAILY_LAST, permnos=union)
    print(f"daily: {data.ret.shape[0]} days x {data.ret.shape[1]} names, "
          f"{len(data.delist_ret)} delistings", flush=True)

    g7_out: dict[str, dict] = {}
    g7_mret: dict[str, pd.Series] = {}
    for name, tg in all_targets.items():
        if not tg:
            g7_out[name] = {"status": "NO_TARGETS"}
            continue
        perms = set()
        for t in tg:
            perms |= set(int(x) for x in t["weights"].index)
        blk, mret = g7_block(name, tg, slice_daily(data, perms), mkt, years)
        g7_out[name] = blk
        g7_mret[name] = mret
        p = blk["power"]
        sm = blk["regimes_gate"].get("_summary", {})
        print(f"  G7 {name}: net excess {100*blk['excess_cagr_net']:+.2f}%/yr "
              f"(arith {100*p.get('arithmetic_excess_annual', float('nan')):+.2f}, "
              f"MDE {100*p.get('mde_80pct_power_annual', float('nan')):.2f}, "
              f"t {p.get('t_newey_west')}), blocks "
              f"{sm.get('blocks_positive_excess')}/{sm.get('blocks_evaluated')}, "
              f"turnover {blk['turnover_1way_annual_g7']:.2f}x", flush=True)

    # ── H3: adjacent-frequency differences, each with its own SE ────────────
    h3_out: dict[str, dict] = {}
    for n in SIZES:
        for lo, hi in ((1, 3), (3, 6)):
            a = g7_mret.get(f"eps_rev_breadth_small_n{n}_m{lo}")
            b = g7_mret.get(f"eps_rev_breadth_small_n{n}_m{hi}")
            if a is None or b is None:
                continue
            common = a.index.intersection(b.index)
            d = (b.reindex(common) - a.reindex(common)).dropna()
            st = series_stats(d, lags=12, ann=12.0)
            st["geometric_cagr_diff"] = (annualize(b.reindex(common))
                                         - annualize(a.reindex(common)))
            st["direction_registered"] = "positive (longer holding improves net)"
            h3_out[f"n{n}_m{hi}_minus_m{lo}"] = st
            print(f"  H3 n{n} m{hi}-m{lo}: {100*st['mean_ann']:+.2f}%/yr "
                  f"(MDE {100*st['mde_ann']:.2f}, t {st['t']})", flush=True)

    # ── controls ────────────────────────────────────────────────────────────
    xs = cross_sectional_information(
        frames[CORPSE], ret, eligible=elig, horizon=1,
        name=f"{CORPSE}|small|h1")
    corpse_ref = books["control_tgt_upside_n50_m1"]["monthly_reference"]
    corpse_g7 = g7_out.get("control_tgt_upside_n50_m1", {})
    noise_ref = books["control_noise_n50_m1"]["monthly_reference"]
    noise_g7 = g7_out.get("control_noise_n50_m1", {})
    controls = {
        "corpse_cross_sectional": {
            "spread_ann": xs.long_short_spread_ann,
            "mde_ann": xs.long_short_spread_mde_ann,
            "t": xs.long_short_spread_t,
            "negative_sign_reproduced": bool(xs.long_short_spread_ann <= 0),
            "note": ("REVINFO-1 measured -0.16%/yr here; the corpse's "
                     "perversity lives in the tail, which is why the "
                     "tail-concentrated arm exists (NIGHT-11 standing rule)"),
        },
        "corpse_tail_concentrated": {
            "monthly_gross_excess_ann": corpse_ref["excess_cagr_gross"],
            "monthly_net_excess_ann": corpse_ref["excess_cagr_net"],
            "g7_net_excess_ann": corpse_g7.get("excess_cagr_net"),
            "g7_power": corpse_g7.get("power"),
            "negative_sign_reproduced": bool(
                corpse_ref["excess_cagr_gross"] <= 0
                and (corpse_g7.get("excess_cagr_net") or 0) <= 0),
            "prior": "ANALYST-IBES-1 small m1 flat25: -8.6%/yr net, gross negative",
        },
        "noise": {
            "rho": books["control_noise_n50_m1"]["noise_rho"],
            "seed": NOISE_SEED,
            "turnover_1way_annual": noise_ref["turnover_1way_annual"],
            "monthly_net_excess_ann": noise_ref["excess_cagr_net"],
            "g7_net_excess_ann": noise_g7.get("excess_cagr_net"),
            "g7_power": noise_g7.get("power"),
        },
    }

    # ── turnover receipts vs the 10x prior ──────────────────────────────────
    turnover = {"prior": TURNOVER_PRIOR, "cells": {}}
    for n in SIZES:
        for c in CLOCKS:
            name = f"eps_rev_breadth_small_n{n}_m{c}"
            turnover["cells"][name] = {
                "monthly_harness_1way_annual":
                    books[name]["diag"]["turnover_1way_annual"],
                "g7_1way_annual": g7_out[name]["turnover_1way_annual_g7"],
            }
    t50m1 = turnover["cells"]["eps_rev_breadth_small_n50_m1"][
        "monthly_harness_1way_annual"]
    turnover["n50_m1_vs_prior"] = {
        "measured": t50m1, "prior": TURNOVER_PRIOR["m1"],
        "ratio": round(t50m1 / TURNOVER_PRIOR["m1"], 3),
        "reading": ("same construction (top-50, band 3x, small, monthly) as "
                    "ANALYST-IBES-1 — a material shortfall vs the prior is a "
                    "bug until shown otherwise"),
    }

    # ── verdicts, frozen rule ───────────────────────────────────────────────
    cells = {}
    for n in SIZES:
        for c in CLOCKS:
            name = f"eps_rev_breadth_small_n{n}_m{c}"
            cells[name] = cell_verdict(h1_out.get(name), g7_out[name])
    vs = [c["verdict"] for c in cells.values()]
    if any(v == "VOID" for v in vs):
        trial_verdict = "VOID"
    elif any(v == "CANDIDATE" for v in vs):
        trial_verdict = "CANDIDATE (cell-level; attended decision only)"
    elif all(v == "NET_DEAD" for v in vs):
        trial_verdict = "NET_DEAD"
    else:
        trial_verdict = "UNRESOLVED"

    payload = {
        "trial": "REVINFO-2",
        "prereg": "TRIALS/PREREG_REVINFO_2_LAYER2.md @ 7409bff",
        "accrues_to_denominator": 1,
        "window": [FIRST, LAST],
        "daily_window": [DAILY_FIRST, DAILY_LAST],
        "holdout_read": False,
        "signal": SIGNAL, "segment": "small",
        "sizes": list(SIZES), "clocks_months": list(CLOCKS),
        "book_size_note": ("prereg says 50-100; BOTH sizes run and reported, "
                           "neither selected"),
        "target_timing": {
            "used": "formation month-end + 1 day (daily_sim's own contract)",
            "sibling_discrepancy": (
                "scripts/g7_daily_sim.py passes effective=test month-end, a "
                "~1-month implementation lag on a month-end-labelled panel; "
                "measured here as a sensitivity arm on n50 m1"),
        },
        "signal_coverage": sig_diag,
        "monthly_reference": {k: rnd(v["monthly_reference"])
                              for k, v in books.items()},
        "H1_decision_boundary": rnd(h1_out),
        "H2_g7": {k: rnd({kk: vv for kk, vv in v.items()})
                  for k, v in g7_out.items()},
        "H3_adjacent_frequency_differences": rnd(h3_out),
        "controls": rnd(controls),
        "turnover": rnd(turnover),
        "cell_verdicts": cells,
        "trial_verdict": trial_verdict,
        "expected_outcome_registered": "UNRESOLVED or NET_DEAD",
        "may_not_conclude": [
            "that REVINFO-1 is confirmed (Layer 2 cannot re-grade Layer 1)",
            "that ANALYST-IBES-1 is overturned (different construction/question)",
            "any money/Sharpe/skill claim (no forward record here)",
            "that a CANDIDATE seeds anything (Murat's decision alone)",
        ],
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "revinfo2.json").write_text(
        json.dumps(payload, indent=1, default=str), encoding="utf-8")

    print("=" * 72, flush=True)
    print(f"TRIAL VERDICT: {trial_verdict}", flush=True)
    for k, v in cells.items():
        print(f"  {k}: {v['verdict']}", flush=True)
    print(f"wrote {OUT / 'revinfo2.json'} ({payload['runtime_secs']}s)",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
