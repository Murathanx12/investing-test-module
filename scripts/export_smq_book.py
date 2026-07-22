"""Export the smallmid-quality book artifact — BRAIN-007 composite, top 30.

Forms TODAY's book under the exact frozen BRAIN-007 spec (mean of winsorized
z-scores: gross_prof PIT + opportunistic-insider 12m flag; universe =
fundamentals coverage AND eligible AND above-median dollar volume), then maps
permno -> latest CRSP ticker. Output is the PROMOTION artifact committed into
aegis-finance/backend/data/ by the human (firewall: this module never writes
there).

Known, documented staleness (refreshed by the quarterly duty):
  - dollar-vol ranks / eligibility from panel end (2024-12)
  - insider flags from the SEC bulk panel (through its panel_end)
  - gp from comp_funda (6-month reporting lag applies)

Usage:  .venv\\Scripts\\python -m scripts.export_smq_book
Output: export/smallmid_quality/smallmid_quality_book.json
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.fundamentals import FundStore, load_characteristics

TOP_N = 30
INSIDER = MODULE_ROOT / "data" / "insider_panel.parquet"
STOCKNAMES = MODULE_ROOT / "data" / "wrds_raw" / "crsp_stocknames.parquet"
OUT = MODULE_ROOT / "export" / "smallmid_quality"


def zscore(s: pd.Series) -> pd.Series:
    return ((s - s.mean()) / s.std(ddof=1)).clip(-3, 3)


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    last_m = panel.monthly_ret.index.max()

    # segment/eligibility at panel end (documented staleness)
    elig = panel.eligible().loc[last_m]
    dv = panel.monthly_dollar_vol.loc[last_m].where(elig)
    large = dv >= dv.median()

    # freshest gp per permno: latest available (PIT-lagged) value
    chars = load_characteristics()
    chars = chars.sort_values("avail_month").drop_duplicates("sym", keep="last")
    chars = chars[chars["avail_month"] <= pd.Timestamp.utcnow().tz_localize(None)]
    gp = chars.set_index("sym")["gross_prof"]

    # insider flag: opportunistic filing in the trailing 12 months of the panel
    ins = pd.read_parquet(INSIDER)
    ins = ins[ins["permno"].notna() & ins["is_classifiable"] & ~ins["is_routine"]]
    cutoff = ins["filing_date"].max() - pd.DateOffset(months=12)
    recent = set(ins.loc[ins["filing_date"] >= cutoff, "permno"]
                 .astype("Int64").astype(str))

    elig_ok = elig.fillna(False).astype(bool)
    large_ok = large.fillna(False).astype(bool)
    uni = [s for s in panel.monthly_ret.columns
           if elig_ok.get(s, False) and large_ok.get(s, False)
           and s in gp.index and pd.notna(gp[s])]
    z_gp = zscore(gp.reindex(uni))
    flag = pd.Series([1.0 if s in recent else 0.0 for s in uni], index=uni)
    z_in = zscore(flag)
    composite = (z_gp + z_in) / 2.0
    top = composite.nlargest(TOP_N)

    # permno -> latest ticker/name
    nm = pd.read_parquet(STOCKNAMES)
    nm["permno"] = nm["permno"].astype("Int64").astype(str)
    nm = nm.sort_values("namedt").drop_duplicates("permno", keep="last")
    nm = nm.set_index("permno")

    holdings = []
    for p, score in top.items():
        row = nm.loc[p] if p in nm.index else None
        holdings.append({
            "permno": p,
            "ticker": (row["ticker"] if row is not None else None),
            "name": (row["comnam"] if row is not None else None),
            "composite_z": round(float(score), 4),
            "z_gp": round(float(z_gp[p]), 4),
            "insider_flag": bool(flag[p] > 0),
        })

    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True,
                          cwd=MODULE_ROOT).stdout.strip()
    art = {
        "artifact": "smallmid_quality_book",
        "method": "BRAIN-007 frozen composite (mean winsorized z: gp PIT + "
                  "opportunistic-insider 12m flag), top 30 EW, above-median "
                  "dollar-vol universe",
        "formed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "module_commit": head,
        "panel_end": str(last_m.date()),
        "insider_panel_max_filing": str(ins["filing_date"].max().date()),
        "n_universe": len(uni),
        "n_with_insider_flag_in_book": int(sum(h["insider_flag"] for h in holdings)),
        "holdings": holdings,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "smallmid_quality_book.json"
    path.write_text(json.dumps(art, indent=2))
    print(json.dumps({k: v for k, v in art.items() if k != "holdings"}, indent=2))
    print(f"{len(holdings)} holdings -> {path}")
    print(pd.DataFrame(holdings).to_string(index=False))


if __name__ == "__main__":
    main()
