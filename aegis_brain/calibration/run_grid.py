"""Stage 3 — the calibration grid (design §6 stage 3, Tables 1-2).

One replication rep:
  null panel (seed SEED_BASE+rep)  →  for each cell (alpha × design):
  inject → 21 signals × 2 segments through the UNCHANGED production
  scan_signal → frozen graduation rule (largemid, t_net ≥ 1.5 AND t_ic ≥ 2.0,
  top-5 cap) → one confirm read (2019-01..2024-12, frozen BRAIN-008 rule) →
  evaluate_candidate with the T×42 batch perf_matrix, DSR at n_trials 42 AND
  179. Registered rep count: n = 250 per cell (±6.2pp Wilson, stated on every
  table) — the Stage 0 descope.

The 21st candidate (injected_edge) is ALWAYS present, at every alpha
including alpha = 0 (k = 0), so every cell has 42 candidates and CRN pairing
across alpha levels is exact. The alpha = 0 cell's adopt rate IS the
per-candidate false-discovery rate; alpha > 0 rows give false-kill.

Registered rules replayed verbatim (provenance):
  - graduation: docs/STRATEGY_FACTORY.md "Graduation rule (frozen before
    results)" — fresh signals only; contaminated references cannot graduate
    and do not occupy cap slots.
  - confirm: scripts/run_confirm_gpsmall.py frozen rule — KILL if mean net
    excess <= 0 OR mean IC <= 0; PASS iff t_net >= 0.8 AND t_ic >= 1.5
    (STRONG PASS at t_net >= 1.5); anything else is a FAIL. confirm_fail =
    not PASS. Confirm cost stays the production 25 bps (largemid).
  - sr_variance: cross-section of the cell's own 42 explore scan Sharpes
    (t_excess_net/sqrt(months)), FLOORED at DEFAULT_SR_VARIANCE per the E1
    rule "may never lower the hurdle"; both values recorded.
  - DSR/PBO: evaluate_candidate on the confirm window's monthly excess_net,
    perf_matrix = the cell's T×42 explore excess_net matrix. pbo=None raises
    (S3). Primary terminal state uses n_trials = 42 (the trials this
    experiment actually ran); the n_trials = 179 production deflation is
    recorded per rep and reported alongside (the delta is a paper exhibit).

Terminal states, mutually exclusive, one per cell per rep — counts MUST sum
to n_reps or the aggregation raises (S5):
    no_graduate | cap_crowded_out | confirm_fail | dsr_fail | pbo_fail | adopt
cap_crowded_out = injected passes both thresholds but is out-ranked by five
luckier fresh candidates at the top-5 cap: a true signal that dies at the
cap, not at a statistical gate.

Silent-failure discipline: scan_signal is called DIRECTLY and any scan
exception aborts the rep (never run_batch, which swallows crashes into
months=0 rows — S1). A rep that errors produces NO output file, so it is
distinguishable from a rep with zero graduates (S5).

NEGATIVE RESULT — cross-segment reuse is INVALID (do not re-add it):
  the first build reused the alpha=0 small scans for I1/I2 cells (and the
  alpha=0 largemid scans for I3) on the argument that injection never
  touches the other segment's returns and signals are columnwise. The
  --smoke assertion refuted it: segment membership MIGRATES. A name in
  largemid at month m carries its injected dr in its own history, and when
  it later sits in the small segment, lookback signals (momentum etc.) read
  that history — the small scan differs (mom_6_1 small: -22.6 vs -22.3
  bps/mo under I1 a=0.6). All 42 scans therefore run fresh in every cell.
  The only optimization kept is per-cell score MEMOIZATION: each
  FactorySignal is wrapped so compute(panel) runs once per panel and is
  shared by the two segment scans and the confirm read — the wrapper
  returns the identical DataFrame (--smoke asserts byte-equal summaries).
  Production code is untouched (assert_production_constants runs at start).

CRN: rep r uses ONE null panel and ONE (X, noise) draw for every cell;
seeds are written into every row.

Run:   .venv/Scripts/python.exe -m aegis_brain.calibration.run_grid --reps 250
Smoke: ... --smoke        Aggregate: ... --aggregate
Rho sensitivity (I2 only, alphas>0): ... --rho 0.3 --reps 250
"""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from aegis_brain.calibration.config import (
    ALPHA_GRID,
    INJECT_SEED_OFFSET,
    INJECTION_DESIGNS,
    REAL_PANEL_DIR,
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
from aegis_brain.calibration.panel_gen import build_dgpa_inputs, gen_null_panel
from aegis_brain.calibration.stage0_seam import subset_panel_to_eligible
from aegis_brain.data.eodhd_panel import Panel, load_cached_panel
from aegis_brain.factory.batch1_price import BATCH1
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.signals import FactorySignal
from aegis_brain.gate.adoption import (
    DEFAULT_SR_VARIANCE,
    DSR_SHIP_THRESHOLD,
    PBO_REJECT_THRESHOLD,
    evaluate_candidate,
)

GRID_DIR = RUNS_DIR / "grid"
CONFIRM_CFG = ScanConfig(first_test_month="2019-01-31",
                         last_test_month="2024-12-31")
POSITIVE_ALPHAS = tuple(a for a in ALPHA_GRID if a > 0)
N_TRIALS_BATCH = 42
N_TRIALS_PRODUCTION = 179
TERMINAL_STATES = ("no_graduate", "cap_crowded_out", "confirm_fail",
                   "dsr_fail", "pbo_fail", "adopt")

INJECTED_NAME = "injected_edge"


# ---------------------------------------------------------------- helpers

def memoized_signals(signals: list[FactorySignal]) -> list[FactorySignal]:
    """Wrap each signal so compute() runs once per (signal, panel) pair.
    Numerically identical output; the cache dies with the returned list."""
    out = []
    for s in signals:
        def compute(panel: Panel, _s=s, _cache={}) -> pd.DataFrame:
            key = id(panel)
            if key not in _cache:
                _cache.clear()          # one panel at a time per signal
                _cache[key] = _s.compute(panel)
            return _cache[key]
        out.append(FactorySignal(s.name, s.hypothesis, compute, s.direction,
                                 contaminated=s.contaminated))
    return out


def scan_segment(panel: Panel, signals: list[FactorySignal],
                 segment: str) -> dict[str, dict]:
    """21 direct scan_signal calls (S1: no run_batch). name -> result."""
    return {s.name: scan_signal(panel, s, segment) for s in signals}


def graduation(largemid: dict[str, dict]) -> dict:
    """The frozen rule. Returns injected candidate's fate at the explore gate."""
    quals = []
    for name, res in largemid.items():
        s = res["summary"]
        if s["contaminated"]:
            continue
        if s["t_excess_net"] >= 1.5 and s["t_ic"] >= 2.0:
            quals.append((name, s["t_excess_net"]))
    quals.sort(key=lambda x: -x[1])
    graduates = [n for n, _ in quals[:5]]
    inj_sum = largemid[INJECTED_NAME]["summary"]
    inj_qualified = any(n == INJECTED_NAME for n, _ in quals)
    inj_rank = next((i + 1 for i, (n, _) in enumerate(quals)
                     if n == INJECTED_NAME), None)
    return {
        "qualifiers": [n for n, _ in quals],
        "graduates": graduates,
        "n_null_qualifiers": sum(1 for n, _ in quals if n != INJECTED_NAME),
        "inj_qualified": inj_qualified,
        "inj_graduated": INJECTED_NAME in graduates,
        "inj_rank_among_qualifiers": inj_rank,
        "inj_t_net": inj_sum["t_excess_net"],
        "inj_t_ic": inj_sum["t_ic"],
        "inj_mean_excess_bps": inj_sum["mean_excess_net_bps"],
    }


def confirm_verdict(summary: dict) -> str:
    """Frozen BRAIN-008 rule, verbatim."""
    pos = summary["mean_excess_net_bps"] > 0 and summary["ic_mean"] > 0
    if not pos:
        return "KILL"
    if summary["t_excess_net"] >= 0.8 and summary["t_ic"] >= 1.5:
        return "STRONG PASS" if summary["t_excess_net"] >= 1.5 else "PASS"
    return "FAIL"


def perf_matrix_and_srvar(largemid: dict, small: dict) -> tuple[np.ndarray, dict]:
    cols = {}
    srs = []
    for seg_label, seg in (("largemid", largemid), ("small", small)):
        for name, res in seg.items():
            cols[f"{name}/{seg_label}"] = res["monthly"]["excess_net"]
            s = res["summary"]
            srs.append(s["t_excess_net"] / np.sqrt(s["months"]))
    if len(cols) != N_TRIALS_BATCH:
        raise RuntimeError(f"perf matrix has {len(cols)} columns, need 42")
    mat = pd.DataFrame(cols)
    emp = float(np.var(srs, ddof=1))
    return mat.to_numpy(), {"sr_var_empirical": round(emp, 6),
                            "sr_var_used": max(emp, DEFAULT_SR_VARIANCE)}


def run_cell(panel: Panel, signals: list[FactorySignal],
             largemid: dict[str, dict], small: dict[str, dict]) -> dict:
    """The ladder for the injected candidate in one (alpha, design) cell."""
    grad = graduation(largemid)
    row = dict(grad)
    pm, srv = perf_matrix_and_srvar(largemid, small)
    row.update(srv)

    if not grad["inj_qualified"]:
        row["terminal"] = "no_graduate"
        return row
    if not grad["inj_graduated"]:
        row["terminal"] = "cap_crowded_out"
        return row

    inj_sig = [s for s in signals if s.name == INJECTED_NAME][0]
    confirm = scan_signal(panel, inj_sig, "largemid", CONFIRM_CFG)
    csum = confirm["summary"]
    verdict = confirm_verdict(csum)
    row["confirm"] = {"verdict": verdict,
                      "t_net": csum["t_excess_net"], "t_ic": csum["t_ic"],
                      "mean_excess_bps": csum["mean_excess_net_bps"],
                      "months": csum["months"]}
    if verdict not in ("PASS", "STRONG PASS"):
        row["terminal"] = "confirm_fail"
        return row

    ret = confirm["monthly"]["excess_net"].dropna().to_numpy()
    gate42 = evaluate_candidate(ret, sr_variance=srv["sr_var_used"],
                                perf_matrix=pm, n_trials=N_TRIALS_BATCH)
    gate179 = evaluate_candidate(ret, sr_variance=srv["sr_var_used"],
                                 perf_matrix=pm, n_trials=N_TRIALS_PRODUCTION)
    if gate42["pbo"] is None:
        raise RuntimeError("pbo=None reached the gate — S3 violated")
    dsr42, dsr179 = gate42["dsr"]["dsr"], gate179["dsr"]["dsr"]
    pbo = gate42["pbo"]["pbo"]
    row["gate"] = {"dsr_42": dsr42, "dsr_179": dsr179, "pbo": pbo,
                   "dsr_ok_179": dsr179 >= DSR_SHIP_THRESHOLD,
                   "adopt_179": dsr179 >= DSR_SHIP_THRESHOLD
                   and pbo < PBO_REJECT_THRESHOLD}
    if dsr42 < DSR_SHIP_THRESHOLD:
        row["terminal"] = "dsr_fail"
    elif pbo >= PBO_REJECT_THRESHOLD:
        row["terminal"] = "pbo_fail"
    else:
        row["terminal"] = "adopt"
    return row


# ---------------------------------------------------------------- worker

_W: dict = {}


def _init_worker() -> None:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    assert_production_constants()
    real = subset_panel_to_eligible(load_cached_panel(REAL_PANEL_DIR))
    _W["inputs"] = build_dgpa_inputs(real)


def run_rep(rep: int, rho: float, designs: tuple[str, ...],
            include_base: bool = True, tag: str = "") -> str:
    if rho != RHO_SIG_HEADLINE:
        tag = f"_rho{rho}"
    out_path = GRID_DIR / f"rep{tag}_{rep:04d}.json"
    if out_path.exists():
        return f"rep {rep}{tag}: exists, skipped"

    t0 = time.time()
    inputs = _W["inputs"]
    panel_null = gen_null_panel(inputs, np.random.default_rng(SEED_BASE + rep))
    inj = build_injection_inputs(
        panel_null, rho,
        np.random.default_rng(SEED_BASE + INJECT_SEED_OFFSET + rep))

    signals = memoized_signals(BATCH1 + [injected_signal(inj)])
    if len(signals) != 21:
        raise RuntimeError("candidate list must be 21 signals")

    cells = {}
    if include_base:
        # alpha = 0 base cell (shared across designs by CRN)
        base_lm = scan_segment(panel_null, signals, "largemid")
        base_sm = scan_segment(panel_null, signals, "small")
        cells["a0.0/base"] = run_cell(panel_null, signals, base_lm, base_sm)

    for design in designs:
        for a in POSITIVE_ALPHAS:
            pnl = inject(panel_null, inj, design, a)
            sigs = memoized_signals(BATCH1 + [injected_signal(inj)])
            lm = scan_segment(pnl, sigs, "largemid")
            sm = scan_segment(pnl, sigs, "small")
            cells[f"a{a}/{design}"] = run_cell(pnl, sigs, lm, sm)

    report = {
        "rep": rep, "rho": rho,
        "seed_panel": SEED_BASE + rep,
        "seed_inject": SEED_BASE + INJECT_SEED_OFFSET + rep,
        "cells": cells,
        "wall_seconds": round(time.time() - t0, 1),
    }
    GRID_DIR.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, default=str), encoding="utf-8")
    tmp.replace(out_path)
    states = {k: v["terminal"] for k, v in cells.items()}
    return (f"rep {rep}{tag}: {round(time.time() - t0, 1)}s "
            f"{json.dumps(states)}")


# ---------------------------------------------------------------- smoke

def smoke() -> None:
    """Assertions + timing on two cells; extrapolates a per-rep estimate."""
    _init_worker()
    inputs = _W["inputs"]
    t0 = time.time()
    panel_null = gen_null_panel(inputs, np.random.default_rng(SEED_BASE))
    print(f"null panel: {time.time() - t0:.1f}s")
    inj = build_injection_inputs(
        panel_null, RHO_SIG_HEADLINE,
        np.random.default_rng(SEED_BASE + INJECT_SEED_OFFSET))

    # memoization is a numeric no-op
    raw = scan_signal(panel_null, BATCH1[4], "largemid")["summary"]
    wrapped = memoized_signals([BATCH1[4]])[0]
    memo = scan_signal(panel_null, wrapped, "largemid")["summary"]
    if raw != memo:
        raise RuntimeError(f"memoized scan differs: {raw} vs {memo}")
    print("memoization no-op: PASS")

    # the migration-leak guard: cross-segment reuse MUST stay invalid.
    # If this ever passes byte-equal, revisit — but do not silently reuse.
    pnl_i1 = inject(panel_null, inj, "I1", 0.6)
    a = scan_signal(panel_null, BATCH1[4], "small")["summary"]
    b = scan_signal(pnl_i1, BATCH1[4], "small")["summary"]
    print(f"migration leak present (reuse stays banned): {a != b}")

    sigs = memoized_signals(BATCH1 + [injected_signal(inj)])
    t0 = time.time()
    base_lm = scan_segment(panel_null, sigs, "largemid")
    base_sm = scan_segment(panel_null, sigs, "small")
    base = run_cell(panel_null, sigs, base_lm, base_sm)
    t_base = time.time() - t0
    print(f"base cell: {t_base:.0f}s terminal={base['terminal']}")

    t0 = time.time()
    pnl = inject(panel_null, inj, "I2", 0.4)
    sigs2 = memoized_signals(BATCH1 + [injected_signal(inj)])
    cell = run_cell(pnl, sigs2, scan_segment(pnl, sigs2, "largemid"),
                    scan_segment(pnl, sigs2, "small"))
    t_cell = time.time() - t0
    print(f"I2/a0.4 cell: {t_cell:.0f}s terminal={cell['terminal']} "
          f"inj_t_net={cell['inj_t_net']}")
    est = t_base + 12 * t_cell
    print(f"estimated per-rep wall: {est / 60:.1f} min "
          f"-> 250 reps at 16 workers ~ {est * 250 / 16 / 3600:.1f}h")


# ---------------------------------------------------------------- aggregate

def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    z = 1.959963984540054
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def aggregate(rho: float) -> None:
    tag = "" if rho == RHO_SIG_HEADLINE else f"_rho{rho}"
    if rho == RHO_SIG_HEADLINE:
        # merge wave files (rep_NNNN + rep_w2_NNNN) by rep number
        files = sorted(GRID_DIR.glob("rep_[0-9]*.json")) + sorted(
            GRID_DIR.glob("rep_w2_[0-9]*.json"))
    else:
        files = sorted(GRID_DIR.glob(f"rep_rho{rho}_[0-9]*.json"))
    if not files:
        raise FileNotFoundError(f"no rep files under {GRID_DIR}")
    by_rep: dict[int, dict] = {}
    for f in files:
        r = json.loads(f.read_text(encoding="utf-8"))
        cur = by_rep.setdefault(r["rep"], {"rep": r["rep"], "cells": {}})
        overlap = set(cur["cells"]) & set(r["cells"])
        if overlap:
            raise RuntimeError(f"duplicate cells {overlap} for rep {r['rep']}")
        cur["cells"].update(r["cells"])
    reps = list(by_rep.values())
    n = len(reps)
    print(f"aggregating {n} reps from {len(files)} files (rho={rho})")

    cell_keys = sorted({k for r in reps for k in r["cells"]})
    t1_rows, t2_rows = [], []
    for key in cell_keys:
        rows = [r["cells"][key] for r in reps if key in r["cells"]]
        m = len(rows)
        counts = {s: sum(1 for r in rows if r["terminal"] == s)
                  for s in TERMINAL_STATES}
        if sum(counts.values()) != m:
            raise RuntimeError(f"terminal states do not sum to n_reps in {key}")
        grad = sum(1 for r in rows if r["inj_graduated"])
        conf = sum(1 for r in rows if r.get("confirm", {}).get("verdict")
                   in ("PASS", "STRONG PASS"))
        dsr42 = sum(1 for r in rows
                    if r.get("gate", {}).get("dsr_42", 0) >= DSR_SHIP_THRESHOLD)
        dsr179 = sum(1 for r in rows if r.get("gate", {}).get("dsr_ok_179"))
        adopt = counts["adopt"]
        adopt179 = sum(1 for r in rows if r.get("gate", {}).get("adopt_179"))
        lo, hi = wilson(adopt, m)
        t1_rows.append({
            "cell": key, "n": m,
            "p_graduate": round(grad / m, 4),
            "p_cap_crowded_out": round(counts["cap_crowded_out"] / m, 4),
            "p_confirm_pass": round(conf / m, 4),
            "p_dsr95_n42": round(dsr42 / m, 4),
            "p_dsr95_n179": round(dsr179 / m, 4),
            "p_adopt_n42": round(adopt / m, 4),
            "p_adopt_n42_wilson95": [round(lo, 4), round(hi, 4)],
            "p_adopt_n179": round(adopt179 / m, 4),
            "false_kill_n42": None if key.startswith("a0.0")
            else round(1 - adopt / m, 4),
            "false_kill_n179": None if key.startswith("a0.0")
            else round(1 - adopt179 / m, 4),
        })
        t2_rows.append({"cell": key, "n": m, **counts})

    out = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rho": rho, "n_reps": n,
        "note": ("n=250 per cell is the REGISTERED Stage-0 descope; Wilson 95% "
                 "intervals stated per cell. Terminal states are for the "
                 "injected candidate; n_trials=42 is the in-experiment "
                 "deflation (primary ladder), n_trials=179 the production "
                 "deflation, both reported."),
        "table1_operating_characteristics": t1_rows,
        "table2_stage_attribution": t2_rows,
    }
    path = RUNS_DIR / f"stage3_tables{tag}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(t1_rows, indent=1))
    print(f"tables -> {path}")


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=250)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--rho", type=float, default=RHO_SIG_HEADLINE)
    ap.add_argument("--wave", type=int, default=0,
                    help="BRAIN-008 grid: 1 = base + I2 headline (the Gate M "
                         "number first), 2 = I1/I3/I4 no base, 0 = one pass. "
                         "RECAL-1 bank (--ruleset/--tag): 1 = base + I1 (the "
                         "acceptance targets), 2 = I2/I3/I4 sweep, 0 = both.")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--aggregate", action="store_true")
    # RECAL-1: when either flag is present this entry point delegates to
    # calibration.bank (the gate-agnostic evidence bank). The frozen
    # BRAIN-008 path below is untouched and stays the default.
    ap.add_argument("--ruleset", default=None,
                    help="RECAL-1 ladder name (e.g. BRAIN-009-seed) or "
                         "@path.json; delegates to calibration.bank")
    ap.add_argument("--tag", default=None,
                    help="RECAL-1 bank tag -> bank_<tag>_NNNN.json (never "
                         "collides with the frozen rep_*.json grid)")
    ap.add_argument("--subset", default="all", choices=("all", "even", "odd"))
    args = ap.parse_args()

    if args.ruleset is not None or args.tag is not None:
        from aegis_brain.calibration import bank
        argv = ["--reps", str(args.reps), "--start", str(args.start),
                "--workers", str(args.workers), "--rho", str(args.rho),
                "--wave", str(args.wave), "--subset", args.subset,
                "--tag", args.tag or "r1"]
        if args.ruleset is not None:
            argv += ["--ruleset", args.ruleset]
        if args.aggregate:
            argv += ["--aggregate"]
        bank.main(argv)
        return

    assert_production_constants()
    if args.smoke:
        smoke()
        return
    if args.aggregate:
        aggregate(args.rho)
        return

    if args.rho != RHO_SIG_HEADLINE:
        designs, include_base, tag = ("I2",), True, ""
    elif args.wave == 1:
        designs, include_base, tag = ("I2",), True, ""
    elif args.wave == 2:
        designs, include_base, tag = ("I1", "I3", "I4"), False, "_w2"
    else:
        designs, include_base, tag = INJECTION_DESIGNS, True, ""
    todo = [r for r in range(args.start, args.start + args.reps)]
    print(f"grid: reps {todo[0]}..{todo[-1]}, rho={args.rho}, wave={args.wave}, "
          f"designs={designs}, workers={args.workers}")
    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers,
                             initializer=_init_worker) as ex:
        futs = {ex.submit(run_rep, r, args.rho, designs, include_base, tag): r
                for r in todo}
        for fut in as_completed(futs):
            done += 1
            print(f"[{done}/{len(todo)} {round(time.time() - t0)}s] "
                  f"{fut.result()}", flush=True)
    print(f"grid complete in {round((time.time() - t0) / 3600, 2)}h")


if __name__ == "__main__":
    main()
