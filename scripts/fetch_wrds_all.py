"""One-connection WRDS harvest: pull everything useful, save each table to raw
parquet the instant it arrives, then build the CRSP panel offline.

Design rules (learned the hard way 2026-07-20):
  - ONE connection, ONE Duo push. Never reconnect, never retry on failure.
  - Save each raw table IMMEDIATELY after fetch, BEFORE any transform, so a
    downstream bug can never cost us the connection (build the panel offline).
  - Best-effort per table: one table failing does not abort the rest.

WRDS data is licensed — the whole data/ tree is git-ignored. Never publish it.

Usage:
    .venv\\Scripts\\python -m scripts.fetch_wrds_all
Output:
    data/wrds_raw/{crsp_msf,comp_funda,comp_fundq,ccm_link,ibes_epsus}.parquet
    data/wrds_raw/manifest.json
    data/crsp_panel_2002/{monthly_ret,month_end_price,monthly_dollar_vol}.parquet + stats.json
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.crsp_panel import build_crsp_panel, fetch_crsp_monthly
from aegis_brain.data.wrds_conn import get_connection

START = "2002-01-01"
RAW = MODULE_ROOT / "data" / "wrds_raw"
PANEL_OUT = MODULE_ROOT / "data" / "crsp_panel_2002"

# Compustat row-uniqueness filters (without these you get duplicate gvkey-datadate rows).
COMP_FILTER = "indfmt='INDL' and datafmt='STD' and popsrc='D' and consol='C' and curcd='USD'"

# gvkey-level annual fundamentals: value / quality / profitability / accruals / investment.
FUNDA_SQL = f"""
    select gvkey, datadate, fyear, cusip, tic, conm,
           at, lt, ceq, seq, ni, ib, sale, revt, cogs, xsga, gp, dp,
           oancf, act, lct, che, dlc, dltt, capx, csho, prcc_f, txditc, pstk
    from comp.funda
    where datadate >= '{START}' and {COMP_FILTER}
"""

# gvkey-level quarterly fundamentals — rdq is the PEAD earnings-announcement date.
FUNDQ_SQL = f"""
    select gvkey, datadate, fyearq, fqtr, rdq, cusip, tic,
           epsfxq, epspxq, ibq, niq, saleq, revtq, atq, ceqq, cshoq, prccq
    from comp.fundq
    where datadate >= '{START}'
      and indfmt='INDL' and datafmt='STD' and popsrc='D' and consol='C' and curcdq='USD'
"""

# The permno <-> gvkey bridge (primary links only) so Compustat/IBES can join CRSP.
CCM_SQL = """
    select gvkey, lpermno as permno, lpermco as permco,
           linktype, linkprim, linkdt, linkenddt
    from crsp.ccmxpf_lnkhist
    where linktype in ('LU','LC') and linkprim in ('P','C')
"""

# IBES US EPS consensus — statpers time series gives the revisions signal.
IBES_SQL = f"""
    select ticker, cusip, cname, statpers, fpi, measure, fpedats,
           numest, meanest, medest, stdev, anndats_act, actual
    from ibes.statsum_epsus
    where statpers >= '{START}' and measure = 'EPS' and fpi in ('1','2','6','7')
"""


def _save(df, name: str) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    df.to_parquet(RAW / f"{name}.parquet")


def _fetch(db, name, sql, manifest, date_cols=None):
    """Fetch one table, save raw immediately, record outcome. Never raises."""
    t = time.time()
    try:
        print(f"[{name}] fetching...", flush=True)
        df = db.raw_sql(sql, date_cols=date_cols or [])
        _save(df, name)
        rec = {"rows": len(df), "cols": list(df.columns), "seconds": round(time.time() - t, 1)}
        manifest[name] = rec
        print(f"[{name}] OK {len(df):,} rows -> data/wrds_raw/{name}.parquet ({rec['seconds']}s)", flush=True)
        return df
    except Exception as e:  # best-effort: log and keep going
        manifest[name] = {"error": f"{type(e).__name__}: {e}"}
        print(f"[{name}] FAILED: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        return None


def main() -> None:
    t0 = time.time()
    manifest: dict = {"start_filter": START, "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    db = get_connection()  # the single auth / single Duo push
    try:
        # CRSP monthly first — the essential, pre-registered dataset. Save raw immediately.
        crsp = None
        try:
            print("[crsp_msf] fetching...", flush=True)
            crsp = fetch_crsp_monthly(db, start=START)
            _save(crsp, "crsp_msf")
            manifest["crsp_msf"] = {"rows": len(crsp), "cols": list(crsp.columns)}
            print(f"[crsp_msf] OK {len(crsp):,} rows -> data/wrds_raw/crsp_msf.parquet", flush=True)
        except Exception as e:
            manifest["crsp_msf"] = {"error": f"{type(e).__name__}: {e}"}
            print(f"[crsp_msf] FAILED: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()

        _fetch(db, "comp_funda", FUNDA_SQL, manifest, date_cols=["datadate"])
        _fetch(db, "comp_fundq", FUNDQ_SQL, manifest, date_cols=["datadate", "rdq"])
        _fetch(db, "ccm_link", CCM_SQL, manifest, date_cols=["linkdt", "linkenddt"])
        _fetch(db, "ibes_epsus", IBES_SQL, manifest, date_cols=["statpers", "fpedats", "anndats_act"])
    finally:
        db.close()  # close the WRDS session as early as possible
        print("[conn] WRDS connection closed", flush=True)

    # Everything below is OFFLINE — a crash here costs no connection.
    if crsp is not None:
        try:
            panel = build_crsp_panel(crsp)
            PANEL_OUT.mkdir(parents=True, exist_ok=True)
            panel.monthly_ret.to_parquet(PANEL_OUT / "monthly_ret.parquet")
            panel.month_end_price.to_parquet(PANEL_OUT / "month_end_price.parquet")
            panel.monthly_dollar_vol.to_parquet(PANEL_OUT / "monthly_dollar_vol.parquet")
            elig = panel.eligible()
            stats = {
                "built_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source": "crsp.msf + msenames (shrcd 10/11, exchcd 1/2/3) + msedelist",
                "start": START,
                "months": len(panel.monthly_ret.index),
                "first_month": str(panel.monthly_ret.index.min().date()),
                "last_month": str(panel.monthly_ret.index.max().date()),
                "permnos": len(panel.symbols),
                "rows_with_real_delisting_return": int(crsp["dlret"].notna().sum()),
                "mean_eligible_names_per_month": round(float(elig.sum(axis=1).mean()), 1),
            }
            (PANEL_OUT / "stats.json").write_text(json.dumps(stats, indent=2))
            manifest["crsp_panel_stats"] = stats
            print("[panel] built ->", PANEL_OUT, flush=True)
            print(json.dumps(stats, indent=2), flush=True)
        except Exception as e:
            manifest["crsp_panel_error"] = f"{type(e).__name__}: {e}"
            print(f"[panel] build FAILED (raw is saved, rebuild offline): {e}", flush=True)
            traceback.print_exc()

    manifest["total_seconds"] = round(time.time() - t0, 1)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("\n=== manifest ===", flush=True)
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
