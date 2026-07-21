"""Export the compact CMP routine-history artifact for LIVE classification.

The bundled insider_panel.parquet ends at the last published SEC quarter, so a live
collector in aegis-finance cannot classify a 2026 Form-4 buyer (routine needs the
insider's 3 prior YEARS of purchase history) — without this artifact every live
buyer would be unclassifiable and the score would silently degrade to zero (the
house failure mode). This distills the panel into the minimum the live rule needs:

  history:      per-insider (rptowner_cik) purchase YEARS and YEAR-MONTHS,
                trans-date-keyed (the classifier consults trans_date), years >= 2020
                — enough to classify filings through panel_end_year + 3.
  recent_buys:  the panel's own CLASSIFIED opportunistic buys with filing_date within
                400d of panel end (ticker, filing_date, cik) — so a trailing-12mo live
                score can union panel coverage with the live Form-4 feed and only the
                post-panel gap rides on live fetches.
  panel_end:    max filing_date — the consumer's staleness guard anchors here.

Output: export/opportunistic_insider/cmp_routine_history.json.gz (~1-2 MB).
Usage:  .venv\\Scripts\\python -m scripts.export_routine_history
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT

PANEL = MODULE_ROOT / "data" / "insider_panel.parquet"
OUT = MODULE_ROOT / "export" / "opportunistic_insider" / "cmp_routine_history.json.gz"
HISTORY_MIN_YEAR = 2020
RECENT_WINDOW_DAYS = 400


def main() -> None:
    df = pd.read_parquet(PANEL)
    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    td = pd.to_datetime(df["trans_date"], errors="coerce")
    panel_end = df["filing_date"].max()

    # --- per-insider trans-date history (the classifier's lookup sets) ---
    hist = df[td.dt.year >= HISTORY_MIN_YEAR].copy()
    hist["_y"] = td[td.dt.year >= HISTORY_MIN_YEAR].dt.year.astype(int)
    hist["_ym"] = hist["_y"].astype(str) + "-" + td[td.dt.year >= HISTORY_MIN_YEAR].dt.month.astype(int).astype(str).str.zfill(2)
    hist = hist.dropna(subset=["rptowner_cik"])
    hist["_cik"] = hist["rptowner_cik"].astype(str).str.strip()
    years = hist.groupby("_cik")["_y"].agg(lambda s: sorted(set(int(v) for v in s)))
    yms = hist.groupby("_cik")["_ym"].agg(lambda s: sorted(set(s)))

    # --- recent classified opportunistic buys (panel side of the live union) ---
    cutoff = panel_end - pd.Timedelta(days=RECENT_WINDOW_DAYS)
    rec = df[df["is_classifiable"].fillna(False) & ~df["is_routine"].fillna(False)
             & (df["filing_date"] >= cutoff)].copy()
    rec = rec.dropna(subset=["rptowner_cik", "issuer_ticker"])
    recent_buys = [
        {"ticker": str(t).strip().upper(), "filing_date": fd.date().isoformat(),
         "cik": str(c).strip()}
        for t, fd, c in zip(rec["issuer_ticker"], rec["filing_date"], rec["rptowner_cik"])
        if str(t).strip()
    ]

    artifact = {
        "built_from": "insider_panel.parquet (SEC Insider Transactions bulk, CMP-classified)",
        "panel_end": panel_end.date().isoformat(),
        "history_min_year": HISTORY_MIN_YEAR,
        "classifier": "Cohen-Malloy-Pomorski 2012: routine = same calendar month in each of "
                      "Y-1..Y-3 (trans-date-keyed); classifiable = >=1 purchase in each of "
                      "Y-1..Y-3; opportunistic = classifiable and not routine",
        "history": {c: {"years": years[c], "year_months": yms[c]} for c in years.index},
        "recent_buys": recent_buys,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump(artifact, f, separators=(",", ":"))
    print(f"panel_end={artifact['panel_end']}  insiders={len(years):,}  "
          f"recent_opportunistic_buys={len(recent_buys):,}")
    print(f"saved -> {OUT}  ({OUT.stat().st_size/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
