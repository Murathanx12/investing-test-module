"""ANALYST-IDENT-1 — is the small-cap A2/A3 sign disagreement coverage churn?

Registered in TRIALS/PREREG_ANALYST_IDENT_1.md. Read it before reading a number
out of this script. Three things it says that matter here:

  * this trial accrues ZERO arms to the search denominator — it is a diagnostic
    of an UNRESOLVED verdict, not a search for a winner;
  * the DATA-QUALITY and POWER gates run BEFORE any arm, and a failure of
    either stops the trial with nothing quoted;
  * no outcome may change `allowed_in_pm` for any signal.

    python -m scripts.run_analyst_ident_1 [--top-n 50]

Writes runs/ARENA1/ANALYST_IDENT_1/*.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.run import Factory
from aegis_brain.pf.spec import StrategySpec

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "ARENA1" / "ANALYST_IDENT_1"

FIRST = "2002-01-31"
LAST = "2022-12-31"

# Registered gates (§3 of the prereg), fixed before any statistic.
MIN_CHURN_FREE_SHARE = 0.30
MIN_MONTHS = 60
MIN_NAMES_PER_MONTH = 20
MDE_TARGET_ANN = 0.040          # 4.0 %/yr
DISPUTED_GAP_ANN = 0.068        # the +6.05 vs -0.73 gap this must be able to see

ARMS = [
    ("A3_nochurn", "ibes:tgt_rev_3m_nochurn",
     "PRIMARY P1: A3 purged of coverage churn — registered POSITIVE in small"),
    ("A3_churn", "ibes:tgt_rev_3m_churn",
     "PRIMARY P2: A3 on churn months only — registered NEGATIVE in small"),
    ("A2_nochurn", "ibes:tgt_rev_breadth_nochurn",
     "PLACEBO P4: A2 is churn-blind by construction; the purge must barely move it"),
]
SEGMENTS = ("small", "largemid")


def _headline(card: dict) -> dict:
    h, imp, risk = card["headline"], card["implementation"], card["risk"]
    gross, bench = imp.get("gross_cagr"), h.get("benchmark_cagr")
    return {
        "excess_cagr_gross": (None if gross is None or bench is None
                              else round(100 * (gross - bench), 3)),
        "excess_cagr_net": round(100 * h["excess_cagr_net"], 3),
        "t_excess_monthly": round(h.get("t_excess_monthly", float("nan")), 3),
        "turnover_1way_annual": imp.get("turnover_1way_annual"),
        "mean_scored_names": (imp.get("signal_coverage") or {}).get(
            "mean_scored_names_per_month"),
        "n_months": card["window"].get("months"),
    }


def gate_data_quality(frames, numest) -> dict:
    """§6: if `numest` is not a clean integer count, `numest_t == numest_{t-3}`
    does not mean "the same analysts", and the whole purge is meaningless."""
    import numpy as np
    vals = numest.to_numpy(dtype="float64")
    finite = vals[np.isfinite(vals)]
    non_integer = float(np.mean(np.abs(finite - np.round(finite)) > 1e-9))
    d = (numest - numest.shift(3)).to_numpy(dtype="float64")
    d = d[np.isfinite(d)]
    mass_at_zero = float(np.mean(np.abs(d) < 1e-9)) if d.size else 0.0
    ok = non_integer < 0.01 and mass_at_zero > 0.05
    return {"check": "DATA_QUALITY", "pass": bool(ok),
            "non_integer_share": round(non_integer, 6),
            "mass_at_zero_delta_numest": round(mass_at_zero, 4),
            "reading": ("numest is a clean integer count with real mass at "
                        "zero change — the purge means what it says"
                        if ok else
                        "numest is not a clean integer count, or its 3m change "
                        "has no mass at zero: 'same count' cannot be read as "
                        "'same analysts'. Trial stops.")}


def gate_power(nochurn, numest, fac, segment: str = "small",
               top_n: int = 50) -> dict:
    """§3: retention floor + MDE, with the MDE computed the way it was
    registered — from the REALISED monthly dispersion of the churn-free
    subsample, not from an assumed constant.

    Only the DISPERSION of the arm's monthly excess series is read here, never
    its mean. Sizing a test off the noise is a power calculation; sizing it off
    the answer is peeking, and the two are kept apart deliberately.

    An underpowered purge cannot distinguish "churn is not the explanation"
    from "we could not have seen it either way", which is the whole point of
    gating before the arms rather than after.
    """
    import numpy as np
    both = numest.notna() & numest.shift(3).notna()
    share = float(nochurn.notna().sum().sum() / max(1, int(both.sum().sum())))
    per_month = nochurn.notna().sum(axis=1)
    good_months = int((per_month >= MIN_NAMES_PER_MONTH).sum())
    n_eff = float(per_month[per_month >= MIN_NAMES_PER_MONTH].mean() or 0.0)

    # Realised dispersion: form the same EW top-N book the arms will form, on
    # the churn-free signal, and read the SD of its monthly excess return.
    elig = fac.eligible(segment)
    sig = nochurn.reindex(index=elig.index, columns=elig.columns).where(elig)
    ret = fac.spine.panel.monthly_ret.reindex(
        index=elig.index, columns=elig.columns)
    bench = fac.spine.mkt.reindex(elig.index)
    excess = []
    for m_prev, m_now in zip(sig.index[:-1], sig.index[1:]):
        row = sig.loc[m_prev].dropna()
        if len(row) < MIN_NAMES_PER_MONTH:
            continue
        picks = row.nlargest(min(top_n, len(row))).index
        r = ret.loc[m_now, picks].dropna()
        if r.empty or not np.isfinite(bench.get(m_now, np.nan)):
            continue
        excess.append(float(r.mean()) - float(bench.loc[m_now]))
    n = len(excess)
    sd_m = float(np.std(excess, ddof=1)) if n > 2 else float("nan")
    # 2.8 = z(0.975) + z(0.80), the standard 80%-power two-sided constant
    mde_ann = (12.0 * 2.8 * sd_m / math.sqrt(n)) if n > 2 else float("inf")

    ok = (share >= MIN_CHURN_FREE_SHARE and good_months >= MIN_MONTHS
          and n > 2 and mde_ann <= MDE_TARGET_ANN)
    return {"check": "POWER", "pass": bool(ok),
            "churn_free_share": round(share, 4),
            "floor_share": MIN_CHURN_FREE_SHARE,
            "months_with_enough_names": good_months, "floor_months": MIN_MONTHS,
            "mean_names_per_retained_month": round(n_eff, 1),
            "realised_monthly_excess_sd": (None if not math.isfinite(sd_m)
                                           else round(sd_m, 5)),
            "n_months_priced": n,
            "mde_annual": (None if not math.isfinite(mde_ann)
                           else round(mde_ann, 4)),
            "mde_target": MDE_TARGET_ANN,
            "mde_basis": ("realised SD of the churn-free EW top-N monthly "
                          "excess series; the MEAN of that series was not read"),
            "disputed_gap": DISPUTED_GAP_ANN,
            "reading": (f"retains {share:.1%} of name-months over {good_months} "
                        f"months; realised MDE "
                        f"{'n/a' if not math.isfinite(mde_ann) else f'{mde_ann:.1%}'}"
                        f"/yr against a disputed gap of {DISPUTED_GAP_ANN:.1%}/yr"
                        + ("" if ok else " — BELOW THE REGISTERED GATE"))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=50)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    fac = Factory(FIRST, LAST, out_dir=OUT)
    # Reach the raw frames the gates need through the Factory's OWN signal
    # library, so the gates and the arms see byte-identical panels.
    frames = fac.lib._ibes()
    nochurn = frames["ibes:tgt_rev_3m_nochurn"]
    numest = _reload_numest(fac)

    gates = [gate_data_quality(frames, numest),
             gate_power(nochurn, numest, fac, "small", a.top_n)]
    for g in gates:
        logger.info("GATE %s: %s — %s", g["check"],
                    "PASS" if g["pass"] else "FAIL", g["reading"])
    if not all(g["pass"] for g in gates):
        payload = {"trial": "ANALYST-IDENT-1",
                   "prereg": "TRIALS/PREREG_ANALYST_IDENT_1.md",
                   "verdict": ("DATA_QUALITY" if not gates[0]["pass"]
                               else "POWER_FAILED"),
                   "gates": gates, "results": [],
                   "denominator_accruing": 0,
                   "note": ("Registered gate failed. No arm was run and no "
                            "number is quoted. The small segment stays "
                            "UNRESOLVED.")}
        (OUT / "results.json").write_text(json.dumps(payload, indent=1),
                                          encoding="utf-8")
        print(json.dumps({k: payload[k] for k in ("verdict", "note")}, indent=1))
        return 0

    results = []
    for arm, key, note in ARMS:
        for seg in SEGMENTS:
            name = f"AIDENT1_{arm}_{seg}_m3"
            spec = StrategySpec(
                name=name, signals=((key, 1.0),), segment=seg,
                top_n=a.top_n, weighting="ew", rebalance_months=3,
                cost_model="flat25", first_month=FIRST, last_month=LAST,
                family="ANALYST-IDENT-1", hypothesis=note,
                tags=("analyst", "ibes", "diagnostic", "non-accruing"))
            try:
                card = fac.run(spec, placebo_draws=0, write=True)
            except Exception as exc:  # noqa: BLE001 — a dead arm is data
                logger.error("%s FAILED: %s: %s", name, type(exc).__name__, exc)
                results.append({"arm": arm, "segment": seg, "status": "FAILED",
                                "error": f"{type(exc).__name__}: {exc}"})
                continue
            results.append({"arm": arm, "signal": key, "segment": seg,
                            "status": "OK", "spec_hash": card["spec_hash"],
                            **_headline(card)})

    payload = {
        "trial": "ANALYST-IDENT-1",
        "prereg": "TRIALS/PREREG_ANALYST_IDENT_1.md",
        "window": [FIRST, LAST], "top_n": a.top_n,
        "denominator_accruing": 0,
        "denominator_note": ("diagnostic of an UNRESOLVED verdict; accrues "
                             "nothing to the search denominator by pre-registration"),
        "gates": gates,
        "runtime_secs": round(time.time() - t0, 1),
        "results": results,
        "parent_control": {
            "note": "ANALYST-IBES-1, same window/segment/top_n — the control",
            "A2_small_1m_gross": 6.05, "A3_small_1m_gross": -0.73,
            "A2_small_3m_gross": 3.53, "A3_small_3m_gross": -0.50,
            "A2_largemid_3m_gross": 1.54, "A3_largemid_3m_gross": 3.05,
        },
    }
    (OUT / "results.json").write_text(json.dumps(payload, indent=1),
                                      encoding="utf-8")
    print(json.dumps(payload["results"], indent=1))
    return 0


def _reload_numest(fac):
    """numest on the same monthly grid the signals use."""
    from aegis_brain.data import ibes_panel as ip
    panel = fac.spine.panel
    ptg = ip._require("ptgsumu")[["ticker", "statpers", "numest"]].copy()
    import pandas as pd
    ptg["statpers"] = pd.to_datetime(ptg["statpers"])
    ptg, _rate = ip._attach_permno(ptg, "statpers")
    ptg["month"] = ip._to_month_end(ptg["statpers"])
    ptg["numest"] = pd.to_numeric(ptg["numest"], errors="coerce")
    idx = panel.monthly_ret.index
    cols = panel.monthly_ret.columns
    return ip._grid(ptg, "numest", idx, cols)


if __name__ == "__main__":
    raise SystemExit(main())
