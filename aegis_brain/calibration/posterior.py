"""Stage 4 — evidence → posterior map (design Table 3), pre-registered.

Everything in this docstring is frozen BEFORE the Stage-3 grid results were
read (the grid was still running when this file was committed).

Likelihood source: the HEADLINE design only — I2-decaying, rho_sig = 0.5 —
plus the shared alpha=0 base cell. I1 is easy mode, I3 is structurally
blind, I4 mixes in the size confound; a decision engine consuming this map
is being told "assuming the world decays like McLean-Pontiff says it does."

Evidence vector per rep, from the injected candidate's ladder record:
    explore-t bucket:  E0 t_net < 1.5 | E1 [1.5,2.0) | E2 [2.0,2.5) | E3 >= 2.5
    confirm-t bucket:  C0 none (no confirm read) | C1 < 0.8 | C2 [0.8,1.5) | C3 >= 1.5
    DSR(n=42) bucket:  D0 none | D1 < 0.5 | D2 [0.5,0.95) | D3 >= 0.95
"none" is ordered lowest in its coordinate.

Estimation: L(E|alpha) = (count + 0.5) / (n + 0.5 * n_observed_buckets)
(Jeffreys add-half over OBSERVED buckets only; raw counts shipped alongside).
Posterior pi(alpha|E) ∝ prior(alpha) * L(E|alpha); the shipped number is
P(alpha >= 0.2 | E) under the pre-registered prior {.85,.09,.045,.015} with
the two sensitivity priors alongside.

SHIP GATE (design §5): the headline-prior map must be MONOTONE under the
product partial order on (E, C, D) — for any two observed buckets where
every coordinate of one >= the other, the posterior must not decrease.
Any violation → posterior_map.json is NOT written; the violations are
reported instead (a noisy likelihood must not steer the sizing ladder).

Band mapping (AEGIS_EXECUTION_ROADMAP.md Question B, frozen 2026-08-02):
    <60% → 0x | 60-70% → 0.25x | 70-80% → 0.5x | 80-90% → 0.75x | >90% → 1.0x

Run:  .venv/Scripts/python.exe -m aegis_brain.calibration.posterior
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from aegis_brain.calibration.config import (
    ALPHA_GRID,
    PRIOR_HEADLINE,
    PRIOR_SENSITIVITY,
    RUNS_DIR,
    assert_production_constants,
)
from aegis_brain.calibration.run_grid import GRID_DIR

HEADLINE_CELLS = {0.0: "a0.0/base", 0.2: "a0.2/I2", 0.4: "a0.4/I2",
                  0.6: "a0.6/I2"}


def bucket_of(cell_row: dict) -> tuple[int, int, int]:
    t = cell_row["inj_t_net"]
    e = 0 if t < 1.5 else 1 if t < 2.0 else 2 if t < 2.5 else 3
    conf = cell_row.get("confirm")
    if conf is None:
        c = 0
    else:
        ct = conf["t_net"]
        c = 1 if ct < 0.8 else 2 if ct < 1.5 else 3
    gate = cell_row.get("gate")
    if gate is None:
        d = 0
    else:
        dv = gate["dsr_42"]
        d = 1 if dv < 0.5 else 2 if dv < 0.95 else 3
    return (e, c, d)


def band(p: float) -> float:
    if p < 0.60:
        return 0.0
    if p < 0.70:
        return 0.25
    if p < 0.80:
        return 0.5
    if p < 0.90:
        return 0.75
    return 1.0


def dominates(a: tuple, b: tuple) -> bool:
    return all(x >= y for x, y in zip(a, b)) and a != b


def build_map() -> dict:
    files = sorted(GRID_DIR.glob("rep_[0-9]*.json"))
    if not files:
        raise FileNotFoundError("no headline rep files — run the grid first")
    reps = [json.loads(f.read_text(encoding="utf-8")) for f in files]

    counts: dict[tuple, dict[float, int]] = {}
    n_per_alpha: dict[float, int] = {a: 0 for a in ALPHA_GRID}
    for r in reps:
        for a, key in HEADLINE_CELLS.items():
            if key not in r["cells"]:
                continue
            n_per_alpha[a] += 1
            b = bucket_of(r["cells"][key])
            counts.setdefault(b, {al: 0 for al in ALPHA_GRID})[a] += 1

    observed = sorted(counts)
    n_buckets = len(observed)
    priors = [("headline", PRIOR_HEADLINE)] + [
        (f"sensitivity_{p[0.0]}", p) for p in PRIOR_SENSITIVITY]

    rows = {}
    for b in observed:
        row = {"counts": {str(a): counts[b][a] for a in ALPHA_GRID}}
        for label, prior in priors:
            post = {}
            for a in ALPHA_GRID:
                lik = (counts[b][a] + 0.5) / (n_per_alpha[a] + 0.5 * n_buckets)
                post[a] = prior[a] * lik
            z = sum(post.values())
            p_real = sum(v for a, v in post.items() if a >= 0.2) / z
            row[label] = round(p_real, 4)
        row["band_multiplier"] = band(row["headline"])
        rows[str(b)] = row

    violations = []
    for a in observed:
        for b in observed:
            if dominates(a, b) and rows[str(a)]["headline"] < rows[str(b)]["headline"] - 1e-12:
                violations.append({"higher_evidence": a, "lower_evidence": b,
                                   "p_higher": rows[str(a)]["headline"],
                                   "p_lower": rows[str(b)]["headline"]})

    return {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_reps_per_alpha": {str(a): n_per_alpha[a] for a in ALPHA_GRID},
        "conditioning": ("P(alpha>=0.2 | evidence) under DGP-A v6 + design I2 "
                        "(decaying, rho_sig=0.5) + the stated prior. NOT a "
                        "universal probability of edge-realness."),
        "prior_headline": {str(k): v for k, v in PRIOR_HEADLINE.items()},
        "buckets": rows,
        "monotonicity_violations": violations,
        "monotone": not violations,
    }


# ------------------------------------------------------- RECAL-1 (bank)
# Same estimator, same Jeffreys add-half, same monotonicity SHIP GATE. Only
# the evidence coordinates move, because BRAIN-009 gates on information:
#   explore t_ic:  E0 <1.5 | E1 [1.5,2.0) | E2 [2.0,2.5) | E3 >=2.5
#   confirm t_ic:  C0 none | C1 <0.75 | C2 [0.75,1.5) | C3 >=1.5
#   DSR@179:       D0 none | D1 <0.25  | D2 [0.25,0.75) | D3 >=0.75
# Pre-registered in docs/RECAL1_SPEC_2026-08-06.md §6 before the bank existed.
# Spec delta S12 (2026-08-07): the DSR axis is DROPPED. Under the frozen
# BRAIN-009 the DSR gate is inert (threshold 0.0), and run 1 measured its top
# bucket at n = 1..3 across 1000 reps — a coordinate that cannot be populated
# manufactures sparse-bucket monotonicity violations and carries no
# information. The reason is structural (S1b: DSR>=0.95 needs SR_ann ~1.5 on a
# book that delivers ~0.03), not a choice made after seeing which buckets
# violated. DSR is still computed and reported per cell; it just stops being
# an axis of the sizing map.
BANK_BUCKETS = {
    "explore_t_ic": (1.5, 2.0, 2.5),
    "confirm_t_ic": (0.75, 1.5),
}


def _cut(x: float, edges: tuple, offset: int) -> int:
    return offset + sum(1 for e in edges if x >= e)


def bucket_of_bank(row: dict) -> tuple[int, int]:
    """Evidence coordinates from a ruleset.evaluate() row.

    "no confirm read" stays coordinate 0 and every rep stays classified: the
    fact that a null candidate almost never reaches the confirm read IS the
    likelihood, and conditioning it away (an attempt tried and rejected on
    2026-08-07) flattens the map to noise.
    """
    e = _cut(row["inj_t_ic"], BANK_BUCKETS["explore_t_ic"], 0)
    conf = row.get("confirm")
    c = 0 if conf is None else _cut(conf["t_ic"],
                                    BANK_BUCKETS["confirm_t_ic"], 1)
    return (e, c)


# ------------------------------------------------- sizing ladder (S12)
# The fine-grained map failed its ship gate twice (M1, and RECAL-1 run 1)
# for the same reason both times: in high-evidence buckets the alpha=0 count
# is 0 or 1, and with the Jeffreys add-half that single observation swings
# P(alpha>=0.2) by ~0.23. That is bucket resolution exceeding what the null
# sample supports, not a defect in the ordering.
#
# Remedy, pre-registered as a RULE rather than a pick: walk an ordered ladder
# of coarsenings from finest to coarsest and ship the FIRST scheme that is
# monotone on the selection half AND on the held-out half INDEPENDENTLY. A
# scheme that only survives on pooled data is rejected — which is exactly what
# happens to S4 (monotone pooled, violated on the odd half).
SIZING_SCHEMES = {                       # confirm t_ic cut points
    "S5": (0.75, 1.5, 2.25),
    "S4": (0.75, 1.5),
    "S3": (1.5,),
}
SIZING_ORDER = ("S5", "S4", "S3")


def sizing_class(row: dict, edges: tuple) -> int:
    """0 = never reached the confirm read; 1.. = confirm t_ic bands."""
    conf = row.get("confirm")
    if conf is None:
        return 0
    return 1 + sum(1 for e in edges if conf["t_ic"] >= e)


def _sizing_rows(reps: list[dict], rs, edges: tuple, design: str) -> tuple:
    from aegis_brain.calibration.ruleset import evaluate

    cells = {0.0: "a0.0/base", 0.2: f"a0.2/{design}", 0.4: f"a0.4/{design}",
             0.6: f"a0.6/{design}"}
    counts: dict[int, dict[float, int]] = {}
    n = {a: 0 for a in ALPHA_GRID}
    for r in reps:
        for a, k in cells.items():
            if k not in r["cells"]:
                continue
            n[a] += 1
            b = sizing_class(evaluate(r["cells"][k], rs), edges)
            counts.setdefault(b, {al: 0 for al in ALPHA_GRID})[a] += 1
    obs = sorted(counts)
    nb = len(obs)
    rows = {}
    for b in obs:
        post = {a: PRIOR_HEADLINE[a] * (counts[b][a] + 0.5)
                / (n[a] + 0.5 * nb) for a in ALPHA_GRID}
        z = sum(post.values())
        p = sum(v for a, v in post.items() if a >= 0.2) / z
        rows[b] = {"p_real": round(p, 4), "band_multiplier": band(p),
                   "n": sum(counts[b].values()),
                   "counts": {str(a): counts[b][a] for a in ALPHA_GRID}}
    viol = [[x, y] for x in obs for y in obs
            if x > y and rows[x]["p_real"] < rows[y]["p_real"] - 1e-12]
    return rows, viol, n


def build_sizing_ladder(tag: str, rs, design: str = "I1") -> dict:
    from aegis_brain.calibration.bank import load_bank

    halves = {s: load_bank(tag, s) for s in ("even", "odd", "all")}
    attempts = []
    shipped = None
    for name in SIZING_ORDER:
        edges = SIZING_SCHEMES[name]
        res = {s: _sizing_rows(halves[s], rs, edges, design)
               for s in ("even", "odd", "all")}
        ok = not res["even"][1] and not res["odd"][1] and not res["all"][1]
        attempts.append({"scheme": name, "edges": list(edges), "monotone": ok,
                         "violations": {s: res[s][1] for s in res},
                         "rows_all": res["all"][0]})
        if ok and shipped is None:
            shipped = {"scheme": name, "edges": list(edges),
                       "ladder": res["all"][0],
                       "n_per_alpha": {str(k): v for k, v in
                                       res["all"][2].items()}}
    return {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tag": tag, "ruleset": rs.name, "design": design,
        "rule": ("finest scheme in SIZING_ORDER that is monotone on the "
                 "selection half AND the held-out half AND pooled; pooled-only "
                 "monotonicity is rejected"),
        "attempts": attempts,
        "shipped": shipped,
        "bands": "<60%->0x | 60-70->0.25x | 70-80->0.5x | 80-90->0.75x | >90->1x",
    }


def build_map_bank(tag: str, rs, design: str = "I2") -> dict:
    """Posterior map from the RECAL-1 bank under one ladder. `design` selects
    the conditioning world: I2 (headline, McLean-Pontiff decay) or I1."""
    from aegis_brain.calibration.bank import load_bank
    from aegis_brain.calibration.ruleset import evaluate

    reps = load_bank(tag, "all")
    cells = {0.0: "a0.0/base", 0.2: f"a0.2/{design}", 0.4: f"a0.4/{design}",
             0.6: f"a0.6/{design}"}
    counts: dict[tuple, dict[float, int]] = {}
    n_per_alpha: dict[float, int] = {a: 0 for a in ALPHA_GRID}
    for r in reps:
        for a, key in cells.items():
            if key not in r["cells"]:
                continue
            n_per_alpha[a] += 1
            b = bucket_of_bank(evaluate(r["cells"][key], rs))
            counts.setdefault(b, {al: 0 for al in ALPHA_GRID})[a] += 1

    observed = sorted(counts)
    n_buckets = len(observed)
    priors = [("headline", PRIOR_HEADLINE)] + [
        (f"sensitivity_{p[0.0]}", p) for p in PRIOR_SENSITIVITY]
    rows = {}
    for b in observed:
        row = {"counts": {str(a): counts[b][a] for a in ALPHA_GRID}}
        for label, prior in priors:
            post = {a: prior[a] * (counts[b][a] + 0.5)
                    / (n_per_alpha[a] + 0.5 * n_buckets) for a in ALPHA_GRID}
            z = sum(post.values())
            row[label] = round(sum(v for a, v in post.items() if a >= 0.2) / z, 4)
        row["band_multiplier"] = band(row["headline"])
        rows[str(b)] = row

    violations = [
        {"higher_evidence": a, "lower_evidence": b,
         "p_higher": rows[str(a)]["headline"], "p_lower": rows[str(b)]["headline"]}
        for a in observed for b in observed
        if dominates(a, b)
        and rows[str(a)]["headline"] < rows[str(b)]["headline"] - 1e-12]

    return {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tag": tag, "ruleset": rs.name, "design": design,
        "n_reps_per_alpha": {str(a): n_per_alpha[a] for a in ALPHA_GRID},
        "conditioning": (f"P(alpha>=0.2 | evidence) under DGP-A v6 + design "
                         f"{design} (rho_sig=0.5) + the stated prior, ladder "
                         f"{rs.name}. NOT a universal probability."),
        "buckets_definition": BANK_BUCKETS,
        "prior_headline": {str(k): v for k, v in PRIOR_HEADLINE.items()},
        "buckets": rows,
        "monotonicity_violations": violations,
        "monotone": not violations,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=None,
                    help="RECAL-1 bank tag; absent = frozen BRAIN-008 path")
    ap.add_argument("--ruleset", default="@runs/GATE-M1/brain009_frozen.json")
    ap.add_argument("--design", default="I2", choices=("I1", "I2"))
    args = ap.parse_args()

    assert_production_constants()
    if args.tag is not None:
        from aegis_brain.calibration.bank import resolve_ruleset
        rs = resolve_ruleset(args.ruleset)

        # the sizing ladder is the artifact the decision engine consumes
        lad = build_sizing_ladder(args.tag, rs, args.design)
        lpath = RUNS_DIR / f"sizing_ladder_{args.tag}_{rs.name}_{args.design}.json"
        lpath.write_text(json.dumps(lad, indent=2), encoding="utf-8")
        if lad["shipped"]:
            s = lad["shipped"]
            print(f"SIZING LADDER SHIPPED ({s['scheme']}, cuts {s['edges']}) "
                  f"-> {lpath}")
            for b, row in sorted(s["ladder"].items()):
                print(f"   class {b}: n={row['n']:<5d} nulls="
                      f"{row['counts']['0.0']:<4d} P={row['p_real']:.3f} "
                      f"-> {row['band_multiplier']}x")
        else:
            print("NO SIZING LADDER SHIPPED — no coarsening was monotone on "
                  f"both halves; attempts -> {lpath}")

        m = build_map_bank(args.tag, rs, args.design)
        suffix = f"_{args.tag}_{rs.name}_{args.design}"
        report_path = RUNS_DIR / f"stage4_posterior_report{suffix}.json"
        report_path.write_text(json.dumps(m, indent=2), encoding="utf-8")
        print(f"report -> {report_path}")
        if m["monotone"]:
            out = RUNS_DIR / f"posterior_map{suffix}.json"
            out.write_text(json.dumps(m, indent=2), encoding="utf-8")
            print(f"MONOTONE — posterior map SHIPPED -> {out}")
        else:
            print(f"NON-MONOTONE ({len(m['monotonicity_violations'])} "
                  "violations) — map NOT shipped (design §5 gate)")
            for v in m["monotonicity_violations"][:10]:
                print("  ", v)
        return

    m = build_map()
    report_path = RUNS_DIR / "stage4_posterior_report.json"
    report_path.write_text(json.dumps(m, indent=2), encoding="utf-8")
    print(f"report -> {report_path}")
    if m["monotone"]:
        out = RUNS_DIR / "posterior_map.json"
        out.write_text(json.dumps(m, indent=2), encoding="utf-8")
        print(f"MONOTONE — posterior map SHIPPED -> {out}")
    else:
        print(f"NON-MONOTONE ({len(m['monotonicity_violations'])} violations) "
              "— posterior map NOT shipped to the sizing ladder (design §5 gate)")
        for v in m["monotonicity_violations"][:10]:
            print("  ", v)


if __name__ == "__main__":
    main()
