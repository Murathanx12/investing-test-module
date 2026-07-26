"""INSTR-ANOMALY-TIME — one shot. Protocol: TRIALS/INSTR-ANOMALY-TIME.md.

Same gross_prof values, two availability clocks (datadate+6mo vs rdq
month-end), scanned through the frozen explore mechanics; confirm window
opens only behind the frozen gate.

Usage:  .venv\\Scripts\\python -m scripts.run_instr_anomaly_time
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel, load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.fundamentals import (RAW, STALE_LIMIT_MONTHS,
                                              load_characteristics)
from aegis_brain.factory.signals import FactorySignal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("anomaly_time")
OUT = MODULE_ROOT / "data" / "factory"

MAX_RDQ_LAG_DAYS = 183


def build_chars() -> tuple[pd.DataFrame, dict]:
    """Characteristics with both availability clocks + coverage diagnostics."""
    chars = load_characteristics()  # has gvkey, sym, datadate, avail_month
    q = pd.read_parquet(RAW / "comp_fundq.parquet",
                        columns=["gvkey", "datadate", "rdq"])
    q = q.dropna(subset=["gvkey", "datadate"]).copy()
    q["gvkey"] = q["gvkey"].astype(str).str.strip()
    q["datadate"] = pd.to_datetime(q["datadate"])
    q["rdq"] = pd.to_datetime(q["rdq"])
    q = (q.sort_values(["gvkey", "datadate"])
          .drop_duplicates(["gvkey", "datadate"], keep="last"))

    chars = chars.copy()
    chars["gvkey"] = chars["gvkey"].astype(str).str.strip()
    m = chars.merge(q, on=["gvkey", "datadate"], how="left")
    lag_days = (m["rdq"] - m["datadate"]).dt.days
    ok = m["rdq"].notna() & (lag_days > 0) & (lag_days <= MAX_RDQ_LAG_DAYS)
    m["avail_ead"] = m["avail_month"]
    m.loc[ok, "avail_ead"] = m.loc[ok, "rdq"] + pd.offsets.MonthEnd(0)

    months_gained = ((m.loc[ok, "avail_month"] - m.loc[ok, "avail_ead"])
                     .dt.days / 30.44)
    diag = {
        "firm_years": int(len(m)),
        "retimed_share": round(float(ok.mean()), 3),
        "median_rdq_lag_days": float(lag_days[ok].median()),
        "median_months_gained": round(float(months_gained.median()), 2),
    }
    log.info("coverage: %s", diag)
    return m, diag


def wide_frame(panel: Panel, chars: pd.DataFrame, avail_col: str) -> pd.DataFrame:
    """FundStore pivot logic, one characteristic, chosen availability clock."""
    c = chars[chars["sym"].isin(panel.monthly_ret.columns)]
    idx = panel.monthly_ret.index
    return (c.pivot_table(index=avail_col, columns="sym",
                          values="gross_prof", aggfunc="last")
             .reindex(idx.union(c[avail_col].unique()).sort_values())
             .ffill(limit=STALE_LIMIT_MONTHS)
             .reindex(index=idx, columns=panel.monthly_ret.columns))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    chars, diag = build_chars()

    frames = {"gp_base": wide_frame(panel, chars, "avail_month"),
              "gp_ead": wide_frame(panel, chars, "avail_ead")}
    sigs = {name: FactorySignal(
                name=name,
                hypothesis="INSTR-ANOMALY-TIME availability-timing test",
                compute=lambda p, f=f: f, direction=+1)
            for name, f in frames.items()}

    results: dict = {"diagnostics": diag, "explore": [], "confirm": []}
    explore50 = ScanConfig(cost_bps_one_way=50.0)
    for name, sig in sigs.items():
        for seg in ("small", "largemid"):
            results["explore"].append(scan_signal(panel, sig, seg)["summary"])
        s50 = scan_signal(panel, sig, "small", explore50)["summary"]
        s50["cost_bps"] = 50.0
        results["explore"].append(s50)

    ex = {(r["signal"], r["segment"], r.get("cost_bps", 25.0)): r
          for r in results["explore"]}
    base50 = ex[("gp_base", "small", 50.0)]["t_excess_net"]
    ead50 = ex[("gp_ead", "small", 50.0)]["t_excess_net"]
    gate = ead50 >= base50 and ead50 >= 1.5
    results["gate"] = {"base_t_net_50": base50, "ead_t_net_50": ead50,
                       "confirm_opens": bool(gate)}
    log.info("GATE: base %.2f vs ead %.2f -> confirm_opens=%s",
             base50, ead50, gate)

    if gate:  # frozen gate — confirm months are read ONLY behind this line
        confirm50 = ScanConfig(cost_bps_one_way=50.0,
                               first_test_month="2019-01-31",
                               last_test_month="2024-12-31")
        for name, sig in sigs.items():
            c = scan_signal(panel, sig, "small", confirm50)["summary"]
            c["window"] = "confirm"
            results["confirm"].append(c)

    with open(OUT / "instr_anomaly_time.json", "w") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
