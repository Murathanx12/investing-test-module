"""P0c WRDS harvest — event-study support layer (runs alongside/after P0b).

Everything here feeds the daily event harness (OPUS_SESSION_PROMPT task 2) and
the queued event families (13D/13G, daily PEAD). Ordered cheapest-decisive
first, per house rules; save-on-arrival; manifest on every checkpoint; every
item independently guarded so one failure never kills the rest.

  1. crsp.dsedelist   -> daily delisting returns. dsf.ret does NOT include the
     delisting return; every daily CAR is biased without this join. Tiny.
  2. crsp.dsi         -> daily market index returns (vwretd/ewretd/sprtrn),
     the abnormal-return benchmark. Tiny.
  3. ff daily factors -> daily factor-adjusted CARs + a WRDS-vintage
     cross-check against our pinned French-library monthly file. Tiny.
  4. ibes.actu_epsus  -> quarterly EPS actuals WITH announcement dates
     (anndats) = the event timestamps for daily PEAD. Moderate.
  5. wrdssec probe    -> is a 13D/13G filings index readable? If yes, pull the
     13D/13G rows 2002+; unblocks the queued activist-event candidate without
     an EDGAR scraper. Probe-first, non-fatal.

Requires the WRDS-routable network (HKU VPN). One connection = one Duo push.

Usage:  .venv\\Scripts\\python -m scripts.fetch_wrds_p0c
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.wrds_conn import get_connection

RAW = MODULE_ROOT / "data" / "wrds_raw"


def _save(df, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def main() -> None:
    t0 = time.time()
    manifest: dict = {
        "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "purpose": "P0c — event-study support: delisting returns, daily index, "
                   "daily FF, IBES announcement dates, 13D/13G probe",
    }
    RAW.mkdir(parents=True, exist_ok=True)

    def checkpoint() -> None:
        (RAW / "manifest_p0c.json").write_text(
            json.dumps(manifest, indent=2, default=str))

    print("opening WRDS connection — APPROVE THE DUO PUSH ON YOUR PHONE", flush=True)
    db = get_connection()          # single Duo push
    print("connected.\n", flush=True)

    try:
        # ── 1. daily delisting returns (tiny, correctness-critical) ──────────
        print("[1/5] crsp.dsedelist", flush=True)
        try:
            df = db.raw_sql("select * from crsp.dsedelist",
                            date_cols=["dlstdt"])
            _save(df, RAW / "crsp_dsedelist.parquet")
            manifest["crsp_dsedelist"] = {"rows": len(df),
                                          "cols": list(df.columns)}
            print(f"  OK {len(df):,} rows", flush=True)
        except Exception as e:                            # noqa: BLE001
            manifest["crsp_dsedelist"] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
            print(f"  FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
        checkpoint()

        # ── 2. daily market index (tiny) ─────────────────────────────────────
        print("[2/5] crsp.dsi daily index", flush=True)
        try:
            df = db.raw_sql("select date, vwretd, vwretx, ewretd, ewretx, sprtrn "
                            "from crsp.dsi where date >= '1990-01-01'",
                            date_cols=["date"])
            _save(df, RAW / "crsp_dsi.parquet")
            manifest["crsp_dsi"] = {"rows": len(df),
                                    "first": str(df["date"].min()),
                                    "last": str(df["date"].max())}
            print(f"  OK {len(df):,} rows "
                  f"({df['date'].min().date()} -> {df['date'].max().date()})",
                  flush=True)
        except Exception as e:                            # noqa: BLE001
            manifest["crsp_dsi"] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
            print(f"  FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
        checkpoint()

        # ── 3. daily Fama-French factors, WRDS vintage (tiny) ────────────────
        print("[3/5] ff daily factors", flush=True)
        for tbl, out in (("ff.factors_daily", "ff_factors_daily.parquet"),
                         ("ff.fivefactors_daily", "ff_fivefactors_daily.parquet")):
            try:
                df = db.raw_sql(f"select * from {tbl}", date_cols=["date"])
                _save(df, RAW / out)
                manifest[tbl] = {"rows": len(df), "cols": list(df.columns)}
                print(f"  {tbl}: {len(df):,} rows, cols {list(df.columns)}",
                      flush=True)
            except Exception as e:                        # noqa: BLE001
                manifest[tbl] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
                print(f"  {tbl}: FAILED — {type(e).__name__}: {str(e)[:160]}",
                      flush=True)
        checkpoint()

        # ── 4. IBES quarterly EPS actuals with announcement dates ────────────
        print("[4/5] ibes.actu_epsus (EPS actuals + anndats)", flush=True)
        try:
            probe = db.raw_sql("select * from ibes.actu_epsus limit 5")
            cols = list(probe.columns)
            manifest["ibes_actu_epsus_cols"] = cols
            print(f"  probe cols: {cols}", flush=True)
            where = "anndats >= '1998-01-01'"
            if "measure" in cols:
                where += " and measure = 'EPS'"
            if "pdicity" in cols:
                where += " and pdicity = 'QTR'"
            t = time.time()
            df = db.raw_sql(f"select * from ibes.actu_epsus where {where}",
                            date_cols=[c for c in ("anndats", "pends")
                                       if c in cols])
            _save(df, RAW / "ibes_actu_epsus.parquet")
            manifest["ibes_actu_epsus"] = {
                "rows": len(df), "where": where,
                "seconds": round(time.time() - t, 1)}
            print(f"  OK {len(df):,} rows ({manifest['ibes_actu_epsus']['seconds']}s)"
                  f"  [{where}]", flush=True)
        except Exception as e:                            # noqa: BLE001
            manifest["ibes_actu_epsus"] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
            print(f"  FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
        checkpoint()

        # ── 5. 13D/13G filings index probe (entitlement unknown, non-fatal) ──
        print("[5/5] wrdssec 13D/13G probe", flush=True)
        try:
            tables = db.list_tables(library="wrdssec")
            manifest["wrdssec_tables"] = tables
            print(f"  wrdssec catalogued: {len(tables)} tables", flush=True)
        except Exception as e:                            # noqa: BLE001
            tables = []
            manifest["wrdssec_tables"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            print(f"  list_tables failed: {type(e).__name__}", flush=True)

        pulled_13dg = False
        for tbl in ("wrds_forms", "forms", "wrds_sec_forms", "form_index"):
            if tables and tbl not in tables:
                continue
            try:
                probe = db.raw_sql(f"select * from wrdssec.{tbl} limit 5")
                cols = list(probe.columns)
                form_col = next((c for c in cols if "form" in c.lower()), None)
                date_col = next((c for c in cols
                                 if c.lower() in ("fdate", "filing_date",
                                                  "fildate", "date_filed",
                                                  "fdate_filed")), None)
                manifest[f"wrdssec_{tbl}_cols"] = cols
                print(f"  wrdssec.{tbl}: READABLE, cols {cols}", flush=True)
                if form_col and date_col:
                    t = time.time()
                    df = db.raw_sql(
                        f"""select * from wrdssec.{tbl}
                            where {form_col} in ('SC 13D', 'SC 13D/A',
                                                 'SC 13G', 'SC 13G/A')
                              and {date_col} >= '2002-01-01'""",
                        date_cols=[date_col])
                    _save(df, RAW / "wrdssec_13dg.parquet")
                    manifest["wrdssec_13dg"] = {
                        "source": f"wrdssec.{tbl}", "rows": len(df),
                        "form_col": form_col, "date_col": date_col,
                        "seconds": round(time.time() - t, 1)}
                    print(f"  13D/13G index: {len(df):,} rows from wrdssec.{tbl} "
                          f"({manifest['wrdssec_13dg']['seconds']}s)", flush=True)
                    pulled_13dg = True
                    break
            except Exception as e:                        # noqa: BLE001
                print(f"  wrdssec.{tbl}: not readable ({type(e).__name__})",
                      flush=True)
        if not pulled_13dg:
            manifest.setdefault(
                "wrdssec_13dg",
                {"status": "NOT PULLED — no readable form-index table with "
                           "recognizable form/date columns; 13D/13G falls back "
                           "to the free EDGAR full-text index path"})
            print("  13D/13G: not pulled — EDGAR fallback path stands", flush=True)
        checkpoint()

    finally:
        try:
            db.close()
        except Exception:                                 # noqa: BLE001
            pass
        manifest["total_seconds"] = round(time.time() - t0, 1)
        checkpoint()
        print(f"\nmanifest -> {RAW / 'manifest_p0c.json'}  "
              f"({manifest['total_seconds']}s total)", flush=True)


if __name__ == "__main__":
    main()
