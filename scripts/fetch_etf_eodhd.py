"""Fetch the buyable-ETF price spine from EODHD, once, and stamp it.

This is the feed NIGHT-4 and NIGHT-5 both recorded as "blocked on Murat". It was
not blocked. The Polygon key is valid but its plan does not cover the timeframe
(HTTP 403 NOT_AUTHORIZED), and the FMP key hits a retired legacy endpoint (403)
and a premium gate on the new one (402) — but `EODHD_API_TOKEN`, already in the
environment since July, serves all four tickers with `adjusted_close` from
inception. Two nights of "waiting on a key" were my failure to test the keys we
already had.

Written to parquet with a fetch stamp so the comparison is reproducible and the
vintage is auditable. Prices only — nothing here decides anything.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aegis_brain.config import MODULE_ROOT

OUT = MODULE_ROOT / "data" / "etf"
TICKERS = ("AVUV", "DFSV", "IJS", "VBR", "SPY", "IWM", "VTI")


def _token() -> str:
    tok = os.getenv("EODHD_API_TOKEN", "")
    if not tok:
        env = Path(r"C:\Users\mrthn\aegis-finance\.env")
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("EODHD_API_TOKEN="):
                    tok = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not tok:
        raise RuntimeError("EODHD_API_TOKEN not set")
    return tok


def fetch(ticker: str, tok: str) -> pd.DataFrame:
    url = (f"https://eodhd.com/api/eod/{ticker}.US?from=1990-01-01"
           f"&period=d&fmt=json&api_token={tok}")
    req = urllib.request.Request(url, headers={"User-Agent": "aegis-research"})
    with urllib.request.urlopen(req, timeout=120) as r:
        rows = json.loads(r.read().decode())
    d = pd.DataFrame(rows)
    d["date"] = pd.to_datetime(d["date"])
    return d.set_index("date").sort_index()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tok = _token()
    meta = {"source": "EODHD /api/eod", "fetched_at":
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "price_field_used": "adjusted_close (total return: splits + "
                                "distributions applied retroactively)",
            "tickers": {}}
    frames = {}
    for t in TICKERS:
        try:
            d = fetch(t, tok)
        except Exception as exc:                            # noqa: BLE001
            meta["tickers"][t] = {"error": str(exc)[:160]}
            print(f"{t:5s} FAILED {str(exc)[:80]}", flush=True)
            continue
        frames[t] = d["adjusted_close"].astype(float)
        meta["tickers"][t] = {"rows": int(len(d)),
                              "first": str(d.index.min().date()),
                              "last": str(d.index.max().date())}
        print(f"{t:5s} {len(d):5d} rows  {d.index.min().date()} .. "
              f"{d.index.max().date()}", flush=True)

    px = pd.DataFrame(frames).sort_index()
    px.to_parquet(OUT / "etf_adjusted_close.parquet")
    monthly = px.resample("ME").last()
    monthly.pct_change().to_parquet(OUT / "etf_monthly_return.parquet")
    meta["monthly_months"] = int(len(monthly))
    (OUT / "etf_FETCH_STAMP.json").write_text(json.dumps(meta, indent=2),
                                              encoding="utf-8")
    print(json.dumps(meta["tickers"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
