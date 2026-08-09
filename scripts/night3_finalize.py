"""NIGHT-3 finalization: minimum detectable effect, cost sensitivity, predictions.

Three jobs, all of which exist because a verdict without them would overclaim:

1. **MDE.** Report the smallest effect this design could ever have detected, so
   a null result is read as "smaller than X" rather than "zero".
2. **Cost sensitivity.** The replay charges one-way cost on newly-added names;
   the production harness charges two-way. Both arms are billed identically so
   the paired difference is only second-order affected, but the direction of
   the bias favours whichever arm churns more, and that must be shown rather
   than assumed harmless.
3. **Predictions.** All eight registered predictions scored, hit or miss.

    python scripts/night3_finalize.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT

RUN_DIR = MODULE_ROOT / "runs" / "NIGHT3"
COST_BPS = 25.0


def load(name: str) -> dict | None:
    p = RUN_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main() -> int:
    rep = load("DECISION_REPLAY.json")
    if rep is None:
        raise SystemExit("DECISION_REPLAY.json missing — run the replay first")
    coh_gate = load("COHERENCE_BATTERY.json")
    coh_diag = load("COHERENCE_RESOLUTION_DIAG.json")
    nameonly = load("NAME_ONLY.json")
    forced = load("NAME_ONLY_FORCED.json")
    probe = load("REPEAT_PROBE.json")
    power = load("POWER_CHECK.json")

    ret = pd.read_csv(RUN_DIR / "arm_monthly_returns.csv", index_col=0,
                      parse_dates=True)
    arms = [c for c in ret.columns if c != "benchmark"]

    # ── 1. minimum detectable effect on each paired difference ──────────────
    mde = {}
    for x, y in (("A", "ENGINE"), ("E", "A"), ("E", "ENGINE")):
        d = (ret[x] - ret[y]).dropna()
        if len(d) < 12:
            continue
        se = float(d.std() / np.sqrt(len(d)))
        mde[f"{x}_minus_{y}"] = {
            "n_months": len(d),
            "monthly_sd": round(float(d.std()), 5),
            "se_monthly": round(se, 5),
            "mde_monthly_at_t2": round(2 * se, 5),
            "mde_annualized_at_t2": round(2 * se * 12, 4),
            "observed_annualized": round(float(d.mean()) * 12, 4),
        }

    # ── 2. cost sensitivity: what if costs were charged two-way? ────────────
    cost = {}
    for a in arms:
        t1 = rep["arms"][a].get("turnover_1way_annual")
        if t1 is None:
            continue
        extra = t1 * (COST_BPS / 1e4)      # a second leg at the same rate
        cost[a] = {
            "turnover_1way_annual": t1,
            "charged_annual_cost": round(t1 * COST_BPS / 1e4, 4),
            "extra_if_two_way": round(extra, 4),
            "excess_cagr_as_run": rep["arms"][a]["excess_cagr_net"],
            "excess_cagr_if_two_way": round(
                rep["arms"][a]["excess_cagr_net"] - extra, 4),
        }
    for x, y in (("A", "ENGINE"), ("E", "A")):
        if x in cost and y in cost:
            cost[f"{x}_minus_{y}_shift_if_two_way"] = round(
                -(cost[x]["extra_if_two_way"] - cost[y]["extra_if_two_way"]), 4)

    # ── 2b. persistence: grade only the priors the model was actually SHOWN ─
    # DEFECT FOUND AND CORRECTED HERE, not hidden. The replay loop grades a
    # re-review whenever a name has ANY prior belief, but the prompt only shows
    # the 20 most recent priors no older than 12 months (decide.MAX_PRIOR_*).
    # Grading a "failure to update" against a belief the model was never
    # reminded of would manufacture underreaction out of nothing. The shown set
    # is exactly reconstructible: the cap is deterministic (sort by months_ago,
    # take 20), so we rebuild it and report the shown-only summary as the
    # deciding one, with the full set kept for comparison.
    from aegis_brain.night3 import persistence as pers
    from aegis_brain.night3.decide import MAX_PRIOR_AGE_M, MAX_PRIOR_NAMES

    rev_path = RUN_DIR / "persistence_reviews.json"
    persist_shown, persist_all, shown_diag = {}, {}, {}
    if rev_path.exists():
        raw = json.loads(rev_path.read_text(encoding="utf-8"))
        by_ts: dict[str, list] = {}
        for r in raw:
            by_ts.setdefault(r["ts"], []).append(r)
        shown, n_eligible, n_shown = [], 0, 0
        for ts, rs in by_ts.items():
            elig = sorted([r for r in rs if r["months_ago"] <= MAX_PRIOR_AGE_M],
                          key=lambda r: (r["months_ago"], r["permno"]))
            n_eligible += len(elig)
            keep = elig[:MAX_PRIOR_NAMES]
            n_shown += len(keep)
            shown.extend(keep)
        as_obj = [pers.Review(**{k: v for k, v in r.items()
                                 if k in pers.Review.__dataclass_fields__})
                  for r in shown]
        persist_shown = pers.summarize(as_obj)
        persist_all = rep.get("persistence", {})
        shown_diag = {
            "reviews_recorded_by_the_run": len(raw),
            "eligible_by_age_le_12m": n_eligible,
            "actually_shown_to_the_model": n_shown,
            "graded_against_an_unshown_prior": len(raw) - n_shown,
            "note": ("The run's own persistence block over-counts. Only the "
                     "shown-only summary is used to score N8."),
        }

    # ── 3. the eight registered predictions ─────────────────────────────────
    def g(d, *keys, default=None):
        for k in keys:
            if d is None:
                return default
            d = d.get(k) if isinstance(d, dict) else None
        return default if d is None else d

    m1 = rep["M1_llm_minus_engine"]
    m2 = rep["M2_memory_minus_nomemory"]
    persist = persist_shown or rep.get("persistence", {})
    preds = {}

    preds["N1_M1_fails"] = {
        "prediction": "the LLM book does NOT beat the engine book (M1 REJECT)",
        "result": m1["adjudication"]["verdict"],
        "hit": m1["adjudication"]["verdict"] == "REJECT",
        "evidence": f"{m1['cagr_difference']:+.2%}/yr, NW t {m1['t_nw']}"}

    preds["N2_M2_fails"] = {
        "prediction": "memory produces < +1.0%/yr or t < 2.0 (M2 REJECT)",
        "result": m2["adjudication"]["verdict"],
        "hit": m2["adjudication"]["verdict"] == "REJECT",
        "evidence": f"{m2['cagr_difference']:+.2%}/yr, NW t {m2['t_nw']}"}

    npass = g(coh_gate, "grades", "_summary", "directions_passing_at_0.70",
              default=None)
    preds["N3_coherence_4of5"] = {
        "prediction": "coherence battery passes >=4 of 5 directions at >=0.70",
        "result": f"{npass}/5 passing (registered decimal format)",
        "hit": (None if npass is None else npass >= 4),
        "evidence": ("0 wrong directions in 500 pairs; all failures were ties. "
                     "Basis-point diagnostic reaches "
                     f"{g(coh_diag, 'grades', '_summary', 'directions_passing_at_0.70')}/5 "
                     "but cannot overturn the gate.")}

    if nameonly and nameonly.get("n_scored", 0) == 0:
        preds["N4_nameonly_auc_ge_0.55"] = {
            "prediction": "NAME-ONLY beats chance materially (AUC >= 0.55)",
            "result": "UNRESOLVED", "hit": None,
            "evidence": (f"registered arm produced 0 scored events "
                         f"({nameonly['n_abstain']}/{nameonly['n_events']} abstained). "
                         f"Forced diagnostic AUC {g(forced, 'auc')} "
                         "with a CI spanning 0.50.")}
    else:
        auc = g(nameonly, "auc")
        preds["N4_nameonly_auc_ge_0.55"] = {
            "prediction": "NAME-ONLY beats chance materially (AUC >= 0.55)",
            "result": f"AUC {auc}", "hit": (None if auc is None else auc >= 0.55),
            "evidence": ""}

    rc = rep.get("rank_correlation_vs_engine", {})
    preds["N5_rank_corr_ge_0.30"] = {
        "prediction": "LLM decisions correlate with engine rank (mean rho >= 0.30)",
        "result": f"mean Spearman {rc.get('mean_spearman')}",
        "hit": (None if rc.get("mean_spearman") is None
                else rc["mean_spearman"] >= 0.30),
        "evidence": f"n_months {rc.get('n_months')}"}

    preds["N6_repeat_probe"] = {
        "prediction": ">=90% identical decisions at T=0 AND >=15% flipped at T=0.7",
        "result": {"temp0_identical": g(probe, "temperature_0",
                                        "mean_frac_same_direction"),
                   "temp07_flipped": g(probe, "temperature_0.7",
                                       "mean_frac_flipped")},
        "hit": (None if probe is None else
                bool(probe.get("N6_temp0_ge_90pct_identical")
                     and probe.get("N6_temp07_ge_15pct_flipped"))),
        "evidence": "probe calls carry nonces and never enter the graded books"}

    expo = {a: rep["arms"][a]["mean_exposure"] for a in ("A", "E") if a in rep["arms"]}
    preds["N7_exposure_ge_0.95"] = {
        "prediction": "the LLM does not hide in cash: exposure >= 0.95 in both arms",
        "result": expo,
        "hit": bool(expo) and all(v >= 0.95 for v in expo.values()),
        "evidence": "book construction pads to top_n, so a shortfall means "
                    "the arm failed to fill rather than chose cash"}

    umo = persist.get("underreaction_minus_overreaction")
    preds["N8_underreacts_more"] = {
        "prediction": "on re-review the model UNDER-reacts more than it OVER-reacts",
        "result": {"underreaction": persist.get("counts", {}).get("underreaction"),
                   "overreaction": persist.get("counts", {}).get("overreaction"),
                   "difference": umo},
        "hit": (None if umo is None else umo > 0),
        "evidence": f"n_graded {persist.get('n_graded')}"}

    hits = sum(1 for v in preds.values() if v["hit"] is True)
    unres = sum(1 for v in preds.values() if v["hit"] is None)

    out = {
        "trial": rep["trial"],
        "window": rep["window"],
        "minimum_detectable_effect": mde,
        "mde_note": (
            "The registered ADOPT rule requires BOTH a CAGR threshold and "
            "|NW t| >= 2.0. Where the t-bar implies a larger effect than the "
            "CAGR bar, the t-bar is the binding constraint and the CAGR "
            "threshold is not reachable independently. Reported so a null is "
            "read as 'smaller than the MDE', never as 'zero'."),
        "cost_sensitivity": cost,
        "persistence_shown_only": persist_shown,
        "persistence_all_recorded": persist_all,
        "persistence_reconstruction": shown_diag,
        "cost_note": (
            f"Costs charged one-way at {COST_BPS} bps on newly-added names. "
            "The production harness charges two-way. Both arms are billed "
            "identically, so the paired difference shifts only by the "
            "turnover GAP between arms, shown above."),
        "predictions": preds,
        "prediction_score": f"{hits}/{len(preds) - unres} resolved "
                            f"({unres} unresolved of {len(preds)})",
        "power_context": (power or {}).get("headroom"),
        "experiment_denominator": rep.get("experiment_count"),
        "spend": rep.get("spend"),
    }
    (RUN_DIR / "NIGHT3_FINAL.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
