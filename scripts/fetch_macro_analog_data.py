"""Fetch the macro data for INSTR-REGIME-JM2 + INSTR-REGIME-ANALOG.

Run ONCE, after the freeze commit (470ed0f). Snapshots are dated and
never overwritten silently. FRED via keyless fredgraph.csv; sector ETFs
via yfinance auto-adjusted closes (total-return proxy, same disclosed
assumption as the batch-4 ETF pull).
"""

from __future__ import annotations

import io
import sys
import time

import pandas as pd
import requests

from aegis_brain.config import MODULE_ROOT

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = MODULE_ROOT / "data" / "macro"
SNAP = "20260726"

FRED_SERIES = [
    "VIXCLS", "BAMLH0A0HYM2", "DGS10", "DGS2", "DTWEXM", "DTWEXBGS",
    "DCOILWTICO", "T10YIE", "GOLDAMGBD228NLBM", "GOLDPMGBD228NLBM",
]
SECTOR_ETFS = ["XLK", "XLE", "XLF", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB"]


def fetch_fred(series_id: str) -> pd.Series | None:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                print(f"  {series_id}: HTTP {r.status_code}")
                return None
            df = pd.read_csv(io.StringIO(r.text))
            date_col = df.columns[0]
            df[date_col] = pd.to_datetime(df[date_col])
            s = pd.to_numeric(df.set_index(date_col).iloc[:, 0], errors="coerce")
            s.name = series_id
            print(f"  {series_id}: {s.dropna().index.min().date()} -> "
                  f"{s.dropna().index.max().date()} ({s.notna().sum()} obs)")
            return s
        except requests.RequestException as exc:
            print(f"  {series_id}: attempt {attempt + 1} failed ({exc})")
            time.sleep(3)
    return None


def main() -> None:
    print("FRED:")
    cols = {}
    for sid in FRED_SERIES:
        s = fetch_fred(sid)
        if s is not None:
            cols[sid] = s
        time.sleep(1)
    fred = pd.DataFrame(cols).sort_index()
    fred_path = OUT / f"fred_macro_snap{SNAP}.parquet"
    if fred_path.exists():
        raise SystemExit(f"REFUSING to overwrite existing snapshot {fred_path}")
    fred.to_parquet(fred_path)
    print(f"wrote {fred_path} shape={fred.shape}")

    # T10YIE standalone CSV (named in the JM2 registration)
    t10 = fred[["T10YIE"]].dropna()
    t10.to_csv(OUT / f"fred_t10yie_snap{SNAP}.csv")
    print(f"wrote fred_t10yie_snap{SNAP}.csv ({len(t10)} rows)")

    print("Sector ETFs (yfinance, auto-adjusted):")
    import yfinance as yf
    px = yf.download(SECTOR_ETFS, start="1998-01-01", auto_adjust=True,
                     progress=False)["Close"]
    px.index = pd.to_datetime(px.index).tz_localize(None)
    sec_path = OUT / "sector_etf_daily_close.parquet"
    if sec_path.exists():
        raise SystemExit(f"REFUSING to overwrite {sec_path}")
    px.sort_index().to_parquet(sec_path)
    print(f"wrote {sec_path} shape={px.shape}")
    print(px.notna().idxmax())


if __name__ == "__main__":
    main()
