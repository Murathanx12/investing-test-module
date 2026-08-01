"""P0b WRDS harvest — OptionMetrics, the largest untried information class.

Follows the P0 pull (2026-07-30) that proved optionm read entitlement via the
three-table probe. This pull lands the actual data for the option-implied
cross-sectional family — the one class all five round-16 reviewers put first
(docs/research/AI_PANEL_2026-08-01_ROUND16.md).

What it pulls and why (registration of the constructs happens AFTER the data
lands, per the CS-SPREAD precedent — register against real table shapes):

  1. optionm.secnmd + wrdsapps.opcrsphist  -> secid<->permno/cusip links.
     Tiny, decisive, FIRST — if the session dies here nothing else is usable
     anyway. opcrsphist is the WRDS-maintained CRSP link; secnmd is the
     cusip fallback path via crsp_stocknames.

  2. vsurfd month-end surface snapshot, 2002-2024 -> the standardized
     30/91-day, |delta| 25/50 grid (8 points/name/month). Feeds: ATM IV level,
     realized-minus-implied spread, put-call IV skew (25-delta), term slope
     (91-30). Month-end only because every candidate construct forms monthly;
     pulling daily surfaces would be ~25x the rows for zero additional
     information at the monthly formation frequency.

  3. opprcd daily per-secid volume aggregates, 2002-2024 -> total/call/put
     option volume + open interest + contract count. Feeds: O/S ratio
     (Johnson-So 2012), put-call volume ratio. Aggregated server-side so the
     per-contract table (largest in the library) never crosses the wire.

House rules honoured: ONE connection = ONE Duo push; cheapest-decisive first,
biggest last; save-on-arrival; per-year checkpointing; resume-safe (re-run
skips years on disk); manifest written on every checkpoint.

Requires the WRDS-routable network (HKU VPN).

Usage:  .venv\\Scripts\\python -m scripts.fetch_wrds_optionm
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
VSURF_DIR = RAW / "optionm_vsurf_me"
OPVOL_DIR = RAW / "optionm_opvol_daily"

START_YEAR, END_YEAR = 2002, 2024        # matches dsf_full / crsp_panel_2002


def _save(df, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def main() -> None:
    t0 = time.time()
    manifest: dict = {
        "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "purpose": "P0b — OptionMetrics surface + option volume for the "
                   "option-implied cross-sectional family",
    }
    RAW.mkdir(parents=True, exist_ok=True)

    print("opening WRDS connection — APPROVE THE DUO PUSH ON YOUR PHONE", flush=True)
    db = get_connection()          # single Duo push
    print("connected.\n", flush=True)

    try:
        # ── 1. link tables (tiny, decisive, first) ───────────────────────────
        print("[1/3] secid link tables", flush=True)
        try:
            nm = db.raw_sql("select secid, cusip, ticker, issuer, effect_date "
                            "from optionm.secnmd", date_cols=["effect_date"])
            _save(nm, RAW / "optionm_secnmd.parquet")
            manifest["optionm_secnmd"] = {"rows": len(nm),
                                          "secids": int(nm["secid"].nunique())}
            print(f"  secnmd: {len(nm):,} rows, "
                  f"{nm['secid'].nunique():,} secids", flush=True)
        except Exception as e:                            # noqa: BLE001
            manifest["optionm_secnmd"] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
            print(f"  secnmd FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)

        linked = False
        for tbl in ("wrdsapps.opcrsphist", "wrdsapps_link_crsp_optionm.opcrsphist"):
            try:
                lk = db.raw_sql(f"select * from {tbl}")
                _save(lk, RAW / "optionm_crsp_link.parquet")
                manifest["optionm_crsp_link"] = {"source": tbl, "rows": len(lk),
                                                 "cols": list(lk.columns)}
                print(f"  {tbl}: {len(lk):,} rows", flush=True)
                linked = True
                break
            except Exception as e:                        # noqa: BLE001
                print(f"  {tbl}: not readable ({type(e).__name__}) — trying next",
                      flush=True)
        if not linked:
            manifest["optionm_crsp_link"] = {
                "error": "no opcrsphist variant readable; use secnmd cusip -> "
                         "crsp_stocknames ncusip as the link path"}
            print("  NO opcrsphist — cusip fallback path will be used", flush=True)
        (RAW / "manifest_optionm.json").write_text(
            json.dumps(manifest, indent=2, default=str))

        # ── 2. vsurfd month-end snapshot, per-year checkpointed ──────────────
        print(f"\n[2/3] vsurfd month-end grid {START_YEAR}-{END_YEAR} "
              f"(days 30/91, |delta| 25/50)", flush=True)
        VSURF_DIR.mkdir(parents=True, exist_ok=True)
        vs_years: dict = {}
        for yr in range(START_YEAR, END_YEAR + 1):
            out = VSURF_DIR / f"vsurf_me_{yr}.parquet"
            if out.exists():                              # resume-safe
                vs_years[yr] = {"skipped_existing": True}
                print(f"  {yr}: already on disk, skipping", flush=True)
                continue
            t = time.time()
            try:
                df = db.raw_sql(
                    f"""select secid, date, days, delta, cp_flag,
                               impl_volatility, impl_strike, dispersion
                        from optionm.vsurfd{yr}
                        where days in (30, 91)
                          and delta in (25, 50, -25, -50)
                          and date in (select max(date) from optionm.vsurfd{yr}
                                       group by date_trunc('month', date))""",
                    date_cols=["date"])
                _save(df, out)
                vs_years[yr] = {"rows": len(df),
                                "secids": int(df["secid"].nunique()),
                                "seconds": round(time.time() - t, 1)}
                print(f"  {yr}: {len(df):,} rows, {df['secid'].nunique():,} secids "
                      f"({vs_years[yr]['seconds']}s)", flush=True)
            except Exception as e:                        # noqa: BLE001
                vs_years[yr] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
                print(f"  {yr}: FAILED — {type(e).__name__}: {str(e)[:200]}",
                      flush=True)
            manifest["vsurfd_me_years"] = vs_years
            (RAW / "manifest_optionm.json").write_text(
                json.dumps(manifest, indent=2, default=str))

        # ── 3. opprcd daily volume aggregates (the monster, LAST) ────────────
        print(f"\n[3/3] opprcd daily volume aggregates {START_YEAR}-{END_YEAR}",
              flush=True)
        OPVOL_DIR.mkdir(parents=True, exist_ok=True)
        ov_years: dict = {}
        for yr in range(START_YEAR, END_YEAR + 1):
            out = OPVOL_DIR / f"opvol_{yr}.parquet"
            if out.exists():                              # resume-safe
                ov_years[yr] = {"skipped_existing": True}
                print(f"  {yr}: already on disk, skipping", flush=True)
                continue
            t = time.time()
            try:
                df = db.raw_sql(
                    f"""select secid, date,
                               sum(volume)        as opt_vol,
                               sum(case when cp_flag = 'C' then volume
                                        else 0 end) as call_vol,
                               sum(case when cp_flag = 'P' then volume
                                        else 0 end) as put_vol,
                               sum(open_interest) as open_int,
                               count(*)           as n_contracts
                        from optionm.opprcd{yr}
                        group by secid, date""",
                    date_cols=["date"])
                _save(df, out)
                ov_years[yr] = {"rows": len(df),
                                "secids": int(df["secid"].nunique()),
                                "seconds": round(time.time() - t, 1)}
                print(f"  {yr}: {len(df):,} rows, {df['secid'].nunique():,} secids "
                      f"({ov_years[yr]['seconds']}s)", flush=True)
            except Exception as e:                        # noqa: BLE001
                ov_years[yr] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
                print(f"  {yr}: FAILED — {type(e).__name__}: {str(e)[:200]}",
                      flush=True)
            manifest["opvol_years"] = ov_years
            (RAW / "manifest_optionm.json").write_text(
                json.dumps(manifest, indent=2, default=str))

        manifest["summary"] = {
            "vsurf_years_ok": len([v for v in vs_years.values() if "rows" in v]),
            "opvol_years_ok": len([v for v in ov_years.values() if "rows" in v]),
            "vsurf_rows": sum(v.get("rows", 0) for v in vs_years.values()),
            "opvol_rows": sum(v.get("rows", 0) for v in ov_years.values()),
        }
    finally:
        try:
            db.close()
        except Exception:                                 # noqa: BLE001
            pass
        manifest["total_seconds"] = round(time.time() - t0, 1)
        (RAW / "manifest_optionm.json").write_text(
            json.dumps(manifest, indent=2, default=str))
        print(f"\nmanifest -> {RAW / 'manifest_optionm.json'}  "
              f"({manifest['total_seconds']}s total)", flush=True)


if __name__ == "__main__":
    main()
