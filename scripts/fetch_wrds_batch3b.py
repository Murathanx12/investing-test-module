"""One-connection WRDS harvest #3 (supplemental) — the long-tail pulls.

Runs AFTER fetch_wrds_batch3 (its own single Duo push). Publication map:
  - Brav-Lehavy 2003 price targets            -> ibes.ptgdet
  - PEAD robustness pre-2002                  -> comp.fundq extension 1971-2001
  - Best-ideas/breadth robustness pre-2002    -> 13F aggregates 1980-2001
  - MAX/idio-vol/Amihud on extension window   -> dsf monthly aggregates 1963-2001
  - comp_pit (as-first-reported Compustat)    -> table CATALOG ONLY this pass
    (vintaged tables are huge; plan the pull from the saved schema first)

Same rules: one connection, save-on-arrival, best-effort, riskiest last.
Usage (HKU VPN on):  .venv\\Scripts\\python -m scripts.fetch_wrds_batch3b
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.wrds_conn import get_connection

RAW = MODULE_ROOT / "data" / "wrds_raw"


def _fetch(db, name, sql, manifest, date_cols=None):
    t = time.time()
    try:
        print(f"[{name}] fetching...", flush=True)
        df = db.raw_sql(sql, date_cols=date_cols or [])
        RAW.mkdir(parents=True, exist_ok=True)
        df.to_parquet(RAW / f"{name}.parquet")
        manifest[name] = {"rows": len(df), "cols": list(df.columns),
                          "seconds": round(time.time() - t, 1)}
        print(f"[{name}] OK {len(df):,} rows ({manifest[name]['seconds']}s)", flush=True)
    except Exception as e:
        manifest[name] = {"error": f"{type(e).__name__}: {e}"}
        print(f"[{name}] FAILED: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()


def main() -> None:
    t0 = time.time()
    manifest: dict = {"fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    db = get_connection()  # single Duo push
    try:
        # 0) comp_pit + optionm + ravenpack table catalogs (cheap, plan-ahead)
        for lib in ("comp_pit", "optionm", "ravenpack_trial", "wrdsapps"):
            try:
                tabs = sorted(db.list_tables(library=lib))
                manifest[f"tables_{lib}"] = tabs
                print(f"[catalog:{lib}] {len(tabs)} tables", flush=True)
            except Exception as e:
                manifest[f"tables_{lib}"] = {"error": str(e)}

        # 1) IBES price-target detail (Brav-Lehavy; medium)
        _fetch(db, "ibes_ptgdet",
               "select ticker, cusip, cname, estimid, horizon, value, "
               "estcur, anndats, amaskcd from ibes.ptgdet "
               "where anndats >= '1999-01-01' and estcur = 'USD'",
               manifest, date_cols=["anndats"])

        # 2) Compustat quarterly extension (PEAD robustness window)
        _fetch(db, "comp_fundq_ext",
               "select gvkey, datadate, fyearq, fqtr, rdq, cusip, tic, "
               "epsfxq, epspxq, ibq, niq, saleq, revtq, atq, ceqq, cshoq, prccq "
               "from comp.fundq "
               "where datadate between '1971-01-01' and '2001-12-31' "
               "and indfmt='INDL' and datafmt='STD' and popsrc='D' "
               "and consol='C' and curcdq='USD'",
               manifest, date_cols=["datadate", "rdq"])

        # 3) 13F ownership aggregates pre-2002 (breadth robustness)
        _fetch(db, "tr13f_ownership_ext",
               "select fdate, cusip, count(distinct mgrno) as n_inst, "
               "sum(shares) as inst_shares from tr_13f.s34type3 "
               "where fdate between '1980-01-01' and '2001-12-31' "
               "group by fdate, cusip",
               manifest, date_cols=["fdate"])

        # 4) daily aggregates on the extension window (heaviest last)
        _fetch(db, "dsf_monthly_agg_ext",
               "select permno, date_trunc('month', date) as month, "
               "count(ret) as n_days, stddev(ret) as vol_d, "
               "max(ret) as max_dret, min(ret) as min_dret, "
               "avg(abs(ret)/nullif(abs(prc)*vol,0)) as amihud_d, "
               "sum(abs(prc)*vol) as dollar_vol "
               "from crsp.dsf "
               "where date between '1963-01-01' and '2001-12-31' "
               "group by permno, date_trunc('month', date)",
               manifest, date_cols=["month"])
    finally:
        db.close()
        print("[conn] WRDS connection closed", flush=True)

    manifest["total_seconds"] = round(time.time() - t0, 1)
    (RAW / "manifest_batch3b.json").write_text(json.dumps(manifest, indent=2, default=str))
    print("\n=== manifest_batch3b ===", flush=True)
    print(json.dumps(manifest, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
