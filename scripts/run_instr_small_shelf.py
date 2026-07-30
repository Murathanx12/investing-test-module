"""INSTR-SMALL-SHELF — one shot. Protocol: TRIALS/INSTR-SMALL-SHELF.md (frozen c95a97b).

Applies the frozen cost-killed-cohort rule to the SMALL segment, re-scans every
member under three cost arms, and runs the confirm window only for graduates
that clear the bar under BOTH the primary and the stress arm.

Usage:  python -m scripts.run_instr_small_shelf
"""

from __future__ import annotations

import glob
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("small_shelf")
OUT = MODULE_ROOT / "data" / "factory"

# ── Frozen cohort rule (verbatim from INSTR-COST-REMEASURE-REJECTS, segment=small)
SEGMENT = "small"
T_IC_MIN = 2.0
T_GROSS_MIN = 1.5
T_NET_MAX = 1.5

EXPLORE = ScanConfig()                                    # 2004-01..2018-12
CONFIRM = ScanConfig(first_test_month="2019-01-31", last_test_month="2024-12-31")
ZERO = ScanConfig(cost_bps_one_way=0.0)


def load_banked() -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(str(OUT / "batch*_summary.csv"))):
        d = pd.read_csv(f)
        d["source"] = Path(f).name
        frames.append(d)
    all_rows = pd.concat(frames, ignore_index=True)
    # a signal can appear in more than one banked file (reruns of the same
    # frozen spec); keep the first occurrence per (signal, segment, source-order)
    return all_rows


def apply_cohort_rule(rows: pd.DataFrame) -> pd.DataFrame:
    d = rows[rows["segment"] == SEGMENT].copy()
    d = d[~d.get("contaminated", False).fillna(False).astype(bool)]
    for c in ("t_ic", "t_excess_gross", "t_excess_net"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["t_ic", "t_excess_gross", "t_excess_net"])
    cohort = d[(d["t_ic"] >= T_IC_MIN)
               & (d["t_excess_gross"] >= T_GROSS_MIN)
               & (d["t_excess_net"] < T_NET_MAX)]
    return cohort.sort_values("t_excess_gross", ascending=False)


def build_signal_registry(panel):
    """Every factory signal, keyed by name, rebuilt byte-identically.

    Stores are constructed lazily and independently; a builder that fails to
    construct (missing local data) is reported, never silently skipped.
    """
    from aegis_brain.factory.batch1_price import BATCH1
    from aegis_brain.factory.batch2_fundamentals import build_batch2
    from aegis_brain.factory.fundamentals import FundStore

    reg: dict = {}
    failures: dict[str, str] = {}

    def add(sigs):
        for s in sigs:
            reg.setdefault(s.name, s)

    add(BATCH1)
    store = FundStore(panel)
    add(build_batch2(store))

    try:
        from aegis_brain.factory.quarterly import QuarterlyStore
        qstore = QuarterlyStore(panel)
    except Exception as exc:            # noqa: BLE001 — reported, not swallowed
        qstore = None
        failures["quarterly_store"] = repr(exc)

    # batch3a signals are constructed inline in scripts/run_factory_batch3a.py
    # rather than in a build_* function; rebuild the cohort-relevant one from
    # the SAME loader with the SAME declared direction (mechanical plumbing,
    # disclosed — no spec, direction or window changes).
    try:
        from aegis_brain.factory.altstores import load_rec_momentum
        from aegis_brain.factory.signals import FactorySignal
        rec = load_rec_momentum(panel)
        add([FactorySignal(
            "rec_mom",
            "Recommendation upgrades minus downgrades (Jegadeesh et al. 2004).",
            lambda p, f=rec: f, +1)])
    except Exception as exc:            # noqa: BLE001
        failures["batch3a_rec_mom"] = repr(exc)
        log.warning("rec_mom rebuild failed: %r", exc)

    for mod, fn, args in [
        ("batch5", "build_batch5", ("panel", "store", "qstore")),
        ("batch6", "build_batch6", ("panel", "store")),
        ("batch7", "build_batch7", ("panel",)),
        ("batch8", "build_batch8", ("panel", "store")),
        ("batch9", "build_batch9", ("panel",)),
    ]:
        try:
            m = __import__(f"aegis_brain.factory.{mod}", fromlist=[fn])
            kw = {"panel": panel, "store": store, "qstore": qstore}
            add(getattr(m, fn)(*[kw[a] for a in args]))
        except Exception as exc:        # noqa: BLE001
            failures[mod] = repr(exc)
            log.warning("builder %s failed: %r", mod, exc)

    return reg, failures


def relief_bps(monthly: pd.DataFrame, spreads: pd.DataFrame, panel) -> float:
    """Mechanical cost relief, bps/mo: mean_traded x (25 - KO_half)."""
    return float("nan")


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    spreads = build_spread_frame(panel)

    banked = load_banked()
    cohort = apply_cohort_rule(banked)
    print("\n=== COHORT (frozen rule, segment=small) ===")
    cols = ["signal", "source", "t_ic", "t_excess_gross", "t_excess_net",
            "turnover_1way", "mean_excess_net_bps"]
    print(cohort[cols].to_string(index=False) if len(cohort) else "  EMPTY")

    # near-miss tables, always banked (the largemid instrument's convention)
    d = banked[banked["segment"] == SEGMENT].copy()
    for c in ("t_ic", "t_excess_gross", "t_excess_net"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    rank_real = d[(d["t_ic"] >= T_IC_MIN) & (d["t_excess_net"] < T_NET_MAX)]
    print("\n=== near-miss: rank-real rejects (t_ic>=2, t_net<1.5), by gross ===")
    print(rank_real.sort_values("t_excess_gross", ascending=False)[cols]
          .head(15).to_string(index=False))

    results = {
        "cohort_rule": {"segment": SEGMENT, "t_ic_min": T_IC_MIN,
                        "t_gross_min": T_GROSS_MIN, "t_net_max": T_NET_MAX},
        "n_banked_small_rows": int(len(d)),
        "cohort": cohort[cols].to_dict("records"),
        "near_miss_rank_real": rank_real.sort_values(
            "t_excess_gross", ascending=False)[cols].head(15).to_dict("records"),
    }

    if not len(cohort):
        results["verdict"] = "COHORT EMPTY — small-cap cost shelf closed"
        (OUT / "instr_small_shelf.json").write_text(json.dumps(results, indent=2,
                                                              default=str))
        print("\nVERDICT: cohort empty. Shelf closed.")
        return

    reg, failures = build_signal_registry(panel)
    results["builder_failures"] = failures
    missing = [n for n in cohort["signal"].unique() if n not in reg]
    results["cohort_signals_unbuildable"] = missing
    if missing:
        log.warning("cohort signals with no builder: %s", missing)

    runs = []
    for name in cohort["signal"].unique():
        sig = reg.get(name)
        if sig is None:
            continue
        for arm, cfg, frame in [("ko_half", EXPLORE, spreads),
                                ("ko_full", EXPLORE, spreads * 2),
                                ("zero_cost_bound", ZERO, None),
                                ("flat25_regression_guard", EXPLORE, None)]:
            try:
                r = scan_signal(panel, sig, SEGMENT, cfg, cost_frame=frame)
                s = r["summary"]
                s.update({"window": "explore", "cost_arm": arm})
                # mechanical relief: mean traded x delta bps
                s["mean_traded"] = round(float(r["monthly"]["traded"].mean()), 4)
                runs.append(s)
            except Exception as exc:    # noqa: BLE001
                log.exception("scan failed %s/%s", name, arm)
                runs.append({"signal": name, "cost_arm": arm, "error": repr(exc)})

    ex = pd.DataFrame([r for r in runs if "error" not in r])
    print("\n=== EXPLORE re-scan, small ===")
    print(ex[["signal", "cost_arm", "mean_excess_net_bps", "t_excess_net",
              "t_excess_gross", "t_ic", "turnover_1way", "max_dd"]]
          .to_string(index=False))

    # graduation: bar cleared under BOTH primary and stress
    def bar(row) -> bool:
        return bool(row["t_excess_net"] >= 1.5 and row["t_ic"] >= 2.0)

    grads = []
    for name in ex["signal"].unique():
        half = ex[(ex["signal"] == name) & (ex["cost_arm"] == "ko_half")]
        full = ex[(ex["signal"] == name) & (ex["cost_arm"] == "ko_full")]
        if len(half) and len(full) and bar(half.iloc[0]) and bar(full.iloc[0]):
            grads.append(name)
    results["explore_runs"] = runs
    results["graduates"] = grads
    print("\nGRADUATES (bar under BOTH KO arms):", grads or "NONE")

    confirms = []
    for name in grads:
        s = scan_signal(panel, reg[name], SEGMENT, CONFIRM,
                        cost_frame=spreads)["summary"]
        s.update({"window": "confirm", "cost_arm": "ko_half"})
        passed = (s["mean_excess_net_bps"] > 0 and s["t_excess_net"] >= 0.8
                  and s["t_ic"] >= 1.5)
        s["confirm_pass"] = bool(passed)
        confirms.append(s)
        print(f"\nCONFIRM {name}: net {s['mean_excess_net_bps']:+.1f} bps "
              f"t {s['t_excess_net']:+.2f} ic_t {s['t_ic']:+.2f} "
              f"-> {'PASS' if passed else 'REJECT'}")
    results["confirm_runs"] = confirms
    results["verdict"] = (
        "CONFIRM SURVIVOR(S): " + ", ".join(c["signal"] for c in confirms
                                            if c["confirm_pass"])
        if any(c["confirm_pass"] for c in confirms)
        else ("NO GRADUATE — shelf closed" if not grads
              else "GRADUATED THEN REJECTED AT CONFIRM"))

    (OUT / "instr_small_shelf.json").write_text(
        json.dumps(results, indent=2, default=str))
    print("\nVERDICT:", results["verdict"])


if __name__ == "__main__":
    main()
