"""TRIAL-EVENT-13DG BOOK STAGE — ONE SHOT PER BOOK.
Protocol: TRIALS/TRIAL-EVENT-13DG.md "BOOK STAGE" (frozen 6fcc381).

NO NEW CANDIDATES. This is the second stage of already-counted arms 175
(`13d_all`) and 177 (`13d_first`). Arm 176 (`13g_all`) failed its CAR gate and
gets no book.

§29 established that 13D drift is real at event resolution. This stage asks the
only question that matters afterwards: could a monthly long-only account have
HARVESTED it? The construction gives up, by design and in advance, the
announcement pop (month-end entry only) and the micro third (rank <= 3000), so
what is measured is the remainder.

Frozen and enforced below:
  * events = exactly the banked sets as run (`13d_all` 12,447; `13d_first`
    7,360 under the rule-as-written, discrepancy disclosed in the trial doc);
  * eligibility = factory universe, dollar-volume rank <= 3000, AT ENTRY;
  * entry at the first month-end ON OR AFTER the filing date;
  * 3-month-end hold, a re-filing resets the clock, no doubled positions;
  * equal weight, rebalanced monthly;
  * deciding number = POOLED net excess vs the EW eligible universe;
  * deciding costs = per-name Kyle-Obizhaeva half-spread on actual turnover,
    with the flat-25 guard and the zero-cost bound reported alongside;
  * bar = pooled net excess t >= 1.5 with positive mean (the IC-t leg of the
    standard bar is N/A for a binary event signal, declared at freeze);
  * segment breakdown reported, NEVER deciding;
  * EXPLORE 2004-2018 only.

If a book clears the bar this script STOPS and flags. Confirm (2019-2024) is
Murat's authorisation, always.

Usage:  .venv\\Scripts\\python -m scripts.run_13dg_book
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory import event_13dg as eg
from aegis_brain.factory import event_book as eb
from aegis_brain.factory.explore import segment_mask

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("book_13dg")
OUT = MODULE_ROOT / "data" / "factory"

BOOKS = ("13d_all", "13d_first")        # 13g_all failed its CAR gate: no book
T_BAR = 1.5                             # frozen: pooled net excess t >= 1.5
CFG = eb.BookConfig()


def clears(summary: dict) -> bool:
    """The frozen bar: pooled net excess t >= 1.5 AND a positive mean."""
    return bool(summary["t_excess_net"] >= T_BAR
                and summary["mean_excess_net_bps"] > 0)


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    spreads = build_spread_frame(panel)
    zero = spreads * 0.0
    elig = eb.eligible_universe(panel, CFG)
    arms = eg.build_arms()

    seg_masks = {"largemid": segment_mask(panel, "largemid"),
                 "small": segment_mask(panel, "small")}

    results, monthlies = {}, {}
    for book in BOOKS:
        events = arms[book]
        held, entry_diag = eb.membership_frame(events, panel, CFG, elig)
        decay = eb.eligibility_decay(held, elig, CFG)

        # (label, cost_frame, deciding)
        plan = [("ko_half", spreads, True),
                ("flat25_guard", None, False),
                ("zero_cost_bound", zero, False)]
        rows = []
        for label, frame, deciding in plan:
            r = eb.run_book(panel, events, CFG, cost_frame=frame,
                            membership=held)
            s = dict(r["summary"])
            s.update({"book": book, "cost_arm": label, "deciding": deciding})
            rows.append(s)
            if deciding:
                monthlies[book] = r["monthly"]

        # segment breakdown — reported, NEVER deciding
        seg_rows = []
        for seg, mask in seg_masks.items():
            try:
                r = eb.run_book(panel, events, CFG, cost_frame=spreads,
                                restrict=mask, membership=held)
                s = dict(r["summary"])
                s.update({"book": book, "segment": seg})
                seg_rows.append(s)
            except ValueError as exc:                     # no scored month
                log.warning("segment %s/%s produced nothing: %s", book, seg, exc)

        results[book] = {"entry_diagnostics": entry_diag,
                         "eligibility_decay": decay,
                         "cost_arms": rows, "segments": seg_rows}

    # ── report ───────────────────────────────────────────────────────────────
    show = ["book", "cost_arm", "deciding", "months", "mean_n_held",
            "mean_excess_net_bps", "t_excess_net", "mean_excess_gross_bps",
            "t_excess_gross", "mean_cost_bps", "turnover_1way", "max_dd",
            "cagr_net"]
    tab = pd.DataFrame([r for b in BOOKS for r in results[b]["cost_arms"]])
    print("\n=== 13DG BOOK STAGE — EXPLORE 2004-2018 (one shot per book) ===")
    print(tab[show].to_string(index=False))

    print("\n=== ENTRY DIAGNOSTICS (where the banked events went) ===")
    print(pd.DataFrame({b: results[b]["entry_diagnostics"]
                        for b in BOOKS}).T.to_string())
    print("\n=== ELIGIBILITY DECAY (entry-time rule, measured not assumed) ===")
    print(pd.DataFrame({b: results[b]["eligibility_decay"]
                        for b in BOOKS}).T.to_string())

    seg_tab = pd.DataFrame([r for b in BOOKS for r in results[b]["segments"]])
    if len(seg_tab):
        print("\n=== SEGMENT BREAKDOWN (reported, NEVER deciding) ===")
        print(seg_tab[["book", "segment", "months", "mean_n_held",
                       "mean_excess_net_bps", "t_excess_net"]].to_string(
            index=False))

    # ── the frozen bar ───────────────────────────────────────────────────────
    verdicts = {}
    for book in BOOKS:
        dec = next(r for r in results[book]["cost_arms"] if r["deciding"])
        verdicts[book] = {"mean_excess_net_bps": dec["mean_excess_net_bps"],
                          "t_excess_net": dec["t_excess_net"],
                          "clears_bar": clears(dec)}
    print("\n=== FROZEN BAR: pooled net excess t >= 1.5 with positive mean ===")
    print(pd.DataFrame(verdicts).T.to_string())

    any_pass = any(v["clears_bar"] for v in verdicts.values())
    if any_pass:
        verdict = (
            "BOOK(S) CLEAR THE BAR: "
            + ", ".join(b for b, v in verdicts.items() if v["clears_bar"])
            + " — STOPPED. The confirm window (2019-2024) is one-use and "
              "reading it is Murat's authorisation, always.")
    else:
        verdict = (
            "NEITHER BOOK CLEARS THE BAR. Recorded finding, as frozen: 13D "
            "drift is REAL at event resolution (NEG_RESULTS 29) and "
            "UNHARVESTABLE by a monthly long-only book at realistic costs. The "
            "family closes at book resolution; a daily-rebalance harvest test "
            "would be a NEW registration against the deflation count, not a "
            "retry of this one. Confirm not read; no forward lane seeded.")
    print("\nVERDICT:", verdict)

    # ── the frozen book-stage prediction, scored ─────────────────────────────
    pred = {}
    for book in BOOKS:
        v = verdicts[book]
        pred[book] = {
            "in_5_to_35_bps": bool(5 <= v["mean_excess_net_bps"] <= 35),
            "t_in_0.5_to_1.5": bool(0.5 <= v["t_excess_net"] <= 1.5),
            "clears_bar": v["clears_bar"],
        }
    pred["13d_first_beats_13d_all"] = bool(
        verdicts["13d_first"]["mean_excess_net_bps"]
        > verdicts["13d_all"]["mean_excess_net_bps"])
    pred["neither_clears"] = not any_pass
    print("\n=== FROZEN BOOK-STAGE PREDICTION, SCORED ===")
    print(json.dumps(pred, indent=2))

    payload = {
        "trial": "TRIAL-EVENT-13DG (BOOK STAGE)",
        "protocol_commit": "6fcc381",
        "candidates": [175, 177],
        "new_candidates": 0,
        "window": "explore 2004-01..2018-12 (confirm NOT read)",
        "bar": "pooled net excess t >= 1.5 with positive mean",
        "results": results,
        "verdicts": verdicts,
        "prediction_scored": pred,
        "verdict": verdict,
        "stopped_for_attended_decision": any_pass,
    }
    (OUT / "trial_13dg_book.json").write_text(
        json.dumps(payload, indent=2, default=str))
    for book, m in monthlies.items():
        m.to_parquet(OUT / f"trial_13dg_book_{book}.parquet")
    log.info("wrote %s", OUT / "trial_13dg_book.json")


if __name__ == "__main__":
    main()
