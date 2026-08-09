"""The check the programme did not have: an INDEPENDENT reimplementation.

External review, section E: "Your fear that undetected harness bugs remain has
exactly one real answer — rebuild the strategy from the frozen spec in a
different code path and see if it reproduces. This is the only defence against
systematic harness error and it is the one practice you don't have."

That is correct, and this file is the answer. It imports **nothing** from
`aegis_brain`. It reads the parquet files directly, re-derives eligibility, the
segment, the OSAP grid and the composite with different code, and rebuilds the
book. In particular it pivots the OSAP long frame with a plain
`pivot_table(aggfunc="last")` instead of the preallocated scatter in
`ScoreGridder` — that scatter is the single place where a silent (month, permno)
misalignment would be fatal and invisible, so it is the place most worth
building twice.

The target is the `hold_band_mult = 1.0` configuration, because with no
incumbency band and a monthly rebalance the book is exactly "the top 150 by
composite, equal-weighted", which can be stated without reference to the
engine's drift and cash bookkeeping. GROSS return is compared: cost accounting
depends on drifted incumbent weights, and reimplementing that would mean
reasoning my way to the same answer rather than checking it.

    python scripts/pf4_independent_reimpl.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\Users\mrthn\Aegis module")
ERA = ROOT / "data" / "crsp_panel_1962_2001"
MODERN = ROOT / "data" / "crsp_panel_2002"
OSAP = ROOT / "data" / "osap" / "firm_char.parquet"
FF = ROOT / "data" / "ff_factors.parquet"
OUT = ROOT / "runs" / "PF4" / "INDEPENDENT_REIMPL.json"

SIGNALS = ["GP", "OperProfRD", "CBOperProf"]
TOP_N = 150
MIN_PRICE = 1.0
MIN_DVOL = 200_000.0
FIRST, LAST = "1963-07-31", "2022-12-31"
MIN_NAMES = 100
MIN_WEIGHT_COVERAGE = 0.5


def stitch(name: str) -> pd.DataFrame:
    a = pd.read_parquet(ERA / f"{name}.parquet")
    b = pd.read_parquet(MODERN / f"{name}.parquet")
    cols = a.columns.union(b.columns)
    out = pd.concat([a.reindex(columns=cols), b.reindex(columns=cols)])
    return out.sort_index().astype("float64")


def main() -> int:
    ret = stitch("monthly_ret")
    prc = stitch("month_end_price")
    dv = stitch("monthly_dollar_vol")
    keep = (ret.index >= pd.Timestamp(FIRST)) & (ret.index <= pd.Timestamp(LAST))
    lead = ret.index[ret.index < pd.Timestamp(FIRST)]
    if len(lead):
        keep |= ret.index == lead.max()
    ret, prc, dv = ret.loc[keep], prc.loc[keep], dv.loc[keep]

    # eligibility + segment, re-derived
    elig = (prc >= MIN_PRICE) & (dv >= MIN_DVOL)
    rank_dv = dv.rank(axis=1, ascending=False)
    small = (rank_dv > 1000) & (rank_dv <= 3000)
    elig = (elig & small).fillna(False)

    # OSAP grid via pivot_table — deliberately the slow, obvious path
    cols = ["permno", "yyyymm"] + SIGNALS
    long = pd.read_parquet(OSAP, columns=cols)
    long["m"] = (pd.to_datetime(long["yyyymm"].astype("int64").astype(str),
                                format="%Y%m") + pd.offsets.MonthEnd(0))
    long["sym"] = long["permno"].astype("int64").astype(str)
    ranks, present = None, None
    for s in SIGNALS:
        grid = long.pivot_table(index="m", columns="sym", values=s,
                                aggfunc="last")
        grid = grid.reindex(index=ret.index, columns=ret.columns)
        grid = grid.where(elig)
        r = grid.rank(axis=1, pct=True)
        ranks = r.fillna(0.0) if ranks is None else ranks + r.fillna(0.0)
        p = r.notna().astype(float)
        present = p if present is None else present + p
    score = (ranks / present).where(present >= MIN_WEIGHT_COVERAGE * len(SIGNALS))

    months = ret.index
    rows = []
    for i in range(1, len(months)):
        fm, tm = months[i - 1], months[i]
        s = score.loc[fm].dropna()
        if len(s) < MIN_NAMES:
            continue
        picks = s.nlargest(TOP_N).index
        r = ret.loc[tm].reindex(picks).fillna(0.0)
        rows.append({"month": tm, "gross": float(r.mean()),
                     "n": int(len(picks))})
    book = pd.DataFrame(rows).set_index("month")["gross"]

    ff = pd.read_parquet(FF)
    bench = (ff["mktrf"] + ff["rf"]).reindex(book.index)
    yrs = len(book) / 12.0
    cagr = float((1 + book).prod() ** (1 / yrs) - 1)
    bcagr = float((1 + bench).prod() ** (1 / yrs) - 1)

    res = {
        "check": "INDEPENDENT REIMPLEMENTATION of PF-PROF-COMPOSITE-150 "
                 "(hold_band_mult=1.0), gross of costs",
        "shares_no_code_with": "aegis_brain — parquet reads, pivot_table grid, "
                               "and book loop are all rewritten",
        "first": str(book.index.min().date()), "last": str(book.index.max().date()),
        "months": len(book),
        "gross_cagr_independent": round(cagr, 4),
        "benchmark_cagr_independent": round(bcagr, 4),
        "gross_excess_cagr_independent": round(cagr - bcagr, 4),
        "mean_names_held": int(np.mean([r["n"] for r in rows])),
    }
    book.to_csv(ROOT / "runs" / "PF4" / "independent_gross_monthly.csv")
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
