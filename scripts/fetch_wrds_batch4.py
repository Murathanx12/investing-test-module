"""One-connection WRDS harvest #4 — the 2026-07-24 shopping list.

Publication map (why each pull exists):
  - ibes.adj (adjustment factors)      -> un-voids the tgt_upside rebuild
    (VOID-TGT-UPSIDE-B3B-B3C: ptgdet values are split-adjusted through the
    download date vs nominal CRSP prc; adj lets us reconstruct
    nominal-on-nominal)
  - crsp.dsf slices (pharma + events)  -> daily-CAR successor studies:
    BRAIN-006's micro segment was untestable at monthly resolution; a daily
    event study is a NEW registration and needs daily returns. Pull daily
    returns for (a) all permnos ever carrying pharma SIC 2830-2836/8731,
    (b) 2002-2024. ~few hundred MB, the biggest pull — runs LAST.
  - comp_pit starter                   -> as-first-reported fundamentals:
    pull the identifying/header table + one small vintaged table to design
    the real pull offline (catalog was saved in batch 3b).
  - BoardEx starter (NEW subscription confirmed 2026-07-24) ->
    org summary + individual profiles + networks headers. Signal class:
    event-driven governance (executive departures), weak prior recorded —
    cross-sectional monthly BoardEx sorts decayed post-2013 per panel review.

Same rules as batch 3/3b: ONE connection (one Duo push), save-on-arrival,
best-effort per table, riskiest/biggest last, manifest written even on
partial failure. Usage (HKU VPN on):
  .venv\\Scripts\\python -m scripts.fetch_wrds_batch4
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
PHARMA_SIC = "(2830,2831,2832,2833,2834,2835,2836,8731)"


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
        # 0) BoardEx catalog first (new subscription — confirm entitlement, cheap)
        for lib in ("boardex", "boardex_na", "boardsmp"):
            try:
                tabs = sorted(db.list_tables(library=lib))
                manifest[f"tables_{lib}"] = tabs
                print(f"[catalog:{lib}] {len(tabs)} tables", flush=True)
            except Exception as e:
                manifest[f"tables_{lib}"] = {"error": str(e)}
                print(f"[catalog:{lib}] unavailable: {e}", flush=True)

        # 0b) funda column extension: retained earnings (Ball et al. RE/ME),
        #     inventory/receivables (divergence signals), payout items
        #     (dvc/prstkc -> net payout yield, Goncalves duration), xrd
        _fetch(db, "comp_funda_ext_cols",
               """select gvkey, datadate, re, invt, rect, dvc, prstkc, xrd, txp
                  from comp.funda
                  where indfmt='INDL' and datafmt='STD' and popsrc='D'
                    and consol='C' and datadate >= '1995-01-01'""",
               manifest, date_cols=["datadate"])

        # 1) IBES adjustment factors (small, the un-voider)
        _fetch(db, "ibes_adj",
               "select ticker, cusip, spdates, adj from ibes.adj",
               manifest, date_cols=["spdates"])

        # 2) comp_pit starter: header/id map + a bounded slice of the
        #    as-first-reported annual table to design the full pull offline
        _fetch(db, "comp_pit_ids",
               "select * from comp_pit.r_company limit 500000", manifest)
        _fetch(db, "comp_pit_sample",
               "select * from comp_pit.co_ifndytd limit 200000", manifest)

        # 3) BoardEx starters (bounded; full pull designed offline from these)
        _fetch(db, "boardex_org_summary",
               "select * from boardex.na_wrds_org_summary limit 500000", manifest)
        _fetch(db, "boardex_dir_profiles",
               "select * from boardex.na_wrds_dir_profile_emp limit 1000000", manifest)
        _fetch(db, "boardex_company_networks",
               "select * from boardex.na_wrds_company_networks limit 1000000", manifest)

        # 4) crsp.dsf pharma slice 2002-2024 (BIGGEST — last)
        _fetch(db, "dsf_pharma_2002",
               f"""select a.permno, a.date, a.ret, a.prc, a.vol
                   from crsp.dsf a
                   where a.date between '2002-01-01' and '2024-12-31'
                     and a.permno in (
                       select distinct permno from crsp.stocknames
                       where siccd in {PHARMA_SIC})""",
               manifest, date_cols=["date"])
    finally:
        db.close()
        manifest["total_seconds"] = round(time.time() - t0, 1)
        (RAW / "manifest_batch4.json").write_text(json.dumps(manifest, indent=1, default=str))
        print(json.dumps({k: v for k, v in manifest.items()
                          if not str(k).startswith("tables_")}, indent=1, default=str))


if __name__ == "__main__":
    main()
