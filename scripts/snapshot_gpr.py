"""Weekly GPR snapshot — the PIT-forward archive for INSTR-GPR-EVENT.

The Caldara-Iacoviello site revises recent data and its dated vintage URLs
404, so the only honest vintage record is the one we keep ourselves: run this
every Monday (site updates the daily file Mondays) and each pull lands under a
dated filename. Never overwrite an existing snapshot.
Usage: .venv\\Scripts\\python -m scripts.snapshot_gpr
"""

from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path

import requests

SNAP_DIR = Path(__file__).resolve().parents[1] / "data" / "macro" / "gpr_snapshots"
FILES = {
    "data_gpr_daily_recent": "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls",
    "data_gpr_export": "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls",
}
MIN_BYTES = 500_000  # both files are ~2.7-3.3MB; a tiny body = error page, fail loud


def main() -> None:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.date.today().strftime("%Y%m%d")
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    failures = []
    for name, url in FILES.items():
        dest = SNAP_DIR / f"{name}_snap{stamp}.xls"
        if dest.exists():
            print(f"SKIP {dest.name} (snapshot already taken today)")
            continue
        for attempt in range(4):
            try:
                r = s.get(url, timeout=120)
                r.raise_for_status()
                if len(r.content) < MIN_BYTES:
                    raise ValueError(f"suspiciously small body ({len(r.content)}B)")
                dest.write_bytes(r.content)
                print(f"OK   {dest.name} ({len(r.content):,} bytes)")
                break
            except Exception as exc:  # noqa: BLE001 — retry then fail loud
                print(f"retry {attempt + 1} {name}: {exc}")
                time.sleep(5 * (attempt + 1))
        else:
            failures.append(name)
    if failures:
        sys.exit(f"SNAPSHOT FAILED for: {failures} — do not silently skip a week")


if __name__ == "__main__":
    main()
