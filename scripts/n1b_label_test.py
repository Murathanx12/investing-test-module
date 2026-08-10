"""N1B axis 7 — was the ordering instrument grading the wrong exam?

AMENDMENT 2 to `TRIALS/PREREG_N1B_WHERE_DOES_THE_IC_LIVE.md`, registered before
this ran.

The first five axes left a contradiction with nowhere to hide. Every rank-based
measurement says the learned rankers are better — on the book's own rebalance
months, in the top decile more than the bottom, at the selection boundary, at
every top-K from 25 to 300, and in the names they add versus the names they drop
— and the book still earns less money.

The remaining suspect is the label. It is a demeaned **log** forward return; a
long-only equal-weight book is paid in **simple** returns. The difference
between them is a variance penalty, so ranking on mean log return systematically
avoids positively skewed names — the exact names whose right tail pays for a
small-cap book.

So: same frozen scores, same months, same eligibility, same top-150 sets, one
thing changed. No model is refitted.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))
sys.path.insert(0, str(HERE))
logging.basicConfig(level=logging.ERROR)

from aegis_brain.pf import decomp as D

from n1b_patch import ARMS, RECEIPT, TOP_N, load_frozen, top_sets
from n1b_where_does_the_ic_live import build_world

LABEL_MONTHS = 12
TOPK = (25, 50, 100, 150, 300)


def labels(ret: pd.DataFrame, elig: pd.DataFrame):
    """The two labels, built the same way apart from the one difference."""
    logr = np.log1p(ret.clip(lower=-0.99))
    fwd_log = logr.rolling(LABEL_MONTHS).sum().shift(-LABEL_MONTHS).where(elig)
    fwd_simple = (np.exp(logr.rolling(LABEL_MONTHS).sum()
                         .shift(-LABEL_MONTHS)) - 1.0).where(elig)
    return (fwd_log.sub(fwd_log.mean(axis=1), axis=0),
            fwd_simple.sub(fwd_simple.mean(axis=1), axis=0))


def rank_ic(score: pd.DataFrame, label: pd.DataFrame, elig, months) -> pd.Series:
    out = {}
    for m in months:
        if m not in score.index or m not in label.index:
            continue
        s = score.loc[m].where(elig.loc[m]).dropna()
        y = label.loc[m].reindex(s.index).dropna()
        s = s.reindex(y.index)
        if len(y) >= 50:
            out[m] = float(s.rank().corr(y.rank()))
    return pd.Series(out).dropna()


def paired_ic(a: pd.Series, b: pd.Series) -> dict:
    d = (a - b).dropna()
    se = float(d.std(ddof=1) / np.sqrt(len(d)))
    return {"months": int(len(d)), "dic_mean": round(float(d.mean()), 5),
            "t_newey_west": D.nw_t(pd.Series(d.to_numpy()), lags=12),
            "mde_ic_units": round(2 * se, 5),
            "unit": "Spearman rank correlation, monthly, not annualisable"}


def topk(score, label, elig, months, k) -> pd.Series:
    out = {}
    for m in months:
        if m not in score.index or m not in label.index:
            continue
        s = score.loc[m].where(elig.loc[m]).dropna()
        if len(s) < k:
            continue
        y = label.loc[m].reindex(s.nlargest(k).index).dropna()
        if len(y) >= max(10, k // 4):
            out[m] = float(y.mean())
    return pd.Series(out).dropna()


def skewness(score, ret: pd.DataFrame, elig, months, k=TOP_N) -> float:
    """Mean forward 12m skewness of the names an arm holds."""
    vals = []
    for m in months:
        if m not in score.index:
            continue
        s = score.loc[m].where(elig.loc[m]).dropna()
        if len(s) < k:
            continue
        names = s.nlargest(k).index
        pos = ret.index.get_loc(m)
        fwd = ret.iloc[pos + 1: pos + 1 + LABEL_MONTHS]
        if len(fwd) < LABEL_MONTHS:
            continue
        tot = (1 + fwd[names]).prod() - 1.0
        tot = tot.replace([np.inf, -np.inf], np.nan).dropna()
        if len(tot) >= 30:
            vals.append(float(tot.skew()))
    return round(float(np.mean(vals)), 4) if vals else None


def main() -> int:
    t0 = time.time()
    f, d, elig, era, ret, _ = build_world()
    lab_log, lab_simple = labels(ret, elig)
    scores = load_frozen()
    res = json.loads(RECEIPT.read_text(encoding="utf-8"))
    first = pd.Timestamp(res["reproduction_gate"]["window"]["first_month"])
    months = [m for m in ret.index if m >= first]
    reb = [m for i, m in enumerate(months) if i % 12 == 0]

    out: dict = {"question": "does the ordering advantage survive when the "
                             "label is the SIMPLE return a long-only book is "
                             "actually paid?",
                 "ic": {}, "topk": {}, "skew": {}}

    ic_log = {a: rank_ic(scores[a], lab_log, elig, months) for a in ARMS}
    ic_sim = {a: rank_ic(scores[a], lab_simple, elig, months) for a in ARMS}
    for a in ARMS[1:]:
        L = paired_ic(ic_log[a], ic_log["R0_composite"])
        S = paired_ic(ic_sim[a], ic_sim["R0_composite"])
        shrink = (1 - S["dic_mean"] / L["dic_mean"]) if L["dic_mean"] else None
        out["ic"][a] = {"log_label": L, "simple_label": S,
                        "shrinkage": round(shrink, 4) if shrink is not None
                        else None}
        print(f"  {a:16s} dIC log {L['dic_mean']:+.5f} (t {L['t_newey_west']})"
              f"   simple {S['dic_mean']:+.5f} (t {S['t_newey_west']})"
              f"   shrink {shrink:.1%}", flush=True)

    print("\ntop-K under the SIMPLE label, rebalance months", flush=True)
    for k in TOPK:
        base = topk(scores["R0_composite"], lab_simple, elig, reb, k)
        row = {"control_mean": round(float(base.mean()), 5)}
        for a in ARMS[1:]:
            s = topk(scores[a], lab_simple, elig, reb, k)
            dd = (s - base).dropna()
            se = float(dd.std(ddof=1) / np.sqrt(len(dd))) if len(dd) > 2 else None
            row[a] = {"arm_mean": round(float(s.mean()), 5),
                      "delta": round(float(dd.mean()), 5),
                      "t_iid": round(float(dd.mean() / se), 2) if se else None,
                      "mde_at_t2": round(2 * se, 5) if se else None,
                      "n": int(len(dd))}
        out["topk"][k] = row
        print(f"  K={k:4d} control {row['control_mean']:+.4f}  " + "  ".join(
            f"{a.split('_')[0]} {row[a]['delta']:+.4f}(t{row[a]['t_iid']})"
            for a in ARMS[1:]), flush=True)

    print("\nforward 12m skewness of each arm's top 150", flush=True)
    for a in ARMS:
        out["skew"][a] = skewness(scores[a], ret, elig, reb)
        print(f"  {a:16s} {out['skew'][a]}", flush=True)

    res["label_test"] = out
    res["label_test"]["runtime_secs"] = round(time.time() - t0, 1)
    RECEIPT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(f"\nmerged. {out['runtime_secs'] if 'runtime_secs' in out else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
