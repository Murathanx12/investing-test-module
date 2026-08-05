"""Counterfactual explore-gate threshold sweep (Gate M recalibration input).

Reads banked wave-1 rep files only — no scans re-run. The injected candidate
is CRN-paired: its alpha=0 stats are a pure null draw, so any (t_net*, t_ic*)
threshold pair gets a per-candidate FDR and a power estimate from the SAME
250 panels. Explore gate only — the confirm wall and DSR sit downstream and
are not swept here.

Includes t_ic-ONLY gates (t_net* = None): costs never touch rank IC, so the
information channel sees an edge the net-excess channel cannot (measured
alpha=0.4 means: t_net -0.23, t_ic +1.67). An IC-gated explore with the cost
question moved to the implementation/sizing layer is the recalibration
candidate this sweep exists to quantify.

Run:  .venv/Scripts/python.exe -m aegis_brain.calibration.sweep
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np

from aegis_brain.calibration.config import RUNS_DIR
from aegis_brain.calibration.run_grid import GRID_DIR

SWEEP_T_NET = (1.5, 1.25, 1.0, 0.75, 0.5, None)   # None = IC-only gate
SWEEP_T_IC = (2.0, 1.5, 1.0)


def main() -> None:
    files = sorted(GRID_DIR.glob("rep_[0-9]*.json"))
    cells: dict[str, list] = {"0.0": [], "0.2": [], "0.4": [], "0.6": []}
    for f in files:
        r = json.loads(f.read_text(encoding="utf-8"))
        for k, v in r["cells"].items():
            a = k.split("/")[0][1:]
            if a in cells:
                cells[a].append((v["inj_t_net"], v["inj_t_ic"]))
    arrs = {a: np.array(v) for a, v in cells.items() if v}
    n = len(arrs["0.0"])
    rows = []
    print(f"reps: {n}   (I2 headline design, rho_sig = 0.5; explore gate only)")
    print(f"{'t_net*':>7} {'t_ic*':>6} | {'FDR%':>5} | power%: a0.2  a0.4  a0.6")
    for tn in SWEEP_T_NET:
        for ti in SWEEP_T_IC:
            out = {}
            for a, arr in arrs.items():
                ok = arr[:, 1] >= ti
                if tn is not None:
                    ok &= arr[:, 0] >= tn
                out[a] = round(float(ok.mean()) * 100, 1)
            rows.append({"t_net": tn, "t_ic": ti, "fdr_pct": out["0.0"],
                         "power_pct": {a: out[a] for a in ("0.2", "0.4", "0.6")}})
            print(f"{str(tn):>7} {ti:>6} | {out['0.0']:>5.1f} | "
                  f"{out['0.2']:>9.1f} {out['0.4']:>5.1f} {out['0.6']:>5.1f}")
    stats = {a: {"t_net_mean": round(float(v[:, 0].mean()), 3),
                 "t_net_sd": round(float(v[:, 0].std(ddof=1)), 3),
                 "t_ic_mean": round(float(v[:, 1].mean()), 3),
                 "t_ic_sd": round(float(v[:, 1].std(ddof=1)), 3)}
             for a, v in arrs.items()}
    print("\ninjected-candidate stats per alpha:", json.dumps(stats, indent=1))
    out_path = RUNS_DIR / "threshold_sweep.json"
    out_path.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_reps": n,
        "note": ("Explore-gate sweep, I2/rho=0.5, injected candidate only "
                 "(CRN-paired). Confirm/DSR downstream not swept. t_net=None "
                 "= IC-only gate."),
        "rows": rows, "candidate_stats": stats,
    }, indent=2), encoding="utf-8")
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
