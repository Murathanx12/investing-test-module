"""PF-2 Phase C — apply decision rule v2 once the placebo bands exist.

Reads the Phase A/M cards and the Phase B bands from disk and re-adjudicates
with `pf_run_batch2.adjudicate_v2` (the rule frozen in
TRIALS/PREREG_PF2_SUCCESSORS.md §5 — this file does not restate it). Prints the
multiple-testing denominator and the verdict split.

    python scripts/pf_finalize_batch2.py
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pf_run_batch2 import (CANDIDATES, G8_RUIN_MAX, META_GRID, OUT,
                                   PF2_DIR, adjudicate_v2)


def load_cards(base_name: str, gridfn) -> list[dict]:
    """Base card first, then the rest of the grid (adjudicate reads [0])."""
    out: dict[str, dict] = {}
    for p in glob.glob(str(PF2_DIR / f"{base_name}*.json")):
        stem = Path(p).stem
        if stem.startswith("PLACEBO") or stem.startswith("CAMPAIGN"):
            continue
        name = stem.rsplit("__", 1)[0]
        if name == base_name or name.startswith(base_name + "__"):
            out[name] = json.loads(Path(p).read_text(encoding="utf-8"))
    if base_name not in out:
        return []
    base = next(b for b, _ in CANDIDATES if b.name == base_name)
    return [out[s.name] for s in gridfn(base) if s.name in out]


def main() -> int:
    state = json.loads(OUT.read_text(encoding="utf-8"))
    state["phase"] = "C (final adjudication)"
    n_runs = n_placebo = 0

    for base, gridfn in CANDIDATES:
        cards = load_cards(base.name, gridfn)
        if not cards:
            state.setdefault("placebo_missing", []).append(
                f"{base.name}: no Phase A cards")
            continue
        n_runs += len(cards)
        pb_path = PF2_DIR / f"PLACEBO_{base.name}.json"
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
            state.setdefault("placebo_missing", []).append(base.name)
        pbar = state.get("product_bar") if base.name == "PF-ENGINE-ALPHA-2" else None
        state["verdicts"][base.name] = adjudicate_v2(
            cards[0], cards, pv, pbar["PASS"] if pbar else None)

    n_meta = len([k for k in state.get("meta", {})
                  if k in {c["name"] for c in META_GRID}
                  or k in ("META-EW", "META-BEST-SINGLE")])
    state["summary"] = (state.get("summary") or {}) | {
        "total_experiments": n_runs + n_placebo + n_meta,
        "strategy_runs": n_runs, "placebo_books": n_placebo, "meta_runs": n_meta,
        "verdicts": {k: v["verdict"] for k, v in state["verdicts"].items()},
        "meta_verdict": state.get("meta_verdict"),
        "ruin_tolerance": G8_RUIN_MAX,
    }
    (PF2_DIR / "CAMPAIGN_PF2_FINAL.json").write_text(
        json.dumps(state, indent=2, default=str), encoding="utf-8")

    print(json.dumps(state["summary"], indent=2, default=str))
    print("\nper-candidate checks:")
    for k, v in state["verdicts"].items():
        fails = v["failed_gates"] or "—"
        print(f"  {k:<26} {v['verdict']:<38} grid {v['grid_positive']:<6} "
              f"excess {v['excess_cagr_net']:+.2%}  "
              f"FF5+UMD a={v['ff5_umd_alpha']} t={v['ff5_umd_t']}  failed: {fails}")
    if state.get("placebo_missing"):
        print(f"\nPLACEBO MISSING (verdicts provisional): {state['placebo_missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
