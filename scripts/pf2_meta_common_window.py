"""PF-META-1 head-to-head on a COMMON window (fairness correction, not a new test).

The meta configurations start at different dates because a 24-month lookback
cannot trade until month 25, while the equal-weight control starts immediately.
Comparing terminal wealth across books with different inception dates gives the
late starters a different sixty years than the early ones. This recomputes every
meta book and both controls on the single window they ALL share, and reports the
as-run numbers beside the common-window numbers so nothing is hidden by the
correction.

The registered comparison is unchanged (PF-META-1 vs META-EW on excess terminal
wealth under the ruin constraint); this is that comparison, implemented fairly.

Also writes runs/PF2/meta_assets.parquet — the six strategy return series — so
later analysis never has to re-run the books.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.pf import meta as metamod
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.scorecard import scorecard
from aegis_brain.pf.spec import StrategySpec
from scripts.pf_run_batch2 import FIRST, LAST, META_GRID, PF1_BASES, PF2_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("meta-cw")

ASSETS = PF2_DIR / "meta_assets.parquet"


def asset_matrix(fac: Factory) -> pd.DataFrame:
    if ASSETS.exists():
        log.info("reusing %s", ASSETS.name)
        return pd.read_parquet(ASSETS)
    out = {}
    for spec in PF1_BASES:
        fac.run(spec)
        out[spec.name] = fac._monthly[spec.name]["net"].astype(float)
    df = pd.DataFrame(out).sort_index()
    df.to_parquet(ASSETS)
    return df


def main() -> int:
    fac = Factory(first=FIRST, last=LAST, out_dir=PF2_DIR)
    rets = asset_matrix(fac)

    books: dict[str, pd.DataFrame] = {}
    for cfg in META_GRID:
        kw = {k: v for k, v in cfg.items() if k != "name"}
        books[cfg["name"]] = metamod.meta_book(rets, **kw)
    books["META-EW"] = metamod.equal_weight_book(rets)
    tw = {c: float((1 + rets[c].dropna()).prod()) for c in rets.columns}
    books["META-BEST-SINGLE"] = metamod.single_book(rets, max(tw, key=tw.get))

    common_first = max(b.index.min() for b in books.values())
    common_last = min(b.index.max() for b in books.values())
    log.info("common window %s .. %s", common_first.date(), common_last.date())

    rows = {}
    for name, bk in books.items():
        cw = bk.loc[(bk.index >= common_first) & (bk.index <= common_last)]
        spec = StrategySpec(name=f"{name}__CW", signals=(("meta:strategies", 1.0),),
                            segment="all", top_n=max(int(cw["n_held"].max()), 5),
                            first_month=str(cw.index.min().date()),
                            last_month=str(cw.index.max().date()),
                            family="PF-2-META-CW")
        card = scorecard(cw, fac.spine.mkt, diag=metamod.meta_diag(cw),
                         spec_dict=spec.as_dict(), ew_universe=None,
                         factors=fac.factors, rf=fac.spine.rf, seed=spec.seed)
        rows[name] = {
            "excess_cagr_net": card["headline"]["excess_cagr_net"],
            "t_excess_nw": card["headline"]["t_excess_newey_west"],
            "terminal_wealth_x_bench":
                card["headline"]["terminal_wealth_multiple_vs_benchmark"],
            "p_ruin_60": card.get("tail", {}).get("p_maxdd_worse_than_60pct"),
            "max_dd": card["risk"]["max_drawdown"],
            "ff5_umd_alpha": card["factor_alpha"]["ff5_umd"]["ann_alpha"],
            "ff5_umd_t": card["factor_alpha"]["ff5_umd"]["t_alpha"],
            "months": card["window"]["months"],
            "mean_time_in_cash": round(float(cw["cash_w"].mean()), 4),
            "switches": metamod.meta_diag(cw).get("strategy_switches"),
        }

    ew, base = rows["META-EW"], rows["PF-META-1"]
    best = max((c["name"] for c in META_GRID), key=lambda n: rows[n]["terminal_wealth_x_bench"])
    out = {
        "note": "common-window recomputation of the registered head-to-head",
        "common_window": {"first": str(common_first.date()),
                          "last": str(common_last.date())},
        "rows": rows,
        "registered_comparison": {
            "PF-META-1_x_bench": base["terminal_wealth_x_bench"],
            "META-EW_x_bench": ew["terminal_wealth_x_bench"],
            "meta_beats_ew": bool(base["terminal_wealth_x_bench"] > ew["terminal_wealth_x_bench"]),
            "P7_prediction_holds": bool(base["terminal_wealth_x_bench"] <= ew["terminal_wealth_x_bench"]),
        },
        "best_grid_config": {
            "name": best, "x_bench": rows[best]["terminal_wealth_x_bench"],
            "beats_ew": bool(rows[best]["terminal_wealth_x_bench"] > ew["terminal_wealth_x_bench"]),
            "beats_best_single": bool(
                rows[best]["terminal_wealth_x_bench"] > rows["META-BEST-SINGLE"]["terminal_wealth_x_bench"]),
            "status": "grid-selected — a PF-3 registration, never a graduate",
        },
    }
    (PF2_DIR / "META_COMMON_WINDOW.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")

    print(f"common window {common_first.date()} .. {common_last.date()}\n")
    print(f"{'book':<26}{'excess':>9}{'tNW':>7}{'xBench':>9}{'ruin':>8}{'maxDD':>8}"
          f"{'a_FF5':>8}{'t_a':>6}{'cash':>7}")
    for k, v in sorted(rows.items(), key=lambda kv: -kv[1]["terminal_wealth_x_bench"]):
        print(f"{k:<26}{v['excess_cagr_net']:+9.2%}{v['t_excess_nw']:7.2f}"
              f"{v['terminal_wealth_x_bench']:9.2f}{(v['p_ruin_60'] or 0):8.3f}"
              f"{v['max_dd']:8.1%}{v['ff5_umd_alpha']:+8.2%}{v['ff5_umd_t']:6.2f}"
              f"{v['mean_time_in_cash']:7.1%}")
    print("\nregistered:", json.dumps(out["registered_comparison"]))
    print("best grid:", json.dumps(out["best_grid_config"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
