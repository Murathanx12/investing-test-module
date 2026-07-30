"""Segment capacity diagnostic — is there a retail-accessible shelf BELOW `small`?

Motivated by round 13 (AI_PANEL_2026-07-30): if the cost-killed cohort is empty
in large/mid, the natural appeal is "go smaller, where funds can't play." This
measures whether such a segment exists at the honest eligibility floors
(MIN_PRICE $1, MIN_MEDIAN_DOLLAR_VOLUME $200k/day) before anyone spends a
registration on it.

Answer, as of the 2002 CRSP panel: no. Reproduces the numbers quoted in
NEGATIVE_RESULTS §22, STATUS.md and the Paper-1 Exhibit A extension.

Usage:  python -m scripts.diag_segment_capacity
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

BANDS = [(0, 1000, "largemid"), (1000, 3000, "small"),
         (3000, 4000, "below-small"), (4000, 10**9, "far tail")]


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    elig = panel.eligible()
    n_elig = elig.sum(axis=1)
    dv = panel.monthly_dollar_vol.where(elig)
    rank = dv.rank(axis=1, ascending=False)

    out: dict = {
        "panel": "crsp_panel_2002",
        "months": int(len(n_elig)),
        "eligible_per_month": {
            "mean": round(float(n_elig.mean()), 1),
            "median": float(n_elig.median()),
            "min": int(n_elig.min()), "max": int(n_elig.max()),
        },
        "months_with_at_least_3000_eligible": int((n_elig >= 3000).sum()),
        "bands": {},
    }
    for lo, hi, label in BANDS:
        cnt = ((rank > lo) & (rank <= hi)).sum(axis=1)
        out["bands"][label] = {
            "rank_range": f"({lo},{hi}]",
            "mean_per_month": round(float(cnt.mean()), 1),
            "median_per_month": float(cnt.median()),
            "min_per_month": int(cnt.min()),
        }

    boundary = dv.apply(
        lambda row: row.nlargest(3000).iloc[-1] if row.notna().sum() >= 3000
        else np.nan, axis=1)
    out["median_adv_at_rank_3000_usd"] = round(float(boundary.median()), 0)
    out["min_names_per_month_gate"] = 100      # ScanConfig.min_names_per_month

    out["verdict"] = (
        "NO SHELF BELOW `small`: the band under dollar-volume rank 3000 holds a "
        f"median of {out['bands']['below-small']['median_per_month']:.0f} eligible "
        "names per month and is empty in "
        f"{out['months'] - out['months_with_at_least_3000_eligible']} of "
        f"{out['months']} months, far under the 100-name scan gate. The marginal "
        f"name at rank 3000 already trades a median "
        f"${out['median_adv_at_rank_3000_usd']:,.0f}/day — `small` IS the "
        "retail-accessible frontier at honest floors."
    )

    print(json.dumps(out, indent=2))
    (MODULE_ROOT / "data" / "factory" / "segment_capacity.json").write_text(
        json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
