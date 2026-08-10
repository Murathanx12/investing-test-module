"""TRIAL-PF7-EXIT-SWEEP-1 — the exit layer, swept with the entry held fixed.

Registered in TRIALS/PREREG_PF7_EXIT_SWEEP.md, committed (a6abd30) BEFORE this
file was written. Every threshold lives in aegis_brain/pf/exits.py as a frozen
constant; nothing here chooses one.

Reconciliation first: A0 is run through the exit-rule code path AND through the
untouched banked path. If the two monthly series differ at all, the harness is
mis-wired and the script refuses to report any arm (prereg §6).
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.WARNING)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf import ledger as L
from aegis_brain.pf.engine import buy_and_hold_universe, run_book
from aegis_brain.pf.exits import build_arms
from aegis_brain.pf.panel63 import annualize, max_drawdown
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT7"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"

CLOCK = 12                 # annual — the shippable config (NIGHT-4/NIGHT-6)
T_BAR = 2.0                # frozen decision bar
MIN_EFFECT = 0.010         # +1.0%/yr, frozen
TURNOVER_G7_TOL = 0.10     # arms beyond this must go through G7 before quoting


def arm_row(f, base_d, arm_key, rule, era, elig, score, mom) -> dict:
    spec = StrategySpec(**{**base_d, "rebalance_months": CLOCK,
                           "cost_model": "ko",
                           "name": f"PF7-EXIT__{arm_key}"})
    out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
                   exit_rule=rule, mom=mom)
    m = out["monthly"]
    net, gross = m["net"].dropna(), m["gross"].dropna()
    bench = f.spine.mkt.reindex(net.index)
    return {
        "arm": arm_key, "label": rule.label, "spec_hash": spec.spec_hash(),
        "months": int(len(net)),
        "cagr_net": round(annualize(net), 4),
        "cagr_gross": round(annualize(gross), 4),
        "excess_cagr_net": round(annualize(net) - annualize(bench), 4),
        "excess_cagr_gross": round(annualize(gross) - annualize(bench), 4),
        "t_excess_nw": D.nw_t((net - bench).dropna()),
        "turnover_1way_annual": out["diag"]["turnover_1way_annual"],
        "cost_drag_annual_bps": out["diag"]["cost_drag_annual_bps"],
        "max_drawdown": round(max_drawdown(net), 4),
        "mean_n_held": out["diag"]["mean_n_held"],
        "rebalances": out["diag"]["rebalances"],
        "interim_exits": out["diag"].get("interim_exits"),
        "interim_exits_unreplaced": out["diag"].get("interim_exits_unreplaced"),
        "_net": net, "_gross": gross,
    }


def paired(arm: dict, base: dict) -> dict:
    """The primary statistic: paired monthly difference vs A0."""
    d = (arm["_net"] - base["_net"]).dropna()
    dg = (arm["_gross"] - base["_gross"]).dropna()
    ann = annualize(arm["_net"]) - annualize(base["_net"])
    t = D.nw_t(d)
    mde = D.mde_annualized(d, T_BAR)
    hit = (t is not None and abs(t) >= T_BAR and abs(ann) >= MIN_EFFECT
           and np.sign(ann) == np.sign(t))
    return {
        "paired_ann_diff_net": round(ann, 4),
        "paired_ann_diff_gross": round(
            annualize(arm["_gross"]) - annualize(base["_gross"]), 4),
        "paired_t_nw_net": t,
        "paired_t_nw_gross": D.nw_t(dg),
        "paired_mde_annualized": mde,
        "months_paired": int(len(d)),
        "corr_with_baseline": round(float(
            arm["_net"].corr(base["_net"])), 4),
        "verdict": "CONFIRMED_DIFFERENT" if hit else "UNRESOLVED",
        "why": ("paired |t| >= 2.0 and |effect| >= 1.0%/yr, same sign"
                if hit else
                f"|t|={abs(t) if t is not None else float('nan'):.2f} or "
                f"|effect|={abs(ann):.2%} below the frozen bar; this arm could "
                f"not have detected an effect smaller than {mde:.2%}/yr"),
    }


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()

    f = Factory()
    elig = f.eligible(d["segment"])
    score, _ = composite_score(f.lib, d["signals"], elig)
    era = D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())
    mom = f.lib.get("native:mom_12_1")

    arms = build_arms(top_n=d["top_n"], hold_band_mult=d["hold_band_mult"])

    # ── prereg §6 reconciliation: the exit code path must not move A0 ───────
    spec0 = StrategySpec(**{**d, "rebalance_months": CLOCK, "cost_model": "ko",
                            "name": "PF7-EXIT__A0_control"})
    ctrl_out = run_book(f.spine.panel, score, elig, spec0, f.spine.rf, era)
    base = arm_row(f, d, "A0_baseline", arms["A0_baseline"], era, elig, score, mom)
    ctrl_net = ctrl_out["monthly"]["net"].dropna()
    max_abs = float((base["_net"] - ctrl_net.reindex(base["_net"].index))
                    .abs().max())
    recon = {"max_abs_monthly_diff": max_abs,
             "months": int(len(ctrl_net)),
             "PASS": bool(max_abs == 0.0)}
    print(f"[recon] exit-path vs banked-path A0: max abs monthly diff "
          f"{max_abs:.2e} -> {'PASS' if recon['PASS'] else 'FAIL'}", flush=True)
    if not recon["PASS"]:
        (OUT / "T2_EXIT_SWEEP.json").write_text(json.dumps(
            {"trial": "TRIAL-PF7-EXIT-SWEEP-1", "VOID": True,
             "reason": "A0 reconciliation failed — the exit code path moves the "
                       "banked baseline, so no arm is interpretable (prereg §6)",
             "reconciliation": recon}, indent=2), encoding="utf-8")
        print("VOID — refusing to report arms on a mis-wired harness")
        return 1

    rows = [base]
    for k, rule in arms.items():
        if k == "A0_baseline":
            continue
        rows.append(arm_row(f, d, k, rule, era, elig, score, mom))
        r = rows[-1]
        print(f"  {k:22s} excess {r['excess_cagr_net']:+.4f}  "
              f"turn {r['turnover_1way_annual']:.3f}  "
              f"exits {r['interim_exits']}", flush=True)

    comp = {}
    for r in rows:
        if r["arm"] == "A0_baseline":
            continue
        p = paired(r, base)
        p["turnover_delta_vs_A0"] = round(
            r["turnover_1way_annual"] - base["turnover_1way_annual"], 4)
        p["needs_G7_before_quoting"] = bool(
            abs(p["turnover_delta_vs_A0"]) > TURNOVER_G7_TOL)
        p["g7_direction"] = (
            "monthly-panel net is an UPPER bound (arm trades more than A0; the "
            "monthly panel understates churn cost ~2.7x - NIGHT-6)"
            if p["turnover_delta_vs_A0"] > TURNOVER_G7_TOL else
            "monthly-panel net is a LOWER bound (arm trades less than A0)"
            if p["turnover_delta_vs_A0"] < -TURNOVER_G7_TOL else
            "turnover materially unchanged; no G7 gate")
        comp[r["arm"]] = p

    spread = (max(r["excess_cagr_net"] for r in rows)
              - min(r["excess_cagr_net"] for r in rows))
    ts = [c["paired_t_nw_net"] for c in comp.values() if c["paired_t_nw_net"]]

    res = {
        "trial": "TRIAL-PF7-EXIT-SWEEP-1",
        "prereg": "TRIALS/PREREG_PF7_EXIT_SWEEP.md",
        "prereg_commit": "a6abd30",
        "entry_held_fixed": {
            "book": "PF-PROF-COMPOSITE-150", "banked_hash": "a1265dc617fb",
            "clock_months": CLOCK, "segment": d["segment"], "top_n": d["top_n"],
            "cost_model": "era-appropriate (KO half-spread + tick floor)"},
        "reconciliation": recon,
        "decision_rule": {
            "primary": "paired monthly difference vs A0, Newey-West(12) t",
            "t_bar": T_BAR, "min_effect_annual": MIN_EFFECT,
            "turnover_g7_tolerance": TURNOVER_G7_TOL},
        "arms": [{k: v for k, v in r.items() if not k.startswith("_")}
                 for r in rows],
        "paired_vs_A0": comp,
        "spread_best_worst_excess_cagr": round(spread, 4),
        "max_abs_paired_t": round(max(abs(t) for t in ts), 3) if ts else None,
        "any_arm_confirmed": any(
            c["verdict"] == "CONFIRMED_DIFFERENT" for c in comp.values()),
        "multiple_testing": L.testing_block(
            max(r["t_excess_nw"] for r in rows if r["t_excess_nw"]), None),
        "branches_this_family": len(arms) + 1,
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "T2_EXIT_SWEEP.json").write_text(json.dumps(res, indent=2),
                                            encoding="utf-8")
    pd.DataFrame({r["arm"]: r["_net"] for r in rows}).to_csv(
        OUT / "T2_exit_arms_monthly.csv")
    print(json.dumps({"spread": res["spread_best_worst_excess_cagr"],
                      "max_abs_paired_t": res["max_abs_paired_t"],
                      "any_confirmed": res["any_arm_confirmed"],
                      "paired": {k: {kk: v[kk] for kk in
                                     ("paired_ann_diff_net", "paired_t_nw_net",
                                      "paired_mde_annualized", "verdict")}
                                 for k, v in comp.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
