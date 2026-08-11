"""RE-AUDIT of the NIGHT-10 power audit, with the standard error it should have used.

NIGHT-10 concluded that this programme's standard adjudication shape cannot see
the effects it hunts, and made that conclusion enforceable by putting an MDE on
every scorecard. The conclusion was right. The arithmetic behind it was not
quite: both the audit (`audit_analyst_power.py`) and the shipped power block
divided by

    SE_iid = sigma / sqrt(n)

while every t-statistic printed on the same page came from Newey-West. Monthly
excess returns on a rebalanced book are serially correlated -- overlapping
holdings, momentum in the underlying, regime persistence -- so the two
estimators disagree, and the published detection thresholds were computed on the
one the same page refused to trust for inference.

This script re-runs the audit's OWN series builder and reports both. It changes
no verdict: every arm was already below its IID threshold, and the HAC
correction can only move thresholds up or leave them alone (the MDE takes
`max(HAC, IID)` -- see `scorecard._power_block` for why a below-IID HAC SE is
not banked as free power). So the direction of the correction is known in
advance: **the instruments are blinder than NIGHT-10 reported, not less blind.**
What was not known in advance is by how much, and that is what this measures.

Discipline carried over from the parent audit: the MEAN of each series is never
read here. The demeaning inside a variance estimator is not a result. The
`parent_reported_gross_pct` figures are quoted from the published verdict.

    python -m scripts.audit_power_hac

Writes runs/ARENA1/ANALYST_IDENT_1/power_audit_hac.json.
"""

from __future__ import annotations

import json
import logging
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.harness.benchmark import newey_west_tstat
from aegis_brain.pf.run import Factory
from scripts.audit_analyst_power import FIRST, LAST, PARENT, TOP_N, excess_series

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "ARENA1" / "ANALYST_IDENT_1"

#: Same constants as the scorecard, imported by value rather than by reference
#: only because this script must keep working if the scorecard is refactored.
MDE_Z = 2.8
SIG_Z = 1.96
HAC_LAGS = 12


def mde_both(fac, frame, segment: str, clock: int) -> dict:
    """IID and HAC detection thresholds for one arm, side by side.

    The HAC standard error of a sample mean is what `newey_west_tstat` divides
    by; it is now returned rather than re-derived, so this number and the t-stat
    on the parent's scorecard come from the same line of code.
    """
    ser = [v for _m, v in excess_series(fac, frame, segment, clock)]
    n = len(ser)
    if n < 12:
        return {"n_months": n, "note": "too few priced months"}

    s = pd.Series(ser, dtype=float)
    nw = newey_west_tstat(s, lags=HAC_LAGS)
    sd = float(s.std(ddof=1))

    se_iid = 100.0 * 12.0 * sd / math.sqrt(n)
    se_hac = 100.0 * 12.0 * float(nw["se"])
    se_bind = max(se_hac, se_iid)
    return {
        "n_months": n,
        "monthly_excess_sd_pct": round(100 * sd, 3),
        "se_annual_pct_iid": round(se_iid, 3),
        "se_annual_pct_hac": round(se_hac, 3),
        "hac_over_iid": round(se_hac / se_iid, 3) if se_iid > 0 else None,
        "se_annual_pct": round(se_bind, 3),
        "mde_estimator": "HAC" if se_hac >= se_iid else "IID (HAC fell below it)",
        "sig_threshold_annual_pct": round(SIG_Z * se_hac, 2),
        "mde_annual_pct_iid": round(MDE_Z * se_iid, 2),
        "mde_annual_pct_hac": round(MDE_Z * se_hac, 2),
        "mde_annual_pct": round(MDE_Z * se_bind, 2),
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    fac = Factory(FIRST, LAST, out_dir=OUT)
    frames = fac.lib._ibes()

    rows = []
    for (key, seg, clock), reported in PARENT.items():
        m = mde_both(fac, frames[key], seg, clock)
        se = m.get("se_annual_pct")
        thr = m.get("mde_annual_pct")
        t = None if not se else round(reported / se, 2)
        rows.append({
            "signal": key, "segment": seg, "clock_months": clock,
            "parent_reported_gross_pct": reported, **m,
            "implied_t": t,
            "significant_at_5pct": (
                None if not m.get("sig_threshold_annual_pct")
                else bool(abs(reported) >= m["sig_threshold_annual_pct"])),
            "above_80pct_power_mde_iid": (
                None if not m.get("mde_annual_pct_iid")
                else bool(abs(reported) >= m["mde_annual_pct_iid"])),
            "above_80pct_power_mde": (
                None if not thr else bool(abs(reported) >= thr)),
        })
        logger.info("%-24s %-8s m%d: MDE iid %5.2f -> hac %5.2f (x%.2f) | "
                    "reported %+.2f | above MDE %s",
                    key, seg, clock, m.get("mde_annual_pct_iid", float("nan")),
                    m.get("mde_annual_pct_hac", float("nan")),
                    m.get("hac_over_iid") or float("nan"), reported,
                    rows[-1]["above_80pct_power_mde"])

    ratios = [r["hac_over_iid"] for r in rows if r.get("hac_over_iid")]
    inflation = [r["mde_annual_pct"] / r["mde_annual_pct_iid"]
                 for r in rows if r.get("mde_annual_pct_iid")]
    payload = {
        "audit": "HAC RE-AUDIT of the ANALYST-IBES-1 power audit",
        "supersedes": "runs/ARENA1/ANALYST_IDENT_1/power_audit.json",
        "why": ("the parent audit and the shipped CANON 19 power block both "
                "used SE_iid while every t-stat beside them was Newey-West"),
        "window": [FIRST, LAST], "top_n": TOP_N, "hac_lags": HAC_LAGS,
        "method": ("same excess_series() as the parent audit; MDE = 2.8 x "
                   "max(SE_hac, SE_iid) annualised. The MEAN of each series is "
                   "never read -- this is a power calculation, not a result."),
        "accrues_to_denominator": 0,
        "rows": rows,
        "n_arms": len(rows),
        "n_above_80pct_power_mde_iid": sum(
            1 for r in rows if r["above_80pct_power_mde_iid"]),
        "n_above_80pct_power_mde": sum(
            1 for r in rows if r["above_80pct_power_mde"]),
        "hac_over_iid_range": [round(min(ratios), 3), round(max(ratios), 3)],
        "mde_inflation_range": [round(min(inflation), 3), round(max(inflation), 3)],
        "mde_range_pct_iid": [min(r["mde_annual_pct_iid"] for r in rows),
                              max(r["mde_annual_pct_iid"] for r in rows)],
        "mde_range_pct": [min(r["mde_annual_pct"] for r in rows),
                          max(r["mde_annual_pct"] for r in rows)],
    }
    (OUT / "power_audit_hac.json").write_text(
        json.dumps(payload, indent=1), encoding="utf-8")
    logger.info("MDE range: IID %s -> binding %s (inflation %s)",
                payload["mde_range_pct_iid"], payload["mde_range_pct"],
                payload["mde_inflation_range"])
    logger.info("arms above their own MDE: %d of %d (was %d of %d under IID)",
                payload["n_above_80pct_power_mde"], len(rows),
                payload["n_above_80pct_power_mde_iid"], len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
