"""ONE-SHOT REPLAY — Stage A: selection under the frozen REPLAY-2 design.

Frozen inputs (TRIALS/PREREG_REPLAY_2.md, ratified 2026-08-08):
  ladder BRAIN-010 geometry (both segments, global top-10 cap by t_ic);
  error control D1 = BH step-up at q = 0.10 on empirical p-values against
  the REAL-NULL-2 pooled persistent-arm CDF of the candidate's segment;
  PLUS the conservative reading of §3 (pre-fire addendum 2026-08-08): each
  candidate's t_ic must also clear max(semantic-family p95, generic p95)
  from the frozen family-null table, families assigned statistics-blind by
  TRIALS/family_ontology.json (KILL_AUDIT Amendment 2 §2).

Candidate universe (receipts in docs/REPLAY2_PREFIRE_ADDENDUM_2026-08-08.md):
  batch*_summary.csv + the valid rerun files (daily-arm and defensive
  re-scans whose original rows are empty) + trial_tgt_rebuild.json.
  VOID rows leave the universe; confirm-burned candidates are excluded.
  A "candidate" is a (signal, segment) row — two hypotheses per signal
  scanned in both segments; the reconciliation to the historical count is
  printed in the freeze output.

Stage A reads banked EXPLORE statistics only. Firing is irreversible
(small-segment rows become examined) — refuses without --fire; output is
write-once; every input is SHA-256-anchored for Stage B.

Run:  python -m aegis_brain.calibration.replay_runner --fire
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from aegis_brain.calibration.config import RUNS_DIR
from aegis_brain.calibration.replay2_eval import bh_reject, empirical_p

Q = 0.10                    # frozen
TOP_N = 10                  # frozen (BRAIN-010)
CONFIRM_T_IC = 0.5          # frozen — used for the conditional accounting
SEGMENTS = ("largemid", "small")
MOD = Path(__file__).resolve().parents[2]
FACTORY_DIR = MOD / "data" / "factory"
FLOOR_DIR = MOD / "runs" / "REPLAY-2"

# ---- receipt-based universe definition (pre-fire audit 2026-08-08) ---------
# VOID rows never produced a valid explore statistic; they leave the universe
# entirely. Keyed (signal, src) — the same signal from a different source
# (a valid rerun/rebuild) stays eligible.
VOID_ROWS = {
    ("tgt_upside", "batch3b_summary.csv"):
        "VOID-TGT-UPSIDE-B3B-B3C: IBES split look-ahead",
    ("tgt_upside_low", "batch3c_summary.csv"):
        "VOID-TGT-UPSIDE-B3B-B3C: IBES split look-ahead",
    ("insider_cluster", "batch5_summary.csv"):
        "VOID-DESIGN-B5-INSIDER-ARMS: decile scan on sparse event cross-section",
    ("insider_si", "batch5_summary.csv"):
        "VOID-DESIGN-B5-INSIDER-ARMS: decile scan on sparse event cross-section",
}
# Confirm-burned candidates were already adjudicated by their own registered
# one-shot confirm; the replay may not read their window twice.
CONFIRM_BURNED = {
    ("gross_prof", "small"): "confirm_gpsmall.json (survivor gp-small)",
    ("conc_low", "largemid"): "confirm_conclow.json (TRIAL-BRAIN-010)",
}
# Valid re-scan files whose ORIGINAL rows are empty (months=0 broken-pipe
# rows, STRATEGY_FACTORY.md §391/§213 — "a broken pipe fixed, not a retry")
# plus the split-guarded TGT rebuild. batch3b_tgt_rerun.csv stays OUT (both
# tgt_upside runs VOID under the IBES receipt). ALL are REQUIRED: a missing
# file aborts rather than silently shrinking the universe.
EXTRA_CANDIDATE_CSVS = ("batch3a_daily_rerun.csv",
                        "batch5_defensive_rerun.csv")
EXTRA_CANDIDATE_JSON = "trial_tgt_rebuild.json"


def load_floor(floor_dir: Path) -> tuple[dict[str, np.ndarray],
                                         dict[str, np.ndarray], dict]:
    """(explore CDFs, confirm arrays, metas) per segment. Refuses VOID or
    inconsistent runs."""
    cdfs, confirms, metas = {}, {}, {}
    for seg in SEGMENTS:
        meta = json.loads((floor_dir / f"real_null_2_{seg}_meta.json")
                          .read_text(encoding="utf-8"))
        if meta.get("status") != "OK":
            raise SystemExit(
                f"REAL-NULL-2 {seg} status is {meta.get('status')!r}, not OK "
                "— the floor CDF is not certified; the replay may not fire.")
        with np.load(floor_dir / f"real_null_2_{seg}.npz") as z:
            ex = z["pooled_t_explore"]
            cf = z["pooled_t_confirm"]
        if len(ex) != meta.get("n_pooled"):
            raise SystemExit(f"{seg}: npz has {len(ex)} samples but meta says "
                             f"{meta.get('n_pooled')} — stale pairing.")
        cdfs[seg] = np.sort(ex)
        confirms[seg] = np.column_stack([ex, cf])
        metas[seg] = meta
    return cdfs, confirms, metas


def load_candidates(factory_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Universe rows, deduped on (signal, segment) after VOID removal.
    Returns (candidates, void_rows)."""
    files = sorted(factory_dir.glob("batch*_summary.csv"))
    if not files:
        raise SystemExit(f"no batch summaries under {factory_dir}")
    for name in EXTRA_CANDIDATE_CSVS:
        p = factory_dir / name
        if not p.exists():
            raise SystemExit(f"required rerun file missing: {p}")
        files.append(p)
    frames = []
    for f in files:
        df = pd.read_csv(f)
        if "t_ic" not in df.columns:
            raise SystemExit(f"{f.name} has no t_ic column — universe "
                             "definition broken, refusing to shrink silently")
        df["src"] = f.name
        frames.append(df)
    extra = factory_dir / EXTRA_CANDIDATE_JSON
    if not extra.exists():
        raise SystemExit(f"required rebuild file missing: {extra}")
    rows = json.loads(extra.read_text(encoding="utf-8"))["explore"]
    df = pd.DataFrame(rows)
    df["src"] = extra.name
    frames.append(df)

    allrows = pd.concat(frames, ignore_index=True)
    allrows = allrows[allrows.segment.isin(SEGMENTS)]
    n_empty = int(allrows.t_ic.isna().sum())
    is_void = pd.Series(
        [(s, src) in VOID_ROWS for s, src in zip(allrows.signal, allrows.src)],
        index=allrows.index)
    void_rows = allrows[is_void]
    live = allrows[~is_void & allrows.t_ic.notna()]
    live = live.drop_duplicates(["signal", "segment"], keep="first")
    live.attrs["n_empty_t_ic"] = n_empty - int(void_rows.t_ic.isna().sum())
    return live, void_rows


def load_family_floors() -> tuple[dict, dict]:
    """(ontology signals, family p95 table)."""
    onto = json.loads((MOD / "TRIALS" / "family_ontology.json")
                      .read_text(encoding="utf-8"))["signals"]
    fam = json.loads((MOD / "docs" / "family_null_tic_r1_frozen.json")
                     .read_text(encoding="utf-8"))["signals"]
    p95 = {(name, seg): fam[name][seg]["p95"]
           for name in fam for seg in fam[name]}
    return onto, p95


def family_bar(signal: str, seg: str, onto: dict, p95: dict) -> float:
    """Conservative §3 reading: semantic-family p95 survives the failed
    correlation surface, maxed with the generic (injected_edge) p95 so
    negative-bias families never lower the bar."""
    if signal not in onto:
        raise KeyError(f"{signal!r} missing from family_ontology.json — the "
                       "ontology must cover every candidate before firing")
    generic = p95[("injected_edge", seg)]
    fam_name = onto[signal]["family"]
    if fam_name == "generic":
        return generic
    return max(p95[(fam_name, seg)], generic)


def conditional_confirm_rate(pairs: np.ndarray, bar: float) -> tuple[float, int]:
    """P(confirm t >= CONFIRM_T_IC | explore t >= bar) from the saved
    REAL-NULL-2 (explore, confirm) pairs. Returns (rate, n_conditioning)."""
    sel = pairs[pairs[:, 0] >= bar]
    if len(sel) == 0:
        return float("nan"), 0
    return float((sel[:, 1] >= CONFIRM_T_IC).mean()), int(len(sel))


def stage_a(cands: pd.DataFrame, cdfs: dict[str, np.ndarray],
            confirm_pairs: dict[str, np.ndarray],
            onto: dict, p95: dict) -> dict:
    """Selection: empirical p vs segment flat floor -> BH(q) ->
    semantic-family t_ic floor -> global top-N cap by t_ic."""
    contam = cands.contaminated.map(
        lambda v: str(v).strip().lower() == "true")
    burned = pd.Series([(s, g) in CONFIRM_BURNED
                        for s, g in zip(cands.signal, cands.segment)],
                       index=cands.index)
    live = cands[~contam & ~burned].copy()
    excluded = cands[contam | burned]
    if live.t_ic.isna().any():
        raise RuntimeError("NaN t_ic reached selection — universe filter broken")

    live["p_floor"] = [empirical_p(t, cdfs[s])
                       for t, s in zip(live.t_ic, live.segment)]
    live["family_floor"] = [family_bar(s, g, onto, p95)
                            for s, g in zip(live.signal, live.segment)]
    live["bh_pass"] = bh_reject(list(live.p_floor), Q)
    live["family_pass"] = live.t_ic >= live.family_floor
    survivors = live[live.bh_pass & live.family_pass].sort_values(
        "t_ic", ascending=False)
    graduates = survivors.head(TOP_N)
    bh_only = live[live.bh_pass & ~live.family_pass]

    # ---- §4 accounting, BOTH columns, computed BEFORE any confirm read -----
    n_grad = len(graduates)
    cond = {}
    for seg in SEGMENTS:
        seg_grads = graduates[graduates.segment == seg]
        if len(seg_grads):
            bar = float(seg_grads.t_ic.min())
            rate, n_c = conditional_confirm_rate(confirm_pairs[seg], bar)
            cond[seg] = {"bar": bar,
                         "rate": round(rate, 4) if np.isfinite(rate) else None,
                         "n_conditioning": n_c}
    e_false_real, terms = 0.0, []
    for _, g in graduates.iterrows():
        c = cond.get(g.segment, {})
        r = c.get("rate")
        if r is None or not np.isfinite(r) or c.get("n_conditioning", 0) < 50:
            r = 0.36    # marginal REAL-NULL-1 basis, labeled ">=" below
        terms.append(r)
        e_false_real += r
    p_ge1_real = 1.0 - float(np.prod([1 - r for r in terms])) if terms else 0.0
    # simulator basis: D1 per-candidate FPR band from the frozen evaluation
    sim_fpr = (0.000, 0.002)
    accounting = {
        "m_candidates_rows": int(len(live)),
        "denominator_note": ("a candidate is a (signal, segment) row; "
                             "reconciliation to the historical 179 printed "
                             "in universe_reconciliation"),
        "bh_q": Q, "top_n": TOP_N,
        "n_bh_survivors": int((live.bh_pass).sum()),
        "n_killed_by_family_floor": int(len(bh_only)),
        "n_graduates": n_grad,
        "explore_false_pass_basis": {
            "real_persistent_floor": ">= 0.082 (lower bound: real candidates "
                                     "are more persistent than any tested arm)",
            "simulator_generic": "0.036 (2.3x narrower; disagreement is the "
                                 "fidelity finding)"},
        "worst_case_all_null": {
            "note": ("upper-bound accounting assuming EVERY graduate is null; "
                     "confirm rates conditioned on each segment's realized "
                     "graduate bar from REAL-NULL-2 saved pairs, falling back "
                     "to the >=0.36 marginal when conditioning support < 50"),
            "conditional_by_segment": cond,
            "E_false_adoptions_real_basis": f">= {round(e_false_real, 3)}",
            "P_at_least_one_false_adoption_real_basis": f">= {round(p_ge1_real, 3)}",
            "E_false_adoptions_sim_basis": [
                round(n_grad * sim_fpr[0], 3), round(n_grad * sim_fpr[1], 3)],
        },
        "dependence_caveat": (
            "BH at q=0.10 controls FDR under PRDS; this batch contains "
            "negatively dependent mirror constructions, so the formal "
            "worst-case guarantee is Benjamini-Yekutieli q*sum(1/i) ~= 0.54. "
            "The operative evidence that realized FDR sits far below worst "
            "case is the measured CRN evaluation (E[null qualifiers] "
            "0.10-0.16, D1 FPR 0.000-0.002), not the theorem. False "
            "adoptions are positively dependent within construction "
            "lineages; P(>=1) is optimistic in the tail."),
        "cap_ordering_note": (
            "the global cap ranks raw t_ic across segments; at equal "
            "evidence the small segment prints larger t (wider floor), so "
            "the cap systematically favors small — per-candidate "
            "within-segment p_floor is printed for exactly this reason."),
    }
    keep_cols = [c for c in live.columns]
    return {"accounting": accounting,
            "graduates": graduates[keep_cols].to_dict("records"),
            "bh_pass_family_fail": bh_only[keep_cols].to_dict("records"),
            "bh_survivors_below_cap": survivors.iloc[TOP_N:][keep_cols]
                                      .to_dict("records"),
            "excluded_contaminated_or_burned":
                excluded[["signal", "segment", "src"]].to_dict("records")}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fire", action="store_true",
                    help="actually read the candidate bank (irreversible)")
    args = ap.parse_args()
    if not args.fire:
        raise SystemExit(
            "Refusing to run without --fire. Stage A reads the small-segment "
            "candidate rows, which is irreversible under the standing rule.")
    out_dir = RUNS_DIR.parent / "REPLAY-2"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "stageA_selection.json"
    if out.exists():
        raise SystemExit(f"{out} already exists — Stage A is one-shot; a "
                         "rerun requires a new trial ID (REPLAY-2 §6).")

    cdfs, confirm_pairs, metas = load_floor(FLOOR_DIR)
    onto, p95 = load_family_floors()
    cands, void_rows = load_candidates(FACTORY_DIR)
    result = stage_a(cands, cdfs, confirm_pairs, onto, p95)
    result["void_rows"] = [
        {"signal": r.signal, "segment": r.segment, "src": r.src,
         "reason": VOID_ROWS[(r.signal, r.src)]}
        for r in void_rows.itertuples()]
    result["universe_reconciliation"] = {
        "rows_in_universe": result["accounting"]["m_candidates_rows"],
        "void_receipt_rows": int(len(void_rows)),
        "empty_t_ic_rows_dropped": int(cands.attrs.get("n_empty_t_ic", -1)),
        "excluded_contaminated_or_burned":
            len(result["excluded_contaminated_or_burned"]),
        "note": ("historical cumulative candidate count 179 includes "
                 "event/macro/instrument trials adjudicated outside the "
                 "batch CSVs; this replay's universe is every valid banked "
                 "(signal, segment) explore row"),
    }

    # accounting FIRST — frozen output order (§4)
    print(json.dumps(result["accounting"], indent=2))
    print(json.dumps({"graduates": result["graduates"]}, indent=2))

    hash_targets = (sorted(FACTORY_DIR.glob("batch*_summary.csv"))
                    + [FACTORY_DIR / n for n in EXTRA_CANDIDATE_CSVS]
                    + [FACTORY_DIR / EXTRA_CANDIDATE_JSON]
                    + [FLOOR_DIR / f"real_null_2_{seg}.npz" for seg in SEGMENTS]
                    + [MOD / "TRIALS" / "family_ontology.json",
                       MOD / "docs" / "family_null_tic_r1_frozen.json"])
    freeze = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputs_sha256": {f.name: sha256(f) for f in hash_targets},
        "floor_meta": metas,
        **result,
    }
    out.write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print(f"written -> {out}")
    print("NEXT: Stage B verifies inputs_sha256; any repair after this point "
          "is a new trial ID.")


if __name__ == "__main__":
    main()
