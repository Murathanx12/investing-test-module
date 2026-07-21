"""Minimal one-table re-pull: Compustat quarterly (comp.fundq).

The main harvest (fetch_wrds_all) got everything except fundq, which failed on a
column-name typo (curcd -> curcdq). This pulls only the missing table so we don't
re-fetch the 1.4M rows we already have. ONE connection, ONE Duo push, no retry.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.wrds_conn import get_connection

RAW = MODULE_ROOT / "data" / "wrds_raw"

FUNDQ_SQL = """
    select gvkey, datadate, fyearq, fqtr, rdq, cusip, tic,
           epsfxq, epspxq, ibq, niq, saleq, revtq, atq, ceqq, cshoq, prccq
    from comp.fundq
    where datadate >= '2002-01-01'
      and indfmt='INDL' and datafmt='STD' and popsrc='D' and consol='C' and curcdq='USD'
"""


def main() -> None:
    t = time.time()
    db = get_connection()
    try:
        df = db.raw_sql(FUNDQ_SQL, date_cols=["datadate", "rdq"])
    finally:
        db.close()
    RAW.mkdir(parents=True, exist_ok=True)
    df.to_parquet(RAW / "comp_fundq.parquet")
    print(f"comp_fundq OK {len(df):,} rows -> data/wrds_raw/comp_fundq.parquet ({round(time.time()-t,1)}s)", flush=True)


if __name__ == "__main__":
    main()
