"""POWER AUDIT of ANALYST-IBES-1, run through the PARENT'S OWN instrument.

A first attempt (`audit_analyst_power.py`) reconstructed the books by hand and
was WITHDRAWN: it reproduced A2 to within 0.7 points but missed A3 monthly by
7.0 and the levels arm by 16.5, so its paired test compared a different pair of
books than the parent's and its t = 0.03 said nothing about the parent's claim.
That failure is kept in the repo as the receipt for why this file exists.

This version runs the parent's exact `StrategySpec`s through `pf.run.Factory`
and reads `Factory._monthly[name]`, so the instrument IS the parent's. It then
asks two questions the parent never asked of itself:

  1. For each arm, what is the standard error of the reported effect — i.e. was
     the trial powered to see the numbers it published?
  2. Is the small-segment A2-vs-A3 "sign disagreement", which the parent treated
     as a REFUTATION of its registered prediction 5, distinguishable from zero
     when tested on the paired monthly series?

Neither question runs a new strategy or searches for a winner: both re-measure
arms that already exist. Accrues ZERO to the search denominator.

    python -m scripts.audit_analyst_power2

Writes runs/ARENA1/ANALYST_IDENT_1/power_audit_factory.json.
"""

from __future__ import annotations

import json
import logging
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.run import Factory
from aegis_brain.pf.spec import StrategySpec

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "ARENA1" / "ANALYST_IDENT_1"

FIRST, LAST = "2002-01-31", "2022-12-31"
TOP_N = 50

# (arm, signal key, segment, clock, the parent's published GROSS excess %/yr)
ARMS = [
    ("A2_tgt_rev_breadth", "ibes:tgt_rev_breadth", "small", 1, 6.05),
    ("A2_tgt_rev_breadth", "ibes:tgt_rev_breadth", "small", 3, 3.53),
    ("A2_tgt_rev_breadth", "ibes:tgt_rev_breadth", "largemid", 1, 2.57),
    ("A2_tgt_rev_breadth", "ibes:tgt_rev_breadth", "largemid", 3, 1.54),
    ("A3_tgt_rev_3m", "ibes:tgt_rev_3m", "small", 1, -0.73),
    ("A3_tgt_rev_3m", "ibes:tgt_rev_3m", "small", 3, -0.50),
    ("A3_tgt_rev_3m", "ibes:tgt_rev_3m", "largemid", 1, 5.94),
    ("A3_tgt_rev_3m", "ibes:tgt_rev_3m", "largemid", 3, 3.05),
    ("A1_tgt_upside", "ibes:tgt_upside", "small", 1, -16.70),
    ("A1_tgt_upside", "ibes:tgt_upside", "largemid", 1, -8.60),
]

#: How far the reconstruction may sit from the published number before the
#: instrument is declared unfaithful and its verdicts withheld.
FIDELITY_TOL_PCT = 1.5


def _spec(name, key, seg, clock) -> StrategySpec:
    return StrategySpec(
        name=name, signals=((key, 1.0),), segment=seg, top_n=TOP_N,
        weighting="ew", rebalance_months=clock, cost_model="flat25",
        first_month=FIRST, last_month=LAST, family="ANALYST-POWER-AUDIT",
        hypothesis="re-measurement of an existing arm; no new search",
        tags=("analyst", "ibes", "audit", "non-accruing"))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    import numpy as np

    fac = Factory(FIRST, LAST, out_dir=OUT)
    rows, series = [], {}

    for arm, key, seg, clock, published in ARMS:
        name = f"AUDIT_{arm}_{seg}_m{clock}"
        card = fac.run(_spec(name, key, seg, clock), placebo_draws=0, write=False)
        monthly = fac._monthly[name]
        gross = card["implementation"].get("gross_cagr")
        bench = card["headline"].get("benchmark_cagr")
        recomputed = None if gross is None or bench is None else 100 * (gross - bench)

        # the arm's monthly excess series, from the Factory's own book
        # the book's GROSS monthly return; the parent's gross numbers are the
        # ones under audit, so costs stay out of the dispersion
        r = monthly["gross"]
        mkt = fac.spine.mkt.reindex(monthly.index)
        ex = (r - mkt).dropna()
        series[(arm, seg, clock)] = ex
        n = len(ex)
        sd = float(ex.std(ddof=1))
        se_ann = 100 * 12 * sd / math.sqrt(n)
        t = (100 * 12 * float(ex.mean())) / se_ann if se_ann else float("nan")
        drift = (None if recomputed is None
                 else round(abs(recomputed - published), 2))
        rows.append({
            "arm": arm, "signal": key, "segment": seg, "clock_months": clock,
            "published_gross_pct": published,
            "recomputed_gross_pct": (None if recomputed is None
                                     else round(recomputed, 2)),
            "fidelity_gap_pct": drift,
            "faithful": (None if drift is None else bool(drift <= FIDELITY_TOL_PCT)),
            "n_months": n,
            "monthly_excess_sd_pct": round(100 * sd, 3),
            "se_annual_pct": round(se_ann, 3),
            "mean_excess_annual_pct": round(100 * 12 * float(ex.mean()), 2),
            "t": round(t, 2),
            "significant_at_5pct": bool(abs(t) >= 1.96),
            "above_80pct_power_mde": bool(abs(100 * 12 * float(ex.mean()))
                                          >= 2.8 * se_ann),
        })
        logger.info("%s %s m%d: published %+.2f, recomputed %s (gap %s) | "
                    "t %.2f | sig %s | powered %s",
                    arm, seg, clock, published, rows[-1]["recomputed_gross_pct"],
                    drift, t, rows[-1]["significant_at_5pct"],
                    rows[-1]["above_80pct_power_mde"])

    unfaithful = [r for r in rows if r["faithful"] is False]

    # The disagreement, tested on the PAIRED series so the correlation between
    # the two books is handled exactly rather than assumed away.
    gap = None
    a2, a3 = series.get(("A2_tgt_rev_breadth", "small", 1)), \
        series.get(("A3_tgt_rev_3m", "small", 1))
    if a2 is not None and a3 is not None:
        common = a2.index.intersection(a3.index)
        d = (a2.reindex(common) - a3.reindex(common)).dropna()
        n = len(d)
        sd = float(d.std(ddof=1))
        se_ann = 100 * 12 * sd / math.sqrt(n)
        mean_ann = 100 * 12 * float(d.mean())
        t = mean_ann / se_ann if se_ann else float("nan")
        both_faithful = all(
            r["faithful"] for r in rows
            if (r["arm"], r["segment"], r["clock_months"]) in
            (("A2_tgt_rev_breadth", "small", 1), ("A3_tgt_rev_3m", "small", 1)))
        gap = {
            "test": "A2 minus A3, paired monthly excess, small segment, 1m clock",
            "n_paired_months": n,
            "series_correlation": round(float(a2.reindex(common).corr(
                a3.reindex(common))), 3),
            "mean_difference_annual_pct": round(mean_ann, 2),
            "se_annual_pct": round(se_ann, 2),
            "t": round(t, 2),
            "significant_at_5pct": bool(abs(t) >= 1.96),
            "both_arms_faithful": bool(both_faithful),
            "reading": (
                "The parent moved the small segment to UNRESOLVED because A2 and "
                "A3 disagreed in SIGN, treating that as a refutation of its "
                f"registered prediction 5. Tested on the paired monthly series "
                f"the difference is t = {t:.2f}. "
                + ("Two point estimates that differ by less than two standard "
                   "errors are not a contradiction — that is what two noisy "
                   "draws of one quantity look like."
                   if abs(t) < 1.96 else
                   "The difference IS distinguishable from zero, so the parent's "
                   "reading stands and the constructions really do disagree.")
                + (" NOTE: at least one arm did not reproduce its published "
                   "number within tolerance, so this test is reported and NOT "
                   "believed." if not both_faithful else "")),
        }

    payload = {
        "audit": "POWER AUDIT of ANALYST-IBES-1 (parent instrument)",
        "supersedes": "scripts/audit_analyst_power.py (hand-rolled books, WITHDRAWN)",
        "parent_verdict": "docs/ANALYST_IBES_1_VERDICT_2026-08-11.md",
        "window": [FIRST, LAST], "top_n": TOP_N,
        "accrues_to_denominator": 0,
        "fidelity_tolerance_pct": FIDELITY_TOL_PCT,
        "n_unfaithful_arms": len(unfaithful),
        "instrument_note": (
            "Arms rebuilt through pf.run.Factory with the parent's specs. Any "
            "arm whose recomputed gross excess sits more than "
            f"{FIDELITY_TOL_PCT} points from the published one is marked "
            "unfaithful and its power reading is not to be quoted."),
        "rows": rows,
        "n_arms": len(rows),
        "n_significant_at_5pct": sum(1 for r in rows if r["significant_at_5pct"]),
        "n_above_80pct_power_mde": sum(1 for r in rows
                                       if r["above_80pct_power_mde"]),
        "small_segment_disagreement": gap,
    }
    (OUT / "power_audit_factory.json").write_text(
        json.dumps(payload, indent=1), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in
                      ("n_arms", "n_unfaithful_arms", "n_significant_at_5pct",
                       "n_above_80pct_power_mde", "small_segment_disagreement")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
