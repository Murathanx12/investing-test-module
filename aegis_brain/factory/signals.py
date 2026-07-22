"""FactorySignal — a Signal plus a declared direction and contamination flag.

direction: +1 means "long HIGH values of compute()", -1 means "long LOW".
Declared here, before any scan runs — flipping the sign after seeing results
is a new candidate in a future batch, never a retry (docs/STRATEGY_FACTORY.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from aegis_brain.data.eodhd_panel import Panel


@dataclass(frozen=True)
class FactorySignal:
    name: str
    hypothesis: str                    # economic mechanism + literature prior
    compute: Callable[[Panel], pd.DataFrame]
    direction: int                     # +1 long-high, -1 long-low
    contaminated: bool = False         # already run over the confirm window
