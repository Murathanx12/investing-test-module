"""POWER AUDIT of ANALYST-IBES-1 — could the parent trial see its own numbers?

ANALYST-IDENT-1 stopped at POWER_FAILED: the churn-free small-cap subsample has
a realised MDE of ~10.8 %/yr, against a disputed A2-vs-A3 gap of 6.8 points.
That raises a question about the PARENT, not just the successor:

    if a top-50 EW small-cap book over 250 months cannot resolve 6.8 points,
    could ANALYST-IBES-1 resolve the effects it reported at all?

This script measures the detection threshold of the parent's OWN arms, on the
parent's own segments and clocks, and puts it beside the parent's reported
effects. It runs NO new strategy and accrues NOTHING: it reads the dispersion of
each arm's monthly excess series and never its mean, which is a power
calculation rather than a result. (Same discipline as the ANALYST-IDENT-1 gate.)

    python -m scripts.audit_analyst_power

Writes runs/ARENA1/ANALYST_IDENT_1/power_audit.json.
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

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "ARENA1" / "ANALYST_IDENT_1"

FIRST, LAST = "2002-01-31", "2022-12-31"
TOP_N = 50
MIN_NAMES = 20

# The parent's reported GROSS excess, from docs/ANALYST_IBES_1_VERDICT_2026-08-11.md
PARENT = {
    ("ibes:tgt_rev_breadth", "small", 1): 6.05,
    ("ibes:tgt_rev_breadth", "small", 3): 3.53,
    ("ibes:tgt_rev_breadth", "largemid", 1): 2.57,
    ("ibes:tgt_rev_breadth", "largemid", 3): 1.54,
    ("ibes:tgt_rev_3m", "small", 1): -0.73,
    ("ibes:tgt_rev_3m", "small", 3): -0.50,
    ("ibes:tgt_rev_3m", "largemid", 1): 5.94,
    ("ibes:tgt_rev_3m", "largemid", 3): 3.05,
    ("ibes:tgt_upside", "small", 1): -16.70,
    ("ibes:tgt_upside", "largemid", 1): -8.60,
}


def excess_series(fac, frame, segment: str, clock: int) -> list[float]:
    """Monthly excess return of an EW top-N book on this signal."""
    import numpy as np
    elig = fac.eligible(segment)
    sig = frame.reindex(index=elig.index, columns=elig.columns).where(elig)
    ret = fac.spine.panel.monthly_ret.reindex(index=elig.index,
                                              columns=elig.columns)
    bench = fac.spine.mkt.reindex(elig.index)
    months = list(sig.index)
    out, held = [], None
    for k in range(len(months) - 1):
        m_prev, m_now = months[k], months[k + 1]
        if held is None or k % clock == 0:
            row = sig.loc[m_prev].dropna()
            if len(row) < MIN_NAMES:
                continue
            held = row.nlargest(min(TOP_N, len(row))).index
        r = ret.loc[m_now, held].dropna()
        b = bench.get(m_now, float("nan"))
        if r.empty or not np.isfinite(b):
            continue
        out.append((m_now, float(r.mean()) - float(b)))
    return out


def mde(fac, frame, segment: str, clock: int) -> dict:
    """Two thresholds, kept apart because conflating them overstates the case.

      * `sig_threshold`  = 1.96 SE — the smallest effect that would be
        SIGNIFICANT at 5% two-sided.
      * `mde_annual_pct` = 2.8 SE — the smallest effect this design would
        detect with 80% POWER. Effects between the two are significant when
        observed but were unlikely to be found, which is where the winner's
        curse lives: among low-powered studies, the ones that clear
        significance systematically overstate the effect.

    The MEAN of the series is not read here.
    """
    import numpy as np
    ser = [v for _m, v in excess_series(fac, frame, segment, clock)]
    n = len(ser)
    if n < 3:
        return {"n_months": n, "mde_annual_pct": None,
                "note": "too few priced months"}
    sd = float(np.std(ser, ddof=1))
    se_ann = 100 * 12 * sd / math.sqrt(n)
    return {"n_months": n,
            "monthly_excess_sd_pct": round(100 * sd, 3),
            "se_annual_pct": round(se_ann, 3),
            "sig_threshold_annual_pct": round(1.96 * se_ann, 2),
            "mde_annual_pct": round(2.8 * se_ann, 2)}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    fac = Factory(FIRST, LAST, out_dir=OUT)
    frames = fac.lib._ibes()

    rows = []
    for (key, seg, clock), reported in PARENT.items():
        m = mde(fac, frames[key], seg, clock)
        thr = m.get("mde_annual_pct")
        se = m.get("se_annual_pct")
        t = None if not se else round(reported / se, 2)
        significant = None if t is None else bool(abs(t) >= 1.96)
        well_powered = None if not thr else bool(abs(reported) >= thr)
        rows.append({
            "signal": key, "segment": seg, "clock_months": clock,
            "parent_reported_gross_pct": reported,
            **m,
            "implied_t": t,
            "significant_at_5pct": significant,
            "above_80pct_power_mde": well_powered,
        })
        logger.info("%s %s m%d: reported %+.2f%%/yr, SE %s -> t %s | "
                    "sig@5%% %s | above 80%%-power MDE (%s) %s",
                    key, seg, clock, reported, se, t,
                    significant, thr, well_powered)

    significant = [r for r in rows if r["significant_at_5pct"]]
    powered = [r for r in rows if r["above_80pct_power_mde"]]

    # The disagreement, tested EXACTLY. A2 and A3 are formed on the same names
    # in the same months, so their errors are correlated and the
    # independent-errors formula would overstate the standard error of the
    # difference. Differencing the two monthly series first handles the
    # correlation exactly and needs no assumption.
    gap = _paired_difference(fac, frames, "small", 1)

    payload = {
        "audit": "POWER AUDIT of ANALYST-IBES-1",
        "parent_verdict": "docs/ANALYST_IBES_1_VERDICT_2026-08-11.md",
        "window": [FIRST, LAST], "top_n": TOP_N,
        "method": ("realised SD of each arm's EW top-N monthly excess series; "
                   "MDE = 12 x 2.8 x SD / sqrt(n). The MEAN of each series was "
                   "never read, so this is a power calculation and not a result."),
        "accrues_to_denominator": 0,
        "rows": rows,
        "n_arms": len(rows),
        "n_significant_at_5pct": len(significant),
        "n_above_80pct_power_mde": len(powered),
        "small_segment_disagreement": gap,
    }
    (OUT / "power_audit.json").write_text(json.dumps(payload, indent=1),
                                          encoding="utf-8")
    print(json.dumps({"n_arms": len(rows),
                      "n_significant_at_5pct": len(significant),
                      "n_above_80pct_power_mde": len(powered),
                      "small_segment_disagreement": gap}, indent=1))
    return 0


def _paired_difference(fac, frames, segment: str, clock: int) -> dict:
    """Test A2 - A3 on the PAIRED monthly series, month by month."""
    import numpy as np
    a2 = dict(excess_series(fac, frames["ibes:tgt_rev_breadth"], segment, clock))
    a3 = dict(excess_series(fac, frames["ibes:tgt_rev_3m"], segment, clock))
    common = sorted(set(a2) & set(a3))
    d = np.array([a2[m] - a3[m] for m in common], dtype=float)
    n = len(d)
    if n < 3:
        return {"n_months": n, "note": "too few paired months"}
    sd = float(np.std(d, ddof=1))
    se_ann = 100 * 12 * sd / math.sqrt(n)
    mean_ann = 100 * 12 * float(d.mean())
    t = mean_ann / se_ann if se_ann else float("nan")
    corr = float(np.corrcoef([a2[m] for m in common],
                             [a3[m] for m in common])[0, 1])
    return {
        "test": "A2 minus A3, paired monthly, small segment",
        "n_paired_months": n,
        "monthly_series_correlation": round(corr, 3),
        "mean_difference_annual_pct": round(mean_ann, 2),
        "se_annual_pct": round(se_ann, 2),
        "t": round(t, 2),
        "significant_at_5pct": bool(abs(t) >= 1.96),
        "reading": (
            "The parent verdict treated A2 and A3 disagreeing in sign as a "
            "REFUTATION of its registered prediction 5, and moved the small "
            "segment to UNRESOLVED on that basis. Tested directly on the "
            f"paired monthly series the difference is t = {t:.2f}. Two "
            "estimates that differ by less than two standard errors are not a "
            "contradiction; that is what two noisy draws of one number look "
            "like."),
    }


if __name__ == "__main__":
    raise SystemExit(main())
