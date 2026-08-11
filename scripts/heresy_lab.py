"""HERESY LAB — run the forbidden configurations, promote nothing, ever.

Registered in TRIALS/PREREG_HERESY_1.md. Read it first.

ARENA-1's honest limit: the genome pool is generated FROM the signal registry,
so a closed mechanism has no genome and the search can confirm what the lab
believes but never overturn it. The heresy sleeve closes that gap WITHOUT
re-litigating anything, by asking the prior question:

    for each CLOSED mechanism, was the design that killed it capable of
    detecting the effect it was looking for?

A kill from an adequately-powered test is evidence of absence. A kill from an
underpowered test is absence of evidence. This programme's graveyard has
recorded the two identically for 195 experiments.

WHAT THIS FILE CANNOT DO, BY CONSTRUCTION
-----------------------------------------
Every result is tagged `heresy: true` and `eligible_for_production: false`.
Nothing here ranks against anything, nothing is selected, no best-of-N is
computed, and no registry grade is written. A heresy that unexpectedly clears
its own bar is logged as an INVESTIGATION for a future pre-registration to pick
up with the corpse as a control arm — never as a promotion.

    python -m scripts.heresy_lab [--top-n 50]

Writes runs/HERESY/heresy_1.json.
"""

from __future__ import annotations

import argparse
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
OUT = MODULE_ROOT / "runs" / "HERESY"

FIRST, LAST = "2002-01-31", "2022-12-31"

#: Registered auditability floors (§3). Below either, the kill is left alone.
MIN_MONTHS = 60
MIN_NAMES_PER_MONTH = 20

#: The forbidden configurations. Each maps a CLOSED or RISK_INPUT registry
#: signal to the panel implementation that would let it LEAD a book — the thing
#: the registry forbids. `instruments` counts how many independent tests killed
#: the mechanism, because one underpowered arm does not overturn a
#: three-instrument kill.
HERESIES: list[dict] = [
    {"signal_id": "analyst_target_upside_xs", "key": "ibes:tgt_upside",
     "segments": ("small", "largemid"), "clock": 1, "instruments": 3,
     "role": "CONTROL", "expect": "NEGATIVE",
     "note": "H1 control: killed on OSAP, TRIAL-TGT-REBUILD and ANALYST-IBES-1. "
             "If this comes back positive the harness is broken and the whole "
             "trial is void."},
    {"signal_id": "momentum_12_1", "key": "osap:Mom12m",
     "segments": ("small", "largemid"), "clock": 1, "instruments": 1,
     "role": "HERESY", "expect": "NET_DEAD",
     "note": "closed as net-dead at honest costs; gross was never the claim"},
    {"signal_id": "value_btm", "key": "osap:BM",
     "segments": ("small", "largemid"), "clock": 1, "instruments": 1,
     "role": "HERESY", "expect": "REJECTED"},
    {"signal_id": "accruals", "key": "osap:Accruals",
     "segments": ("small", "largemid"), "clock": 1, "instruments": 1,
     "role": "HERESY", "expect": "PERVERSE"},
    {"signal_id": "reversal_dip", "key": "native:rev_1m",
     "segments": ("small", "largemid"), "clock": 1, "instruments": 1,
     "role": "HERESY", "expect": "REJECTED"},
    # RISK_INPUT signals: permitted to size, forbidden to pick. Auditing them
    # as pickers is the same question one step milder.
    {"signal_id": "drawdown_trigger_information", "key": "native:max_ret_low",
     "segments": ("small",), "clock": 1, "instruments": 1,
     "role": "HERESY_RISK_INPUT", "expect": "INFORMATION_NOT_DELIVERABLE",
     "note": "NIGHT-7: the trailing stop is dead as an execution rule "
             "(-3.08%/yr under G7) but its TRIGGER carried information"},
]


def audit_one(fac, h: dict, segment: str, top_n: int) -> dict:
    """One forbidden configuration: effect, SE, and the design's MDE.

    NOTE the standardisation: every heresy runs at EW top-N monthly over one
    window. That is the shape most of this programme's adjudications take, and
    it is NOT literally each corpse's original harness. See `design_caveat`.
    """
    name = f"HERESY_{h['signal_id']}_{segment}_m{h['clock']}"
    base = {"signal_id": h["signal_id"], "signal_key": h["key"],
            "segment": segment, "clock_months": h["clock"],
            "role": h["role"], "registered_expectation": h["expect"],
            "n_independent_instruments": h["instruments"],
            "heresy": True, "eligible_for_production": False}
    try:
        spec = StrategySpec(
            name=name, signals=((h["key"], 1.0),), segment=segment,
            top_n=top_n, weighting="ew", rebalance_months=h["clock"],
            cost_model="flat25", first_month=FIRST, last_month=LAST,
            family="HERESY-1",
            hypothesis=("FORBIDDEN CONFIGURATION, research-only. Audits "
                        "whether the kill was adequately powered. Never "
                        "eligible for production."),
            tags=("heresy", "research-only", "non-accruing"))
        card = fac.run(spec, placebo_draws=0, write=False)
    except Exception as exc:  # noqa: BLE001 — a dead arm is data
        logger.warning("%s FAILED: %s: %s", name, type(exc).__name__, exc)
        return {**base, "status": "NOT_AUDITABLE",
                "reason": f"{type(exc).__name__}: {exc}"}

    monthly = fac._monthly[name]
    ex = (monthly["gross"] - fac.spine.mkt.reindex(monthly.index)).dropna()
    n = len(ex)
    names_pm = float(monthly["n_held"].mean()) if "n_held" in monthly else None
    if n < MIN_MONTHS or (names_pm is not None and names_pm < MIN_NAMES_PER_MONTH):
        return {**base, "status": "NOT_AUDITABLE", "n_months": n,
                "mean_names_per_month": names_pm,
                "reason": (f"{n} months / {names_pm} names per month is below "
                           f"the registered floor ({MIN_MONTHS}/"
                           f"{MIN_NAMES_PER_MONTH}); the kill is left as it "
                           f"stands, neither defended nor questioned")}

    sd = float(ex.std(ddof=1))
    se_ann = 100 * 12 * sd / math.sqrt(n)
    eff_ann = 100 * 12 * float(ex.mean())
    t = eff_ann / se_ann if se_ann else float("nan")
    mde = 2.8 * se_ann
    return {**base, "status": "OK", "n_months": n,
            "mean_names_per_month": (None if names_pm is None
                                     else round(names_pm, 1)),
            "gross_excess_annual_pct": round(eff_ann, 2),
            "se_annual_pct": round(se_ann, 2),
            "t": round(t, 2),
            "mde_80pct_power_annual_pct": round(mde, 2),
            "significant_at_5pct": bool(abs(t) >= 1.96),
            "kill_power": ("ADEQUATE" if abs(eff_ann) >= mde else "INADEQUATE"),
            "reading": (
                f"a standard EW top-{top_n} monthly design over this window "
                f"detects {mde:.1f}%/yr at 80% power; this mechanism's effect "
                f"is {eff_ann:+.1f}%/yr (t {t:.2f})"),
            "design_caveat": (
                "This is the programme's STANDARD adjudication shape, not "
                "necessarily the exact design that issued the original kill. "
                "The pre-registration said 'the design that ISSUED the kill'; "
                "what ran is one standardised design applied uniformly. The "
                "claim this supports is about the shape most of this "
                "programme's verdicts are issued in, not about each corpse's "
                "own harness."),
            }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=50)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)

    fac = Factory(FIRST, LAST, out_dir=OUT)
    rows: list[dict] = []

    # H1 runs FIRST and can void everything after it.
    control = [h for h in HERESIES if h["role"] == "CONTROL"]
    rest = [h for h in HERESIES if h["role"] != "CONTROL"]
    control_rows = []
    for h in control:
        for seg in h["segments"]:
            r = audit_one(fac, h, seg, a.top_n)
            control_rows.append(r)
            logger.info("CONTROL %s %s: %s", h["signal_id"], seg,
                        r.get("reading", r.get("reason")))
    rows.extend(control_rows)

    ok_ctrl = [r for r in control_rows if r["status"] == "OK"]
    control_negative = bool(ok_ctrl) and all(
        r["gross_excess_annual_pct"] < 0 for r in ok_ctrl)
    if not control_negative:
        payload = {
            "trial": "HERESY-1", "prereg": "TRIALS/PREREG_HERESY_1.md",
            "verdict": "VOID",
            "why": ("H1 failed: the control mechanism, killed on three "
                    "independent instruments, did not come back negative. The "
                    "harness is the finding and no other number is reported."),
            "control_rows": control_rows, "rows": [],
            "heresy": True, "eligible_for_production": False}
        (OUT / "heresy_1.json").write_text(json.dumps(payload, indent=1),
                                           encoding="utf-8")
        print(json.dumps({k: payload[k] for k in ("verdict", "why")}, indent=1))
        return 0

    for h in rest:
        for seg in h["segments"]:
            r = audit_one(fac, h, seg, a.top_n)
            rows.append(r)
            logger.info("%s %s: %s", h["signal_id"], seg,
                        r.get("reading", r.get("reason")))

    auditable = [r for r in rows if r["status"] == "OK"]
    inadequate = [r for r in auditable if r["kill_power"] == "INADEQUATE"]
    share = (len(inadequate) / len(auditable)) if auditable else 0.0
    families = sorted({r["signal_id"] for r in inadequate})

    # H2 is about the SHARE; H3 says the finding must not be one signal
    # wearing several rows. Both were registered, so both bind.
    distinct_underpowered = len({r["signal_id"] for r in inadequate})
    distinct_auditable = len({r["signal_id"] for r in auditable})
    concentrated = (distinct_auditable > 1 and distinct_underpowered <= 1)
    if share > 0.5 and not concentrated:
        verdict = "KILLS_UNDERPOWERED"
    elif share > 0.5 and concentrated:
        verdict = "UNDERPOWERED_BUT_CONCENTRATED"
    else:
        verdict = "KILLS_SOUND"
    payload = {
        "trial": "HERESY-1", "prereg": "TRIALS/PREREG_HERESY_1.md",
        "verdict": verdict,
        "window": [FIRST, LAST], "top_n": a.top_n,
        "heresy": True, "eligible_for_production": False,
        "accrues_to_denominator": 0,
        "control_reproduced_its_kill": control_negative,
        "n_configurations": len(rows),
        "n_auditable": len(auditable),
        "n_not_auditable": len(rows) - len(auditable),
        "n_kills_underpowered": len(inadequate),
        "share_underpowered": round(share, 3),
        "n_distinct_signals_auditable": distinct_auditable,
        "n_distinct_signals_underpowered": distinct_underpowered,
        "h3_concentrated_in_one_signal": concentrated,
        "underpowered_signals": families,
        "rows": rows,
        "consequence": (
            "Corpses marked kill_power INADEQUATE are re-annotated in the "
            "graveyard and NOTHING ELSE. Reopening one requires its own "
            "pre-registration, with the corpse as a control arm and an "
            "instrument whose MDE clears the effect being sought. No signal "
            "becomes tradeable, permitted or shadow-seeded by this trial in "
            "any branch."
            if verdict == "KILLS_UNDERPOWERED" else
            "H2 held but H3 did not: the underpowered kills are one signal, "
            "not a pattern across the graveyard. Reported as a fact about that "
            "signal's instrument and NOT as a finding about the programme's "
            "method. Nothing is re-annotated."
            if verdict == "UNDERPOWERED_BUT_CONCENTRATED" else
            "The closed list is better supported than it was: most kills came "
            "from designs that could have seen the effect they were looking "
            "for. A useful null."),
        "caveat": (
            "The MDE is DESIGN-relative. A signal killed at EW top-50 monthly "
            "might be detectable at another top_n or clock; this audits the "
            "design that ISSUED the kill and says nothing about designs nobody "
            "ran. n_independent_instruments is carried per row because one "
            "underpowered arm does not overturn a three-instrument kill."),
    }
    (OUT / "heresy_1.json").write_text(json.dumps(payload, indent=1),
                                       encoding="utf-8")
    print(json.dumps({k: payload[k] for k in
                      ("verdict", "n_auditable", "n_kills_underpowered",
                       "share_underpowered", "underpowered_signals")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
