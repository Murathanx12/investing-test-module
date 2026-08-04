"""Frozen configuration for the Gate M1 factory calibration.

Two jobs:
1. Hold every calibration parameter (DGP, injection grid, rep counts, seeds,
   priors) in one place, fixed BEFORE any grid runs.
2. Snapshot the production constants the calibration certifies, and provide
   ``assert_production_constants()`` — run at the start of every calibration
   entry point. If production drifts from this snapshot, the calibration no
   longer describes the pipeline that is running, and everything here raises
   rather than silently producing a stale posterior map (design §4.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- locations
MODULE_ROOT = Path(__file__).resolve().parents[2]
# The panel that judged the 179 candidates — the headline calibration target.
# crsp_msf_full (1963->) is Stage 6's out-of-era check ONLY (design §0).
REAL_PANEL_DIR = MODULE_ROOT / "data" / "crsp_panel_2002"
RUNS_DIR = MODULE_ROOT / "runs" / "GATE-M1"

# ---------------------------------------------------------------- seeding
SEED_BASE = 20_260_804  # date-stamped; rep r uses default_rng(SEED_BASE + r)

# ---------------------------------------------------------------- DGP-A
AR1_PHI = 0.9            # persistence of the injected characteristic X (§3.1)
FACTOR_SET = ("mktrf", "smb", "hml", "rmw", "cma", "umd")

# ---------------------------------------------------------------- injection
RHO_SIG_HEADLINE = 0.5   # the honesty knob (§3.1)
RHO_SIG_SENSITIVITY = (0.3, 1.0)
ALPHA_GRID = (0.0, 0.2, 0.4, 0.6)          # annualized Sharpe of the edge
INJECTION_DESIGNS = ("I1", "I2", "I3", "I4")
I2_DECAY_TAU_MONTHS = 60
TOP_DECILE_MEAN_PCTRANK = 0.95              # -> per-month payoff ~= 0.9 * k
I4_SIZE_CORR = 0.5                          # corr(X, size) for design I4

# Stage 0 measured null decile-book excess vol (runs/GATE-M1/stage0_seam.json).
# Frozen here: k = S_ann * SIGMA_HAT / (0.9 * sqrt(12)). All designs use this
# largemid-book unit, including I3-small (stated: injected Sharpe is defined
# against the largemid sigma unit; realized small-book vol reported alongside).
SIGMA_HAT_MONTHLY = 0.009712678472979281

# Seed lanes: panel rng = SEED_BASE + rep; injection rng gets its own offset so
# X/noise draws never collide with the panel permutation stream.
INJECT_SEED_OFFSET = 10_000_000

# Stage 2 gate tolerances (design §6 stage 2)
S2_SHARPE_REL_TOL = 0.20     # perfect-foresight book vs target, per alpha level
S2_MIN_NONZERO_FRAC = 0.99   # (r_inj - r_null) must differ on >=99% of cells

# Pre-registered rep counts (§4.4) — fixed before results. If Stage 0 finds
# even this infeasible, the registered descope is n=250 everywhere, stated.
N_REPS_HEADLINE = 1_000   # alpha grid x I2, rho_sig = 0.5
N_REPS_SECONDARY = 250    # I1/I3/I4 and rho_sig sensitivity

# Stage 0 kill criterion (design §6): one rep (40 scans) must cost <= this
# after the §4.4 optimizations, or the 1k grid is unaffordable.
MAX_SECONDS_PER_REP = 10.0

# ---------------------------------------------------------------- posterior
# Pre-registered prior over injected-alpha levels (§ Table 3), justified by
# McLean-Pontiff decay, Harvey-Liu FDR, and our own 4-of-179 survival rate.
PRIOR_HEADLINE = {0.0: 0.85, 0.2: 0.09, 0.4: 0.045, 0.6: 0.015}
PRIOR_SENSITIVITY = (
    {0.0: 0.75, 0.2: 0.15, 0.4: 0.075, 0.6: 0.025},
    {0.0: 0.95, 0.2: 0.03, 0.4: 0.015, 0.6: 0.005},
)

# ---------------------------------------------------------------- production snapshot
@dataclass(frozen=True)
class ProductionConstants:
    """The frozen pipeline this calibration certifies (docs/STRATEGY_FACTORY.md)."""

    top_frac: float = 0.10
    hold_band_frac: float = 0.30
    cost_bps_one_way: float = 25.0
    min_names_per_month: int = 100
    first_test_month: str = "2004-01-31"
    last_test_month: str = "2018-12-31"
    # graduation rule (largemid segment only)
    grad_t_net: float = 1.5
    grad_t_ic: float = 2.0
    grad_top_n: int = 5
    # adoption gate
    dsr_ship_threshold: float = 0.95
    pbo_reject_threshold: float = 0.5
    default_sr_variance: float = 0.01
    # batch-1 scan universe
    n_batch1_signals: int = 20
    segments: tuple[str, ...] = ("largemid", "small")


PRODUCTION = ProductionConstants()


def assert_production_constants() -> None:
    """Raise if the live pipeline differs from the snapshot this calibration
    was computed against. Called at the start of every calibration entry point.
    """
    from aegis_brain.factory.batch1_price import BATCH1
    from aegis_brain.factory.explore import ScanConfig
    from aegis_brain.gate import adoption

    live = ScanConfig()
    mismatches: list[str] = []

    def chk(name: str, live_val, frozen_val) -> None:
        if live_val != frozen_val:
            mismatches.append(f"{name}: live={live_val!r} frozen={frozen_val!r}")

    chk("ScanConfig.top_frac", live.top_frac, PRODUCTION.top_frac)
    chk("ScanConfig.hold_band_frac", live.hold_band_frac, PRODUCTION.hold_band_frac)
    chk("ScanConfig.cost_bps_one_way", live.cost_bps_one_way,
        PRODUCTION.cost_bps_one_way)
    chk("ScanConfig.min_names_per_month", live.min_names_per_month,
        PRODUCTION.min_names_per_month)
    chk("ScanConfig.first_test_month", live.first_test_month,
        PRODUCTION.first_test_month)
    chk("ScanConfig.last_test_month", live.last_test_month,
        PRODUCTION.last_test_month)
    chk("adoption.DSR_SHIP_THRESHOLD", adoption.DSR_SHIP_THRESHOLD,
        PRODUCTION.dsr_ship_threshold)
    chk("adoption.PBO_REJECT_THRESHOLD", adoption.PBO_REJECT_THRESHOLD,
        PRODUCTION.pbo_reject_threshold)
    chk("adoption.DEFAULT_SR_VARIANCE", adoption.DEFAULT_SR_VARIANCE,
        PRODUCTION.default_sr_variance)
    chk("len(BATCH1)", len(BATCH1), PRODUCTION.n_batch1_signals)

    if mismatches:
        raise RuntimeError(
            "Production constants drifted from the calibration snapshot — the "
            "calibration no longer describes the running pipeline. Re-freeze "
            "calibration/config.py deliberately or revert the drift:\n  "
            + "\n  ".join(mismatches)
        )
