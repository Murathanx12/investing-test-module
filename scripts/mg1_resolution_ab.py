"""MARKET-GRAPH-1 — the resolution-rate A/B, on ONE fixed edge corpus.

WHY THIS IS A SEPARATE SCRIPT
=============================
The first pass of this trial stopped at "resolution is 13.9% — the binding
constraint is exact-name matching ('Adobe' vs `ADOBE SYSTEMS INC`), not
universe size". That is a causal claim about attrition and it deserves to be
measured rather than asserted, because the two candidate causes call for
opposite work: a matcher problem is fixed with normalisation, a universe
problem is fixed by changing who is in the panel, and doing the wrong one costs
a night.

So this measures all four cells on the SAME 3,500-document edge corpus, with
nothing else moving:

                          exact-only matcher     widened matcher
    legacy universe              A                      B
    rebuilt universe             C                      D

  A is what the first pass measured.
  B - A is everything name normalisation can buy.
  C - A is everything the universe rebuild can buy.
  D is where the trial actually runs.

"Legacy universe" is the original construction, reproduced exactly: top 300 by
market cap among names that are (i) CRSP-eligible AND (ii) carry a 10-K linked
by the plain `link_filings_by_cik` bridge, with no share-class re-link. That
bridge drops every dual-class issuer and every CRSP name its abbreviations
prevent from joining EDGAR's spelling, which is why the legacy panel contained
no Alphabet and no IBM.

    python -m scripts.mg1_resolution_ab
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT                       # noqa: E402
from aegis_brain.events.name_link import link_filings_by_cik     # noqa: E402
from scripts import mg1_config as C                              # noqa: E402
from scripts import mg1_panel as P                               # noqa: E402
from scripts.mg1_resolve import (OUT, STRICT_ROUTES,             # noqa: E402
                                 WIDE_ROUTES, NameIndex, nkey,
                                 resolve_one)


def legacy_universe(cut_dates: pd.DatetimeIndex) -> set[int]:
    """The permno set the ORIGINAL construction would have produced."""
    z = np.load(P.PANELF, allow_pickle=False)
    dates = pd.DatetimeIndex(z["dates"].astype("datetime64[ns]"))
    permnos = z["permnos"].astype(int)
    RET, PRC, MCAP = z["RET"], z["PRC"], z["MCAP"]

    subs = pd.read_parquet(P.SUBS)
    f = subs[subs["form"].isin(P.ANNUAL_FORMS)
             & (subs["primary_document"] != "")]
    f = f[(f["filing_date"] >= "2013-01-01")
          & (f["filing_date"] <= "2024-12-31")]
    linked, _ = link_filings_by_cik(f, "cik", "filing_date")   # no share class
    linked["filing_date"] = pd.to_datetime(linked["filing_date"])

    names = P.name_rows_at(cut_dates)
    out: set[int] = set()
    for t in cut_dates:
        nm = names[t]
        ix = int(np.searchsorted(dates, t, side="right") - 1)
        have = np.isin(permnos, nm.index.to_numpy())
        shrcd = np.full(len(permnos), -1)
        shrcd[have] = nm["shrcd"].reindex(permnos[have]).to_numpy()
        px = np.abs(PRC[ix].astype(np.float64))
        mc = MCAP[ix].astype(np.float64)
        tr = np.isfinite(RET[ix - C.TRAIL_DAYS + 1:ix + 1]).sum(axis=0)
        fw = np.isfinite(RET[ix + 1:ix + 1 + C.HORIZON_DAYS]).sum(axis=0)
        elig = (have & np.isin(shrcd, C.SHRCD_OK) & (px >= C.MIN_PRICE)
                & np.isfinite(mc) & (mc > 0)
                & (tr >= int(0.8 * C.TRAIL_DAYS))
                & (fw >= int(0.8 * C.HORIZON_DAYS)))
        g = linked[(linked["filing_date"] < t)
                   & (linked["filing_date"] >= t - pd.Timedelta(
                       days=C.MAX_FILING_AGE_DAYS))]
        has_doc = np.isin(permnos, g["permno"].unique()) & elig
        cand = np.where(has_doc)[0]
        cand = cand[np.argsort(-mc[cand])][:C.UNIVERSE_N]
        out.update(int(p) for p in permnos[cand])
    return out


def rate(idx: NameIndex, rows: list, routes) -> tuple[int, int, Counter]:
    n = ok = 0
    by = Counter()
    for r in rows:
        when = pd.Timestamp(r["filing_date"])
        subj = int(r["permno"])
        for e in r["edges"]:
            n += 1
            key = nkey(e["counterparty_name"])
            tk = (e.get("counterparty_ticker") or "").upper().strip() or None
            p, route, _ = resolve_one(idx, key, tk, when, routes)
            if p is None or p == subj:
                by["unresolved" if p is None else "self_loop"] += 1
                continue
            ok += 1
            by[route] += 1
    return ok, n, by


def main() -> None:
    uni = pd.read_parquet(OUT / "universe.parquet")
    uni["date"] = pd.to_datetime(uni["date"])
    cut_dates = pd.DatetimeIndex(sorted(uni["date"].unique()))
    mcap = {(d.year * 100 + d.month, int(p)): float(m)
            for d, p, m in zip(uni["date"], uni["permno"], uni["mcap"])}

    by_acc: dict = {}
    for line in (OUT / "edges_raw.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        if r.get("status") == "ok":
            by_acc[r["accession"]] = r
    rows = list(by_acc.values())

    new_set = set(uni["permno"].astype(int))
    old_set = legacy_universe(cut_dates)
    print(f"legacy universe permnos {len(old_set)}  "
          f"rebuilt {len(new_set)}  overlap {len(old_set & new_set)}",
          flush=True)

    cells = {}
    for uname, pset in (("legacy", old_set), ("rebuilt", new_set)):
        idx = NameIndex(pset, mcap)
        for mname, routes in (("exact_only", STRICT_ROUTES),
                              ("widened", WIDE_ROUTES)):
            ok, n, by = rate(idx, rows, routes)
            cells[f"{uname}/{mname}"] = {
                "resolved": ok, "raw_edges": n, "rate": round(ok / max(1, n), 4),
                "routes": dict(by)}
            print(f"  {uname:8s} universe x {mname:10s} matcher : "
                  f"{ok:6,}/{n:,} = {ok / max(1, n):6.2%}", flush=True)

    a = cells["legacy/exact_only"]["rate"]
    out = {
        "n_documents": len(rows),
        "cells": cells,
        "delta_from_matcher_only": round(
            cells["legacy/widened"]["rate"] - a, 4),
        "delta_from_universe_only": round(
            cells["rebuilt/exact_only"]["rate"] - a, 4),
        "delta_total": round(cells["rebuilt/widened"]["rate"] - a, 4),
        "n_legacy_universe_permnos": len(old_set),
        "n_rebuilt_universe_permnos": len(new_set),
    }
    (OUT / "resolution_ab.json").write_text(json.dumps(out, indent=2),
                                            encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "cells"}, indent=2))


if __name__ == "__main__":
    main()
