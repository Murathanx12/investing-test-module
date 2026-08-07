"""ONE-SHOT REPLAY — Stage A: selection under the frozen REPLAY-2 design.

Frozen inputs (TRIALS/PREREG_REPLAY_2.md, ratified 2026-08-08):
  ladder BRAIN-010 geometry (both segments, global top-10 cap by t_ic);
  error control D1 = BH step-up at q = 0.10 on empirical p-values;
  veto = FLAT real-data floor (correlation surface failed its R² gate):
  every candidate's p-value is computed against the REAL-NULL-2 pooled
  persistent-arm explore CDF of its own segment.

Stage A reads the banked EXPLORE statistics only (batch*_summary.csv). It
does not touch the confirm window. Firing it still spends something
irreversible — the small-segment rows become examined — so it refuses to run
without --fire, and records SHA-256 hashes of every input (the §6 freeze
list) so Stage B's confirm harness is anchored to exactly what Stage A saw.

Stage B (confirm scans for the graduates) is a separate registration per
REPLAY-2 §6: any post-reveal repair creates a new trial ID.

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
SEGMENTS = ("largemid", "small")
MOD = Path(__file__).resolve().parents[2]
FACTORY_DIR = MOD / "data" / "factory"
FLOOR_DIR = MOD / "runs" / "REPLAY-2"

# ---- receipt-based exclusions (assembled 2026-08-08, pre-fire audit) -------
# VOID rows never produced a valid explore statistic; they leave the universe
# entirely (m excludes them). Keyed (signal, src) — the same signal name from
# a different source (e.g. the split-guarded rebuild) stays eligible.
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
# Valid split-guarded rebuild rows (TRIAL-TGT-REBUILD #154-155), stored
# outside the batch*_summary.csv glob; confirm untouched.
EXTRA_CANDIDATE_JSON = "trial_tgt_rebuild.json"


def load_floor(floor_dir: Path) -> dict[str, np.ndarray]:
    """Pooled persistent-arm explore CDFs, one per segment. Refuses VOID runs."""
    cdfs = {}
    for seg in SEGMENTS:
        meta = json.loads((floor_dir / f"real_null_2_{seg}_meta.json")
                          .read_text(encoding="utf-8"))
        if meta.get("status") != "OK":
            raise SystemExit(
                f"REAL-NULL-2 {seg} status is {meta.get('status')!r}, not OK "
                "— the floor CDF is not certified; the replay may not fire.")
        with np.load(floor_dir / f"real_null_2_{seg}.npz") as z:
            cdfs[seg] = np.sort(z["pooled_t_explore"])
    return cdfs


def load_candidates(factory_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """All banked explore rows, deduped on (signal, segment), first batch
    occurrence wins (a later re-scan of the same name is not a new candidate).

    Returns (candidates, void_rows). VOID rows (receipt-annotated invalid
    explore statistics) are removed BEFORE dedup so a valid rebuild row of
    the same name survives. The split-guarded TGT rebuild rows are appended
    from EXTRA_CANDIDATE_JSON."""
    files = sorted(factory_dir.glob("batch*_summary.csv"))
    if not files:
        raise SystemExit(f"no batch summaries under {factory_dir}")
    frames = []
    for f in files:
        df = pd.read_csv(f)
        if "t_ic" not in df.columns:
            continue
        df["src"] = f.name
        frames.append(df)
    extra = factory_dir / EXTRA_CANDIDATE_JSON
    if extra.exists():
        rows = json.loads(extra.read_text(encoding="utf-8"))["explore"]
        df = pd.DataFrame(rows)
        df["src"] = extra.name
        frames.append(df)
    allrows = pd.concat(frames, ignore_index=True)
    allrows = allrows[allrows.segment.isin(SEGMENTS) & allrows.t_ic.notna()]
    is_void = [
        (s, src) in VOID_ROWS for s, src in zip(allrows.signal, allrows.src)]
    void_rows = allrows[pd.Series(is_void, index=allrows.index)]
    live = allrows[~pd.Series(is_void, index=allrows.index)]
    return live.drop_duplicates(["signal", "segment"], keep="first"), void_rows


def stage_a(cands: pd.DataFrame, cdfs: dict[str, np.ndarray],
            confirm_null_rate: dict[str, float]) -> dict:
    """Selection: empirical p vs segment floor -> BH(q) -> top-N cap by t_ic."""
    # contaminated column may arrive as bool or as "True"/"False" strings from
    # CSV round-trips; normalize explicitly — str "False" is truthy under a
    # bare astype(bool)
    contam = cands.contaminated.map(
        lambda v: str(v).strip().lower() == "true")
    burned = [(s, g) in CONFIRM_BURNED
              for s, g in zip(cands.signal, cands.segment)]
    burned = pd.Series(burned, index=cands.index)
    live = cands[~contam & ~burned].copy()
    excluded = cands[contam | burned]

    live["p_floor"] = [
        empirical_p(t, cdfs[s]) for t, s in zip(live.t_ic, live.segment)]
    flags = bh_reject(list(live.p_floor), Q)
    live["bh_pass"] = flags
    survivors = live[live.bh_pass].sort_values("t_ic", ascending=False)
    graduates = survivors.head(TOP_N)

    # ---- §4 accounting, computed BEFORE any confirm read -------------------
    n_grad = len(graduates)
    p_cf = [confirm_null_rate[s] for s in graduates.segment]
    e_false = float(np.sum(p_cf))            # if EVERY graduate were null
    p_ge1 = 1.0 - float(np.prod([1 - p for p in p_cf])) if p_cf else 0.0
    accounting = {
        "m_candidates": int(len(live)),
        "n_excluded_contaminated_or_burned": int(len(excluded)),
        "bh_q": Q, "top_n": TOP_N,
        "n_bh_survivors": int(len(survivors)),
        "n_graduates": n_grad,
        "bh_guarantee": ("E[false graduates]/max(1, graduates) <= q under "
                         "the floor null, by BH under the flat CDF"),
        "worst_case_all_null": {
            "note": ("upper bound: assumes every graduate is null; "
                     "confirm-null pass rates are REAL-NULL-2 measured"),
            "confirm_null_rate_by_segment": confirm_null_rate,
            "E_false_adoptions": round(e_false, 3),
            "P_at_least_one_false_adoption": round(p_ge1, 3),
        },
        "sim_basis_reference": ("D1 FPR 0.000-0.002 per candidate, "
                                "docs/replay2_d1_eval_q0.1_2026-08-08.json"),
    }
    return {"accounting": accounting,
            "graduates": graduates.drop(columns=["bh_pass"])
                                  .to_dict("records"),
            "bh_survivors_below_cap": survivors.iloc[TOP_N:]
                                  .drop(columns=["bh_pass"]).to_dict("records"),
            "excluded_contaminated": excluded[["signal", "segment", "src"]]
                                  .to_dict("records")}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fire", action="store_true",
                    help="actually read the candidate bank (irreversible: "
                         "small-segment rows become examined)")
    args = ap.parse_args()
    if not args.fire:
        raise SystemExit(
            "Refusing to run without --fire. Stage A reads the small-segment "
            "candidate rows, which is irreversible under the standing rule.")

    cdfs = load_floor(FLOOR_DIR)
    metas = {seg: json.loads(
        (FLOOR_DIR / f"real_null_2_{seg}_meta.json").read_text(encoding="utf-8"))
        for seg in SEGMENTS}
    confirm_null_rate = {seg: metas[seg]["p_confirm_given_grad"]
                         for seg in SEGMENTS}

    cands, void_rows = load_candidates(FACTORY_DIR)
    result = stage_a(cands, cdfs, confirm_null_rate)
    result["void_rows"] = [
        {"signal": r.signal, "segment": r.segment, "src": r.src,
         "reason": VOID_ROWS[(r.signal, r.src)]}
        for r in void_rows.itertuples()]

    # accounting FIRST — frozen output order (§4)
    print(json.dumps(result["accounting"], indent=2))
    print(json.dumps({"graduates": result["graduates"]}, indent=2))

    freeze = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputs_sha256": {
            **{f.name: sha256(f)
               for f in sorted(FACTORY_DIR.glob("batch*_summary.csv"))},
            **{f"real_null_2_{seg}.npz": sha256(
                FLOOR_DIR / f"real_null_2_{seg}.npz") for seg in SEGMENTS},
        },
        "floor_meta": metas,
        **result,
    }
    out = RUNS_DIR.parent / "REPLAY-2" / "stageA_selection.json"
    if out.exists():
        raise SystemExit(f"{out} already exists — Stage A is one-shot; a "
                         "rerun requires a new trial ID (REPLAY-2 §6).")
    out.write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print(f"written -> {out}")
    print("NEXT: Stage B confirm harness freezes against inputs_sha256; any "
          "repair after this point is a new trial ID.")


if __name__ == "__main__":
    main()
