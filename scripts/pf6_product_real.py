"""TRIAL-PF6-PRODUCT-REAL-1 — the book against the funds, not against a proxy.

Registered in TRIALS/PREREG_PF6_PRODUCT_REAL.md, committed 9b8ad30 before this
comparison ran. The decision rule is read from there; nothing is chosen here.

Mandatory disclosure per the execution standard's product-track amendment §(c)
is computed unconditionally, not on a pass: every negative regime block by name,
the worst calendar year, time underwater, and the FF5+UMD decomposition naming
which premia are being harvested.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.ERROR)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf import ledger as L
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "PF6"
ETF = MODULE_ROOT / "data" / "etf" / "etf_monthly_return.parquet"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"

CARRY = ("IJS", "VBR")                 # these decide
UNDERPOWERED = ("AVUV", "DFSV")        # registered as such before the numbers
REFERENCE = ("SPY", "IWM")


def blocks(ex: pd.Series) -> dict:
    """Per-regime-block excess, every negative one named. Standard §(c)."""
    out = {}
    for lab, lo, hi in (("2004-2007 expansion", "2004-01", "2007-09"),
                        ("2007-2009 GFC", "2007-10", "2009-03"),
                        ("2009-2015 recovery", "2009-04", "2015-12"),
                        ("2016-2019 late cycle", "2016-01", "2019-12"),
                        ("2020 COVID", "2020-01", "2020-12"),
                        ("2021-2022 inflation", "2021-01", "2022-12")):
        x = ex[(ex.index >= lo) & (ex.index <= hi)].dropna()
        if len(x) < 6:
            continue
        out[lab] = round(float((1 + x).prod() ** (12 / len(x)) - 1), 4)
    return out


def underwater(net: pd.Series) -> dict:
    cum = (1 + net).cumprod()
    dd = cum / cum.cummax() - 1.0
    uw = dd < -1e-9
    longest, run = 0, 0
    for f in uw:
        run = run + 1 if f else 0
        longest = max(longest, run)
    return {"max_drawdown": round(float(dd.min()), 4),
            "longest_underwater_months": int(longest),
            "share_of_months_underwater": round(float(uw.mean()), 3)}


def compare(net: pd.Series, other: pd.Series, label: str,
            factors: pd.DataFrame) -> dict:
    idx = net.index.intersection(other.dropna().index)
    a, b = net.reindex(idx), other.reindex(idx)
    d = (a - b).dropna()
    if len(d) < 10:
        return {"etf": label, "months": int(len(d)), "error": "overlap too short"}
    ruin = None
    cum = (1 + a).cumprod()
    ruin = bool((cum / cum.cummax() - 1.0).min() < -0.60)
    return {
        "etf": label,
        "months": int(len(d)),
        "window": [str(idx.min())[:7], str(idx.max())[:7]],
        "book_cagr": round(annualize(a), 4),
        "etf_cagr": round(annualize(b), 4),
        "excess_annualized": round(annualize(a) - annualize(b), 4),
        "t_paired_nw": D.nw_t(d),
        "mde_annualized": round(D.mde_annualized(d), 4),
        "book_maxdd": round(float((cum / cum.cummax() - 1).min()), 4),
        "book_breached_60pct_dd": ruin,
        "alpha_vs_etf_ff5_umd": D.alpha_report(d, factors, D.FF6),
        "negative_blocks": {k: v for k, v in blocks(d).items() if v < 0},
        "all_blocks": blocks(d),
        "worst_calendar_year": (
            lambda y: {"year": int(y.idxmin()), "excess": round(float(y.min()), 4)}
        )((1 + d).groupby(d.index.year).prod() - 1),
    }


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()
    d.update({"rebalance_months": 12, "cost_model": "ko",
              "name": "PF-PROF-COMPOSITE-150__ann_era"})
    spec = StrategySpec(**d)

    f = Factory()
    elig = f.eligible(spec.segment)
    score, _ = composite_score(f.lib, spec.signals, elig)
    era = D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())
    out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era)
    net = out["monthly"]["net"].dropna()
    net.index = net.index.to_period("M").to_timestamp("M")

    etf = pd.read_parquet(ETF)
    etf.index = etf.index.to_period("M").to_timestamp("M")

    res = {"trial": "TRIAL-PF6-PRODUCT-REAL-1",
           "prereg": "TRIALS/PREREG_PF6_PRODUCT_REAL.md",
           "prereg_commit": "9b8ad30",
           "book": {"spec_hash": spec.spec_hash(), "months": int(len(net)),
                    "cagr": round(annualize(net), 4), **underwater(net)},
           "deciding": {}, "underpowered_cannot_be_headline": {},
           "reference": {}}

    for t in CARRY:
        if t in etf:
            res["deciding"][t] = compare(net, etf[t], t, f.factors)
            r = res["deciding"][t]
            print(f"  {t}: {r.get('months')}mo excess "
                  f"{r.get('excess_annualized')} t {r.get('t_paired_nw')} "
                  f"MDE {r.get('mde_annualized')}", flush=True)
    for t in UNDERPOWERED:
        if t in etf:
            res["underpowered_cannot_be_headline"][t] = compare(
                net, etf[t], t, f.factors)
            r = res["underpowered_cannot_be_headline"][t]
            print(f"  [underpowered] {t}: {r.get('months')}mo excess "
                  f"{r.get('excess_annualized')} t {r.get('t_paired_nw')}",
                  flush=True)
    for t in REFERENCE:
        if t in etf:
            res["reference"][t] = compare(net, etf[t], t, f.factors)

    # ── the frozen decision rule ───────────────────────────────────────────
    dec = [res["deciding"].get(t, {}) for t in CARRY]
    ok = [x for x in dec if "t_paired_nw" in x]
    if len(ok) < len(CARRY):
        verdict, why = "UNRESOLVED", "a deciding fund did not produce a comparison"
    elif all(x["t_paired_nw"] >= 2.0 for x in ok) and \
            not any(x["book_breached_60pct_dd"] for x in ok):
        verdict, why = "PRODUCT EDGE SHOWN", (
            "beats both deciding funds at t >= 2.0 within the ruin constraint")
    elif any(x["t_paired_nw"] <= -2.0 for x in ok):
        verdict, why = "NO PRODUCT EDGE SHOWN", (
            "the paired difference against a deciding fund is negative at "
            "t <= -2.0")
    else:
        mdes = ", ".join(f"{x['etf']} {x['mde_annualized']:.2%}" for x in ok)
        verdict, why = "UNRESOLVED", (
            f"neither bar is reached. The comparison could not have detected a "
            f"difference smaller than: {mdes}. Per the NIGHT-5 amendment this "
            "null is published WITH its detectable effect size and may not be "
            "written as 'no difference'.")

    res["VERDICT"] = {"verdict": verdict, "reading": why,
                      "deciding_funds": list(CARRY)}
    res["multiple_testing"] = L.testing_block(
        max((x["t_paired_nw"] for x in ok), default=None))
    res["decision_branches_this_family"] = len(CARRY) + len(UNDERPOWERED)
    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "T1_PRODUCT_REAL.json").write_text(json.dumps(res, indent=2,
                                                         default=str),
                                              encoding="utf-8")
    print(json.dumps(res["VERDICT"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
