"""Signal interface (L2).

A Signal is one hand-designed, economically grounded hypothesis. Its compute()
returns a wide frame (dates × symbols) where the value AT date t uses only
information available at the end of month t — the harness pairs it with the
return of month t+1. PIT-safety lives here; get it wrong and everything
downstream is fiction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from aegis_brain.data.eodhd_panel import Panel


@dataclass(frozen=True)
class Signal:
    name: str
    # One-line economic mechanism + literature prior. Required — a signal
    # without a stated mechanism is data mining (GKX).
    hypothesis: str
    compute: Callable[[Panel], pd.DataFrame]
