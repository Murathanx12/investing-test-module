"""Assemble the full opportunistic-insider panel from the 76 downloaded quarters.

Parse every quarter -> concat -> classify routine/opportunistic on the FULL history
(the 3-year lookback needs all prior years) -> attach CRSP permno (PIT) -> save.

Output: data/insider_panel.parquet  (git-ignored) + prints match/classification diagnostics.
Usage:  .venv\\Scripts\\python -m scripts.build_insider_panel
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.events.insider import parse_insider_quarter, classify_routine_opportunistic
from aegis_brain.events.crsp_link import attach_permno

SRC = MODULE_ROOT / "data" / "sec_insider"
OUT = MODULE_ROOT / "data" / "insider_panel.parquet"


def main() -> None:
    t0 = time.time()
    zips = sorted(SRC.glob("*_form345.zip"))
    print(f"parsing {len(zips)} quarters...", flush=True)
    frames = []
    for z in zips:
        try:
            frames.append(parse_insider_quarter(z))
        except Exception as e:
            print(f"  {z.name} FAILED: {type(e).__name__}: {e}", flush=True)
    df = pd.concat(frames, ignore_index=True)
    print(f"total open-market purchases: {len(df):,}", flush=True)

    df = classify_routine_opportunistic(df)
    n_class = int(df["is_classifiable"].sum())
    n_routine = int((df["is_classifiable"] & df["is_routine"]).sum())
    n_opp = int((df["is_classifiable"] & ~df["is_routine"]).sum())
    print(f"classifiable: {n_class:,} | routine: {n_routine:,} | opportunistic: {n_opp:,}", flush=True)

    df, diag = attach_permno(df)
    print("permno match:", diag, flush=True)

    df.to_parquet(OUT)
    print(f"\nsaved -> {OUT}  ({round(time.time()-t0,1)}s)", flush=True)


if __name__ == "__main__":
    main()
