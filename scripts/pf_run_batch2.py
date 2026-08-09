"""PF-2 CAMPAIGN — successors, the product track, and the meta-portfolio.

Pre-registration: TRIALS/PREREG_PF2_SUCCESSORS.md, committed BEFORE this file
computed anything. Governing rule: EXECUTION_STANDARD as amended 2026-08-09
(G4a factor gate, FACTOR-HARVEST PRODUCT, NEAR-MISS).

Phase V  re-validation: the ENGINE-ALPHA base must reproduce PF-1 exactly
Phase A  strategy grids (4 candidates x 8 configs) + product alternatives
Phase M  the meta-portfolio and its two controls
Phase B  placebo bands on the bases
Phase C  decision rule v2 -> verdicts + campaign summary

Nothing here seeds a lane, flips a flag, or reads the holdout.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import controls as ctrl
from aegis_brain.pf import meta as metamod
from aegis_brain.pf.run import Factory, write_artifacts
from aegis_brain.pf.scorecard import scorecard
from aegis_brain.pf.spec import StrategySpec

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pf2")

PF2_DIR = MODULE_ROOT / "runs" / "PF2"
OUT = PF2_DIR / "CAMPAIGN_PF2.json"
FIRST, LAST = "1963-07-31", "2022-12-31"
KO_FIRST = "2002-01-31"
PLACEBO_DRAWS = 100

# ── banked PF-1 numbers the re-validation must reproduce (PREREG §2.1) ───────
BANKED_ENGINE_ALPHA = {"excess_cagr_net": 0.0521, "t_excess_nw": 2.72,
                       "ff5_umd_t": 0.71}
REVALIDATION_TOL = 0.0002        # 2 bps on the CAGR; a regression stops the run

ENGINE_SIGNALS = (("osap:GP", 1.0), ("osap:BM", 1.0), ("native:mom_12_1", 1.0),
                  ("native:vol_12m_low", 0.5), ("native:max_ret_low", 0.5))
PROF_SIGNALS = (("osap:GP", 1.0), ("osap:OperProfRD", 1.0),
                ("osap:CBOperProf", 1.0))

# ── the four registered candidates (PREREG §3) ──────────────────────────────
ENGINE_ALPHA_2 = StrategySpec(
    name="PF-ENGINE-ALPHA-2", signals=ENGINE_SIGNALS, segment="all", top_n=25,
    first_month=FIRST, last_month=LAST, family="PF-2",
    hypothesis="The engine composite's regime hole can be closed by a CONSTANT "
               "market allocation rather than by timing. Registered question: "
               "does any construction hold >=+3%/yr AND >=4/5 regime blocks, "
               "and does any carry real FF5+UMD alpha?")

PROF_150 = StrategySpec(
    name="PF-PROF-COMPOSITE-150", signals=PROF_SIGNALS, segment="small",
    top_n=150, first_month=FIRST, last_month=LAST, family="PF-2",
    hypothesis="Breadth fixes PF-1 PROF-COMPOSITE's only failure (ruin 0.241). "
               "Registered as a pre-declared candidate, not a post-hoc rescue.")

INSIDER_2 = StrategySpec(
    name="PF-INSIDER-2-TIEAWARE",
    signals=(("insider:tieaware12m", 1.0), ("osap:GP", 0.5)),
    segment="all", top_n=25, first_month="2007-01-31", last_month=LAST,
    family="PF-2",
    hypothesis="PF-1's insider book ranked on a small-integer buyer count "
               "(14 distinct values in the top 100). A dollar-weighted, "
               "recency-decayed, size-scaled intensity breaks the ties. If it "
               "still fails, the family closes.")

# the product track's investable alternatives (PREREG §3.2)
ALTERNATIVES = [
    StrategySpec(name="ALT-VALUE-PROF",
                 signals=(("osap:BM", 1.0), ("osap:GP", 1.0)), segment="all",
                 top_n=150, first_month=FIRST, last_month=LAST, family="PF-2-ALT",
                 hypothesis="What a value+quality screen buys you."),
    StrategySpec(name="ALT-MULTIFACTOR",
                 signals=(("osap:BM", 1.0), ("osap:GP", 1.0),
                          ("native:mom_12_1", 1.0)),
                 segment="all", top_n=150, first_month=FIRST, last_month=LAST,
                 family="PF-2-ALT",
                 hypothesis="What a naive three-factor mix buys you."),
]


def grid_engine_alpha(b: StrategySpec) -> list[StrategySpec]:
    return [b,
            b.variant(name=f"{b.name}__blend25", blend_market=0.25),
            b.variant(name=f"{b.name}__blend40", blend_market=0.40),
            b.variant(name=f"{b.name}__blend50", blend_market=0.50),
            b.variant(name=f"{b.name}__N50", top_n=50),
            b.variant(name=f"{b.name}__N50blend40", top_n=50, blend_market=0.40),
            b.variant(name=f"{b.name}__largemid", segment="largemid"),
            b.variant(name=f"{b.name}__Q", rebalance_months=3)]


def grid_prof150(b: StrategySpec) -> list[StrategySpec]:
    return [b,
            b.variant(name=f"{b.name}__N100", top_n=100),
            b.variant(name=f"{b.name}__N200", top_n=200),
            b.variant(name=f"{b.name}__Q", rebalance_months=3),
            b.variant(name=f"{b.name}__KO", cost_model="ko",
                      first_month=KO_FIRST),
            b.variant(name=f"{b.name}__all", segment="all"),
            b.variant(name=f"{b.name}__largemid", segment="largemid"),
            b.variant(name=f"{b.name}__blend25", blend_market=0.25)]


def grid_insider2(b: StrategySpec) -> list[StrategySpec]:
    return [b,
            b.variant(name=f"{b.name}__N50", top_n=50),
            b.variant(name=f"{b.name}__N100", top_n=100),
            b.variant(name=f"{b.name}__Q", rebalance_months=3),
            b.variant(name=f"{b.name}__alone",
                      signals=(("insider:tieaware12m", 1.0),)),
            b.variant(name=f"{b.name}__largemid", segment="largemid"),
            b.variant(name=f"{b.name}__small", segment="small"),
            b.variant(name=f"{b.name}__blend25", blend_market=0.25)]


CANDIDATES = [(ENGINE_ALPHA_2, grid_engine_alpha),
              (PROF_150, grid_prof150),
              (INSIDER_2, grid_insider2)]

# ── PF-META-1 grid (PREREG §3.5) ────────────────────────────────────────────
META_GRID = [
    {"name": "PF-META-1", "lookback_months": 12, "hold_top": 1, "review_months": 1},
    {"name": "PF-META-1__L6T1", "lookback_months": 6, "hold_top": 1, "review_months": 1},
    {"name": "PF-META-1__L24T1", "lookback_months": 24, "hold_top": 1, "review_months": 1},
    {"name": "PF-META-1__L6T2", "lookback_months": 6, "hold_top": 2, "review_months": 1},
    {"name": "PF-META-1__L12T2", "lookback_months": 12, "hold_top": 2, "review_months": 1},
    {"name": "PF-META-1__L24T2", "lookback_months": 24, "hold_top": 2, "review_months": 1},
    {"name": "PF-META-1__L12T1Q", "lookback_months": 12, "hold_top": 1, "review_months": 3},
    {"name": "PF-META-1__L12T1_FREE", "lookback_months": 12, "hold_top": 1,
     "review_months": 1, "switch_bps": 0.0},
]

# the PF-1 bases, re-run to supply the meta-portfolio's assets
PF1_BASES = [
    StrategySpec(name="PF1-GP-SMALL", signals=(("osap:GP", 1.0),),
                 segment="small", top_n=25, first_month=FIRST, last_month=LAST,
                 family="PF-2-META-ASSET"),
    StrategySpec(name="PF1-PROF-COMPOSITE", signals=PROF_SIGNALS,
                 segment="small", top_n=25, first_month=FIRST, last_month=LAST,
                 family="PF-2-META-ASSET"),
    StrategySpec(name="PF1-ENGINE-ALPHA", signals=ENGINE_SIGNALS, segment="all",
                 top_n=25, first_month=FIRST, last_month=LAST,
                 family="PF-2-META-ASSET"),
    StrategySpec(name="PF1-INSIDER-TILT",
                 signals=(("insider:cluster12m", 1.0), ("osap:GP", 0.5)),
                 segment="all", top_n=25, first_month="2007-01-31",
                 last_month=LAST, family="PF-2-META-ASSET"),
    StrategySpec(name="PF1-REGIME-SWITCH", signals=ENGINE_SIGNALS, segment="all",
                 top_n=25, regime_rule="bull_risk_on", first_month=FIRST,
                 last_month=LAST, family="PF-2-META-ASSET"),
    StrategySpec(name="PF1-RISK-SAT-1",
                 signals=(("native:mom_12_1", 1.0), ("osap:GP", 0.5)),
                 segment="all", top_n=10, max_weight=0.15, first_month=FIRST,
                 last_month=LAST, family="PF-2-META-ASSET"),
]

# ── frozen decision rule v2 (PREREG §5) ─────────────────────────────────────
G1_MATERIAL = 0.03
G4A_ALPHA = 0.02
G4A_T = 2.0
G6_EX_BEST_YEAR = 0.015
G8_RUIN_MAX = 0.20
REGIME_MIN_POSITIVE = 4
GRID_MIN_POSITIVE = 6
MIN_YEARS_FOR_RESOLUTION = 15.0


def adjudicate_v2(base_card: dict, grid_cards: list[dict],
                  placebo: dict | None, product_pass: bool | None = None) -> dict:
    h, rb = base_card["headline"], base_card["robustness"]
    rg = base_card["regimes_gate"]["_summary"]
    tail = base_card.get("tail", {})
    fa = (base_card.get("factor_alpha") or {}).get("ff5_umd") or {}
    yrs = base_card["window"]["years"]
    excess = h["excess_cagr_net"]
    grid_pos = sum(1 for c in grid_cards if c["headline"]["excess_cagr_net"] > 0)

    g4a = bool(fa.get("ann_alpha", -1) >= G4A_ALPHA and fa.get("t_alpha", 0) >= G4A_T)
    checks = {
        "G1_material_excess_ge_3pct": bool(excess >= G1_MATERIAL),
        "G3_grid_ge_6_of_8_positive": bool(grid_pos >= GRID_MIN_POSITIVE),
        "G4_placebo_pass": (bool(placebo["PASS"]) if placebo else None),
        "G4a_factor_alpha": g4a,
        "G6_ex_best_year_ge_1.5pct": bool(
            rb["excess_cagr_ex_best_year"] >= G6_EX_BEST_YEAR),
        "G6_ex_top1pct_months_ge_0": bool(
            rb["excess_cagr_ex_top_1pct_months"] >= 0),
        "regime_blocks_ge_4_of_5": bool(
            rg["blocks_positive_excess"] >= REGIME_MIN_POSITIVE),
        "G8_ruin_le_20pct": bool(
            tail.get("p_maxdd_worse_than_60pct", 1.0) <= G8_RUIN_MAX),
    }
    failed = [k for k, v in checks.items() if v is False]

    provisional = placebo is None
    if placebo is not None and not placebo["PASS"]:
        verdict, cls = "FAILED", "placebo_gate"
    elif excess <= 0:
        verdict, cls = "FAILED", "negative_excess"
    elif not failed:
        verdict, cls = "WINNER (ENGINE SKILL)", ""
    elif failed == ["G4a_factor_alpha"]:
        # every gate but the factor gate: a product, if it also beats what a
        # person could actually buy instead
        if product_pass:
            verdict, cls = "WINNER (FACTOR-HARVEST PRODUCT)", "no_engine_alpha"
        elif product_pass is None:
            verdict, cls = "NEAR-MISS(G4a_factor_alpha)", "product_bar_not_tested"
        else:
            verdict, cls = "NEAR-MISS(G4a_factor_alpha)", "lost_to_investable_alternatives"
    elif len(failed) == 1:
        verdict, cls = f"NEAR-MISS({failed[0]})", "single_gate"
    elif yrs < MIN_YEARS_FOR_RESOLUTION:
        verdict, cls = "UNRESOLVED", "window_too_short"
    elif failed == ["G1_material_excess_ge_3pct"] and excess > 0:
        verdict, cls = "UNRESOLVED", "positive_but_below_material_bar"
    else:
        verdict, cls = "FAILED", "+".join(failed)

    if provisional and not verdict.startswith("FAILED"):
        # the placebo gate is HARD; an untested hard gate cannot yield a
        # graduation, only a provisional reading
        verdict = f"PROVISIONAL[{verdict}]"
        cls = (cls + "|placebo_untested").strip("|")

    return {"verdict": verdict, "reason_class": cls, "checks": checks,
            "failed_gates": failed, "excess_cagr_net": excess,
            "grid_positive": f"{grid_pos}/{len(grid_cards)}", "years": yrs,
            "ff5_umd_alpha": fa.get("ann_alpha"), "ff5_umd_t": fa.get("t_alpha"),
            "terminal_wealth_multiple_vs_benchmark":
                h["terminal_wealth_multiple_vs_benchmark"],
            "p_ruin_60pct": tail.get("p_maxdd_worse_than_60pct")}


def save(state: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def _slim(card: dict) -> dict:
    fa = (card.get("factor_alpha") or {}).get("ff5_umd") or {}
    return {
        "spec_hash": card["spec_hash"], "window": card["window"],
        "excess_cagr_net": card["headline"]["excess_cagr_net"],
        "cagr_net": card["headline"]["cagr_net"],
        "t_excess_nw": card["headline"]["t_excess_newey_west"],
        "max_dd": card["risk"]["max_drawdown"],
        "sharpe": card["risk"]["sharpe_net"],
        "turnover": card["implementation"]["turnover_1way_annual"],
        "ff5_umd_alpha": fa.get("ann_alpha"), "ff5_umd_t": fa.get("t_alpha"),
        "regime_blocks": card["regimes_gate"]["_summary"],
        "p_ruin_60": card.get("tail", {}).get("p_maxdd_worse_than_60pct"),
        "terminal_wealth_x_bench":
            card["headline"]["terminal_wealth_multiple_vs_benchmark"],
    }


def main() -> int:
    t0 = time.time()
    skip_placebo = "--skip-placebo" in sys.argv
    fac = Factory(first=FIRST, last=LAST, out_dir=PF2_DIR)
    state: dict = {
        "campaign": "PF-2", "prereg": "TRIALS/PREREG_PF2_SUCCESSORS.md",
        "standard": "EXECUTION_STANDARD amended 2026-08-09 (001fa4d)",
        "provenance": fac.spine.provenance,
        "experiment_count": {"strategy_runs": 0, "placebo_books": 0,
                             "meta_runs": 0},
        "revalidation": {}, "runs": {}, "meta": {}, "placebos": {},
        "verdicts": {}, "errors": {},
    }
    grids: dict[str, list[dict]] = {}

    # ── Phase V — the harness must still reproduce PF-1 ──────────────────────
    log.info("=== Phase V: re-validation against banked PF-1 ===")
    rev = fac.run(PF1_BASES[2])                       # PF1-ENGINE-ALPHA
    d_excess = rev["headline"]["excess_cagr_net"] - BANKED_ENGINE_ALPHA["excess_cagr_net"]
    state["revalidation"] = {
        "banked": BANKED_ENGINE_ALPHA,
        "reproduced_excess_cagr_net": rev["headline"]["excess_cagr_net"],
        "delta": round(d_excess, 6),
        "reproduced_ff5_umd_t": rev["factor_alpha"]["ff5_umd"]["t_alpha"],
        "PASS": bool(abs(d_excess) <= REVALIDATION_TOL)}
    save(state)
    if not state["revalidation"]["PASS"]:
        log.error("RE-VALIDATION FAILED: excess %.4f vs banked %.4f (delta %.4f) "
                  "— the harness changed under PF-2's extensions. Stopping "
                  "rather than running a campaign on a drifted instrument.",
                  rev["headline"]["excess_cagr_net"],
                  BANKED_ENGINE_ALPHA["excess_cagr_net"], d_excess)
        return 2
    log.info("re-validation PASS (delta %.6f)", d_excess)

    # ── Phase A — candidate grids + product alternatives ─────────────────────
    for base, gridfn in CANDIDATES:
        grids[base.name] = []
        for spec in gridfn(base):
            try:
                card = fac.run(spec)
            except Exception as exc:
                log.exception("%s failed", spec.name)
                state["errors"][spec.name] = f"{type(exc).__name__}: {exc}"
                save(state)
                continue
            grids[base.name].append(card)
            state["runs"][spec.name] = _slim(card)
            state["experiment_count"]["strategy_runs"] += 1
            save(state)
        log.info("=== %s grid done (%d/8) ===", base.name, len(grids[base.name]))

    for alt in ALTERNATIVES:
        try:
            card = fac.run(alt)
            state["runs"][alt.name] = _slim(card)
            state["experiment_count"]["strategy_runs"] += 1
        except Exception as exc:
            log.exception("%s failed", alt.name)
            state["errors"][alt.name] = f"{type(exc).__name__}: {exc}"
        save(state)

    # ── Phase M — the meta-portfolio and its controls ────────────────────────
    log.info("=== Phase M: PF-META-1 ===")
    asset_rets: dict[str, pd.Series] = {}
    for spec in PF1_BASES:
        try:
            if spec.name not in fac._monthly:
                fac.run(spec)
                state["experiment_count"]["strategy_runs"] += 1
            asset_rets[spec.name] = fac._monthly[spec.name]["net"].astype(float)
        except Exception as exc:
            log.exception("meta asset %s failed", spec.name)
            state["errors"][f"meta-asset:{spec.name}"] = f"{type(exc).__name__}: {exc}"
    save(state)

    if len(asset_rets) >= 2:
        rets = pd.DataFrame(asset_rets).sort_index()
        state["meta"]["assets"] = {k: {"months": int(v.notna().sum())}
                                   for k, v in asset_rets.items()}
        books: dict[str, tuple] = {}
        for cfg in META_GRID:
            name = cfg["name"]
            kw = {k: v for k, v in cfg.items() if k != "name"}
            try:
                bk = metamod.meta_book(rets, **kw)
                books[name] = (bk, metamod.meta_diag(bk))
            except Exception as exc:
                log.exception("%s failed", name)
                state["errors"][name] = f"{type(exc).__name__}: {exc}"
        try:
            bk = metamod.equal_weight_book(rets)
            books["META-EW"] = (bk, metamod.meta_diag(bk))
        except Exception as exc:
            state["errors"]["META-EW"] = f"{type(exc).__name__}: {exc}"
        # BEST-SINGLE: hindsight-chosen, an unfair reference, never a gate
        tw = {c: float((1 + rets[c].dropna()).prod()) for c in rets.columns}
        best = max(tw, key=tw.get)
        state["meta"]["best_single_name"] = best
        try:
            bk = metamod.single_book(rets, best)
            books["META-BEST-SINGLE"] = (bk, metamod.meta_diag(bk))
        except Exception as exc:
            state["errors"]["META-BEST-SINGLE"] = f"{type(exc).__name__}: {exc}"

        for name, (bk, diag) in books.items():
            spec = StrategySpec(name=name, signals=(("meta:strategies", 1.0),),
                                segment="all", top_n=max(int(bk["n_held"].max()), 5),
                                first_month=str(bk.index.min().date()),
                                last_month=str(bk.index.max().date()),
                                family="PF-2-META",
                                hypothesis="Strategy-of-strategies. House "
                                           "prediction: loses to equal weight.")
            card = scorecard(bk, fac.spine.mkt, diag=diag,
                             spec_dict=spec.as_dict(), ew_universe=None,
                             factors=fac.factors, rf=fac.spine.rf, seed=spec.seed)
            card["spec_hash"] = spec.spec_hash()
            card["provenance"] = dict(fac.spine.provenance)
            card["meta_config"] = next((c for c in META_GRID
                                        if c["name"] == name), {"control": name})
            write_artifacts(spec, card, out_dir=PF2_DIR)
            state["meta"][name] = _slim(card) | {
                "strategy_switches": diag.get("strategy_switches"),
                "holding_share": diag.get("holding_share")}
            state["experiment_count"]["meta_runs"] += 1
            save(state)
            log.info("%-24s excess %+.2f%%/yr  ruin %.3f  switches %s", name,
                     100 * card["headline"]["excess_cagr_net"],
                     card.get("tail", {}).get("p_maxdd_worse_than_60pct", float("nan")),
                     diag.get("strategy_switches"))

    # ── Phase B — placebo bands on the three candidate bases ─────────────────
    log.info("=== Phase B: placebo bands ===")
    for base, _ in CANDIDATES:
        if skip_placebo:
            log.info("Phase B skipped (--skip-placebo) — run "
                     "scripts/pf_placebo2_one.py per base, then "
                     "scripts/pf_finalize_batch2.py")
            break
        if not grids.get(base.name):
            continue
        try:
            elig = fac.eligible(base.segment)
            cf = fac.cost_frame() if base.cost_model == "ko" else None
            turnover = grids[base.name][0]["implementation"]["turnover_1way_annual"]
            band = ctrl.placebo_band(fac.spine.panel, elig, base, fac.spine.rf,
                                     cf, fac.spine.mkt, turnover,
                                     n_draws=PLACEBO_DRAWS)
            verdict = ctrl.placebo_verdict(
                grids[base.name][0]["headline"]["excess_cagr_net"], band)
            state["placebos"][base.name] = {"band": band, "verdict": verdict}
            state["experiment_count"]["placebo_books"] += PLACEBO_DRAWS
            log.info("placebo %s: %+.2f%% vs p95 %+.2f%% -> %s", base.name,
                     100 * verdict["strategy_excess_cagr"],
                     100 * band["excess_cagr"]["p95"],
                     "PASS" if verdict["PASS"] else "FAIL")
        except Exception as exc:
            log.exception("placebo %s failed", base.name)
            state["errors"][f"placebo:{base.name}"] = f"{type(exc).__name__}: {exc}"
        save(state)

    # ── Phase C — decision rule v2 ───────────────────────────────────────────
    log.info("=== Phase C: adjudication ===")
    # the product bar (PREREG §3.2): beat every investable alternative on
    # excess terminal wealth, with ruin inside tolerance
    def product_bar(card: dict) -> dict | None:
        alts = {}
        for n in ("ALT-VALUE-PROF", "ALT-MULTIFACTOR"):
            if n in state["runs"]:
                alts[n] = state["runs"][n]["terminal_wealth_x_bench"]
        ewc = card.get("controls", {})
        if not alts or "ew_universe_cagr" not in ewc:
            return None
        yrs = card["window"]["years"]
        ew_x = ((1 + ewc["ew_universe_cagr"]) ** yrs) / (
            (1 + card["headline"]["benchmark_cagr"]) ** yrs)
        alts["ALT-EW-UNIVERSE"] = round(ew_x, 3)
        alts["BENCHMARK"] = 1.0
        mine = card["headline"]["terminal_wealth_multiple_vs_benchmark"]
        ruin = card.get("tail", {}).get("p_maxdd_worse_than_60pct", 1.0)
        beats = {k: bool(mine > v) for k, v in alts.items()}
        return {"candidate_x_bench": mine, "alternatives_x_bench": alts,
                "beats": beats, "ruin": ruin,
                "PASS": bool(all(beats.values()) and ruin <= G8_RUIN_MAX)}

    for base, _ in CANDIDATES:
        cards = grids.get(base.name) or []
        if not cards:
            continue
        pv = state["placebos"].get(base.name, {}).get("verdict")
        pb = None
        if base.name == "PF-ENGINE-ALPHA-2":
            pb = product_bar(cards[0])
            state["product_bar"] = pb
        state["verdicts"][base.name] = adjudicate_v2(
            cards[0], cards, pv, pb["PASS"] if pb else None)
        save(state)

    # META-1's verdict is a head-to-head, not the gate ladder
    if "PF-META-1" in state["meta"] and "META-EW" in state["meta"]:
        m, ew = state["meta"]["PF-META-1"], state["meta"]["META-EW"]
        best_cfg = max((c["name"] for c in META_GRID
                        if c["name"] in state["meta"]),
                       key=lambda n: state["meta"][n]["terminal_wealth_x_bench"])
        state["meta_verdict"] = {
            "prediction_P7": "PF-META-1 does NOT beat META-EW",
            "meta_excess_cagr": m["excess_cagr_net"],
            "ew_excess_cagr": ew["excess_cagr_net"],
            "meta_x_bench": m["terminal_wealth_x_bench"],
            "ew_x_bench": ew["terminal_wealth_x_bench"],
            "meta_beats_ew": bool(m["terminal_wealth_x_bench"] > ew["terminal_wealth_x_bench"]),
            "best_meta_config": best_cfg,
            "best_meta_x_bench": state["meta"][best_cfg]["terminal_wealth_x_bench"],
            "best_meta_beats_ew": bool(
                state["meta"][best_cfg]["terminal_wealth_x_bench"] > ew["terminal_wealth_x_bench"]),
            "best_single": state["meta"].get("best_single_name"),
            "best_single_x_bench": state["meta"].get("META-BEST-SINGLE", {}).get(
                "terminal_wealth_x_bench"),
        }
        save(state)

    ec = state["experiment_count"]
    state["summary"] = {
        "total_experiments": ec["strategy_runs"] + ec["placebo_books"] + ec["meta_runs"],
        **ec,
        "revalidation": state["revalidation"],
        "verdicts": {k: v["verdict"] for k, v in state["verdicts"].items()},
        "meta_verdict": state.get("meta_verdict"),
        "errors": state["errors"],
        "runtime_secs": round(time.time() - t0, 1),
    }
    save(state)
    print(json.dumps(state["summary"], indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
