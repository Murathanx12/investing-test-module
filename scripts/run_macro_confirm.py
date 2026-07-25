"""CONFIRM runs for INSTR-REGIME-JM + INSTR-TSMOM-XA — held-out 2019-2024.

Pre-registered in TRIALS/INSTR-MACRO-BATCH4.md (confirm section committed
BEFORE this runs). Byte-identical specs to the explore run; lam=50 only.
ONE run. Results final.

Usage:  .venv\\Scripts\\python -m scripts.run_macro_confirm
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aegis_brain.macro.daily_harness as dh
from aegis_brain.config import MODULE_ROOT
from aegis_brain.macro.daily_harness import (backtest, daily_returns,
                                             load_closes, stats,
                                             t_excess_monthly)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
OUT = MODULE_ROOT / "data" / "factory"

CONFIRM_START = pd.Timestamp("2019-01-01")
CONFIRM_END = pd.Timestamp("2024-12-31")
COST_BPS = 5.0
LAM = 50.0


def main() -> None:
    # extend the causal refit loop through confirm end, then read 2019+ only
    dh.EXPLORE_END = CONFIRM_END  # noqa: the loop bound; slicing below is confirm-only
    from scripts.run_macro_batch4 import run_jm, run_tsmom  # noqa: E402

    closes = load_closes()
    rets = daily_returns(closes)
    cf = slice(CONFIRM_START, CONFIRM_END)
    spy_cf = rets["SPY"].loc[cf].dropna()

    risk_off, n_refits = run_jm(rets, LAM)
    w = pd.DataFrame({"SPY": 1.0 - risk_off, "TLT": risk_off.astype(float)})
    w = w.shift(1).dropna()
    net = backtest(w, rets, COST_BPS)["net"].loc[cf]
    switches = int(risk_off.loc[cf].diff().abs().sum())
    spy_stats = stats(spy_cf, "SPY 2019-24")
    jm_stats = stats(net, "JM lam=50 confirm")
    jm_pass = (jm_stats["cagr"] >= spy_stats["cagr"] - 0.01
               and jm_stats["max_dd"] >= (2 / 3) * spy_stats["max_dd"]
               and switches / 6 <= 12)

    w_ts = run_tsmom(closes, rets)
    ts_net = backtest(w_ts, rets, COST_BPS)["net"].loc[cf]
    overlay = 0.5 * spy_cf + 0.5 * ts_net.reindex(spy_cf.index).fillna(0.0)
    ts_stats = stats(ts_net, "TSMOM confirm")
    ov_stats = stats(overlay, "overlay confirm")
    y2020 = float((1 + ts_net.loc["2020"]).prod() - 1)
    ts_pass = (ts_stats["sharpe"] >= 0.3 and y2020 > 0
               and ov_stats["max_dd"] >= 0.75 * spy_stats["max_dd"])

    out = {
        "window": "2019-01-01..2024-12-31 (held out until this run)",
        "JM": {**jm_stats, "switches_per_yr": round(switches / 6, 1),
               "pct_risk_off": round(float(risk_off.loc[cf].mean()), 3),
               "t_excess_vs_spy_monthly": round(t_excess_monthly(net, spy_cf), 2),
               "n_refits_total": n_refits,
               "calendar_2020": round(float((1 + net.loc["2020"]).prod() - 1), 4),
               "calendar_2022": round(float((1 + net.loc["2022"]).prod() - 1), 4),
               "verdict": "PASS" if jm_pass else "REJECT"},
        "TSMOM": {**ts_stats, "calendar_2020": round(y2020, 4),
                  "calendar_2022": round(float((1 + ts_net.loc["2022"]).prod() - 1), 4),
                  "overlay": ov_stats,
                  "t_overlay_vs_spy_monthly": round(t_excess_monthly(overlay, spy_cf), 2),
                  "verdict": "PASS" if ts_pass else "REJECT"},
        "benchmarks": {"spy": spy_stats,
                       "6040": stats((0.6 * rets["SPY"] + 0.4 * rets["TLT"]).loc[cf].dropna(),
                                     "60/40 2019-24")},
    }
    with open(OUT / "macro_confirm.json", "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
