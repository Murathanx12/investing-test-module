"""PF-1 Phase C — apply the frozen decision rule, write the campaign receipt.

Reads the Phase A scorecards and the Phase B placebo bands from disk and
adjudicates with `pf_run_batch1.adjudicate` (the rule frozen in
TRIALS/PREREG_PF1_FACTORY.md §4 — this file does not restate or reinterpret
it). Prints the multiple-testing denominator, the WINNER / UNRESOLVED / FAILED
split, and the ranking by excess terminal wealth under the ruin constraint.

    python scripts/pf_finalize_batch1.py
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from scripts.pf_run_batch1 import BASES, PLACEBO_DRAWS, adjudicate, oat_grid

PF = MODULE_ROOT / "runs" / "PF"


def load_cards(base_name: str) -> list[dict]:
    """Base card first, then the rest of the grid (order matters: adjudicate
    reads grid_cards[0] as the base)."""
    out: dict[str, dict] = {}
    for p in glob.glob(str(PF / f"{base_name}*.json")):
        stem = Path(p).stem
        if stem.startswith("PLACEBO"):
            continue
        name = stem.rsplit("__", 1)[0]
        if name == base_name or name.startswith(base_name + "__"):
            out[name] = json.loads(Path(p).read_text(encoding="utf-8"))
    if base_name not in out:
        return []
    ordered = [out[s.name] for s in oat_grid(next(b for b in BASES
                                                 if b.name == base_name))
               if s.name in out]
    return ordered


def main() -> int:
    state: dict = {
        "campaign": "PF-1", "phase": "C (adjudication)",
        "prereg": "TRIALS/PREREG_PF1_FACTORY.md",
        "instrument": "runs/PF/VALIDATION.json (PASS)",
        "verdicts": {}, "placebo_missing": [], "runs": {},
    }
    n_runs = n_placebo = 0

    for base in BASES:
        cards = load_cards(base.name)
        if not cards:
            state["placebo_missing"].append(f"{base.name}: no Phase A cards")
            continue
        n_runs += len(cards)
        for c in cards:
            state["runs"][c["spec"]["name"]] = {
                "excess_cagr_net": c["headline"]["excess_cagr_net"],
                "t_excess": c["headline"]["t_excess_monthly"],
                "t_excess_nw": c["headline"]["t_excess_newey_west"],
                "years": c["window"]["years"],
                "max_dd": c["risk"]["max_drawdown"],
                "p_ruin_60": c.get("tail", {}).get("p_maxdd_worse_than_60pct"),
                "terminal_wealth_x_bench":
                    c["headline"]["terminal_wealth_multiple_vs_benchmark"],
            }
        pb_path = PF / f"PLACEBO_{base.name}.json"
        pv = None
        if pb_path.exists():
            pb = json.loads(pb_path.read_text(encoding="utf-8"))
            pv = pb["verdict"]
            state.setdefault("placebos", {})[base.name] = {
                "rho": pb["band"]["rho"],
                "placebo_turnover": pb["band"]["placebo_turnover_mean"],
                "strategy_turnover": pb["band"]["strategy_turnover"],
                "placebo_excess": pb["band"]["excess_cagr"],
                "verdict": pv}
            n_placebo += pb["band"]["n_draws"]
        else:
            state["placebo_missing"].append(base.name)
        state["verdicts"][base.name] = adjudicate(cards[0], cards, pv)
        if pv is None:
            state["verdicts"][base.name]["NOTE"] = (
                "placebo band not yet computed — the G4 hard gate is UNTESTED, "
                "so this verdict is PROVISIONAL")

    ranked = sorted(state["verdicts"].items(),
                    key=lambda kv: -(kv[1]["terminal_wealth_multiple_vs_benchmark"] or 0))
    state["summary"] = {
        "total_experiments": n_runs + n_placebo,
        "strategy_runs": n_runs, "placebo_books": n_placebo,
        "placebo_draws_per_strategy": PLACEBO_DRAWS,
        "winners": [k for k, v in state["verdicts"].items() if v["verdict"] == "WINNER"],
        "unresolved": [k for k, v in state["verdicts"].items() if v["verdict"] == "UNRESOLVED"],
        "failed": [k for k, v in state["verdicts"].items() if v["verdict"] == "FAILED"],
        "ranked_by_excess_terminal_wealth": [
            {"name": k, "x_benchmark": v["terminal_wealth_multiple_vs_benchmark"],
             "excess_cagr": v["excess_cagr_net"], "p_ruin_60": v["p_ruin_60pct"],
             "verdict": v["verdict"], "reason": v["reason_class"]}
            for k, v in ranked],
    }
    (PF / "CAMPAIGN_PF1_FINAL.json").write_text(
        json.dumps(state, indent=2, default=str), encoding="utf-8")
    print(json.dumps(state["summary"], indent=2, default=str))
    print("\nper-strategy checks:")
    for k, v in state["verdicts"].items():
        fails = [c for c, ok in v["checks"].items() if ok is False]
        print(f"  {k:<20} {v['verdict']:<11} grid {v['grid_positive']:<5} "
              f"failed: {fails if fails else '—'}")
    if state["placebo_missing"]:
        print(f"\nPLACEBO STILL MISSING (verdicts provisional): "
              f"{state['placebo_missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
