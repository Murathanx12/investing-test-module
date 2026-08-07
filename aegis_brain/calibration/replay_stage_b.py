"""ONE-SHOT REPLAY — Stage B: confirm wall for Stage A's graduates.

Frozen jurisdiction (TRIALS/PREREG_REPLAY_2.md §5-§6, ratified 2026-08-08):
  confirm scan 2019-01..2024-12, production book (ScanConfig defaults with
  the confirm window), rule: mean IC > 0 AND t_ic >= 0.5 (BRAIN-010);
  sizing S3: confirm t_ic >= 1.5 -> 0.75x, else adopt-with-0x (ledger
  entry, zero capital); terminal states ADOPT_075 / ADOPT_0 / CONFIRM_FAIL /
  SUPPORT_INADEQUATE / ABORTED.

Discipline:
  - Stage A's inputs_sha256 must re-verify byte-identically before any
    confirm read (tamper evidence).
  - Every graduate's signal is REBUILT from source and must reproduce its
    banked explore line exactly (t_ic and t_net to the printed 2dp) before
    its confirm window is opened. A mismatch is ABORTED, never "close
    enough" — a repair after this point is a new trial ID.
  - SUPPORT_INADEQUATE fires when the confirm scan yields < 36 scored
    months (the monthly-signal proxy for the episode floor of 3; episodic
    event candidates need their own episode count, none are in this bank).
  - Output is write-once.

Run:  python -m aegis_brain.calibration.replay_stage_b --fire
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from aegis_brain.calibration.config import RUNS_DIR
from aegis_brain.data.eodhd_panel import Panel, load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.signals import FactorySignal

MOD = Path(__file__).resolve().parents[2]
FACTORY_DIR = MOD / "data" / "factory"
STAGE_A = MOD / "runs" / "REPLAY-2" / "stageA_selection.json"

CONFIRM_CFG = ScanConfig(first_test_month="2019-01-31",
                         last_test_month="2024-12-31")
CONFIRM_T_IC = 0.5          # frozen (BRAIN-010)
SIZE_BAND_T_IC = 1.5        # frozen (S3)
MIN_CONFIRM_MONTHS = 36     # SUPPORT_INADEQUATE proxy floor


def resolve_signal(name: str, panel: Panel) -> tuple[FactorySignal | None, str]:
    """Rebuild one candidate's FactorySignal from source. Returns
    (signal, provenance) or (None, reason). Builders are probed lazily and
    every failure is a reason string, never a silent skip."""
    probes = []

    def _try(label, fn):
        try:
            sigs = fn()
            hit = [s for s in sigs if s.name == name]
            if hit:
                return hit[0], label
            probes.append(f"{label}: not present")
        except Exception as e:            # noqa: BLE001 — reason is reported
            probes.append(f"{label}: {type(e).__name__}: {e}")
        return None, ""

    from aegis_brain.factory.batch1_price import BATCH1
    sig, src = _try("batch1", lambda: BATCH1)
    if sig:
        return sig, src

    from aegis_brain.factory import batch7, batch9, tgt_rebuild
    for label, fn in (("batch7", lambda: batch7.build_batch7(panel)),
                      ("batch9", lambda: batch9.build_batch9(panel)),
                      ("tgt_rebuild", lambda: tgt_rebuild.build_signals(panel))):
        sig, src = _try(label, fn)
        if sig:
            return sig, src

    def _stores():
        from aegis_brain.factory.fundamentals import FundStore
        return FundStore(panel)

    def _b2():
        from aegis_brain.factory.batch2_fundamentals import build_batch2
        return build_batch2(_stores())

    def _b5():
        from aegis_brain.factory.batch5 import build_batch5
        from aegis_brain.factory.quarterly import QuarterlyStore
        return build_batch5(panel, _stores(), QuarterlyStore(panel))

    def _b6():
        from aegis_brain.factory.batch6 import build_batch6
        return build_batch6(panel, _stores())

    def _b8():
        from aegis_brain.factory.batch8 import build_batch8
        return build_batch8(panel, _stores())

    for label, fn in (("batch2", _b2), ("batch5", _b5), ("batch6", _b6),
                      ("batch8", _b8)):
        sig, src = _try(label, fn)
        if sig:
            return sig, src
    return None, " | ".join(probes)


def confirm_verdict(summary: dict) -> tuple[str, float]:
    """(terminal_state, size) from a confirm scan summary — pure, testable."""
    if summary["months"] < MIN_CONFIRM_MONTHS:
        return "SUPPORT_INADEQUATE", 0.0
    if summary["ic_mean"] <= 0 or summary["t_ic"] < CONFIRM_T_IC:
        return "CONFIRM_FAIL", 0.0
    if summary["t_ic"] >= SIZE_BAND_T_IC:
        return "ADOPT_075", 0.75
    return "ADOPT_0", 0.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_freeze(stage_a: dict) -> None:
    search_dirs = (FACTORY_DIR, MOD / "runs" / "REPLAY-2",
                   MOD / "TRIALS", MOD / "docs")
    for fname, want in stage_a["inputs_sha256"].items():
        hits = [d / fname for d in search_dirs if (d / fname).exists()]
        if not hits:
            raise SystemExit(f"FREEZE VIOLATION: {fname} is gone since "
                             "Stage A — Stage B may not run (REPLAY-2 §6).")
        if sha256(hits[0]) != want:
            raise SystemExit(f"FREEZE VIOLATION: {fname} hash changed since "
                             "Stage A — Stage B may not run (REPLAY-2 §6).")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fire", action="store_true")
    args = ap.parse_args()
    if not args.fire:
        raise SystemExit("Refusing without --fire: Stage B burns the confirm "
                         "window for every graduate. One shot.")
    if not STAGE_A.exists():
        raise SystemExit("no stageA_selection.json — Stage A has not fired")
    out_path = RUNS_DIR.parent / "REPLAY-2" / "stageB_confirm.json"
    if out_path.exists():
        raise SystemExit(f"{out_path} exists — Stage B is one-shot; a rerun "
                         "requires a new trial ID (REPLAY-2 §6).")

    stage_a = json.loads(STAGE_A.read_text(encoding="utf-8"))
    verify_freeze(stage_a)
    panel = load_cached_panel(MOD / "data" / "crsp_panel_2002")

    results = []
    for g in stage_a["graduates"]:
        name, seg = g["signal"], g["segment"]
        rec = {"signal": name, "segment": seg, "explore_banked":
               {"t_ic": g["t_ic"], "t_net": g.get("t_excess_net")}}
        sig, provenance = resolve_signal(name, panel)
        if sig is None:
            rec.update(terminal="ABORTED",
                       reason=f"unresolvable: {provenance}", size=0.0)
            results.append(rec)
            print(json.dumps(rec))
            continue
        rec["provenance"] = provenance

        # ---- explore reproduction guard (before ANY confirm read) ---------
        rep = scan_signal(panel, sig, seg)["summary"]
        same = (round(rep["t_ic"], 2) == round(float(g["t_ic"]), 2)
                and (g.get("t_excess_net") is None
                     or round(rep["t_excess_net"], 2)
                     == round(float(g["t_excess_net"]), 2)))
        rec["explore_reproduced"] = {"t_ic": rep["t_ic"],
                                     "t_net": rep["t_excess_net"],
                                     "match": bool(same)}
        if not same:
            rec.update(terminal="ABORTED",
                       reason="explore line did not reproduce", size=0.0)
            results.append(rec)
            print(json.dumps(rec))
            continue

        # ---- the one confirm read -----------------------------------------
        conf = scan_signal(panel, sig, seg, CONFIRM_CFG)["summary"]
        terminal, size = confirm_verdict(conf)
        rec.update(confirm=conf, terminal=terminal, size=size)
        results.append(rec)
        print(json.dumps({k: rec[k] for k in
                          ("signal", "segment", "terminal", "size")}))

    adopted = [r for r in results if r["terminal"].startswith("ADOPT")]
    out = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "frozen": {"confirm_t_ic": CONFIRM_T_IC,
                   "size_band_t_ic": SIZE_BAND_T_IC,
                   "min_confirm_months": MIN_CONFIRM_MONTHS,
                   "confirm_window": [CONFIRM_CFG.first_test_month,
                                      CONFIRM_CFG.last_test_month]},
        "stage_a_utc": stage_a["utc"],
        "accounting_echo": stage_a["accounting"],
        "results": results,
        "n_adopted": len(adopted),
        "n_funded": sum(1 for r in adopted if r["size"] > 0),
    }
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"written -> {out_path}")


if __name__ == "__main__":
    main()
