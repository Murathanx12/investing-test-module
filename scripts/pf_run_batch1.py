"""PF-1 CAMPAIGN — the six frozen strategies, their OAT grids, the placebo gates.

Pre-registration: TRIALS/PREREG_PF1_FACTORY.md (registered BEFORE this file
computed anything; registry rows PF-HARNESS-VALID + PF-1-FACTORY-BATCH).
Instrument calibration: runs/PF/VALIDATION.json (VERDICT PASS).

Phase A  48 strategy runs (6 bases x 8 one-at-a-time configurations)
Phase B  6 placebo bands (100 turnover-matched random books each)
Phase C  frozen decision rule -> WINNER / UNRESOLVED / FAILED + campaign summary

Writes incrementally to runs/PF/CAMPAIGN_PF1.json so a partial night still has
receipts. Nothing here seeds a lane, flips a flag, or reads the holdout.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.run import Factory
from aegis_brain.pf.spec import StrategySpec

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pf1")

OUT = MODULE_ROOT / "runs" / "PF" / "CAMPAIGN_PF1.json"
FIRST, LAST = "1963-07-31", "2022-12-31"
KO_FIRST = "2002-01-31"          # KO cost frame coverage starts here
PLACEBO_DRAWS = 100

ENGINE_SIGNALS = (("osap:GP", 1.0), ("osap:BM", 1.0), ("native:mom_12_1", 1.0),
                  ("native:vol_12m_low", 0.5), ("native:max_ret_low", 0.5))

BASES: list[StrategySpec] = [
    StrategySpec(
        name="PF-GP-SMALL", signals=(("osap:GP", 1.0),), segment="small",
        top_n=25, first_month=FIRST, last_month=LAST,
        hypothesis="Novy-Marx gross profitability earns a premium concentrated "
                   "in small caps; a 25-name book keeps >=3%/yr net of 25bps.",
        family="PF-1"),
    StrategySpec(
        name="PF-PROF-COMPOSITE",
        signals=(("osap:GP", 1.0), ("osap:OperProfRD", 1.0),
                 ("osap:CBOperProf", 1.0)),
        segment="small", top_n=25, first_month=FIRST, last_month=LAST,
        hypothesis="Averaging three profitability measures cancels accounting "
                   "noise; era receipts show CBOperProf net t 4.30 (1985-2001).",
        family="PF-1"),
    StrategySpec(
        name="PF-ENGINE-ALPHA", signals=ENGINE_SIGNALS, segment="all",
        top_n=25, first_month=FIRST, last_month=LAST,
        hypothesis="The engine's composite (quality+value+momentum+low-vol+"
                   "lottery-aversion), panel-implementable proxy, picks stocks "
                   "that beat the market net of costs.",
        family="PF-1"),
    StrategySpec(
        name="PF-INSIDER-TILT",
        signals=(("insider:cluster12m", 1.0), ("osap:GP", 0.5)),
        segment="all", top_n=25, first_month="2007-01-31", last_month=LAST,
        hypothesis="Clustered opportunistic insider buying over a quality base "
                   "predicts returns; window-limited by the SEC bulk archive.",
        family="PF-1"),
    StrategySpec(
        name="PF-REGIME-SWITCH", signals=ENGINE_SIGNALS, segment="all",
        top_n=25, regime_rule="bull_risk_on", first_month=FIRST, last_month=LAST,
        hypothesis="Holding cash when the trailing year was negative improves "
                   "the engine composite. House prior: it does not.",
        family="PF-1"),
    StrategySpec(
        name="PF-RISK-SAT-1",
        signals=(("native:mom_12_1", 1.0), ("osap:GP", 0.5)),
        segment="all", top_n=10, max_weight=0.15, first_month=FIRST,
        last_month=LAST,
        hypothesis="A deliberately concentrated momentum+quality satellite "
                   "earns more excess return at materially higher ruin risk.",
        family="PF-1"),
]

OTHER_SEGMENTS = {"small": ("largemid", "all"), "largemid": ("small", "all"),
                  "all": ("small", "largemid")}


def oat_grid(base: StrategySpec) -> list[StrategySpec]:
    """The 8 frozen configurations: base + 7 one-at-a-time perturbations."""
    out = [base]
    out.append(base.variant(name=f"{base.name}__N10", top_n=10))
    out.append(base.variant(name=f"{base.name}__N50", top_n=50))
    out.append(base.variant(name=f"{base.name}__N150", top_n=150))
    out.append(base.variant(name=f"{base.name}__Q", rebalance_months=3))
    out.append(base.variant(name=f"{base.name}__KO", cost_model="ko",
                            first_month=max(base.first_month, KO_FIRST)))
    for seg in OTHER_SEGMENTS[base.segment]:
        out.append(base.variant(name=f"{base.name}__{seg}", segment=seg))
    return out


# ── frozen decision rule (PREREG §4) ────────────────────────────────────────
G1_MATERIAL = 0.03
G6_EX_BEST_YEAR = 0.015
G8_RUIN_MAX = 0.20
REGIME_MIN_POSITIVE = 4
GRID_MIN_POSITIVE = 6
MIN_YEARS_FOR_RESOLUTION = 15.0


def adjudicate(base_card: dict, grid_cards: list[dict],
               placebo: dict | None) -> dict:
    h = base_card["headline"]
    rb = base_card["robustness"]
    rg = base_card["regimes_gate"]["_summary"]
    tail = base_card.get("tail", {})
    yrs = base_card["window"]["years"]

    excess = h["excess_cagr_net"]
    grid_pos = sum(1 for c in grid_cards
                   if c["headline"]["excess_cagr_net"] > 0)
    checks = {
        "G1_material_excess_ge_3pct": bool(excess >= G1_MATERIAL),
        "G4_placebo_pass": (bool(placebo["PASS"]) if placebo else None),
        "G6_ex_best_year_ge_1.5pct": bool(
            rb["excess_cagr_ex_best_year"] >= G6_EX_BEST_YEAR),
        "G6_ex_top1pct_months_ge_0": bool(
            rb["excess_cagr_ex_top_1pct_months"] >= 0),
        "regime_blocks_ge_4_of_5": bool(
            rg["blocks_positive_excess"] >= REGIME_MIN_POSITIVE),
        "G3_grid_ge_6_of_8_positive": bool(grid_pos >= GRID_MIN_POSITIVE),
        "G8_ruin_le_20pct": bool(
            tail.get("p_maxdd_worse_than_60pct", 1.0) <= G8_RUIN_MAX),
    }
    reasons = [k for k, v in checks.items() if v is False]

    if placebo is not None and not placebo["PASS"]:
        verdict, cls = "FAILED", "placebo_gate"
    elif excess <= 0:
        verdict, cls = "FAILED", "negative_excess"
    elif not reasons:
        verdict, cls = "WINNER", ""
    elif yrs < MIN_YEARS_FOR_RESOLUTION:
        verdict, cls = "UNRESOLVED", "window_too_short"
    elif reasons == ["G1_material_excess_ge_3pct"] and excess > 0:
        verdict, cls = "UNRESOLVED", "positive_but_below_material_bar"
    else:
        verdict, cls = "FAILED", "+".join(reasons)

    return {"verdict": verdict, "reason_class": cls, "checks": checks,
            "excess_cagr_net": excess, "grid_positive": f"{grid_pos}/8",
            "years": yrs,
            "terminal_wealth_multiple_vs_benchmark":
                h["terminal_wealth_multiple_vs_benchmark"],
            "p_ruin_60pct": tail.get("p_maxdd_worse_than_60pct")}


def save(state: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def main() -> int:
    t0 = time.time()
    fac = Factory(first=FIRST, last=LAST)
    state: dict = {
        "campaign": "PF-1", "prereg": "TRIALS/PREREG_PF1_FACTORY.md",
        "instrument": "runs/PF/VALIDATION.json (PASS)",
        "provenance": fac.spine.provenance,
        "experiment_count": {"strategy_runs": 0, "placebo_books": 0},
        "runs": {}, "placebos": {}, "verdicts": {}, "errors": {},
    }
    grids: dict[str, list[dict]] = {}

    # ── Phase A ─────────────────────────────────────────────────────────────
    for base in BASES:
        grids[base.name] = []
        for spec in oat_grid(base):
            try:
                card = fac.run(spec, placebo_draws=0)
            except Exception as exc:                     # record, skip forward
                log.exception("%s failed", spec.name)
                state["errors"][spec.name] = f"{type(exc).__name__}: {exc}"
                save(state)
                continue
            grids[base.name].append(card)
            state["runs"][spec.name] = {
                "spec_hash": card["spec_hash"],
                "window": card["window"],
                "excess_cagr_net": card["headline"]["excess_cagr_net"],
                "cagr_net": card["headline"]["cagr_net"],
                "benchmark_cagr": card["headline"]["benchmark_cagr"],
                "t_excess": card["headline"]["t_excess_monthly"],
                "t_excess_nw": card["headline"]["t_excess_newey_west"],
                "max_dd": card["risk"]["max_drawdown"],
                "sharpe": card["risk"]["sharpe_net"],
                "turnover": card["implementation"]["turnover_1way_annual"],
                "terminal_wealth_x_bench":
                    card["headline"]["terminal_wealth_multiple_vs_benchmark"],
                "p_ruin_60": card.get("tail", {}).get("p_maxdd_worse_than_60pct"),
            }
            state["experiment_count"]["strategy_runs"] += 1
            save(state)
        log.info("=== %s grid done (%d/8) ===", base.name, len(grids[base.name]))

    # ── Phase B ─────────────────────────────────────────────────────────────
    from aegis_brain.pf import controls as ctrl
    for base in BASES:
        if not grids[base.name]:
            continue
        try:
            elig = fac.eligible(base.segment)
            cost_frame = fac.cost_frame() if base.cost_model == "ko" else None
            turnover = grids[base.name][0]["implementation"]["turnover_1way_annual"]
            band = ctrl.placebo_band(fac.spine.panel, elig, base, fac.spine.rf,
                                     cost_frame, fac.spine.mkt, turnover,
                                     n_draws=PLACEBO_DRAWS)
            verdict = ctrl.placebo_verdict(
                grids[base.name][0]["headline"]["excess_cagr_net"], band)
            state["placebos"][base.name] = {"band": band, "verdict": verdict}
            state["experiment_count"]["placebo_books"] += PLACEBO_DRAWS
            log.info("placebo %s: strategy %+.2f%% vs p95 %+.2f%% -> %s",
                     base.name, 100 * verdict["strategy_excess_cagr"],
                     100 * band["excess_cagr"]["p95"],
                     "PASS" if verdict["PASS"] else "FAIL")
        except Exception as exc:
            log.exception("placebo %s failed", base.name)
            state["errors"][f"placebo:{base.name}"] = f"{type(exc).__name__}: {exc}"
        save(state)

    # ── Phase C ─────────────────────────────────────────────────────────────
    for base in BASES:
        cards = grids.get(base.name) or []
        if not cards:
            continue
        pv = state["placebos"].get(base.name, {}).get("verdict")
        state["verdicts"][base.name] = adjudicate(cards[0], cards, pv)
        save(state)

    winners = [k for k, v in state["verdicts"].items() if v["verdict"] == "WINNER"]
    ranked = sorted(state["verdicts"].items(),
                    key=lambda kv: -(kv[1]["terminal_wealth_multiple_vs_benchmark"]
                                     or 0))
    state["summary"] = {
        "total_experiments": (state["experiment_count"]["strategy_runs"]
                              + state["experiment_count"]["placebo_books"]),
        "winners": winners,
        "unresolved": [k for k, v in state["verdicts"].items()
                       if v["verdict"] == "UNRESOLVED"],
        "failed": [k for k, v in state["verdicts"].items()
                   if v["verdict"] == "FAILED"],
        "ranked_by_excess_terminal_wealth": [
            {"name": k, "x_benchmark": v["terminal_wealth_multiple_vs_benchmark"],
             "excess_cagr": v["excess_cagr_net"], "p_ruin_60": v["p_ruin_60"],
             "verdict": v["verdict"]} for k, v in ranked],
        "runtime_secs": round(time.time() - t0, 1),
    }
    save(state)
    print(json.dumps(state["summary"], indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
