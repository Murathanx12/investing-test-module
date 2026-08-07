"""REPLAY-2 §1 — evaluate D1 (BH step-up on empirical p-values) on the bank.

D1 replaces the frozen ladder's fixed explore threshold with batch-level
error control: each (signal, segment) candidate's explore t_ic becomes an
empirical p-value against its OWN measured null CDF, and BH at q selects
across the whole batch. Everything downstream (global cap by t_ic, confirm
wall, inert DSR/PBO) is unchanged from the ratified ladder.

D2 (e-BH) is NOT evaluable on this bank: e-processes need the monthly IC
series and the bank stores summaries only. Re-scanning would cost full grid
nights, so D2 cannot meet the frozen "<= half the compute" clause — under
PREREG_REPLAY_2.md §1 the selection rule therefore ships D1. Recorded here,
not silently.

Discipline: null CDFs are built on one rep half and every rate is read on the
other half, both directions reported. CRN pairs live inside a rep, so a rep is
the atomic unit and the split cannot leak (same protocol as select.py).

Run:  python -m aegis_brain.calibration.replay2_eval --tag r1 --q 0.10
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import numpy as np

from aegis_brain.calibration.bank import load_bank, resolve_ruleset
from aegis_brain.calibration.config import RUNS_DIR
from aegis_brain.calibration.ruleset import INJECTED_NAME, Ruleset
from aegis_brain.calibration.run_grid import wilson
from dataclasses import replace

CELLS = ("a0.0/base", "a0.2/I1", "a0.4/I1", "a0.6/I1",
         "a0.4/I3", "a0.6/I3", "a0.4/I4", "a0.6/I4")


def build_null_cdfs(reps: list[dict]) -> dict[tuple[str, str], np.ndarray]:
    """Sorted null t_ic samples per (signal, segment) from a0.0/base cells."""
    samples: dict[tuple[str, str], list[float]] = {}
    for r in reps:
        cell = r["cells"].get("a0.0/base")
        if cell is None:
            continue
        for seg in ("largemid", "small"):
            for name, stat in cell["explore"][seg].items():
                samples.setdefault((name, seg), []).append(stat["t_ic"])
    if not samples:
        raise SystemExit("no a0.0/base cells in this rep half")
    return {k: np.sort(np.array(v)) for k, v in samples.items()}


def empirical_p(t: float, null_sorted: np.ndarray) -> float:
    """P(T >= t) under the null, add-one smoothed (never exactly 0)."""
    n = len(null_sorted)
    ge = n - int(np.searchsorted(null_sorted, t, side="left"))
    return (1 + ge) / (n + 1)


def bh_reject(pvals: list[float], q: float) -> list[bool]:
    """Benjamini-Hochberg step-up. Returns per-hypothesis rejection flags."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    k_star = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= q * rank / m:
            k_star = rank
    out = [False] * m
    for rank, i in enumerate(order, start=1):
        if rank <= k_star:
            out[i] = True
    return out


def evaluate_d1(cell: dict, rs: Ruleset,
                cdfs: dict[tuple[str, str], np.ndarray], q: float) -> dict:
    """evaluate() with the explore qualification replaced by BH selection.
    Downstream (cap by rank key, confirm, DSR, PBO) mirrors ruleset.evaluate.
    """
    cands: list[tuple[str, str, float, float]] = []  # name, seg, rankval, p
    for seg in rs.explore_segments:
        for name, stat in cell["explore"][seg].items():
            if stat["contaminated"]:
                continue
            key = (name, seg)
            if key not in cdfs:
                raise KeyError(f"no null CDF for {key} — half mismatch")
            cands.append((name, seg, stat[rs.explore_rank_by],
                          empirical_p(stat["t_ic"], cdfs[key])))

    rej = bh_reject([c[3] for c in cands], q)
    quals = [c for c, r in zip(cands, rej) if r]
    quals.sort(key=lambda x: -x[2])
    graduates = quals[:rs.explore_top_n]

    inj_entries = [c for c in quals if c[0] == INJECTED_NAME]
    row = {
        "n_qualifiers": len(quals),
        "n_null_qualifiers": sum(1 for c in quals if c[0] != INJECTED_NAME),
        "inj_qualified": bool(inj_entries),
        "inj_graduated": any(c[0] == INJECTED_NAME for c in graduates),
    }
    if not row["inj_qualified"]:
        row["terminal"] = "no_graduate"
        return row
    if not row["inj_graduated"]:
        row["terminal"] = "cap_crowded_out"
        return row

    seg = max(inj_entries, key=lambda c: c[2])[1]
    c = cell["confirm"][f"{seg}/{rs.confirm_book}"]
    killed = ((rs.confirm_sign_net and c["mean_excess_bps"] <= 0)
              or (rs.confirm_sign_ic and c["ic_mean"] <= 0))
    passed = (not killed
              and (rs.confirm_t_ic is None or c["t_ic"] >= rs.confirm_t_ic)
              and (rs.confirm_t_net is None or c["t_net"] >= rs.confirm_t_net))
    if not passed:
        row["terminal"] = "confirm_fail"
        return row

    dsr = cell["dsr"][f"{seg}/{rs.dsr_book}_{rs.dsr_n_trials}"]
    if dsr < rs.dsr_threshold:
        row["terminal"] = "dsr_fail"
    elif cell["pbo"] >= rs.pbo_threshold:
        row["terminal"] = "pbo_fail"
    else:
        row["terminal"] = "adopt"
    return row


def score_half(reps: list[dict], rs: Ruleset,
               cdfs: dict, q: float) -> dict:
    from aegis_brain.calibration.ruleset import evaluate as eval_fixed
    out: dict = {}
    for cellkey in CELLS:
        rows_d1, rows_b10 = [], []
        for r in reps:
            cell = r["cells"].get(cellkey)
            if cell is None:
                continue
            rows_d1.append(evaluate_d1(cell, rs, cdfs, q))
            rows_b10.append(eval_fixed(cell, rs))
        if not rows_d1:
            continue
        n = len(rows_d1)
        k_d1 = sum(1 for x in rows_d1 if x["terminal"] == "adopt")
        k_b10 = sum(1 for x in rows_b10 if x["terminal"] == "adopt")
        lo1, hi1 = (float(x) for x in wilson(k_d1, n))
        out[cellkey] = {
            "n": n,
            "d1_adopt": round(k_d1 / n, 4), "d1_wilson": [round(lo1, 4), round(hi1, 4)],
            "b10_adopt": round(k_b10 / n, 4),
            "d1_mean_null_qualifiers": round(
                float(np.mean([x["n_null_qualifiers"] for x in rows_d1])), 3),
            "b10_mean_null_qualifiers": round(
                float(np.mean([x.get("n_null_qualifiers", 0) for x in rows_b10])), 3),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="r1")
    ap.add_argument("--q", type=float, default=0.10)
    ap.add_argument("--ruleset", default="@runs/GATE-M1/brain009_frozen.json")
    args = ap.parse_args()

    b9 = resolve_ruleset(args.ruleset)
    b10 = replace(b9, name="BRAIN-010",
                  explore_segments=("largemid", "small"), explore_top_n=10)

    even = load_bank(args.tag, "even")
    odd = load_bank(args.tag, "odd")
    print(f"even: {len(even)} reps | odd: {len(odd)} reps | q = {args.q}")

    report = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tag": args.tag, "q": args.q, "ladder": "BRAIN-010",
        "d2_note": ("e-BH not evaluable: bank stores summary stats, no "
                    "monthly IC series; re-scan would exceed the <=half-"
                    "compute clause -> D1 ships per PREREG_REPLAY_2 §1"),
        "cdf_even__eval_odd": score_half(odd, b10, build_null_cdfs(even), args.q),
        "cdf_odd__eval_even": score_half(even, b10, build_null_cdfs(odd), args.q),
    }
    print(json.dumps({k: report[k] for k in
                      ("cdf_even__eval_odd", "cdf_odd__eval_even")}, indent=1))

    out_dir = RUNS_DIR.parent / "REPLAY-2"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"d1_eval_q{args.q}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"written -> {out}")


if __name__ == "__main__":
    main()
