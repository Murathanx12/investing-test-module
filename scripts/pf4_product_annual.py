"""The product question, asked of the configuration that should actually ship.

Stage D found that annual rebalancing under era-appropriate costs dominates the
registered monthly/flat-25 configuration on every axis at once — higher t,
higher post-2001 excess, a fifth of the turnover, a quarter of the cost drag and
a shallower drawdown. That is the configuration a person could hold, so it is
the one that should face the buyable alternative.

Reported, never deciding: the primary metric and the verdict are unchanged by
anything here.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.WARNING)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf.engine import buy_and_hold_universe, run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec
from scripts.pf4_product_benchmark import URL, compare, parse_french  # noqa: E402

OUT = MODULE_ROOT / "runs" / "PF4"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"


def main() -> int:
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()
    d.update({"rebalance_months": 12, "cost_model": "ko",
              "name": "PF-PROF-COMPOSITE-150__ann_era"})
    spec = StrategySpec(**d)

    f = Factory()
    elig = f.eligible(spec.segment)
    score, _ = composite_score(f.lib, spec.signals, elig)
    era = D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())
    out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era)
    net = out["monthly"]["net"].dropna()
    bench = f.spine.mkt.reindex(net.index)
    ew = buy_and_hold_universe(f.spine.panel, elig, spec, f.spine.rf).reindex(net.index)
    pd.DataFrame({"net": net, "bench": bench}).to_csv(OUT / "annual_era_monthly.csv")

    import io
    import urllib.request
    import zipfile
    req = urllib.request.Request(URL, headers={"User-Agent": "aegis-research"})
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(req, timeout=90).read()))
    parsed = parse_french(z.read(z.namelist()[0]).decode("latin-1"))

    res = {"trial": "TRIAL-PF4-DECOMPOSITION-1",
           "arm": "product benchmark, shippable configuration",
           "status": "REPORTED-NEVER-DECIDING",
           "configuration": "150 names, annual rebalance, era-appropriate costs "
                            "(KO where available, mechanical tick floor always)",
           "book": {"cagr": round(annualize(net), 4),
                    "excess_vs_benchmark": round(annualize(net)
                                                 - annualize(bench), 4),
                    "t_excess_nw": D.nw_t(net - bench),
                    "turnover_1way_annual": out["diag"]["turnover_1way_annual"],
                    "cost_drag_annual_bps": out["diag"]["cost_drag_annual_bps"],
                    "incremental_alpha_ff5_umd": D.alpha_report(
                        (net - ew).dropna(), f.factors, D.FF6)}}
    for wkey, df in parsed.items():
        col = next((c for c in df.columns
                    if c.upper().replace(" ", "") == "SMALLHIOP"), None)
        if col is None:
            continue
        res[wkey] = compare(net, df[col], bench, f"SMALL HiOP ({wkey})")
        post = net.index > "2001-03-31"
        idx = net.index[post].intersection(df[col].dropna().index)
        if len(idx) > 24:
            res[wkey]["post_2001_book_excess_vs_product"] = round(
                annualize(net.reindex(idx)) - annualize(df[col].reindex(idx)), 4)
            res[wkey]["post_2001_t_nw"] = D.nw_t(
                (net.reindex(idx) - df[col].reindex(idx)).dropna())
    res["reading"] = (
        "the French portfolios are gross of trading costs and of any expense "
        "ratio while this book is net of a measured cost model, so the "
        "comparison is biased AGAINST the book — and it is still the honest "
        "product question, because the alternative is one ticker and no work.")
    (OUT / "STAGE_C2_PRODUCT_ANNUAL.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(json.dumps(res, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
