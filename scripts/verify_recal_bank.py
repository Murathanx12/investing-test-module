"""RECAL-1 pre-flight: does the evidence bank reproduce the M1 grid?

Runs rep 0's a0.0/base and a0.6/I1 cells through the NEW bank path, replays
the BRAIN-008 replica over the bank, and compares to what the frozen M1 grid
actually recorded for the same rep (runs/GATE-M1/grid/rep_0000.json and
rep_w2_0000.json). Explore t-stats must match to the stored precision and the
terminal state must be identical.

If this disagrees, the overnight is comparing the recalibration against the
wrong control arm — do not launch the grid until it passes.

  .venv\\Scripts\\python.exe scripts\\verify_recal_bank.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.calibration.bank import bank_cell            # noqa: E402
from aegis_brain.calibration.config import (                  # noqa: E402
    INJECT_SEED_OFFSET,
    RHO_SIG_HEADLINE,
    SEED_BASE,
)
from aegis_brain.calibration.inject import (                  # noqa: E402
    build_injection_inputs,
    inject,
    injected_signal,
)
from aegis_brain.calibration.panel_gen import gen_null_panel  # noqa: E402
from aegis_brain.calibration.ruleset import BRAIN_008, evaluate  # noqa: E402
from aegis_brain.calibration.run_grid import (                # noqa: E402
    GRID_DIR,
    _init_worker,
    _W,
    memoized_signals,
    scan_segment,
)
from aegis_brain.factory.batch1_price import BATCH1           # noqa: E402

CASES = [("base", 0.0, "rep_0000.json"), ("I1", 0.6, "rep_w2_0000.json")]


def main() -> None:
    t0 = time.time()
    _init_worker()
    panel_null = gen_null_panel(_W["inputs"], np.random.default_rng(SEED_BASE))
    inj = build_injection_inputs(
        panel_null, RHO_SIG_HEADLINE,
        np.random.default_rng(SEED_BASE + INJECT_SEED_OFFSET))
    print(f"panel + injection ready ({time.time() - t0:.0f}s)", flush=True)

    failures = []
    for design, alpha, m1_file in CASES:
        key = f"a{alpha}/{design}"
        m1 = json.loads((GRID_DIR / m1_file).read_text(encoding="utf-8"))
        if key not in m1["cells"]:
            raise SystemExit(f"{m1_file} has no cell {key}")
        old = m1["cells"][key]

        t1 = time.time()
        sigs = memoized_signals(BATCH1 + [injected_signal(inj)])
        pnl = panel_null if design == "base" else inject(panel_null, inj,
                                                         design, alpha)
        lm = scan_segment(pnl, sigs, "largemid")
        sm = scan_segment(pnl, sigs, "small")
        cell = bank_cell(pnl, sigs, lm, sm)
        new = evaluate(cell, BRAIN_008)

        checks = {
            "terminal": (old["terminal"], new["terminal"]),
            "inj_t_net": (old["inj_t_net"], new["inj_t_net"]),
            "inj_t_ic": (old["inj_t_ic"], new["inj_t_ic"]),
            "inj_graduated": (old["inj_graduated"], new["inj_graduated"]),
            "n_null_qualifiers": (old["n_null_qualifiers"],
                                  new["n_null_qualifiers"]),
            "sr_var_used": (old["sr_var_used"], new["sr_var_used"]),
        }
        if "confirm" in old and "confirm" in new:
            checks["confirm_t_net"] = (old["confirm"]["t_net"],
                                       new["confirm"]["t_net"])
            checks["confirm_t_ic"] = (old["confirm"]["t_ic"],
                                      new["confirm"]["t_ic"])
        print(f"\n{key}  ({time.time() - t1:.0f}s)")
        for name, (a, b) in checks.items():
            ok = (a == b) if isinstance(a, (str, bool)) else \
                abs(float(a) - float(b)) < 1e-9
            print(f"  {'OK  ' if ok else 'FAIL'} {name}: M1={a} bank={b}")
            if not ok:
                failures.append((key, name, a, b))
        print(f"  extra: pbo={cell['pbo']} "
              f"dsr(prod,179)={cell['dsr']['largemid/prod_179']} "
              f"dsr(eng,179)={cell['dsr']['largemid/eng_179']} "
              f"turnover prod={cell['confirm']['largemid/prod']['turnover_1way']}"
              f" eng={cell['confirm']['largemid/eng']['turnover_1way']} "
              f"SRann prod="
              f"{cell['confirm']['largemid/prod']['sharpe_excess_ann']} "
              f"eng={cell['confirm']['largemid/eng']['sharpe_excess_ann']}")

    print(f"\ntotal {time.time() - t0:.0f}s")
    if failures:
        raise SystemExit(f"BANK VERIFICATION FAILED: {failures}")
    print("BANK VERIFICATION PASSED — bank + BRAIN-008 replica reproduce M1")


if __name__ == "__main__":
    main()
