"""Stage 2 — injection + magnitude calibration gate (design §6).

Kill criterion (pre-registered): perfect-foresight book on X realizes the
target Sharpe outside ±20% at any alpha level, OR (r_injected − r_null) is
nonzero on fewer than 99% of eligible cells → mapping broken, NO grid run.
This is the S2 silent-failure guard: a no-op injector (k=0 bug, wrong month
alignment, wrong column alignment) must be IMPOSSIBLE, because it would
masquerade as a catastrophically overpowered pipeline.

The perfect-foresight statistic is the realized dr payoff of the top-decile-X
book divided by the FROZEN sigma_hat (the definition of the k mapping), so
the gate tests the injector, not the panel's noise draw. Realized book Sharpe
on the injected panel (noise included) is reported as a diagnostic.

Run:  .venv/Scripts/python.exe -m aegis_brain.calibration.stage2_run
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import numpy as np

from aegis_brain.calibration.config import (
    INJECT_SEED_OFFSET,
    INJECTION_DESIGNS,
    REAL_PANEL_DIR,
    RHO_SIG_HEADLINE,
    RUNS_DIR,
    S2_MIN_NONZERO_FRAC,
    S2_SHARPE_REL_TOL,
    SEED_BASE,
    SIGMA_HAT_MONTHLY,
    assert_production_constants,
)
from aegis_brain.calibration.inject import (
    _design_X,
    build_injection_inputs,
    delta_frame,
    inject,
)
from aegis_brain.calibration.panel_gen import build_dgpa_inputs, gen_null_panel
from aegis_brain.calibration.stage0_seam import subset_panel_to_eligible
from aegis_brain.data.eodhd_panel import load_cached_panel

N_S2_REPS = 3
S2_ALPHAS = (0.2, 0.4, 0.6)


def pf_book_stats(panel_null, inj, design: str, s_ann: float) -> dict:
    """Perfect-foresight top-decile-X book, and the nonzero-cell fraction."""
    dr = delta_frame(panel_null, inj, design, s_ann)
    X = _design_X(inj, design, panel_null)
    mask = inj.masks[design]
    ret = panel_null.monthly_ret
    months = ret.index

    payoffs = []
    realized_excess = []
    n_nonzero = 0
    n_eligible_cells = 0
    for m_pos in range(len(months) - 1):
        fm, tm = months[m_pos], months[m_pos + 1]
        in_mask = mask.loc[fm]
        x = X.loc[fm].dropna()
        x = x[x.index.isin(in_mask[in_mask].index)]
        if len(x) < 2:
            continue
        live = ret.loc[tm].reindex(x.index).notna()
        n_eligible_cells += int(live.sum())
        n_nonzero += int((dr.loc[tm].reindex(x.index)[live] != 0.0).sum())

        n_top = max(int(len(x) * 0.10), 10)
        book = x.nlargest(n_top).index
        payoffs.append(float(dr.loc[tm].reindex(book).mean()))
        r_inj_row = (ret.loc[tm] + dr.loc[tm]).reindex(x.index)
        realized_excess.append(
            float(r_inj_row.reindex(book).mean() - r_inj_row.mean()))

    payoffs = np.asarray(payoffs)
    realized = np.asarray(realized_excess)
    pf_sharpe = float(payoffs.mean() / SIGMA_HAT_MONTHLY * np.sqrt(12.0))
    realized_sd = realized.std(ddof=1)
    return {
        "pf_sharpe_ann": round(pf_sharpe, 4),
        "mean_dr_payoff_bps": round(float(payoffs.mean()) * 1e4, 3),
        "realized_book_sharpe_ann": round(
            float(realized.mean() / realized_sd * np.sqrt(12.0)), 4)
        if realized_sd > 0 else None,
        "realized_book_vol_monthly": round(float(realized_sd), 6),
        "nonzero_frac": round(n_nonzero / n_eligible_cells, 6),
        "n_eligible_cells": n_eligible_cells,
    }


def main() -> dict:
    t0 = time.time()
    print("STAGE 2 — injection + magnitude calibration gate")
    print("=" * 70)
    assert_production_constants()

    real = subset_panel_to_eligible(load_cached_panel(REAL_PANEL_DIR))
    inputs = build_dgpa_inputs(real)

    cells = []
    failures = []
    for rep in range(N_S2_REPS):
        panel_null = gen_null_panel(inputs, np.random.default_rng(SEED_BASE + rep))
        inj = build_injection_inputs(
            panel_null, RHO_SIG_HEADLINE,
            np.random.default_rng(SEED_BASE + INJECT_SEED_OFFSET + rep))

        # k=0 must be an EXACT no-op (the alpha=0 cell of the grid).
        dr0 = delta_frame(panel_null, inj, "I1", 0.0)
        if (dr0.to_numpy() != 0.0).any():
            raise RuntimeError("alpha=0 injection is not a no-op")

        for design in INJECTION_DESIGNS:
            for s_ann in S2_ALPHAS:
                st = pf_book_stats(panel_null, inj, design, s_ann)
                rel_err = abs(st["pf_sharpe_ann"] - s_ann) / s_ann
                ok = (rel_err <= S2_SHARPE_REL_TOL
                      and st["nonzero_frac"] >= S2_MIN_NONZERO_FRAC)
                row = {"rep": rep, "design": design, "alpha": s_ann,
                       "target_sharpe": s_ann, **st,
                       "rel_err": round(rel_err, 4), "pass": ok}
                cells.append(row)
                if not ok:
                    failures.append(row)
                print(f"  rep{rep} {design} a={s_ann}: PF {st['pf_sharpe_ann']:+.3f} "
                      f"(target {s_ann}, rel {rel_err:.1%}) "
                      f"nonzero {st['nonzero_frac']:.4f} "
                      f"realized {st['realized_book_sharpe_ann']} "
                      f"-> {'PASS' if ok else 'FAIL'}")

    verdict = ("STAGE 2 PASS — injector certified for the grid"
               if not failures else
               f"STAGE 2 FAIL — {len(failures)} cells outside gate; NO GRID RUN")
    print("=" * 70)
    print(verdict)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "stage": 2,
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_reps": N_S2_REPS,
        "rho_sig": RHO_SIG_HEADLINE,
        "sigma_hat": SIGMA_HAT_MONTHLY,
        "seed_base": SEED_BASE,
        "cells": cells,
        "verdict": verdict,
        "wall_seconds": round(time.time() - t0, 1),
    }
    (RUNS_DIR / "stage2_injection.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"report -> {RUNS_DIR / 'stage2_injection.json'}")
    if failures:
        raise SystemExit(1)
    return report


if __name__ == "__main__":
    main()
