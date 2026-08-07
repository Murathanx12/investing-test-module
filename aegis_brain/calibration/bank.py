"""RECAL-1 Stage 3' — the gate-agnostic evidence bank.

Same simulator, same injector, same production scans as the M1 grid; the ONE
change is what a rep file contains. M1 wrote the terminal state of the frozen
ladder, so every candidate ladder needed its own overnight. A bank rep writes
the SUFFICIENT STATISTICS for the whole ladder family:

  explore   : (t_net, t_ic, contaminated, months) for all 21 signals x 2
              segments — everything an explore gate, a ranking key or a
              top-N cap can ask
  confirm   : the injected candidate's held-out read (2019-01..2024-12) in
              BOTH segments and BOTH books (production 30% hold band, and the
              engineered 50% hold band = the implementation/turnover layer),
              summary + the monthly excess-net series
  pbo       : CSCV over the cell's own 42 explore books (ladder-independent)
  dsr       : deflated Sharpe of each confirm book at n_trials 42 and 179
  sr_var    : empirical cross-trial Sharpe variance and the floored value

Cost of the extra generality: 4 confirm scans per cell instead of at most 1,
i.e. 46 scans where M1 ran 42 — about +9%. In exchange every ladder in the
family is a pure function over the bank (ruleset.evaluate), so the ladder
search and its held-out validation cost zero additional compute and the
overnight grid runs exactly ONCE.

The bank is written under a --tag (default r1 -> bank_r1_NNNN.json). It never
reads or writes the frozen BRAIN-008 rep files (rep_*.json).

Run (via the chain, not directly):
  scripts\\run_recal_overnight.cmd [workers] [tag]
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import numpy as np

from aegis_brain.calibration.config import (
    INJECT_SEED_OFFSET,
    RHO_SIG_HEADLINE,
    RUNS_DIR,
    SEED_BASE,
    assert_production_constants,
)
from aegis_brain.calibration.inject import (
    build_injection_inputs,
    inject,
    injected_signal,
)
from aegis_brain.calibration.panel_gen import gen_null_panel
from aegis_brain.calibration.ruleset import (
    RULESETS,
    TERMINAL_STATES,
    Ruleset,
    evaluate,
)
from aegis_brain.calibration.run_grid import (
    GRID_DIR,
    INJECTED_NAME,
    _W,
    _init_worker,
    memoized_signals,
    perf_matrix_and_srvar,
    scan_segment,
    wilson,
)
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.discipline.overfitting import (
    deflated_sharpe_from_returns,
    probability_of_backtest_overfitting,
)
from aegis_brain.factory.batch1_price import BATCH1
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.signals import FactorySignal

SEGMENTS = ("largemid", "small")
N_TRIALS = (42, 179)

# The two implementation layers the adoption gate may read. "prod" is the
# frozen production book M1 measured. "eng" is the turnover-engineered book:
# the hold band widens 30% -> 50%, so incumbents are kept longer and the
# 25 bps cost is paid less often. COSTS ARE NOT A KNOB — cost_bps_one_way
# stays at the production 25 bps in both books; only the trading rule moves.
CONFIRM_BOOKS = {
    "prod": ScanConfig(first_test_month="2019-01-31",
                       last_test_month="2024-12-31"),
    "eng": ScanConfig(first_test_month="2019-01-31",
                      last_test_month="2024-12-31", hold_band_frac=0.50),
}

# Cells per wave. Wave 1 carries every RECAL-1 acceptance target (FDR from the
# alpha=0 base cell, primary power from I1 — the constant edge is the only
# design whose edge still EXISTS in the confirm window; see the spec). Wave 2
# is the design sweep. NOT the full M1 13-cell grid: I3/I4 at alpha=0.2 are
# dropped (both were 0-graduation cells under the old gate and are the least
# informative), which is logged here rather than silently truncated.
WAVES = {
    1: (("base", 0.0), ("I1", 0.2), ("I1", 0.4), ("I1", 0.6)),
    2: (("I2", 0.2), ("I2", 0.4), ("I2", 0.6),
        ("I3", 0.4), ("I3", 0.6), ("I4", 0.4), ("I4", 0.6)),
    # Wave 3 = NULL EXTENSION (run 2, spec delta S12). One cell per rep, so
    # extra null reps cost a quarter of a wave-1 rep. Run 1 measured FDR
    # 1.6% at n=250 with a Wilson upper of 5.65%: the posterior map's
    # non-monotonicity was driven by 0-vs-1 counts in the alpha=0 cell, and
    # the highest-power ladder was rejected on its Wilson bound alone.
    # Both are sample-size problems in exactly this one cell.
    #   --wave 3 --start 250 --reps 1000  ->  n = 1250 at alpha = 0
    3: (("base", 0.0),),
}
WAVES[0] = WAVES[1] + WAVES[2]


# ------------------------------------------------------------------ bank

def _explore_rec(scans: dict[str, dict]) -> dict:
    return {name: {"t_net": s["summary"]["t_excess_net"],
                   "t_ic": s["summary"]["t_ic"],
                   "contaminated": bool(s["summary"]["contaminated"]),
                   "months": s["summary"]["months"]}
            for name, s in scans.items()}


def bank_cell(panel: Panel, signals: list[FactorySignal],
              largemid: dict[str, dict], small: dict[str, dict]) -> dict:
    """Every statistic any ladder in the family can ask of one cell."""
    inj_sig = [s for s in signals if s.name == INJECTED_NAME][0]
    pm, srv = perf_matrix_and_srvar(largemid, small)
    pbo_rep = probability_of_backtest_overfitting(pm)
    if pbo_rep.get("pbo") is None or not np.isfinite(pbo_rep["pbo"]):
        raise RuntimeError(f"PBO not computable: {pbo_rep}")

    confirm: dict[str, dict] = {}
    dsr: dict[str, float] = {}
    for seg in SEGMENTS:
        for book, cfg in CONFIRM_BOOKS.items():
            res = scan_signal(panel, inj_sig, seg, cfg)
            s = res["summary"]
            ret = res["monthly"]["excess_net"].dropna().to_numpy()
            confirm[f"{seg}/{book}"] = {
                "t_net": s["t_excess_net"], "t_ic": s["t_ic"],
                "mean_excess_bps": s["mean_excess_net_bps"],
                "ic_mean": s["ic_mean"], "months": s["months"],
                "turnover_1way": s["turnover_1way"],
                "sharpe_excess_ann": round(
                    float(ret.mean() / ret.std(ddof=1) * np.sqrt(12)), 4)
                if ret.std(ddof=1) > 0 else 0.0,
                "excess_net": [round(float(x), 8) for x in ret],
            }
            for n in N_TRIALS:
                dsr[f"{seg}/{book}_{n}"] = deflated_sharpe_from_returns(
                    ret, n_trials=n, sr_variance=srv["sr_var_used"])["dsr"]

    return {
        "explore": {"largemid": _explore_rec(largemid),
                    "small": _explore_rec(small)},
        "confirm": confirm,
        "dsr": dsr,
        "pbo": round(float(pbo_rep["pbo"]), 4),
        **srv,
    }


def run_rep_bank(rep: int, rho: float, cells: tuple, tag: str) -> str:
    """Compute the cells of `cells` that this rep does not already hold, and
    merge them into its bank file.

    Idempotency is CELL-aware, not file-aware. The first RECAL-1 run lost a
    whole wave to the file-aware version: wave 2 saw the wave-1 file, reported
    "exists, skipped" for all 250 reps in 24 seconds, and exited 0 — green,
    silent, and empty. The M1 grid dodged this only by putting the wave in the
    filename. Merging is strictly better: it is idempotent AND it reuses the
    scans a previous wave already paid for.
    """
    out_path = GRID_DIR / f"bank_{tag}_{rep:04d}.json"
    existing: dict[str, dict] = {}
    if out_path.exists():
        prev = json.loads(out_path.read_text(encoding="utf-8"))
        if prev.get("schema") != "bank-v1":
            raise RuntimeError(f"{out_path.name}: schema {prev.get('schema')!r}")
        existing = prev["cells"]
    todo = [(d, a) for d, a in cells if f"a{a}/{d}" not in existing]
    if not todo:
        return (f"rep {rep} [{tag}]: all {len(cells)} cells present, skipped")

    t0 = time.time()
    inputs = _W["inputs"]
    panel_null = gen_null_panel(inputs, np.random.default_rng(SEED_BASE + rep))
    inj = build_injection_inputs(
        panel_null, rho,
        np.random.default_rng(SEED_BASE + INJECT_SEED_OFFSET + rep))

    out: dict[str, dict] = {}
    for design, alpha in todo:
        sigs = memoized_signals(BATCH1 + [injected_signal(inj)])
        if len(sigs) != 21:
            raise RuntimeError("candidate list must be 21 signals")
        pnl = (panel_null if design == "base"
               else inject(panel_null, inj, design, alpha))
        lm = scan_segment(pnl, sigs, "largemid")
        sm = scan_segment(pnl, sigs, "small")
        out[f"a{alpha}/{design}"] = bank_cell(pnl, sigs, lm, sm)

    merged = {**existing, **out}
    report = {
        "rep": rep, "rho": rho, "tag": tag,
        "seed_panel": SEED_BASE + rep,
        "seed_inject": SEED_BASE + INJECT_SEED_OFFSET + rep,
        "schema": "bank-v1",
        "cells": merged,
        "wall_seconds": round(time.time() - t0, 1),
    }
    GRID_DIR.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, default=str), encoding="utf-8")
    tmp.replace(out_path)
    return (f"rep {rep} [{tag}]: {round(time.time() - t0)}s "
            f"+{len(out)} cells ({len(merged)} total)")


# ------------------------------------------------------------- aggregate

def load_bank(tag: str, subset: str = "all") -> list[dict]:
    """Bank reps merged by rep number. subset: all | even | odd (the
    pre-registered selection / held-out validation split)."""
    files = sorted(GRID_DIR.glob(f"bank_{tag}_[0-9]*.json"))
    if not files:
        raise FileNotFoundError(f"no bank files bank_{tag}_*.json in {GRID_DIR}")
    by_rep: dict[int, dict] = {}
    for f in files:
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("schema") != "bank-v1":
            raise RuntimeError(f"{f.name}: unexpected schema {r.get('schema')!r}")
        cur = by_rep.setdefault(r["rep"], {"rep": r["rep"], "cells": {}})
        dup = set(cur["cells"]) & set(r["cells"])
        if dup:
            raise RuntimeError(f"duplicate cells {dup} for rep {r['rep']}")
        cur["cells"].update(r["cells"])
    reps = [by_rep[k] for k in sorted(by_rep)]
    if subset == "even":
        reps = [r for r in reps if r["rep"] % 2 == 0]
    elif subset == "odd":
        reps = [r for r in reps if r["rep"] % 2 == 1]
    elif subset != "all":
        raise ValueError(f"unknown subset {subset!r}")
    return reps


def tables(reps: list[dict], rs: Ruleset) -> dict:
    """Tables 1-2 for one ladder over a set of bank reps."""
    cell_keys = sorted({k for r in reps for k in r["cells"]})
    t1, t2 = [], []
    for key in cell_keys:
        rows = [evaluate(r["cells"][key], rs) for r in reps if key in r["cells"]]
        m = len(rows)
        counts = {s: sum(1 for x in rows if x["terminal"] == s)
                  for s in TERMINAL_STATES}
        if sum(counts.values()) != m:
            raise RuntimeError(f"terminal states do not sum to n_reps in {key}")
        grad = sum(1 for x in rows if x["inj_graduated"])
        conf = sum(1 for x in rows
                   if x.get("confirm", {}).get("verdict") == "PASS")
        adopt = counts["adopt"]
        lo, hi = wilson(adopt, m)
        glo, ghi = wilson(grad, m)
        t1.append({
            "cell": key, "n": m,
            "p_graduate": round(grad / m, 4),
            "p_graduate_wilson95": [round(glo, 4), round(ghi, 4)],
            "p_cap_crowded_out": round(counts["cap_crowded_out"] / m, 4),
            "p_confirm_pass": round(conf / m, 4),
            "p_adopt": round(adopt / m, 4),
            "p_adopt_wilson95": [round(lo, 4), round(hi, 4)],
            "false_kill": None if key.startswith("a0.0")
            else round(1 - adopt / m, 4),
        })
        t2.append({"cell": key, "n": m, **counts})
    return {"table1_operating_characteristics": t1,
            "table2_stage_attribution": t2}


def aggregate(tag: str, rs: Ruleset, subset: str = "all") -> dict:
    reps = load_bank(tag, subset)
    out = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tag": tag, "ruleset": rs.name, "ruleset_key": rs.key(),
        "subset": subset, "n_reps": len(reps),
        "note": ("RECAL-1 bank evaluation. Terminal states are for the "
                 "injected candidate. subset=even is the ladder-SELECTION "
                 "half, subset=odd the pre-registered HELD-OUT half."),
        **tables(reps, rs),
    }
    path = RUNS_DIR / f"stage3_tables_{tag}_{rs.name}_{subset}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out["table1_operating_characteristics"], indent=1))
    print(f"tables -> {path}")
    return out


def resolve_ruleset(spec: str) -> Ruleset:
    """A registered name, or @path to a frozen ladder JSON (select.py output)."""
    if spec.startswith("@"):
        d = json.loads(open(spec[1:], encoding="utf-8").read())
        return Ruleset(**(d["ruleset"] if "ruleset" in d else d))
    if spec not in RULESETS:
        raise SystemExit(f"unknown ruleset {spec!r}; known: {sorted(RULESETS)}")
    return RULESETS[spec]


# ------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> None:
    from concurrent.futures import ProcessPoolExecutor, as_completed

    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=250)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--rho", type=float, default=RHO_SIG_HEADLINE)
    ap.add_argument("--wave", type=int, default=0, choices=(0, 1, 2, 3))
    ap.add_argument("--tag", default="r1")
    ap.add_argument("--ruleset", default="BRAIN-009-seed")
    ap.add_argument("--subset", default="all", choices=("all", "even", "odd"))
    ap.add_argument("--aggregate", action="store_true")
    args = ap.parse_args(argv)

    assert_production_constants()
    if args.aggregate:
        aggregate(args.tag, resolve_ruleset(args.ruleset), args.subset)
        return

    cells = WAVES[args.wave]
    todo = list(range(args.start, args.start + args.reps))
    if not todo:
        # --reps 0 is the wiring pre-flight: proves launcher -> run_grid ->
        # bank delegation and the production-constant assert without paying
        # for a single scan.
        print(f"no reps requested (wave={args.wave} cells={cells}) — "
              "delegation and production constants OK")
        return
    print(f"bank grid: reps {todo[0]}..{todo[-1]} tag={args.tag} "
          f"rho={args.rho} wave={args.wave} cells={cells} "
          f"workers={args.workers}", flush=True)
    if args.wave in (0, 2):
        print("NOTE: I3/I4 at alpha=0.2 are deliberately NOT in the RECAL-1 "
              "grid (least-informative cells; stated in the spec).", flush=True)
    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers,
                             initializer=_init_worker) as ex:
        futs = {ex.submit(run_rep_bank, r, args.rho, cells, args.tag): r
                for r in todo}
        for fut in as_completed(futs):
            done += 1
            print(f"[{done}/{len(todo)} {round(time.time() - t0)}s] "
                  f"{fut.result()}", flush=True)
    print(f"bank grid complete in {round((time.time() - t0) / 3600, 2)}h")

    # Coverage assertion — a wave that ran green must have left its cells on
    # disk. Run 1 lost wave 2 to a silent skip that exited 0; this makes that
    # class of failure loud instead of invisible.
    want = {f"a{a}/{d}" for d, a in cells}
    missing: dict[str, int] = {}
    checked = 0
    for rep in todo:
        path = GRID_DIR / f"bank_{tag}_{rep:04d}.json"
        if not path.exists():
            missing["<no file>"] = missing.get("<no file>", 0) + 1
            continue
        have = set(json.loads(path.read_text(encoding="utf-8"))["cells"])
        checked += 1
        for k in want - have:
            missing[k] = missing.get(k, 0) + 1
    if missing:
        raise SystemExit(
            f"COVERAGE FAILURE: {checked}/{len(todo)} rep files checked and "
            f"these cells are still absent: {missing}. The wave did NOT do "
            "its work — do not aggregate.")
    print(f"coverage OK: {checked} rep files each hold all {len(want)} "
          f"cells of wave {args.wave}", flush=True)


if __name__ == "__main__":
    main()
