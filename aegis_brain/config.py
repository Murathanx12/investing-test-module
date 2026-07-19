"""Paths and constants for the Investor Brain module.

The EODHD archive lives inside the main aegis-finance checkout and is treated as
STRICTLY READ-ONLY. Nothing in this module may write under AEGIS_FINANCE_ROOT.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Locations ────────────────────────────────────────────────────────────
MODULE_ROOT = Path(__file__).resolve().parents[1]

AEGIS_FINANCE_ROOT = Path(
    os.environ.get("AEGIS_FINANCE_ROOT", r"C:\Users\mrthn\aegis-finance")
)
EODHD_ROOT = Path(
    os.environ.get("AEGIS_EODHD_ROOT", str(AEGIS_FINANCE_ROOT / "engine" / "data" / "eodhd"))
)

TRIALS_DIR = MODULE_ROOT / "TRIALS"
RUNS_DIR = MODULE_ROOT / "runs"  # gitignored run artifacts

# ── Panel window ─────────────────────────────────────────────────────────
# The EODHD acceptance gate (V5) only validated delisting coverage for 2017+
# deaths (12/12 audit names); pre-2016 coverage FAILED (14/20). The
# survivorship-safe window therefore starts here.
PANEL_START = "2017-01-01"

# ── Universe hygiene defaults ────────────────────────────────────────────
# Microcap-tilted by design (that's where surviving anomalies live), but with
# floors that keep us out of untradeable penny-stock noise.
MIN_PRICE = 1.0                # dollars, at formation date
MIN_MEDIAN_DOLLAR_VOLUME = 200_000.0   # 63-day median daily dollar volume

# ── Cost model defaults ──────────────────────────────────────────────────
# One-way cost in basis points applied to turnover. Deliberately punitive for
# a microcap book: 25 bps one-way ≈ spread + impact for small size in
# $200k+/day names. A signal that dies at 25 bps was never real for us.
COST_BPS_ONE_WAY = 25.0

# ── Delisting convention ─────────────────────────────────────────────────
# EODHD histories simply END at delisting — no delisting return is provided
# (CRSP has one; that's part of the WRDS unlock). Until then we apply the
# Shumway (1997) convention: a held name whose history ends gets this return
# in its final month. Conservative for long books.
DELIST_RETURN = -0.30

# ── Multiple-testing base count ──────────────────────────────────────────
# The main aegis-finance registry stood at 14 cumulative trials at V5 close
# (2026-07-19). Local trials deflate against base + local count. Never lower.
MAIN_REPO_TRIAL_BASE = 14
