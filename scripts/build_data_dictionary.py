"""Human-readable data dictionary for the WRDS harvest.

For each raw table: every column with a plain-English meaning, dtype, non-null %,
and three real example values pulled from the file. Writes a markdown doc you can
read top-to-bottom, and prints the CRSP monthly section to the console.

Output (git-ignored — WRDS is licensed):
    data/DATA_DICTIONARY.md
Usage:
    .venv\\Scripts\\python -m scripts.build_data_dictionary
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT

RAW = MODULE_ROOT / "data" / "wrds_raw"
OUT = MODULE_ROOT / "data" / "DATA_DICTIONARY.md"

# Curated plain-English meanings for the columns we actually pulled.
DESC = {
    # --- CRSP monthly (crsp_msf) ---
    "permno": "CRSP permanent security id — stable through ticker/name changes. THE join key.",
    "date": "Month-end date of the observation.",
    "ret": "Total holding-period return for the month (incl. dividends), decimal (0.03 = +3%).",
    "prc": "Month-end price. NEGATIVE = bid/ask midpoint (no trade that day); we take abs(prc).",
    "vol": "Monthly share volume in units of 100 shares (CRSP convention).",
    "exchcd": "Exchange: 1=NYSE, 2=AMEX, 3=NASDAQ (we keep only these three).",
    "dlret": "Delisting return — the return realized when the stock left the exchange (from msedelist).",
    "dlstcd": "Delisting code: 100=still active; 200s=merger/acquisition; 500 & 520-584=performance/liquidity (the 'bad' delists).",
    "dlstdt": "Delisting date.",
    # --- Compustat annual (comp_funda) ---
    "gvkey": "Compustat permanent company id. Join to CRSP permno via the CCM link table.",
    "datadate": "Fiscal period-end date (annual or quarterly).",
    "fyear": "Fiscal year.",
    "cusip": "Security CUSIP (links to IBES / other vendors).",
    "tic": "Ticker symbol (point-in-time, can change).",
    "conm": "Company name.",
    "at": "Total assets ($M).",
    "lt": "Total liabilities ($M).",
    "ceq": "Common/ordinary equity ($M) — book equity for B/M.",
    "seq": "Stockholders' equity ($M).",
    "ni": "Net income ($M).",
    "ib": "Income before extraordinary items ($M).",
    "sale": "Sales/turnover ($M).",
    "revt": "Total revenue ($M).",
    "cogs": "Cost of goods sold ($M).",
    "xsga": "SG&A expense ($M).",
    "gp": "Gross profit ($M) — gross-profitability signal (Novy-Marx).",
    "dp": "Depreciation & amortization ($M).",
    "oancf": "Operating activities net cash flow ($M) — accruals = ni - oancf.",
    "act": "Current assets ($M).",
    "lct": "Current liabilities ($M).",
    "che": "Cash & short-term investments ($M).",
    "dlc": "Debt in current liabilities ($M).",
    "dltt": "Long-term debt ($M).",
    "capx": "Capital expenditures ($M) — investment signal.",
    "csho": "Common shares outstanding (M).",
    "prcc_f": "Fiscal-year-close price. Market cap = prcc_f * csho.",
    "txditc": "Deferred taxes & investment tax credit ($M).",
    "pstk": "Preferred stock ($M).",
    # --- Compustat quarterly (comp_fundq) ---
    "fyearq": "Fiscal year of the quarter.",
    "fqtr": "Fiscal quarter (1-4).",
    "rdq": "Report date of quarterly earnings — THE PEAD event date (when earnings became public).",
    "epsfxq": "EPS fully diluted, quarter.",
    "epspxq": "EPS basic excl. extraordinary, quarter.",
    "ibq": "Income before extraordinary items, quarter ($M).",
    "niq": "Net income, quarter ($M).",
    "saleq": "Sales, quarter ($M).",
    "revtq": "Revenue, quarter ($M).",
    "atq": "Total assets, quarter ($M).",
    "ceqq": "Common equity, quarter ($M).",
    "cshoq": "Shares outstanding, quarter (M).",
    "prccq": "Quarter-close price.",
    # --- CCM link (ccm_link) ---
    "permco": "CRSP permanent COMPANY id (a company can have several permnos).",
    "linktype": "Link quality: LC/LU are the reliable primary links.",
    "linkprim": "P=primary, C=primary-in-a-range — keep these to avoid double counting.",
    "linkdt": "Link valid-from date.",
    "linkenddt": "Link valid-to date (NaT = still valid).",
    # --- IBES (ibes_epsus) ---
    "ticker": "IBES ticker (NOT the exchange ticker) — IBES's own security id.",
    "cname": "Company name in IBES.",
    "statpers": "Statistical period — the date this consensus snapshot was compiled (monthly).",
    "fpi": "Forecast period: 1=FY1, 2=FY2, 6/7=next quarters.",
    "measure": "Estimate type (we pulled EPS).",
    "fpedats": "Forecast period-end date the estimate targets.",
    "numest": "Number of analysts in the consensus.",
    "meanest": "Mean EPS estimate — track month-over-month to get the REVISION signal.",
    "medest": "Median EPS estimate.",
    "stdev": "Dispersion of estimates (disagreement).",
    "anndats_act": "Date the actual was announced.",
    "actual": "Realized actual EPS (for surprise = actual - meanest).",
}

TABLE_DESC = {
    "crsp_msf": "CRSP monthly stock file — survivorship-free prices & returns with real delisting returns. The backtest spine.",
    "comp_funda": "Compustat annual fundamentals — balance sheet & income statement for value/quality/accruals/investment signals.",
    "comp_fundq": "Compustat quarterly fundamentals — includes rdq, the earnings-announcement date that anchors PEAD studies.",
    "ccm_link": "CRSP<->Compustat link history — bridges permno (prices) to gvkey (fundamentals).",
    "ibes_epsus": "IBES US EPS consensus history — analyst mean/median estimates over time -> revision & surprise signals.",
}

ORDER = ["crsp_msf", "comp_funda", "comp_fundq", "ccm_link", "ibes_epsus"]


def _examples(s: pd.Series, k: int = 3) -> str:
    vals = s.dropna().unique()[:k]
    out = []
    for v in vals:
        if isinstance(v, float):
            out.append(f"{v:.4g}")
        else:
            out.append(str(v)[:24])
    return ", ".join(out) if out else "(all null)"


def table_section(stem: str) -> str:
    fp = RAW / f"{stem}.parquet"
    if not fp.exists():
        return f"## `{stem}` — MISSING\n\n"
    df = pd.read_parquet(fp)
    lines = [f"## `{stem}` — {TABLE_DESC.get(stem, '')}",
             f"\n**{len(df):,} rows × {df.shape[1]} columns**  ·  file {fp.stat().st_size/1e6:.1f} MB\n",
             "| column | meaning | dtype | non-null | example values |",
             "|---|---|---|---|---|"]
    for c in df.columns:
        nn = f"{df[c].notna().mean()*100:.0f}%"
        desc = DESC.get(c, "_(see WRDS manual)_").replace("|", "\\|")
        lines.append(f"| `{c}` | {desc} | {df[c].dtype} | {nn} | {_examples(df[c])} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parts = ["# WRDS Data Dictionary",
             "\n_Auto-generated from the harvested parquet files. WRDS data is licensed — this file "
             "lives under the git-ignored `data/` tree; do not publish._\n",
             "Column meanings are curated; example values are pulled live from the data.\n"]
    for stem in ORDER:
        parts.append(table_section(stem))
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {OUT}\n", flush=True)
    # Echo the CRSP monthly section so it shows in the console.
    print(table_section("crsp_msf"), flush=True)


if __name__ == "__main__":
    main()
