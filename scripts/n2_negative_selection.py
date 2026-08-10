"""N2 — is refusing the worst worth more than picking the best?

TRIAL-N2-NEGATIVE-SELECTION-1. Across 179 candidates this factory only ever
tested picking the top. This is the first test of the opposite operation.

The veto acts on the ELIGIBLE SET at the annual rebalance, before selection. The
composite score is computed once and never changes — only which names it is
allowed to choose from. The book still holds 150 names, drawing deeper into the
ranking to replace what the veto removed, so "refusing the worst" is not
confounded with "holding fewer names".

  V0  none (control)            V3  bottom decile OScore (distress)
  V1  bottom decile Accruals    V4  union of V1-V3
  V2  bottom decile ShareIss1Y  V5  PLACEBO: random veto, size-matched to V4

V5 is read FIRST and is not optional. Any veto forces replacements, and a book
that holds different names for no reason will still post a different return.

Reported, never deciding.
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
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT8"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
SEED = 20260810
DECILE = 0.10
BAR = 0.015
VETOES = {"V1_accruals": "osap:Accruals",
          "V2_share_issuance": "osap:ShareIss1Y",
          "V3_distress": "osap:OScore"}


def veto_frame(lib, key: str, elig: pd.DataFrame) -> pd.DataFrame:
    """True where the name sits in the bottom decile of `key` among eligibles.

    The OSAP wide file is PRE-SIGNED (higher = higher predicted return), so the
    bottom decile is the unattractive end. A name with no value for the signal is
    NOT vetoed: absence of evidence is not evidence of distress, and vetoing on
    missingness would quietly veto the whole pre-Compustat era.
    """
    f = lib.get(key).where(elig)
    r = f.rank(axis=1, pct=True)
    return (r <= DECILE).where(r.notna(), False) & elig


def paired(a: pd.Series, b: pd.Series) -> dict:
    d = (a - b).dropna()
    if len(d) < 24:
        return {"months": int(len(d)), "insufficient": True}
    return {"months": int(len(d)),
            "annualized_pct": round(float(d.mean()) * 12, 4),
            "t_newey_west": D.nw_t(pd.Series(d.to_numpy()), lags=12),
            "mde_annualized": D.mde_annualized(d * 12),
            "correlation": round(float(a.corr(b)), 4)}


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()

    f = Factory()
    elig = f.eligible(d["segment"])
    score, _ = composite_score(f.lib, d["signals"], elig)
    era = D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())

    f.lib.preload(list(VETOES.values()))
    vetoes = {k: veto_frame(f.lib, v, elig) for k, v in VETOES.items()}
    union = None
    for v in vetoes.values():
        union = v if union is None else (union | v)
    vetoes["V4_union"] = union

    # PLACEBO: same number of names vetoed each month as V4, chosen at random
    n_by_month = union.sum(axis=1)
    cols = np.array(elig.columns)
    rand = pd.DataFrame(False, index=elig.index, columns=elig.columns)
    for m in elig.index:
        live = cols[elig.loc[m].to_numpy()]
        k = int(min(n_by_month.get(m, 0), len(live)))
        if k > 0:
            rand.loc[m, rng.choice(live, k, replace=False)] = True
    vetoes["V5_placebo_random"] = rand

    arms = {"V0_control": elig}
    for k, v in vetoes.items():
        arms[k] = elig & ~v

    # how much of the veto even bites? a name outside the top 150 was never
    # going to be bought, and vetoing it changes nothing
    base_spec = StrategySpec(**{**d, "rebalance_months": 12, "cost_model": "ko",
                                "name": "N2__V0_control"})
    H0: list[dict] = []
    out0 = run_book(f.spine.panel, score, elig, base_spec, f.spine.rf, era,
                    holdings_out=H0)
    held_by_month = {pd.Timestamp(h["test"]): set(h["weights"].index)
                     for h in H0 if h.get("rebalanced")}
    bite = {}
    for k, v in vetoes.items():
        hit, tot = 0, 0
        for m, held in held_by_month.items():
            if m not in v.index:
                continue
            row = set(np.array(v.columns)[v.loc[m].to_numpy()])
            hit += len(row & held)
            tot += len(held)
        bite[k] = {"vetoed_names_per_month": round(
            float(v.sum(axis=1).reindex(held_by_month).mean()), 1),
            "share_of_held_book_vetoed": round(hit / tot, 4) if tot else None}
        print(f"  {k:20s} vetoes {bite[k]['vetoed_names_per_month']:6.1f} "
              f"names/mo, {bite[k]['share_of_held_book_vetoed']:.3f} of the "
              f"held book", flush=True)

    monthly, diags = {"V0_control": out0["monthly"]["net"]}, \
        {"V0_control": out0["diag"]}
    for name, e in arms.items():
        if name == "V0_control":
            continue
        spec = StrategySpec(**{**d, "rebalance_months": 12, "cost_model": "ko",
                               "name": f"N2__{name}"})
        out = run_book(f.spine.panel, score, e, spec, f.spine.rf, era)
        monthly[name] = out["monthly"]["net"]
        diags[name] = out["diag"]
        print(f"  {name:20s} months {out['diag']['months']:4d} turnover "
              f"{out['diag']['turnover_1way_annual']:.3f}", flush=True)

    base = monthly["V0_control"]
    res = {
        "trial": "TRIAL-N2-NEGATIVE-SELECTION-1",
        "question": "is refusing the worst worth more than picking the best?",
        "status": "REPORTED-NEVER-DECIDING",
        "prereg": "TRIALS/PREREG_N2_NEGATIVE_SELECTION.md",
        "data_grade": "crsp", "bar_pct_yr": BAR, "decile": DECILE, "seed": SEED,
        "veto_bite": bite,
        "diagnostics": diags,
        "paired": {k: paired(v, base) for k, v in monthly.items()
                   if k != "V0_control"},
    }

    # the placebo is read FIRST
    pl = res["paired"]["V5_placebo_random"]
    pt = pl.get("t_newey_west")
    placebo_failed = pt is not None and abs(pt) >= 2.0
    res["placebo_gate"] = {
        "placebo_annualized_pct": pl.get("annualized_pct"),
        "placebo_t": pt,
        "verdict": ("FAILED — a random veto of the same size moves the book as "
                    "much as the anomaly vetoes do, so this instrument is "
                    "measuring the ACT of vetoing, not the signals"
                    if placebo_failed else
                    "PASS — a random veto of the same size does not move the "
                    "book, so a real arm's effect is attributable to its signal")}

    turn0 = diags["V0_control"]["turnover_1way_annual"]
    res["turnover_gate"] = {
        "control": turn0,
        "arms_needing_g7": [k for k, v in diags.items()
                            if k != "V0_control"
                            and abs(v["turnover_1way_annual"] - turn0) > 0.10],
        "rule": "CANON 15: any arm more than 0.10 from the control routes "
                "through G7 before its net number is quoted"}

    def state(k: str) -> str:
        if placebo_failed and k != "V5_placebo_random":
            return "PLACEBO_FAILED"
        v = res["paired"][k]
        t, eff, mde = (v.get("t_newey_west"), v.get("annualized_pct"),
                       v.get("mde_annualized"))
        if t is not None and eff is not None:
            if eff >= BAR and t >= 2.0:
                return "CONFIRMED"
            if eff <= -BAR and t <= -2.0:
                return "REJECTED"
        if mde is not None and mde > BAR:
            return "POWER_FAILED"
        return "UNRESOLVED"

    res["verdicts"] = {k: state(k) for k in res["paired"]}
    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "N2_NEGATIVE_SELECTION.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8")

    print("\n" + "=" * 72)
    print("PLACEBO:", res["placebo_gate"]["verdict"])
    for k, v in res["paired"].items():
        print(f"{k:20s} {res['verdicts'][k]:16s} {v.get('annualized_pct')}%/yr "
              f"(NW t {v.get('t_newey_west')}, MDE {v.get('mde_annualized')}, "
              f"rho {v.get('correlation')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
