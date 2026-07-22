"""One-connection WRDS harvest #2 — everything the publication playbook needs.

Publication -> dataset map (why each pull exists):
  - Cohen-Frazzini 2008 "Economic Links"      -> Compustat Segment customers
    (suppliers-vs-appliers thesis, TRIAL-THEME-SUPPLY)
  - Cohen-Polk-Silli 2010 "Best Ideas"        -> Thomson 13F top holdings
  - Chen-Hong-Stein 2002 breadth of ownership -> 13F per-cusip aggregates
  - Rapach-Ringgenberg-Zhou 2016              -> short interest
  - Jegadeesh et al. 2004 / Barber et al.     -> IBES recommendations
  - Bali MAX / Ang idio-vol / Amihud (daily)  -> crsp.dsf server-side monthly
    aggregates (real daily vol/max/illiquidity instead of monthly proxies)
  - Fama-French convention (samples from 1963)-> CRSP + funda pre-2002
    extension (graduate robustness re-runs)

Design rules (same as fetch_wrds_all.py, learned 2026-07-20):
  - ONE connection, ONE Duo push. Never reconnect, never retry on failure.
  - Save each raw table IMMEDIATELY after fetch; transforms happen offline.
  - Best-effort per table; priority order = value/size, riskiest queries LAST.
  - Table names differ by subscription -> discovered live via
    information_schema, with candidate fallbacks; full library list saved to
    data/wrds_raw/wrds_catalog.json for future planning.

WRDS data is licensed — data/ is git-ignored. Never publish it.

Usage (HKU VPN on):  .venv\\Scripts\\python -m scripts.fetch_wrds_batch3
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.crsp_panel import fetch_crsp_monthly
from aegis_brain.data.wrds_conn import get_connection

RAW = MODULE_ROOT / "data" / "wrds_raw"
EXT_START, EXT_END = "1963-01-01", "2001-12-31"   # pre-panel extension window
MODERN_START = "2002-01-01"

COMP_FILTER = "indfmt='INDL' and datafmt='STD' and popsrc='D' and consol='C' and curcd='USD'"


def _save(df, name: str) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    df.to_parquet(RAW / f"{name}.parquet")


def _fetch(db, name, sql, manifest, date_cols=None):
    t = time.time()
    try:
        print(f"[{name}] fetching...", flush=True)
        df = db.raw_sql(sql, date_cols=date_cols or [])
        _save(df, name)
        rec = {"rows": len(df), "cols": list(df.columns),
               "seconds": round(time.time() - t, 1)}
        manifest[name] = rec
        print(f"[{name}] OK {len(df):,} rows ({rec['seconds']}s)", flush=True)
        return df
    except Exception as e:
        manifest[name] = {"error": f"{type(e).__name__}: {e}"}
        print(f"[{name}] FAILED: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        return None


def _discover(db, manifest) -> dict[str, str]:
    """Resolve subscription-specific table locations; dump the full catalog."""
    found: dict[str, str] = {}
    try:
        cat = db.raw_sql("""
            select table_schema, table_name from information_schema.tables
            where table_name ilike '%seg_customer%'
               or table_name in ('s34type1','s34type3','s34','sec_shortint',
                                 'recdsum','stocknames')
               or table_schema ilike '%supplychain%'
               or table_schema ilike 'wrdsapps%'
        """)
        pairs = [f"{r.table_schema}.{r.table_name}" for r in cat.itertuples()]
        manifest["discovery"] = pairs
        print("[discovery] candidates:", pairs, flush=True)
        for want in ("seg_customer", "s34type1", "s34type3", "sec_shortint",
                     "recdsum", "stocknames"):
            hits = [p for p in pairs if p.endswith(f".{want}")
                    or p.endswith(f".wrds_{want}")]
            if hits:
                # prefer wrds_-prefixed merged tables, then shortest schema
                hits.sort(key=lambda p: (0 if ".wrds_" in p else 1, len(p)))
                found[want] = hits[0]
        print("[discovery] resolved:", found, flush=True)
    except Exception as e:
        manifest["discovery"] = {"error": str(e)}
        print(f"[discovery] FAILED (using defaults): {e}", flush=True)
    try:
        libs = sorted(db.list_libraries())
        (RAW / "wrds_catalog.json").write_text(json.dumps(libs, indent=2))
        print(f"[catalog] {len(libs)} libraries -> wrds_catalog.json", flush=True)
    except Exception as e:
        print(f"[catalog] list_libraries failed: {e}", flush=True)
    return found


def main() -> None:
    t0 = time.time()
    manifest: dict = {"fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    RAW.mkdir(parents=True, exist_ok=True)

    db = get_connection()  # the single auth / single Duo push
    try:
        found = _discover(db, manifest)
        seg = found.get("seg_customer", "compseg.wrds_seg_customer")
        s34t1 = found.get("s34type1", "tr_13f.s34type1")
        s34t3 = found.get("s34type3", "tr_13f.s34type3")
        shortint = found.get("sec_shortint", "comp.sec_shortint")
        recdsum = found.get("recdsum", "ibes.recdsum")
        stocknames = found.get("stocknames", "crsp.stocknames")

        # 1) THE HEADLINE: customer-supplier links (small, Cohen-Frazzini)
        _fetch(db, "seg_customer",
               f"select * from {seg} where srcdate >= '1990-01-01'",
               manifest, date_cols=["srcdate", "datadate"])

        # 2) cusip<->permno bridge for 13F/IBES offline joins (small)
        _fetch(db, "crsp_stocknames", f"select * from {stocknames}", manifest,
               date_cols=["namedt", "nameenddt"])

        # 3) short interest (small; Rapach et al. aggregate + crowding)
        _fetch(db, "short_interest",
               f"select gvkey, iid, datadate, shortint, shortintadj "
               f"from {shortint} where datadate >= '{MODERN_START}'",
               manifest, date_cols=["datadate"])

        # 4) IBES recommendation summary (rec momentum; Jegadeesh 2004)
        _fetch(db, "ibes_recdsum",
               f"select ticker, cusip, statpers, meanrec, medrec, numrec, "
               f"numup, numdown from {recdsum} "
               f"where statpers >= '1993-01-01'",
               manifest, date_cols=["statpers"])

        # 5) 13F manager file (small)
        _fetch(db, "tr13f_mgr",
               f"select distinct mgrno, mgrname, fdate from {s34t1} "
               f"where fdate >= '{MODERN_START}'",
               manifest, date_cols=["fdate"])

        # 6) 13F per-cusip aggregates (breadth + total inst shares; server-side)
        _fetch(db, "tr13f_ownership",
               f"select fdate, cusip, count(distinct mgrno) as n_inst, "
               f"sum(shares) as inst_shares from {s34t3} "
               f"where fdate >= '{MODERN_START}' group by fdate, cusip",
               manifest, date_cols=["fdate"])

        # 7) CRSP monthly extension 1963-2001 (graduate robustness window)
        try:
            print("[crsp_msf_ext] fetching...", flush=True)
            ext = fetch_crsp_monthly(db, start=EXT_START, end=EXT_END)
            _save(ext, "crsp_msf_ext")
            manifest["crsp_msf_ext"] = {"rows": len(ext)}
            print(f"[crsp_msf_ext] OK {len(ext):,} rows", flush=True)
        except Exception as e:
            manifest["crsp_msf_ext"] = {"error": f"{type(e).__name__}: {e}"}
            print(f"[crsp_msf_ext] FAILED: {e}", flush=True)

        # 8) Compustat annual extension 1963-2001
        _fetch(db, "comp_funda_ext",
               f"""select gvkey, datadate, fyear, cusip, tic, conm,
                          at, lt, ceq, seq, ni, ib, sale, revt, cogs, xsga, gp,
                          dp, oancf, act, lct, che, dlc, dltt, capx, csho,
                          prcc_f, txditc, pstk
                   from comp.funda
                   where datadate between '{EXT_START}' and '{EXT_END}'
                     and {COMP_FILTER}""",
               manifest, date_cols=["datadate"])

        # 9) daily-file monthly aggregates (server-side; real vol/MAX/Amihud)
        _fetch(db, "dsf_monthly_agg",
               f"""select permno, date_trunc('month', date) as month,
                          count(ret) as n_days, stddev(ret) as vol_d,
                          max(ret) as max_dret, min(ret) as min_dret,
                          avg(abs(ret)/nullif(abs(prc)*vol,0)) as amihud_d,
                          sum(abs(prc)*vol) as dollar_vol
                   from crsp.dsf where date >= '{MODERN_START}'
                   group by permno, date_trunc('month', date)""",
               manifest, date_cols=["month"])

        # 10) RISKIEST LAST — best-ideas raw: top-10 holdings per mgr-quarter
        #     by shares x month-end CRSP price (join server-side, rank, keep 10)
        _fetch(db, "tr13f_top10",
               f"""with px as (
                     select permno, date_trunc('month', date) as m, abs(prc) as prc
                     from crsp.msf where date >= '{MODERN_START}'
                   ), nm as (
                     select permno, ncusip, namedt,
                            coalesce(nameenddt, current_date) as nameenddt
                     from {stocknames} where ncusip is not null
                   ), h as (
                     select t.fdate, t.mgrno, t.cusip, t.shares, px.prc,
                            row_number() over (partition by t.mgrno, t.fdate
                                               order by t.shares*px.prc desc) rn
                     from {s34t3} t
                     join nm on substr(t.cusip,1,8) = nm.ncusip
                            and t.fdate between nm.namedt and nm.nameenddt
                     join px on px.permno = nm.permno
                            and px.m = date_trunc('month', t.fdate)
                     where t.fdate >= '{MODERN_START}' and t.shares > 0
                   )
                   select fdate, mgrno, cusip, shares, prc,
                          shares*prc as value, rn
                   from h where rn <= 10""",
               manifest, date_cols=["fdate"])
    finally:
        db.close()
        print("[conn] WRDS connection closed", flush=True)

    manifest["total_seconds"] = round(time.time() - t0, 1)
    (RAW / "manifest_batch3.json").write_text(json.dumps(manifest, indent=2, default=str))
    print("\n=== manifest_batch3 ===", flush=True)
    print(json.dumps(manifest, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
