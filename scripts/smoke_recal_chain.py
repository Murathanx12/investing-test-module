"""RECAL-1 pre-flight #2: does the DOWNSTREAM chain run end to end?

Generates a SYNTHETIC bank (no scans, no panel, seeded) under tag `synth`,
then drives select -> aggregate -> posterior -> exhibits exactly as the
overnight chain does. Its only job is to prove the plumbing — file names,
argument wiring, JSON shapes, the freeze handoff, the matplotlib path — so
that a night of compute cannot be lost to a typo at 04:00.

The synthetic statistics are drawn to look like the measured M1 world
(t_ic ~ N(mu_alpha, 1) with mu from threshold_sweep.json, t_net ~ N(mu-1.5,1),
PBO ~ 0.5, DSR small) but NOTHING here is evidence: the numbers it prints are
meaningless and the run writes brain009_synth.json, never the real freeze
record. Cleans up its own files unless --keep.

  .venv\\Scripts\\python.exe scripts\\smoke_recal_chain.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aegis_brain.calibration.config import RUNS_DIR          # noqa: E402
from aegis_brain.calibration.run_grid import GRID_DIR        # noqa: E402

PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
TAG = "synth"
# 250 = the registered rep count. Anything smaller cannot exercise the
# feasibility rule honestly: Wilson-95 upper on 0/12 is 0.24, so at small n
# NO ladder is feasible and the smoke would fail for arithmetic reasons.
N_REPS = 250
# measured injected-candidate t_ic means per alpha (threshold_sweep.json)
MU_T_IC = {0.0: -0.081, 0.2: 0.796, 0.4: 1.667, 0.6: 2.524}
CELLS = [("base", 0.0)] + [(d, a) for d in ("I1", "I2", "I3", "I4")
                           for a in (0.2, 0.4, 0.6)]


def synth_cell(rng: np.random.Generator, design: str, alpha: float) -> dict:
    mu = MU_T_IC[alpha]
    # I2 decays to ~9% by the confirm window; I3 puts the edge in `small`
    conf_mu = mu * (0.09 if design == "I2" else 0.63)   # sqrt(72/180)=0.63

    def stat(m_ic: float, m_net: float) -> dict:
        return {"t_net": round(float(rng.normal(m_net, 1)), 2),
                "t_ic": round(float(rng.normal(m_ic, 1)), 2),
                "contaminated": False, "months": 180}

    lm, sm = {}, {}
    for i in range(20):
        lm[f"sig{i}"] = stat(0.0, -0.9)
        sm[f"sig{i}"] = stat(0.0, -0.9)
    if design == "I3":
        lm["injected_edge"] = stat(0.0, -0.9)
        sm["injected_edge"] = stat(mu, mu - 0.9)
    else:
        lm["injected_edge"] = stat(mu, mu - 0.9)
        sm["injected_edge"] = stat(mu * 0.5, mu * 0.5 - 0.9)

    confirm, dsr = {}, {}
    for seg in ("largemid", "small"):
        base_ic = conf_mu if (seg == "small") == (design == "I3") else 0.0
        for book, bump in (("prod", 0.0), ("eng", 0.24)):
            t_ic = float(rng.normal(base_ic, 1))
            sr = base_ic / 13.4 * np.sqrt(12) + bump + float(rng.normal(0, .1))
            confirm[f"{seg}/{book}"] = {
                "t_net": round(float(rng.normal(base_ic - 0.9, 1)), 2),
                "t_ic": round(t_ic, 2),
                "mean_excess_bps": round(sr * 30, 1),
                "ic_mean": round(t_ic / 8.5, 4),
                "months": 72, "turnover_1way": 0.134 if book == "prod" else 0.09,
                "sharpe_excess_ann": round(sr, 4),
                "excess_net": [round(float(x), 6)
                               for x in rng.normal(sr / 40, 0.02, 72)],
            }
            for n in (42, 179):
                dsr[f"{seg}/{book}_{n}"] = round(
                    float(np.clip(rng.beta(1.2, 6) * (0.4 + 0.3 * sr), 0, 1)), 4)
    return {"explore": {"largemid": lm, "small": sm}, "confirm": confirm,
            "dsr": dsr, "pbo": round(float(rng.uniform(0.35, 0.65)), 4),
            "sr_var_empirical": 0.004, "sr_var_used": 0.01}


def write_bank() -> None:
    GRID_DIR.mkdir(parents=True, exist_ok=True)
    for rep in range(N_REPS):
        rng = np.random.default_rng(1_000 + rep)
        cells = {f"a{a}/{d}": synth_cell(rng, d, a) for d, a in CELLS}
        (GRID_DIR / f"bank_{TAG}_{rep:04d}.json").write_text(json.dumps({
            "rep": rep, "rho": 0.5, "tag": TAG, "schema": "bank-v1",
            "seed_panel": -1, "seed_inject": -1, "cells": cells,
            "wall_seconds": 0.0}), encoding="utf-8")
    print(f"synthetic bank: {N_REPS} reps x {len(CELLS)} cells -> {GRID_DIR}")


def run(step: str, *args: str) -> None:
    cmd = [PY, "-m", f"aegis_brain.calibration.{step}", *args]
    print(f"\n$ {' '.join(cmd[2:])}", flush=True)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail = "\n".join((r.stdout or "").strip().splitlines()[-6:])
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        raise SystemExit(f"CHAIN SMOKE FAILED at {step} (exit {r.returncode})")
    print(tail)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    real_freeze = RUNS_DIR / "brain009_frozen.json"
    before = real_freeze.exists()

    write_bank()
    frozen = f"@{RUNS_DIR / 'brain009_synth.json'}"
    run("select", "--tag", TAG, "--out", "brain009_synth.json")
    for subset in ("all", "even", "odd"):
        run("bank", "--aggregate", "--tag", TAG, "--ruleset", frozen,
            "--subset", subset)
    run("bank", "--aggregate", "--tag", TAG, "--ruleset", "BRAIN-008",
        "--subset", "all")
    for design in ("I2", "I1"):
        run("posterior", "--tag", TAG, "--ruleset", frozen, "--design", design)
    # exhibits reads the tables/posterior by ruleset NAME (select names the
    # frozen ladder BRAIN-009), so this is the same call the chain makes
    run("exhibits", "--tag", TAG, "--ruleset", "BRAIN-009", "--design", "I2")

    if real_freeze.exists() != before:
        raise SystemExit("SMOKE CONTAMINATION: the real freeze record moved")

    made = (sorted(GRID_DIR.glob(f"bank_{TAG}_*.json"))
            + sorted(RUNS_DIR.glob(f"*{TAG}*")))
    print(f"\nartifacts produced: {len(made)}")
    if not args.keep:
        for p in made:
            p.unlink()
        print("cleaned up (pass --keep to inspect)")
    print("CHAIN SMOKE PASSED — plumbing is sound (numbers are meaningless)")


if __name__ == "__main__":
    main()
