"""Era expansion pull — CRSP monthly 1962-2001 panel + pre-2002 Compustat.

Data plumbing only (roadmap Phase 3 / INSTR-ERA-CAL-1 prerequisite). No
strategy statistic is computed here. Same pipeline, filters, and delisting
handling as the certified 2002+ panel (build_crsp_panel.py) — byte-level
format compatibility so every harness runs unchanged on the era panel.

Usage:  python -m scripts.build_era_panel_pre2002   (needs HKU VPN / WRDS)
Output: data/crsp_panel_1962_2001/{monthly_ret,month_end_price,
        monthly_dollar_vol}.parquet + stats.json
        data/wrds_pre2002/{funda,fundq}.parquet (+ ccm.parquet if absent)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.crsp_panel import build_crsp_panel, fetch_crsp_monthly
from aegis_brain.data.wrds_conn import get_connection

PANEL_OUT = MODULE_ROOT / "data" / "crsp_panel_1962_2001"
COMP_OUT = MODULE_ROOT / "data" / "wrds_pre2002"
START, END = "1962-01-01", "2001-12-31"

COMP_FILTER = ("indfmt='INDL' and datafmt='STD' and popsrc='D' "
               "and consol='C' and curcd='USD'")
FUNDA_SQL = f"""
    select gvkey, datadate, fyear, cusip, tic, conm,
           at, lt, ceq, seq, ni, ib, sale, revt, cogs, xsga, gp, dp,
           oancf, act, lct, che, dlc, dltt, capx, csho, prcc_f, txditc, pstk
    from comp.funda
    where datadate < '2002-01-01' and {COMP_FILTER}
"""
FUNDQ_SQL = """
    select gvkey, datadate, fyearq, fqtr, rdq, cusip, tic,
           epsfxq, epspxq, ibq, niq, saleq, revtq, atq, ceqq, cshoq, prccq
    from comp.fundq
    where datadate < '2002-01-01'
      and indfmt='INDL' and datafmt='STD' and popsrc='D' and consol='C'
      and curcdq='USD'
"""
CCM_SQL = """
    select gvkey, lpermno as permno, lpermco as permco,
           linktype, linkprim, linkdt, linkenddt
    from crsp.ccmxpf_lnkhist
    where linktype in ('LU','LC') and linkprim in ('P','C')
"""


def main() -> None:
    t0 = time.time()
    db = get_connection()

    df = fetch_crsp_monthly(db, start=START, end=END)
    print(f"CRSP rows fetched: {len(df):,}", flush=True)
    panel = build_crsp_panel(df)
    PANEL_OUT.mkdir(parents=True, exist_ok=True)
    panel.monthly_ret.to_parquet(PANEL_OUT / "monthly_ret.parquet")
    panel.month_end_price.to_parquet(PANEL_OUT / "month_end_price.parquet")
    panel.monthly_dollar_vol.to_parquet(PANEL_OUT / "monthly_dollar_vol.parquet")
    elig = panel.eligible()
    stats = {
        "built_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "crsp.msf + msenames (shrcd 10/11, exchcd 1/2/3) + msedelist",
        "start": START, "end": END,
        "months": len(panel.monthly_ret.index),
        "first_month": str(panel.monthly_ret.index.min().date()),
        "last_month": str(panel.monthly_ret.index.max().date()),
        "permnos": len(panel.symbols),
        "rows_with_real_delisting_return": int(df["dlret"].notna().sum()),
        "mean_eligible_names_per_month": round(
            float(elig.sum(axis=1).mean()), 1),
        "note": ("ERA PANEL: registered-use-only per ROADMAP Phase 3 — every "
                 "era gets its own registration before first scan; pre-2004 "
                 "money legs are gross-only until a period cost model is "
                 "registered (INSTR-ERA-CAL-1)."),
    }
    (PANEL_OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2), flush=True)

    COMP_OUT.mkdir(parents=True, exist_ok=True)
    for name, sql, date_cols in (
            ("funda", FUNDA_SQL, ["datadate"]),
            ("fundq", FUNDQ_SQL, ["datadate", "rdq"])):
        t1 = time.time()
        d = db.raw_sql(sql, date_cols=date_cols)
        d.to_parquet(COMP_OUT / f"{name}.parquet")
        print(f"{name}: {len(d):,} rows ({time.time()-t1:.0f}s)", flush=True)
    ccm_path = COMP_OUT / "ccm.parquet"
    if not ccm_path.exists():
        d = db.raw_sql(CCM_SQL, date_cols=["linkdt", "linkenddt"])
        d.to_parquet(ccm_path)
        print(f"ccm: {len(d):,} rows", flush=True)
    db.close()
    print(f"TOTAL {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
