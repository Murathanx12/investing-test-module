"""Disclosure for TRIAL-PF6-PRODUCT-REAL-1 — is one year carrying the result?

The registered verdict is UNRESOLVED and nothing here changes it. But two things
in the artifact would be dishonest to publish without their stress test:

  1. The 2020 COVID block shows +47.7 %/yr excess against IJS. A single block
     that large can carry an entire 22-year average, and the reader cannot see
     that from the headline.

  2. The FF5+UMD alpha against IJS is +7.17 %/yr at t 5.07 — far higher than the
     raw paired difference's t 1.78. NIGHT-4 established that FF5+UMD's RMW is
     the WRONG control for this book: a properly built small-cap profitability
     factor absorbed almost all of the alpha last time. Quoting the FF5+UMD
     number without repeating that test would be repeating the mistake NIGHT-4
     already caught.

Both are computed and printed whatever they say. Reported, never deciding.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.ERROR)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "PF6"
ETF = MODULE_ROOT / "data" / "etf" / "etf_monthly_return.parquet"
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
    net = run_book(f.spine.panel, score, elig, spec, f.spine.rf,
                   era)["monthly"]["net"].dropna()
    net.index = net.index.to_period("M").to_timestamp("M")

    # the small-cap profitability factor NIGHT-4 built — the RIGHT control
    prof = D.long_short_factor(score, elig, f.spine.panel.monthly_ret)
    prof.index = prof.index.to_period("M").to_timestamp("M")

    etf = pd.read_parquet(ETF)
    etf.index = etf.index.to_period("M").to_timestamp("M")

    res = {"analysis": "DISCLOSURE for TRIAL-PF6-PRODUCT-REAL-1",
           "status": "REPORTED-NEVER-DECIDING — the registered verdict "
                     "(UNRESOLVED) is unchanged by anything here",
           "funds": {}}

    for t in ("IJS", "VBR"):
        idx = net.index.intersection(etf[t].dropna().index)
        diff = (net.reindex(idx) - etf[t].reindex(idx)).dropna()
        ex2020 = diff[diff.index.year != 2020]
        # yearly excess, to show how concentrated the result is
        yearly = ((1 + diff).groupby(diff.index.year).prod() - 1).sort_values()

        fac = f.factors.reindex(diff.index)
        fac6 = fac.assign(prof=prof.reindex(diff.index))
        res["funds"][t] = {
            "months": int(len(diff)),
            "full_excess_annualized": round(annualize(diff), 4),
            "full_t": D.nw_t(diff),
            "ex2020_excess_annualized": round(annualize(ex2020), 4),
            "ex2020_t": D.nw_t(ex2020),
            "ex2020_months": int(len(ex2020)),
            "share_of_total_from_2020": round(
                1 - (1 + ex2020).prod() ** (12 / len(ex2020))
                / (1 + diff).prod() ** (12 / len(diff)), 3),
            "best_year": {"year": int(yearly.index[-1]),
                          "excess": round(float(yearly.iloc[-1]), 4)},
            "worst_year": {"year": int(yearly.index[0]),
                           "excess": round(float(yearly.iloc[0]), 4)},
            "positive_years": int((yearly > 0).sum()),
            "total_years": int(len(yearly)),
            "alpha_ff5_umd": D.alpha_report(diff, f.factors, D.FF6),
            "alpha_ff5_umd_PLUS_smallcap_profitability":
                D.alpha_report(diff, fac6, D.FF6 + ["prof"]),
        }
        r = res["funds"][t]
        print(f"{t}: full {r['full_excess_annualized']:+.4f} t {r['full_t']} | "
              f"ex-2020 {r['ex2020_excess_annualized']:+.4f} t {r['ex2020_t']} | "
              f"alpha FF6 {r['alpha_ff5_umd']['ann_alpha']:+.4f} "
              f"t {r['alpha_ff5_umd']['t_alpha']} -> +prof "
              f"{r['alpha_ff5_umd_PLUS_smallcap_profitability']['ann_alpha']:+.4f} "
              f"t {r['alpha_ff5_umd_PLUS_smallcap_profitability']['t_alpha']}",
              flush=True)
        print(f"   positive years {r['positive_years']}/{r['total_years']}, "
              f"best {r['best_year']}, worst {r['worst_year']}", flush=True)

    (OUT / "T1b_PRODUCT_DISCLOSURE.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
