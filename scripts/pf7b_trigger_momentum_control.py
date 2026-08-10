"""T2c control — is the stop trigger anything other than momentum?

The raw event study said triggered names underperform their fellow holdings by
roughly -8%/yr at 3, 6 and 12 months (t -2.4, -3.1, -4.7). Before that becomes a
finding, the obvious alternative has to be killed:

    "this name has fallen 20% from its peak" is very nearly a momentum sort.

Losers continuing to lose is Jegadeesh-Titman, discovered in 1993, present in
every factor library including our own signal shelf. Rediscovering it and calling
it an exit signal would be exactly the "correctly quoted number, wrong
population" error the T1 citation gate caught in the reviewers.

Two controls, both within-month so market direction cancels:

  RAW           triggered minus all other held names (the original)
  MOM-NEUTRAL   forward return residualised on within-month momentum rank
                BEFORE the comparison, so only the part of the trigger that
                momentum does not already explain can show up
  MATCHED       each triggered name compared only against held names in the same
                within-month momentum quintile

If the effect dies under MOM-NEUTRAL and MATCHED, the trigger is momentum wearing
a costume and A1 closes for good. If it survives, there is something to register.

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
from aegis_brain.pf.exits import STOP_DRAWDOWN, ExitRule
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT7"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
HORIZONS = (3, 6, 12)
N_QUINTILES = 5


class TriggerObserver(ExitRule):
    name = "trigger_observer"
    label = "OBSERVER — records the trigger, sells nothing"

    def __init__(self) -> None:
        self.log: list[tuple[pd.Timestamp, str]] = []
        self._fired: set[str] = set()

    def interim(self, ctx):
        dd = ctx.peak_dd.reindex(ctx.held).dropna()
        for s in dd.index[dd <= STOP_DRAWDOWN]:
            if s not in self._fired:
                self.log.append((ctx.formation_m, s))
                self._fired.add(s)
        self._fired &= set(ctx.held)
        return pd.Index([])


def tstat(x: pd.Series, horizon: int) -> dict:
    """Plain AND Newey-West t. The plain one is not admissible here.

    Forward k-month returns sampled every month OVERLAP by k-1 months, so
    consecutive observations share most of their data and an i.i.d. t-stat is
    inflated by roughly sqrt(k). The Newey-West t with k lags is the number that
    may be quoted; the naive one is printed beside it only to show the size of
    the correction.
    """
    x = pd.Series(x).dropna()
    if len(x) < 3:
        return {"t_naive": None, "t_newey_west": None, "nw_lags": horizon}
    naive = float(x.mean() / x.std(ddof=1) * np.sqrt(len(x)))
    x.index = pd.RangeIndex(len(x))
    return {"t_naive": round(naive, 3),
            "t_newey_west": D.nw_t(x, lags=horizon),
            "nw_lags": horizon}


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()

    f = Factory()
    elig = f.eligible(d["segment"])
    score, _ = composite_score(f.lib, d["signals"], elig)
    era = D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())
    mom = f.lib.get("native:mom_12_1")

    obs = TriggerObserver()
    spec = StrategySpec(**{**d, "rebalance_months": 12, "cost_model": "ko",
                           "name": "PF7B-TRIG-CTRL"})
    H: list[dict] = []
    run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
             exit_rule=obs, mom=mom, holdings_out=H)
    trig = pd.DataFrame(obs.log, columns=["month", "permno"])
    trig_by_month = {m: set(g["permno"]) for m, g in trig.groupby("month")}
    held_by_month = {pd.Timestamp(h["test"]): list(h["weights"].index) for h in H}

    ret = f.spine.panel.monthly_ret
    logret = np.log1p(ret.clip(lower=-0.99))
    fwd = {k: logret.rolling(k).sum().shift(-k) for k in HORIZONS}

    # how confounded is the trigger with momentum in the first place?
    conf = []
    for m, held in held_by_month.items():
        fired = trig_by_month.get(m, set())
        if not fired or m not in mom.index:
            continue
        mr = mom.loc[m].reindex(held).dropna()
        if len(mr) < 20:
            continue
        q = pd.qcut(mr.rank(method="first"), N_QUINTILES, labels=False)
        t_names = [x for x in mr.index if x in fired]
        if t_names:
            conf.append(float(q.reindex(t_names).mean()))
    mean_q = float(np.mean(conf)) if conf else float("nan")

    out = {}
    for k in HORIZONS:
        raw, neutral, matched = [], [], []
        for m, held in held_by_month.items():
            fired = trig_by_month.get(m, set())
            if not fired or m not in mom.index:
                continue
            r = fwd[k].loc[m].reindex(held).dropna()
            mr = mom.loc[m].reindex(r.index).dropna()
            r = r.reindex(mr.index)
            if len(r) < 30:
                continue
            t_names = [x for x in r.index if x in fired]
            c_names = [x for x in r.index if x not in fired]
            if not t_names or len(c_names) < 10:
                continue

            raw.append(float(r.reindex(t_names).mean()
                             - r.reindex(c_names).mean()))

            # MOM-NEUTRAL: strip the linear momentum-rank component first
            xr = mr.rank(pct=True)
            X = np.column_stack([np.ones(len(xr)), xr.to_numpy()])
            beta, *_ = np.linalg.lstsq(X, r.to_numpy(), rcond=None)
            resid = pd.Series(r.to_numpy() - X @ beta, index=r.index)
            neutral.append(float(resid.reindex(t_names).mean()
                                 - resid.reindex(c_names).mean()))

            # MATCHED: same within-month momentum quintile only
            q = pd.qcut(mr.rank(method="first"), N_QUINTILES, labels=False)
            per = []
            for nm in t_names:
                peers = [x for x in c_names if q.get(x) == q.get(nm)]
                if len(peers) >= 5:
                    per.append(float(r[nm] - r.reindex(peers).mean()))
            if per:
                matched.append(float(np.mean(per)))

        row = {}
        for label, series in (("RAW", raw), ("MOM_NEUTRAL", neutral),
                              ("MOM_MATCHED", matched)):
            s = pd.Series(series).dropna()
            row[label] = {
                "months": int(len(s)),
                "annualized_diff_pct": round(float(np.expm1(s.mean() * (12.0 / k))), 4)
                if len(s) else None,
                **tstat(s, k),
                "mde_annualized": D.mde_annualized(s / k)
                if len(s) > 2 else None,
            }
        out[f"{k}m"] = row
        print(f"  +{k:2d}m  RAW {row['RAW']['annualized_diff_pct']} "
              f"(NW t {row['RAW']['t_newey_west']}, naive {row['RAW']['t_naive']})"
              f"   MOM-NEUTRAL {row['MOM_NEUTRAL']['annualized_diff_pct']} "
              f"(NW t {row['MOM_NEUTRAL']['t_newey_west']})"
              f"   MATCHED {row['MOM_MATCHED']['annualized_diff_pct']} "
              f"(NW t {row['MOM_MATCHED']['t_newey_west']})", flush=True)

    def _nw(v, key):
        t = v[key]["t_newey_west"]
        return t is not None and abs(t) >= 2.0

    survives = [k for k, v in out.items()
                if _nw(v, "MOM_NEUTRAL") and _nw(v, "MOM_MATCHED")]

    res = {
        "task": "T2c control — is the stop trigger anything but momentum?",
        "status": "REPORTED-NEVER-DECIDING",
        "total_triggers": int(len(trig)),
        "confound_check": {
            "mean_momentum_quintile_of_triggered_names": round(mean_q, 3),
            "neutral_would_be": (N_QUINTILES - 1) / 2,
            "reading": ("0 = lowest momentum quintile. A triggered name sitting "
                        "far below the neutral value means the trigger is largely "
                        "a momentum sort, which is what the controls then test."),
        },
        "by_horizon": out,
        "survives_momentum_control": survives,
        "verdict": (
            "CLOSED — the trigger's apparent information is momentum. It does "
            "not survive within-month momentum residualisation or "
            "quintile-matching, so there is nothing to carry into a low-turnover "
            "rank penalty, and A1 closes completely."
            if not survives else
            f"SURVIVES at {survives} — the trigger carries information beyond "
            "momentum. Register a low-turnover rank-penalty test at the annual "
            "rebalance. Do NOT resurrect the stop itself (G7: -3.08%/yr)."),
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "T2c_TRIGGER_MOM_CONTROL.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    print("\n" + res["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
