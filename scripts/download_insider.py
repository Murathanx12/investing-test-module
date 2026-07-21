"""Download all SEC Insider Transactions quarterly zips, 2006Q1 to the present.

Paced under SEC's 10 req/s fair-access cap; skips already-downloaded quarters so it
is resumable. Data lands in data/sec_insider/ (git-ignored). This is step 1 of the
quarterly artifact refresh (download -> build_insider_panel -> export_routine_history);
quarters SEC has not published yet fail with a harmless 404.

Usage:  .venv\\Scripts\\python -m scripts.download_insider
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.events.insider import download_quarter

DEST = MODULE_ROOT / "data" / "sec_insider"
START_YEAR, END_YEAR = 2006, date.today().year


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    ok, skip, fail = 0, 0, 0
    for year in range(START_YEAR, END_YEAR + 1):
        for qtr in range(1, 5):
            existing = DEST / f"{year}q{qtr}_form345.zip"
            if existing.exists() and existing.stat().st_size > 0:
                skip += 1
                continue
            p = download_quarter(year, qtr, DEST, sleep_s=0.4)
            if p is not None:
                ok += 1
                print(f"[{year}Q{qtr}] OK -> {p.name} ({p.stat().st_size/1e6:.1f} MB)", flush=True)
            else:
                fail += 1
                print(f"[{year}Q{qtr}] FAILED", flush=True)
            time.sleep(0.3)
    print(f"\ndone: {ok} downloaded, {skip} already present, {fail} failed -> {DEST}", flush=True)


if __name__ == "__main__":
    main()
