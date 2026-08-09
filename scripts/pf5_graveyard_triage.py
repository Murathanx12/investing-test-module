"""T4c — re-classify the closed search under verdict taxonomy v2.

Murat's question was "what happened to the 200 ideas?" and external review 3
sharpened it into something testable: a strategy can die because the IDEA was
bad or because the EXPERIMENT was bad. The old ledger said FAILED and did not
distinguish, so a broken scalpel and a healthy patient looked identical.

Everything here is a re-reading of numbers ALREADY ON DISK
(`data/factory/batch*_summary.csv`). No book is re-run, no signal is re-scored,
and nothing here can promote anything. The classification rules are the ones in
`aegis_brain/verdicts.classify`, which is unit-tested and takes no judgement.

TWO PREMISES CHECKED BEFORE USE, one of which does not survive:

  * the never-indexed $200k dollar-volume floor. The home session expected it to
    have penalised every small/illiquid candidate that ever entered the harness.
    It did not touch this search: the scan ran on the 2002-2024 panel, where the
    small segment carries ~1,950 eligible names throughout. The floor is a
    63-year-panel problem, and it deletes 1963-1982 there. Recorded because a
    triage built on a premise nobody checked would repeat the error it exists
    to find.

  * era-appropriate costs. Also weaker here than expected, and for the same
    reason: the scan window is entirely post-decimalisation, so the mechanical
    tick floor is ~1c and flat 25bps is not obviously too kind. The scan doc's
    own warning is the live one — 25bps UNDERSTATES small-cap costs, so the
    small-segment rows are, if anything, flattered.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.verdicts import MEANING, Verdict, classify

OUT = MODULE_ROOT / "runs" / "PF5"

#: The execution standard's bar: net excess CAGR of +3%/yr over the benchmark.
BAR_PCT_PER_YEAR = 3.0
MIN_MONTHS = 24


def load() -> pd.DataFrame:
    ds = []
    for f in sorted(glob.glob(str(MODULE_ROOT / "data" / "factory"
                                  / "batch*_summary.csv"))):
        d = pd.read_csv(f)
        d["batch"] = os.path.basename(f).split("_")[0]
        ds.append(d)
    d = pd.concat(ds, ignore_index=True)
    # monthly bps -> %/yr, and the SE backed out of the reported t
    d["point_pct_yr"] = d.mean_excess_net_bps * 12 / 100.0
    se = (d.mean_excess_net_bps / d.t_excess_net).abs()
    d["mde_pct_yr"] = 2 * se * 12 / 100.0
    return d


def main() -> int:
    d = load()
    rows = []
    for _, r in d.iterrows():
        months = int(r.months) if pd.notna(r.months) else 0
        point = float(r.point_pct_yr) if pd.notna(r.point_pct_yr) else None
        mde = float(r.mde_pct_yr) if pd.notna(r.mde_pct_yr) else None
        state, why = classify(
            months=months, point=point, mde=mde, bar=BAR_PCT_PER_YEAR,
            gross_t=float(r.t_excess_gross) if pd.notna(r.t_excess_gross) else None,
            net_t=float(r.t_excess_net) if pd.notna(r.t_excess_net) else None,
            ic_t=float(r.t_ic) if pd.notna(r.t_ic) else None,
            min_months=MIN_MONTHS)
        rows.append({
            "signal": r.signal, "segment": r.segment, "batch": r.batch,
            "months": months, "contaminated": bool(r.contaminated),
            "point_pct_yr": None if point is None else round(point, 2),
            "mde_pct_yr": None if mde is None else round(mde, 2),
            "t_excess_net": None if pd.isna(r.t_excess_net) else float(r.t_excess_net),
            "t_excess_gross": None if pd.isna(r.t_excess_gross) else float(r.t_excess_gross),
            "t_ic": None if pd.isna(r.t_ic) else float(r.t_ic),
            "turnover_1way": None if pd.isna(r.turnover_1way) else float(r.turnover_1way),
            "verdict": state.value, "why": why})

    cen = Counter(r["verdict"] for r in rows)
    df = pd.DataFrame(rows)

    # "bad idea" vs "bad experiment", the question actually asked
    bad_idea = cen[Verdict.REJECTED.value]
    bad_experiment = (cen[Verdict.POWER_FAILED.value]
                      + cen[Verdict.DATA_FAILED.value]
                      + cen[Verdict.IMPLEMENTATION_FAILED.value])

    # resurrection shortlist, capped at 5 by the night's instruction.
    # Eligibility: killed by the EXPERIMENT, not by the idea, and carrying
    # positive information. Ranked by rank-IC t, which is the statistic the
    # replay night established is the adequately powered one.
    cand = df[df.verdict.isin([Verdict.IMPLEMENTATION_FAILED.value,
                               Verdict.POWER_FAILED.value,
                               Verdict.DATA_FAILED.value])
              & (~df.contaminated)].copy()
    cand = cand[(cand.t_ic.fillna(-9) >= 3.0) | (cand.months < MIN_MONTHS)]
    cand["rank_key"] = cand.t_ic.fillna(-9)
    short = cand.sort_values("rank_key", ascending=False).head(5)

    res = {
        "analysis": "T4c GRAVEYARD TRIAGE under verdict taxonomy v2",
        "status": "RE-CLASSIFICATION OF BANKED NUMBERS — no book re-run, "
                  "nothing promoted, no new evidence created",
        "source": "data/factory/batch*_summary.csv",
        "bar_pct_per_year": BAR_PCT_PER_YEAR,
        "denominator": {
            "scan_rows_signal_x_segment": len(df),
            "unique_signals": int(df.signal.nunique()),
            "contaminated_rows": int(df.contaminated.sum()),
            "note": ("the programme has quoted '179 candidates'; the batch "
                     "summaries on disk carry "
                     f"{len(df)} signal x segment rows over "
                     f"{int(df.signal.nunique())} unique signals. The larger "
                     "figure includes reruns and variants not banked as "
                     "summary rows. Both numbers are printed rather than "
                     "reconciled silently.")},
        "premises_checked": {
            "200k_dollar_volume_floor_applies": False,
            "floor_evidence": ("the scan ran on the 2002-2024 panel where the "
                               "small segment carries ~1,950 eligible names; "
                               "the floor empties the small segment only "
                               "before 1982 on the 63-year panel"),
            "era_costs_apply": "weakly — the scan window is post-decimalisation",
        },
        "census": {k: cen[k] for k in sorted(cen)},
        "census_meaning": {k: MEANING[Verdict(k)] for k in sorted(cen)},
        "headline": {
            "killed_by_the_idea_REJECTED": bad_idea,
            "killed_by_the_experiment": bad_experiment,
            "of_which_never_produced_a_number": cen[Verdict.DATA_FAILED.value],
            "of_which_underpowered_at_the_bar": cen[Verdict.POWER_FAILED.value],
            "of_which_information_present_money_absent":
                cen[Verdict.IMPLEMENTATION_FAILED.value],
            "median_mde_pct_yr": round(float(df.mde_pct_yr.median()), 2),
            "share_that_could_not_detect_the_bar": round(float(
                (df.mde_pct_yr > BAR_PCT_PER_YEAR).mean()), 3),
            "median_point_estimate_pct_yr": round(float(
                df.point_pct_yr.median()), 2),
        },
        "resurrection_shortlist": short[[
            "signal", "segment", "verdict", "months", "t_ic", "t_excess_net",
            "t_excess_gross", "turnover_1way", "point_pct_yr", "mde_pct_yr",
            "why"]].to_dict("records"),
        "resurrection_rule": (
            "each entry is a NEW pre-registered trial with its own decision "
            "rule, never a rescue of the old number, and the old test stays in "
            "the denominator forever"),
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "T4_GRAVEYARD_TRIAGE.json").write_text(json.dumps(res, indent=2),
                                                  encoding="utf-8")
    df.to_csv(OUT / "T4_graveyard_rows.csv", index=False)

    print(json.dumps({k: res[k] for k in
                      ("denominator", "census", "headline")}, indent=2))
    print("\nRESURRECTION SHORTLIST")
    print(short[["signal", "segment", "verdict", "months", "t_ic",
                 "t_excess_net", "turnover_1way"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
