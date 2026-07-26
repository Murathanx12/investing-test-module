"""INSTR-REGIME-JM2 — ONE execution, both windows (frozen in
TRIALS/INSTR-REGIME-JM2.md, freeze commit 470ed0f, BEFORE this ran).

POST-HOC-REPAIR PROVENANCE: explore is descriptive context only (~zero
evidential weight); confirm bars are the only gate and are themselves
weakened (2022 is inside). State machine byte-identical to JM1 via
run_macro_batch4.run_jm (lam=50). New element: T10YIE inflation gate
routes risk-off to GLD (cash pre-GLD-history) vs TLT.

Usage:  .venv\\Scripts\\python -m scripts.run_jm2
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

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("jm2")
OUT = MODULE_ROOT / "data" / "factory"

EXPLORE = slice(pd.Timestamp("2004-01-01"), pd.Timestamp("2018-12-31"))
CONFIRM = slice(pd.Timestamp("2019-01-01"), pd.Timestamp("2024-12-31"))
CONFIRM_END = pd.Timestamp("2024-12-31")
COST_BPS = 5.0
LAM = 50.0
GATE_LOOKBACK = 126          # primary (frozen); {63, 252} diagnostics only
GATE_THRESHOLD_PP = 0.10
GLD_MIN_HISTORY = 252


def load_t10yie(index: pd.DatetimeIndex) -> pd.Series:
    snap = MODULE_ROOT / "data" / "macro" / "fred_t10yie_snap20260726.csv"
    t10 = pd.read_csv(snap, index_col=0, parse_dates=True).iloc[:, 0]
    return t10.reindex(index).ffill(limit=5)


def gate_series(t10: pd.Series, lookback: int) -> pd.Series:
    """True = breakevens rising (inflationary): lookback-td change > +0.10pp."""
    return (t10 - t10.shift(lookback)) > GATE_THRESHOLD_PP


def build_weights(risk_off: pd.Series, gate: pd.Series,
                  gld_ok: pd.Series) -> pd.DataFrame:
    ro = risk_off.astype(bool)
    g = gate.reindex(risk_off.index).fillna(False)
    ok = gld_ok.reindex(risk_off.index).fillna(False)
    w = pd.DataFrame(0.0, index=risk_off.index, columns=["SPY", "TLT", "GLD"])
    w.loc[~ro, "SPY"] = 1.0
    w.loc[ro & ~g, "TLT"] = 1.0
    w.loc[ro & g & ok, "GLD"] = 1.0
    # ro & g & ~ok -> all zero = cash at 0% (disclosed, conservative)
    return w


def window_block(net: pd.Series, spy: pd.Series, risk_off: pd.Series,
                 gate: pd.Series, label: str, years: float) -> dict:
    win_ro = risk_off.reindex(net.index).astype(bool)
    win_gate = gate.reindex(net.index).fillna(False)
    switches = int(risk_off.reindex(net.index).diff().abs().sum())
    gate_flips_in_ro = int((win_gate.astype(int).diff().abs() * win_ro).sum())
    return {
        **dh.stats(net, label),
        "switches_per_yr": round(switches / years, 1),
        "gate_flips_while_risk_off": gate_flips_in_ro,
        "pct_risk_off": round(float(win_ro.mean()), 3),
        "pct_gate_on": round(float(win_gate.mean()), 3),
        "pct_risk_off_gated_to_gld_or_cash":
            round(float((win_ro & win_gate).sum() / max(win_ro.sum(), 1)), 3),
        "t_excess_vs_spy_monthly": round(dh.t_excess_monthly(net, spy), 2),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "jm2.json"
    if out_path.exists():
        raise SystemExit("jm2.json exists — one-shot rule; REFUSING rerun")

    # extend the causal refit loop through confirm end (established pattern)
    dh.EXPLORE_END = CONFIRM_END
    from scripts.run_macro_batch4 import run_jm  # noqa: E402  (picks up mutation)

    closes = dh.load_closes()
    rets = dh.daily_returns(closes)

    risk_off, n_refits = run_jm(rets, LAM)          # byte-identical state machine
    t10 = load_t10yie(rets.index)
    gate = gate_series(t10, GATE_LOOKBACK)
    gld_ok = closes["GLD"].notna().cumsum() >= GLD_MIN_HISTORY

    # JM2 book
    w2 = build_weights(risk_off, gate, gld_ok).shift(1).dropna()
    net2 = dh.backtest(w2, rets, COST_BPS)["net"]
    # JM1 ablation (same states, TLT-only)
    w1 = pd.DataFrame({"SPY": 1.0 - risk_off, "TLT": risk_off.astype(float)})
    w1 = w1.shift(1).dropna()
    net1 = dh.backtest(w1, rets, COST_BPS)["net"]

    out: dict = {"provenance": "POST-HOC REPAIR (declared): explore ~zero weight; "
                               "confirm weakened (2022 inside); forward only clean test",
                 "n_refits": n_refits}

    for name, win, years in (("explore_2004_2018", EXPLORE, 15.0),
                             ("confirm_2019_2024", CONFIRM, 6.0)):
        spy = rets["SPY"].loc[win].dropna()
        n2, n1 = net2.loc[win], net1.loc[win]
        blk = {
            "jm2": window_block(n2, spy, risk_off, gate, f"JM2 {name}", years),
            "jm1_ablation": {**dh.stats(n1, f"JM1 {name}"),
                             "t_jm2_vs_jm1_monthly":
                                 round(dh.t_excess_monthly(n2, n1), 2)},
            "benchmarks": {
                "spy_bh": dh.stats(spy, "SPY B&H"),
                "6040": dh.stats((0.6 * rets["SPY"] + 0.4 * rets["TLT"])
                                 .loc[win].dropna(), "60/40"),
            },
            "calendar": {y: round(float((1 + n2.loc[y]).prod() - 1), 4)
                         for y in (["2008"] if name.startswith("explore")
                                   else ["2020", "2022"])},
        }
        out[name] = blk

    # frozen confirm bars
    cf = out["confirm_2019_2024"]
    spy_cf = cf["benchmarks"]["spy_bh"]
    jm2_cf = cf["jm2"]
    bars = {
        "cagr_bar": jm2_cf["cagr"] >= spy_cf["cagr"] - 0.01,
        "dd_bar": jm2_cf["max_dd"] >= (2 / 3) * spy_cf["max_dd"],
        "switch_bar": jm2_cf["switches_per_yr"] <= 12,
    }
    out["confirm_bars"] = {**bars, "verdict":
        "PASS (forward paper-lane CANDIDACY only, provenance attached)"
        if all(bars.values()) else "REJECT — instrument CLOSES, family closed"}

    # gate-lookback diagnostics (confirm window, reported never re-picked)
    diag = {}
    for lb in (63, 252):
        g_d = gate_series(t10, lb)
        w_d = build_weights(risk_off, g_d, gld_ok).shift(1).dropna()
        n_d = dh.backtest(w_d, rets, COST_BPS)["net"].loc[CONFIRM]
        diag[f"lookback_{lb}"] = dh.stats(n_d, f"JM2 diag lb={lb} confirm")
    out["gate_diagnostics_confirm_never_repicked"] = diag

    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))
    print(f"\n-> {out_path}")


if __name__ == "__main__":
    main()
