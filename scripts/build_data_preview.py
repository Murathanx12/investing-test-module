"""Build a human-readable Excel preview of everything we harvested from WRDS.

One workbook: an Overview sheet (row counts, date ranges, one-line description of
each table) + a 100-row sample sheet per dataset + the CRSP panel stats. Lets you
eyeball what we gathered without loading millions of rows.

Output (git-ignored — WRDS data is licensed, never publish):
    data/WRDS_DATA_PREVIEW.xlsx

Usage:
    .venv\\Scripts\\python -m scripts.build_data_preview
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT

RAW = MODULE_ROOT / "data" / "wrds_raw"
PANEL = MODULE_ROOT / "data" / "crsp_panel_2002"
OUT = MODULE_ROOT / "data" / "WRDS_DATA_PREVIEW.xlsx"

# (file stem, sheet name, date column for range, one-line description)
TABLES = [
    ("crsp_msf", "CRSP_monthly", "date",
     "CRSP monthly stock file 2002+ (paper-grade returns incl. real delisting). shrcd 10/11, exchcd 1/2/3."),
    ("comp_funda", "Compustat_annual", "datadate",
     "Compustat annual fundamentals: assets, equity, income, cash flow -> value/quality/accruals signals."),
    ("comp_fundq", "Compustat_quarterly", "datadate",
     "Compustat quarterly fundamentals incl. rdq (earnings-announcement date) -> PEAD event studies."),
    ("ccm_link", "CRSP_Compustat_link", "linkdt",
     "The permno<->gvkey bridge (primary links) so Compustat/IBES can join CRSP prices."),
    ("ibes_epsus", "IBES_estimates", "statpers",
     "IBES US EPS consensus history (mean/median/#analysts) -> analyst-revision signal."),
]

SAMPLE_ROWS = 100


def main() -> None:
    overview = []
    sheets: list[tuple[str, pd.DataFrame]] = []

    for stem, sheet, datecol, desc in TABLES:
        fp = RAW / f"{stem}.parquet"
        if not fp.exists():
            overview.append({"table": sheet, "file": f"{stem}.parquet", "status": "MISSING (not fetched)",
                             "rows": 0, "columns": 0, "date_range": "", "size_MB": 0.0, "description": desc})
            continue
        df = pd.read_parquet(fp)
        rng = ""
        if datecol in df.columns and df[datecol].notna().any():
            rng = f"{pd.to_datetime(df[datecol]).min().date()} -> {pd.to_datetime(df[datecol]).max().date()}"
        overview.append({
            "table": sheet, "file": f"{stem}.parquet", "status": "OK",
            "rows": len(df), "columns": df.shape[1], "date_range": rng,
            "size_MB": round(fp.stat().st_size / 1e6, 2), "description": desc,
        })
        sheets.append((sheet, df.head(SAMPLE_ROWS)))

    # CRSP panel stats (if built)
    stats_fp = PANEL / "stats.json"
    panel_df = None
    if stats_fp.exists():
        import json
        stats = json.loads(stats_fp.read_text())
        panel_df = pd.DataFrame(list(stats.items()), columns=["metric", "value"])
        overview.append({"table": "CRSP_panel", "file": "crsp_panel_2002/", "status": "BUILT",
                         "rows": stats.get("months", 0), "columns": stats.get("permnos", 0),
                         "date_range": f"{stats.get('first_month','')} -> {stats.get('last_month','')}",
                         "size_MB": 0.0,
                         "description": "The backtest-ready monthly panel (months x permnos) built from CRSP_monthly."})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT, engine="openpyxl") as xl:
        pd.DataFrame(overview).to_excel(xl, sheet_name="Overview", index=False)
        if panel_df is not None:
            panel_df.to_excel(xl, sheet_name="CRSP_panel_stats", index=False)
        for sheet, sample in sheets:
            sample.to_excel(xl, sheet_name=sheet[:31], index=False)

    print(f"wrote {OUT}", flush=True)
    print(pd.DataFrame(overview)[["table", "status", "rows", "columns", "date_range"]].to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
