"""Two loose ends from NIGHT-7, both raised by external review.

A3 — SEGMENT DRIFT (the prediction I registered and then failed to measure).
Prediction 4 said the fundamental-break arm would drift furthest out of the small
segment, because unsold winners grow out of it. It was never computed. Rather
than leave it as PRE_SPECIFIED_NOT_MEASURED forever, it is computed here and
labelled exactly what it is: **late-computed, non-decision-bearing.** It scores a
prediction; it changes no verdict.

T2c — STOP-TRIGGER INFORMATIVENESS (the reviewer's best idea).
G7 rejected the trailing-stop *implementation* decisively (-3.08%/yr, 74% of
starting capital in extra costs). It did NOT answer a different question: does the
trigger carry information? A1 showed +0.98%/yr GROSS at t 0.94 — unresolved, not
zero. If stop triggers genuinely mark names that subsequently do worse, that
information could be used at the next ANNUAL rebalance as a rank penalty, at
zero extra turnover — extracting the signal while discarding the expensive
vehicle.

This runs as a pure event study on the BASELINE book, which never sells on a
stop. Names are observed, not traded. No portfolio is constructed and no trade
is charged, so nothing here can be flattered by execution assumptions.

Within-month demeaning is what makes the comparison fair: triggered names are
compared only against other names held in the SAME month, so market direction,
regime and the book's own factor tilt all cancel.

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
from aegis_brain.pf.exits import STOP_DRAWDOWN, ExitRule, build_arms
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT7"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
HORIZONS = (1, 3, 6, 12)


class TriggerObserver(ExitRule):
    """Records stop triggers and sells NOTHING. An instrument, not a strategy."""

    name = "trigger_observer"
    label = "OBSERVER — records the trailing-stop trigger without acting on it"

    def __init__(self) -> None:
        self.log: list[tuple[pd.Timestamp, str]] = []
        self._fired: set[str] = set()

    def interim(self, ctx):
        dd = ctx.peak_dd.reindex(ctx.held).dropna()
        hit = dd.index[dd <= STOP_DRAWDOWN]
        for s in hit:
            # FIRST trigger per holding episode only. Counting every month a name
            # sits below the threshold would weight one long slide as many
            # observations and manufacture significance out of persistence.
            if s not in self._fired:
                self.log.append((ctx.formation_m, s))
                self._fired.add(s)
        still = set(ctx.held)
        self._fired &= still          # a name that leaves the book can re-arm
        return pd.Index([])


def segment_drift(f, holdings: list[dict]) -> dict:
    """Mean dollar-volume rank of held names, by year. Small = rank 1000-3000."""
    rank = f.spine.panel.monthly_dollar_vol.rank(axis=1, ascending=False)
    rows = []
    for h in holdings:
        m = pd.Timestamp(h["test"])
        if m not in rank.index:
            continue
        w = pd.Series(h["weights"]).astype(float)
        r = rank.loc[m].reindex(w.index).dropna()
        if len(r):
            rows.append({"month": m, "mean_rank": float(r.mean()),
                         "frac_out_of_small": float(((r <= 1000)
                                                     | (r > 3000)).mean())})
    if not rows:
        return {}
    df = pd.DataFrame(rows).set_index("month")
    first5 = df.iloc[:60]
    last5 = df.iloc[-60:]
    return {
        "mean_rank_overall": round(float(df["mean_rank"].mean()), 1),
        "mean_rank_first_5y": round(float(first5["mean_rank"].mean()), 1),
        "mean_rank_last_5y": round(float(last5["mean_rank"].mean()), 1),
        "drift_first_to_last": round(float(last5["mean_rank"].mean()
                                           - first5["mean_rank"].mean()), 1),
        "frac_held_outside_small_segment": round(
            float(df["frac_out_of_small"].mean()), 4),
    }


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
    arms = build_arms(top_n=d["top_n"], hold_band_mult=d["hold_band_mult"])

    # ── A3: segment drift for every arm ─────────────────────────────────────
    drift = {}
    for k, rule in arms.items():
        spec = StrategySpec(**{**d, "rebalance_months": 12, "cost_model": "ko",
                               "name": f"PF7B-DRIFT__{k}"})
        H: list[dict] = []
        run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
                 exit_rule=rule, mom=mom, holdings_out=H)
        drift[k] = segment_drift(f, H)
        print(f"  {k:22s} mean rank {drift[k]['mean_rank_overall']:7.1f}  "
              f"drift {drift[k]['drift_first_to_last']:+7.1f}  "
              f"outside-small {drift[k]['frac_held_outside_small_segment']:.3f}",
              flush=True)

    ranked = sorted(drift.items(), key=lambda kv: -kv[1]["drift_first_to_last"])
    a3_worst = ranked[0][0]

    # ── T2c: does the trigger carry information? ────────────────────────────
    obs = TriggerObserver()
    spec = StrategySpec(**{**d, "rebalance_months": 12, "cost_model": "ko",
                           "name": "PF7B-TRIGGER-OBS"})
    Hobs: list[dict] = []
    run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
             exit_rule=obs, mom=mom, holdings_out=Hobs)
    trig = pd.DataFrame(obs.log, columns=["month", "permno"])
    print(f"\n  stop triggers observed: {len(trig)} over {len(Hobs)} months",
          flush=True)

    ret = f.spine.panel.monthly_ret
    months = ret.index
    held_by_month = {pd.Timestamp(h["test"]): list(h["weights"].index)
                     for h in Hobs}
    trig_by_month = {m: set(g["permno"]) for m, g in trig.groupby("month")}

    fwd = {}
    for k in HORIZONS:
        logret = np.log1p(ret.clip(lower=-0.99))
        fwd[k] = (logret.rolling(k).sum().shift(-k))   # forward k-month log return

    results = {}
    for k in HORIZONS:
        diffs, n_t, n_c = [], 0, 0
        for m, held in held_by_month.items():
            if m not in months:
                continue
            # triggers are logged on the FORMATION month; the forward window
            # must start after the month whose return the book already realised
            fired = trig_by_month.get(m, set())
            if not fired:
                continue
            row = fwd[k].loc[m].reindex(held).dropna()
            if len(row) < 20:
                continue
            t_names = [x for x in row.index if x in fired]
            c_names = [x for x in row.index if x not in fired]
            if len(t_names) < 1 or len(c_names) < 10:
                continue
            # within-month demeaning: compare only against names held the SAME
            # month, so market direction and the book's own tilt cancel
            diffs.append(float(row.reindex(t_names).mean()
                               - row.reindex(c_names).mean()))
            n_t += len(t_names)
            n_c += len(c_names)
        s = pd.Series(diffs).dropna()
        mean_log = float(s.mean()) if len(s) else float("nan")
        results[f"{k}m"] = {
            "months_with_triggers": int(len(s)),
            "triggered_name_months": n_t,
            "control_name_months": n_c,
            "mean_log_return_diff": round(mean_log, 5),
            "annualized_diff_pct": round(
                float(np.expm1(mean_log * (12.0 / k))), 4) if len(s) else None,
            "t_stat": round(float(s.mean() / s.std(ddof=1) * np.sqrt(len(s))), 3)
            if len(s) > 2 else None,
            "mde_annualized": D.mde_annualized(s * (12.0 / k)) if len(s) > 2 else None,
        }
        print(f"   +{k:2d}m: diff {results[f'{k}m']['annualized_diff_pct']} "
              f"t {results[f'{k}m']['t_stat']} "
              f"(n months {results[f'{k}m']['months_with_triggers']})", flush=True)

    sig = [k for k, v in results.items()
           if v["t_stat"] is not None and abs(v["t_stat"]) >= 2.0]

    res = {
        "task": "NIGHT-7 loose ends — A3 segment drift + T2c stop-trigger study",
        "status": "REPORTED-NEVER-DECIDING",
        "A3_segment_drift": {
            "label": "LATE-COMPUTED, NON-DECISION-BEARING — scores a registered "
                     "prediction, changes no verdict",
            "prediction": "A3 (fundamental-break) drifts furthest from the small "
                          "segment because unsold winners grow out of it",
            "by_arm": drift,
            "worst_drifter": a3_worst,
            "prediction_4_verdict": ("HIT" if a3_worst == "A3_fundamental_break"
                                     else f"MISS — worst drifter is {a3_worst}"),
        },
        "T2c_stop_trigger_informativeness": {
            "question": ("does a trailing-stop TRIGGER identify names that "
                         "subsequently underperform, independent of whether "
                         "acting on it is affordable?"),
            "design": ("event study on the baseline book, which never sells on a "
                       "stop; first trigger per holding episode only; forward "
                       "returns demeaned within month against names held the "
                       "same month"),
            "threshold": STOP_DRAWDOWN,
            "total_triggers": int(len(trig)),
            "by_horizon": results,
            "significant_horizons": sig,
            "verdict": ("UNRESOLVED — no horizon reaches |t| 2.0; the trigger "
                        "carries no measurable information about subsequent "
                        "relative returns, so there is nothing to salvage into "
                        "a low-turnover rank penalty" if not sig else
                        f"SIGNAL AT {sig} — register a low-turnover rank-penalty "
                        "test; do NOT resurrect the stop itself"),
        },
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "T2c_TRIGGER_AND_A3_DRIFT.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    print("\n" + json.dumps({
        "A3_worst_drifter": a3_worst,
        "prediction_4": res["A3_segment_drift"]["prediction_4_verdict"],
        "trigger_verdict": res["T2c_stop_trigger_informativeness"]["verdict"]},
        indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
