"""P0 WRDS harvest — the one session that unblocks the roadmap (2026-07-30).

Adjudicated in `aegis-finance docs/research/AI_PANEL_2026-07-30C_ROUND15.md` §5.
Round 15's finding was that all five external reviewers' falsifiable predictions
were UNRUNNABLE on the current data layer. This pull is the fix.

Publication map (why each item is here):

  1. optionm entitlement probe   -> settles the single-stock options branch.
     578 tables are CATALOGUED, which proves visibility, NOT read access. One
     10-row query answers it. Cheapest decisive item in the project, so it runs
     FIRST — if the Duo session dies later, this answer is already banked.

  2. crsp.msf shrout             -> shares outstanding, absent from every CRSP
     file we hold (verified 2026-07-30). Without it there is no institutional
     ownership FRACTION, only a share count, so the Kirk (2025) abnormal-IO
     construction cannot be built cleanly. One column, 1980+ to cover the
     tr13f_ownership_ext history.

  3. crsp.dsf full universe      -> daily returns. Unblocks THREE families
     closed only at monthly resolution (PEAD NEG_RESULTS §14, 8-K §20, FDA §16)
     plus the queued 13D/13G candidate, and makes the round-15 panel prediction
     R15-4 scoreable. Includes askhi/bidlo, which also unblocks a
     Corwin-Schultz spread estimator — INSTR-COST-MODEL recorded it as
     infeasible precisely because our pull had no daily high/low, so this gives
     the KO cost model a second, independent check.

House rules honoured: ONE connection = ONE Duo push; cheapest-and-most-decisive
first; the biggest/riskiest pull LAST; save-on-arrival; per-year checkpointing
so a mid-pull failure keeps everything already fetched; resume-safe (re-running
skips years already on disk); manifest written even on partial failure.

Requires the WRDS-routable network (HKU VPN).

Usage:  python -m scripts.fetch_wrds_p0
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
DSF_DIR = RAW / "dsf_full"

DSF_START_YEAR, DSF_END_YEAR = 2002, 2024      # matches crsp_panel_2002
SHROUT_START = "1980-01-01"                    # covers tr13f_ownership_ext


def _save(df, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def main() -> None:
    t0 = time.time()
    manifest: dict = {
        "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "purpose": "P0 roadmap unblock — options entitlement, shrout, daily CRSP",
    }
    RAW.mkdir(parents=True, exist_ok=True)

    print("opening WRDS connection — APPROVE THE DUO PUSH ON YOUR PHONE", flush=True)
    db = get_connection()          # single Duo push
    print("connected.\n", flush=True)

    try:
        # ── 1. optionm entitlement probe (cheapest decisive item) ────────────
        print("[1/3] optionm entitlement probe", flush=True)
        probe: dict = {}
        for tbl in ("opprcd2015", "secprd2015", "vsurfd2015"):
            try:
                df = db.raw_sql(f"select * from optionm.{tbl} limit 5")
                probe[tbl] = {"readable": True, "cols": list(df.columns),
                              "n_returned": len(df)}
                print(f"  optionm.{tbl}: READABLE ({len(df.columns)} cols)", flush=True)
            except Exception as e:                       # noqa: BLE001
                probe[tbl] = {"readable": False,
                              "error": f"{type(e).__name__}: {str(e)[:300]}"}
                print(f"  optionm.{tbl}: NOT READABLE — "
                      f"{type(e).__name__}: {str(e)[:160]}", flush=True)
        manifest["optionm_probe"] = probe
        manifest["optionm_entitled"] = any(v.get("readable") for v in probe.values())
        print(f"  => optionm read entitlement: "
              f"{'YES' if manifest['optionm_entitled'] else 'NO'}\n", flush=True)
        (RAW / "manifest_p0.json").write_text(json.dumps(manifest, indent=2, default=str))

        # ── 2. shrout (one column, small, unblocks Kirk-style abnormal IO) ───
        print("[2/3] crsp.msf shrout", flush=True)
        t = time.time()
        try:
            sh = db.raw_sql(
                f"""select a.permno, a.date, a.shrout
                    from crsp.msf a
                    join crsp.msenames b
                      on a.permno = b.permno
                     and a.date between b.namedt
                         and coalesce(b.nameendt, current_date)
                    where a.date >= '{SHROUT_START}'
                      and b.shrcd in (10, 11)
                      and b.exchcd in (1, 2, 3)""",
                date_cols=["date"])
            _save(sh, RAW / "crsp_msf_shrout.parquet")
            manifest["crsp_msf_shrout"] = {
                "rows": len(sh), "permnos": int(sh["permno"].nunique()),
                "first": str(sh["date"].min()), "last": str(sh["date"].max()),
                "seconds": round(time.time() - t, 1)}
            print(f"  OK {len(sh):,} rows, {sh['permno'].nunique():,} permnos "
                  f"({manifest['crsp_msf_shrout']['seconds']}s)\n", flush=True)
        except Exception as e:                           # noqa: BLE001
            manifest["crsp_msf_shrout"] = {"error": f"{type(e).__name__}: {e}"}
            print(f"  FAILED: {type(e).__name__}: {e}\n", flush=True)
            traceback.print_exc()
        (RAW / "manifest_p0.json").write_text(json.dumps(manifest, indent=2, default=str))

        # ── 3. crsp.dsf full universe, per-year, checkpointed (the monster) ──
        print(f"[3/3] crsp.dsf {DSF_START_YEAR}-{DSF_END_YEAR}, per-year checkpointed",
              flush=True)
        DSF_DIR.mkdir(parents=True, exist_ok=True)
        years: dict = {}
        for yr in range(DSF_START_YEAR, DSF_END_YEAR + 1):
            out = DSF_DIR / f"dsf_{yr}.parquet"
            if out.exists():                              # resume-safe
                print(f"  {yr}: already on disk, skipping", flush=True)
                years[yr] = {"skipped_existing": True}
                continue
            t = time.time()
            try:
                df = db.raw_sql(
                    f"""select a.permno, a.date, a.ret, a.prc, a.vol,
                               a.askhi, a.bidlo, a.openprc, a.shrout
                        from crsp.dsf a
                        join crsp.msenames b
                          on a.permno = b.permno
                         and a.date between b.namedt
                             and coalesce(b.nameendt, current_date)
                        where a.date between '{yr}-01-01' and '{yr}-12-31'
                          and b.shrcd in (10, 11)
                          and b.exchcd in (1, 2, 3)""",
                    date_cols=["date"])
                _save(df, out)
                years[yr] = {"rows": len(df),
                             "permnos": int(df["permno"].nunique()),
                             "seconds": round(time.time() - t, 1)}
                print(f"  {yr}: {len(df):,} rows, {df['permno'].nunique():,} permnos "
                      f"({years[yr]['seconds']}s)", flush=True)
            except Exception as e:                        # noqa: BLE001
                years[yr] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
                print(f"  {yr}: FAILED — {type(e).__name__}: {str(e)[:200]}", flush=True)
            manifest["crsp_dsf_years"] = years
            (RAW / "manifest_p0.json").write_text(
                json.dumps(manifest, indent=2, default=str))

        ok = [y for y, v in years.items() if "rows" in v]
        manifest["crsp_dsf_summary"] = {
            "years_fetched": len(ok),
            "years_failed": [y for y, v in years.items() if "error" in v],
            "total_rows": sum(v["rows"] for v in years.values() if "rows" in v),
        }
    finally:
        try:
            db.close()
        except Exception:                                 # noqa: BLE001
            pass
        manifest["total_seconds"] = round(time.time() - t0, 1)
        (RAW / "manifest_p0.json").write_text(json.dumps(manifest, indent=2, default=str))
        print(f"\nmanifest -> {RAW / 'manifest_p0.json'}  "
              f"({manifest['total_seconds']}s total)", flush=True)


if __name__ == "__main__":
    main()
