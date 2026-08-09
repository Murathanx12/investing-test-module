"""PF-4 stage C (rebuilt) — is there a buyable thing that already does this?

The dossier compared the book to the market and never to the products that
implement small-cap profitability screening in one ticker. That omission is the
single most important product question in it, and external review was right to
say so.

Ken French's 6 portfolios sorted on size x operating profitability give the
long-history proxy. Two of them matter:

  SMALL HiOP, value-weighted  — the fair proxy for a BUYABLE fund (AVUV, DFSV
                                and friends are cap-weighted within their screen)
  SMALL HiOP, equal-weighted  — the fair proxy for OUR CONSTRUCTION, since the
                                book is equal-weighted

Both are GROSS of trading costs and of any expense ratio, so the comparison
flatters the product and not the book. French rebalances annually in June; the
book rebalances monthly. Neither is adjusted to the other — the differences are
stated rather than engineered away.

AVUV/DFSV themselves are NOT run: they need a PIT-clean price source this repo
does not have, and yfinance is forbidden for money claims. That gap is named.
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.harness.benchmark import load_ff_factors, newey_west_tstat
from aegis_brain.pf.panel63 import annualize, max_drawdown

OUT = MODULE_ROOT / "runs" / "PF4"
URL = ("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
       "6_Portfolios_ME_OP_2x3_CSV.zip")


def nw(x):
    r = newey_west_tstat(pd.Series(x).dropna(), lags=12)
    return None if r.get("t") is None else round(float(r["t"]), 2)


def parse_french(txt: str) -> dict[str, pd.DataFrame]:
    """Return {'value_weighted': df, 'equal_weighted': df} of monthly decimals."""
    lines = txt.splitlines()
    starts = [(i, l) for i, l in enumerate(lines) if "Returns -- Monthly" in l]
    out: dict[str, pd.DataFrame] = {}
    for i, title in starts:
        key = ("value_weighted" if "Value Weighted" in title
               else "equal_weighted" if "Equal Weighted" in title else None)
        if key is None or key in out:
            continue
        hdr = [c.strip() for c in lines[i + 1].split(",")][1:]
        rows = []
        for line in lines[i + 2:]:
            parts = [c.strip() for c in line.split(",")]
            if len(parts) != len(hdr) + 1 or len(parts[0]) != 6 \
                    or not parts[0].isdigit():
                break
            rows.append(parts)
        if not rows:
            continue
        df = pd.DataFrame(rows)
        idx = pd.to_datetime(df[0], format="%Y%m") + pd.offsets.MonthEnd(0)
        vals = df.iloc[:, 1:].astype(float)
        vals.columns = hdr
        vals.index = idx
        out[key] = vals.replace([-99.99, -999.0], np.nan) / 100.0
    return out


def compare(book: pd.Series, prod: pd.Series, bench: pd.Series,
            label: str) -> dict:
    idx = book.index.intersection(prod.dropna().index)
    b, p, m = book.reindex(idx), prod.reindex(idx), bench.reindex(idx)
    d = (b - p).dropna()
    return {
        "label": label, "months": len(idx),
        "first": str(idx.min().date()), "last": str(idx.max().date()),
        "book_cagr": round(annualize(b), 4),
        "product_cagr": round(annualize(p), 4),
        "benchmark_cagr": round(annualize(m), 4),
        "book_excess_vs_product": round(annualize(b) - annualize(p), 4),
        "product_excess_vs_benchmark": round(annualize(p) - annualize(m), 4),
        "t_book_minus_product_nw": nw(d),
        "book_max_dd": round(max_drawdown(b), 4),
        "product_max_dd": round(max_drawdown(p), 4),
        "terminal_wealth_ratio_book_over_product": round(
            float((1 + b).prod() / (1 + p).prod()), 3),
    }


def main() -> int:
    base = OUT / "base_monthly.csv"
    if not base.exists():
        raise SystemExit("runs/PF4/base_monthly.csv missing — run "
                         "scripts/pf4_gate_power.py first")
    bm = pd.read_csv(base, index_col=0, parse_dates=True)
    book, bench = bm["net"].dropna(), bm["bench"]

    req = urllib.request.Request(URL, headers={"User-Agent": "aegis-research"})
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(req, timeout=90).read()))
    parsed = parse_french(z.read(z.namelist()[0]).decode("latin-1"))

    res = {"trial": "TRIAL-PF4-DECOMPOSITION-1", "arm": "product benchmark",
           "source": URL,
           "caveats": [
               "French portfolios are GROSS of trading costs and of any fund "
               "expense ratio; the book's number is NET of 25bps trading. The "
               "comparison flatters the product.",
               "French rebalances annually in June; the book rebalances "
               "monthly. Neither is adjusted to the other.",
               "SMALL HiOP value-weighted is the fair proxy for a buyable fund; "
               "equal-weighted is the fair proxy for this book's construction.",
           ],
           "avuv_dfsv": {
               "status": "DEFERRED — NOT RUN",
               "reason": "needs a PIT-clean ETF price source; yfinance is "
                         "forbidden for money claims and none is wired in",
               "needed_from_murat": "one clean price feed (Polygon or FMP) for "
                                    "AVUV, DFSV, IJS, VBR from 2019-09"}}

    for wkey, df in parsed.items():
        col = next((c for c in df.columns if c.upper().replace(" ", "")
                    == "SMALLHIOP"), None)
        if col is None:
            res[wkey] = {"status": "column not found",
                         "columns": list(df.columns)}
            continue
        res[wkey] = compare(book, df[col], bench, f"SMALL HiOP ({wkey})")

    ff = load_ff_factors(MODULE_ROOT / "data")
    vw = parsed.get("value_weighted")
    if vw is not None:
        col = next(c for c in vw.columns if c.upper().replace(" ", "") == "SMALLHIOP")
        idx = book.index.intersection(vw[col].dropna().index)
        d = (book.reindex(idx) - vw[col].reindex(idx)).dropna()
        from aegis_brain.pf.decomp import FF6, alpha_report
        res["book_minus_buyable_product_alpha"] = alpha_report(d, ff, FF6)
        res["book_minus_buyable_product_alpha"]["reading"] = (
            "this is the number that decides whether the book is a PRODUCT: "
            "what it adds over the buyable implementation of the same idea, "
            "after factor exposures. If it is not clearly positive there is no "
            "product, only a different way to buy something purchasable in one "
            "click.")
    (OUT / "STAGE_C_PRODUCT_BENCHMARK.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(json.dumps(res, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
