"""Harvest the EDGAR 13D/13G quarterly form index, 2002-2024, and measure what
it can actually resolve.

Free public data — no WRDS (wrdssec is not subscribed). Every request is paced
through `edgar_13dg._sec_get` (8/s, declared UA, 403 retry, fail loud); each
quarter is checkpointed so a failure costs one quarter, not the harvest.

This harvests the INDEX ONLY. Filing bodies are not fetched: resolving the
filer/subject role for certain needs ~400k more requests and is a separate,
attended decision. What this script reports is how far the index alone gets.

Usage:  .venv\\Scripts\\python -m scripts.harvest_edgar_13dg
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.edgar_13dg import OUT_DIR, collect, resolution_report

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("harvest_13dg")

YEARS = range(2002, 2025)


def main() -> None:
    idx = collect(YEARS)
    combined = OUT_DIR / "edgar_13dg_index.parquet"
    idx.to_parquet(combined, index=False)
    log.info("wrote %s (%d rows)", combined, len(idx))

    print("\n=== filings per year by form type ===")
    idx["year"] = pd.to_datetime(idx["filed_date"]).dt.year
    acc = idx.drop_duplicates(["accession", "form_type", "year"])
    piv = (acc.pivot_table(index="year", columns="form_type",
                           values="accession", aggfunc="nunique")
           .fillna(0).astype(int))
    piv["TOTAL"] = piv.sum(axis=1)
    print(piv.to_string())

    rep = resolution_report(idx)
    print("\n=== resolution report (index alone) ===")
    print(json.dumps(rep, indent=2, default=str))

    (MODULE_ROOT / "data" / "events" /
     "edgar_13dg_resolution.json").write_text(json.dumps(
         {"per_year": piv.to_dict(), "resolution": rep}, indent=2, default=str))


if __name__ == "__main__":
    main()
