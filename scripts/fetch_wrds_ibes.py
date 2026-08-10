"""IBES harvest — the analyst spine Murat's actual process runs on (2026-08-11).

WHY THIS EXISTS. BUILD-1.1 called every retail analyst vendor and printed the
status code: per-analyst price-target HISTORY is 402/403 on every tier we hold
(FMP legacy and stable, Finnhub, EODHD), and Yahoo returns a consensus target
with no timestamp at all. The conclusion recorded there was that our own
append-only ledger was the ONLY route to a target revision — true for the
retail data layer, and it is one day old.

The probe (runs/ARENA1/wrds_ibes_probe.json) then found ibes.ptgdet readable on
the HKU account. That is the same object the vendors sell for ~$10k/mo, back to
1999 for targets and 1992 for recommendations. It does not make the retail
ledger redundant — the ledger is what the LIVE product will run on, and IBES is
lagged and academic — but it means the QUESTION can finally be answered:

    does high analyst-implied upside predict returns, and do REVISIONS survive
    where LEVELS do not?

Pull order is cheapest-and-most-decisive first, because a WRDS session can die
at any moment and every table is written the instant it arrives:

  1. wrdsapps_link_crsp_ibes.ibcrsphist  tiny, and NOTHING joins without it
  2. ibes.ptgsumu       consensus target history  -> ANALYST-UPSIDE-1 spine
  3. ibes.recddet       per-analyst recommendations -> rating revisions
  4. ibes.statsumu_epsus EPS consensus (FY1)      -> estimate revisions
  5. ibes.ptgdet        per-analyst target detail -> the analyst RELIABILITY
                        ledger, and the only table that carries analyst identity

PIT DISCIPLINE. Every table here is pulled with its announcement/activation
dates intact (anndats/actdats, statpers). NOTHING is pulled "as of today" and
back-projected. The unadjusted (`u`) summary files are used deliberately: the
adjusted files restate history for splits, which is a look-ahead leak in a
point-in-time panel.

Usage:  python -m scripts.fetch_wrds_ibes [--only ptgsumu] [--skip ptgdet]
Writes: data/wrds_raw/ibes/*.parquet + _manifest.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT

RAW = MODULE_ROOT / "data" / "wrds_raw" / "ibes"
MANIFEST = RAW / "_manifest.json"

# US firms only (usfirm = 1) everywhere it exists: the panel is CRSP US common.
JOBS: list[tuple[str, str, str]] = [
    (
        "ibcrsphist",
        """select ticker, permno, ncusip, sdate, edate, score
           from wrdsapps_link_crsp_ibes.ibcrsphist""",
        "IBES ticker <-> CRSP permno link with validity window. Nothing joins "
        "without this, and `score` is the link quality we must filter on.",
    ),
    (
        "ptgsumu",
        """select ticker, cusip, oftic, statpers, measure, curr, numest,
                  numup4w, numdown4w, numup1m, numdown1m,
                  meanptg, medptg, stdev, ptghigh, ptglow, usfirm
           from ibes.ptgsumu
           where usfirm = '1'""",
        "Monthly CONSENSUS price target, unadjusted. `meanptg` is the exact "
        "object the PM haircuts today (implied upside = meanptg/px - 1), and "
        "numup1m/numdown1m are target-revision BREADTH — levels and revisions "
        "in one file, which is precisely the comparison ANALYST-REVISION-1 needs.",
    ),
    (
        "recddet",
        """select ticker, cusip, oftic, estimid, analyst, itext, ireccd, etext,
                  ereccd, emaskcd, amaskcd, anndats, anntims, actdats, acttims,
                  revdats, revtims, usfirm
           from ibes.recddet
           where usfirm = '1' and anndats >= '1993-01-01'""",
        "Per-analyst RECOMMENDATION with announcement timestamp. Carries analyst "
        "(amaskcd) and broker (estimid) identity -> the reliability ledger, and "
        "rating CHANGES, which is a revision rather than a level.",
    ),
    (
        "statsumu_epsus",
        """select ticker, cusip, oftic, statpers, fpi, measure, fiscalp,
                  fpedats, numest, numup, numdown, medest, meanest, stdev,
                  highest, lowest, curcode, usfirm
           from ibes.statsumu_epsus
           where usfirm = '1' and fpi in ('1','2') and measure = 'EPS'
             and statpers >= '1985-01-01'""",
        "EPS consensus summary, FY1 and FY2, unadjusted. numup/numdown ARE the "
        "canonical revision-breadth signal the literature says survives.",
    ),
    (
        "actu_epsus",
        """select ticker, cusip, oftic, pends, measure, pdicity, anndats,
                  anntims, actdats, acttims, value, curr_act, usfirm
           from ibes.actu_epsus
           where usfirm = '1' and measure = 'EPS'""",
        "Reported EPS actuals with the announcement date. Consensus minus actual "
        "is the surprise, and anndats is what makes it point-in-time rather than "
        "a number we knew afterwards.",
    ),
    (
        "ptgdet",
        """select ticker, cusip, oftic, estimid, alysnam, amaskcd, horizon,
                  value, curr, estcur, measure, anndats, anntims,
                  actdats, acttims, usfirm
           from ibes.ptgdet
           where usfirm = '1' and anndats >= '1999-01-01'""",
        "Per-analyst PRICE TARGET with announcement timestamp — the table the "
        "retail vendors gate at 402/403. Analyst identity (amaskcd) means "
        "per-analyst reliability becomes CALIBRATABLE instead of UNCALIBRATED.",
    ),
]


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - a corrupt manifest must not block a pull
            return {"corrupt_manifest_replaced_at": _stamp(), "tables": {}}
    return {"created": _stamp(), "tables": {}}


def _write_manifest(man: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    man["updated"] = _stamp()
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--skip", nargs="*", default=[])
    ap.add_argument("--force", action="store_true", help="re-pull even if on disk")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    man = _load_manifest()
    man.setdefault("tables", {})

    from aegis_brain.data.wrds_conn import get_connection

    conn = None
    try:
        for name, sql, why in JOBS:
            if args.only and name not in args.only:
                continue
            if name in args.skip:
                print(f"[skip] {name}")
                continue
            path = RAW / f"{name}.parquet"
            if path.exists() and not args.force:
                print(f"[have] {name} -> {path.name} ({path.stat().st_size/1e6:.1f} MB)")
                continue

            if conn is None:  # ONE connection = ONE Duo push
                print("[conn] opening WRDS connection ...", flush=True)
                conn = get_connection()

            print(f"[pull] {name} ...", flush=True)
            t0 = time.time()
            try:
                df = conn.raw_sql(sql)
            except Exception as exc:  # noqa: BLE001 - record and keep going
                print(f"[FAIL] {name}: {type(exc).__name__}: {str(exc)[:300]}")
                man["tables"][name] = {
                    "status": "FAILED",
                    "at": _stamp(),
                    "error": f"{type(exc).__name__}: {str(exc)[:500]}",
                    "traceback": traceback.format_exc()[-1500:],
                    "why_it_matters": why,
                }
                _write_manifest(man)
                continue

            df.to_parquet(path, index=False)
            secs = round(time.time() - t0, 1)
            entry = {
                "status": "OK",
                "at": _stamp(),
                "rows": int(len(df)),
                "columns": list(df.columns),
                "megabytes": round(path.stat().st_size / 1e6, 2),
                "seconds": secs,
                "sql": " ".join(sql.split()),
                "why_it_matters": why,
            }
            # Date coverage is the fact that decides what can be tested.
            for col in ("statpers", "anndats", "sdate"):
                if col in df.columns and len(df):
                    entry[f"{col}_min"] = str(df[col].min())
                    entry[f"{col}_max"] = str(df[col].max())
            for col in ("ticker", "amaskcd", "permno"):
                if col in df.columns:
                    entry[f"n_unique_{col}"] = int(df[col].nunique())
            man["tables"][name] = entry
            _write_manifest(man)
            print(f"[ok]   {name}: {len(df):,} rows, {entry['megabytes']} MB, {secs}s")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001, S110
                pass
        _write_manifest(man)

    print("\n" + json.dumps({k: v.get("status") for k, v in man["tables"].items()}, indent=2))
    print(f"manifest -> {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
