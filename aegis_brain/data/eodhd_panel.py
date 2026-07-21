"""Read-only loader over the aegis-finance EODHD archive.

Archive layout (STRICTLY READ-ONLY, see config.py):
    <EODHD_ROOT>/active/<SYMBOL>.csv.gz     — 18,128 live listings
    <EODHD_ROOT>/delisted/<SYMBOL>.csv.gz   — 32,334 dead listings (the scarce asset)

Each file: Date,Open,High,Low,Close,Adjusted_close,Volume (daily rows).

The panel is monthly and delisting-aware: a delisted name stays in the panel
until its history ends, then receives DELIST_RETURN (Shumway convention) in the
month after its last full month — EODHD carries no true delisting return; that
limitation is inherent until WRDS/CRSP lands and must be reported with results.
"""

from __future__ import annotations

import gzip
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from aegis_brain.config import (
    DELIST_RETURN,
    EODHD_ROOT,
    MIN_MEDIAN_DOLLAR_VOLUME,
    MIN_PRICE,
    PANEL_START,
)

logger = logging.getLogger(__name__)


# Universe hygiene: TRIAL-BRAIN-000 exposed that OTC/pink-sheet listings carry
# catastrophic data glitches (monthly "returns" up to 3.3e9). The clean universe
# is a DEFINITION (major listed exchanges, common stock only), not result-driven
# data editing.
CLEAN_EXCHANGES = {"NYSE", "NASDAQ", "AMEX", "NYSE ARCA", "NYSE MKT", "BATS"}
CLEAN_TYPES = {"Common Stock"}

# Monthly returns beyond these bounds are data errors, not markets: a positive
# price series cannot lose more than 100%, and >2000% in a month on a major
# exchange is adjusted-close corruption. Nulled with a count in build stats.
RET_FLOOR = -1.0
RET_CAP = 20.0


def load_symbol_metadata(root: Path | None = None) -> dict[str, dict[str, dict]]:
    """{'active': {code: {exchange, type}}, 'delisted': {...}} from the archive's
    symbol-list JSONs (latest file per directory kind)."""
    root = Path(root) if root else EODHD_ROOT
    out: dict[str, dict[str, dict]] = {}
    for kind in ("active", "delisted"):
        lists = sorted(root.glob(f"{kind}_symbol_list_*.json.gz"))
        meta: dict[str, dict] = {}
        if lists:
            with gzip.open(lists[-1], "rt") as fh:
                for row in json.load(fh):
                    meta[row.get("Code", "")] = {
                        "exchange": row.get("Exchange"),
                        "type": row.get("Type"),
                    }
        out[kind] = meta
    return out


def list_symbols(universe: str = "all", root: Path | None = None) -> dict[str, Path]:
    """Map symbol → file path for 'active', 'delisted', or 'all'.

    On symbol collision (a ticker present in both dirs) the delisted file wins
    for the historical panel only if the active one is missing — in practice
    collisions are ticker reuse, and the active listing is the current claimant,
    so active wins and the reused dead history is dropped (bias noted: this
    slightly UNDERSTATES historical deaths; report alongside results).
    """
    root = Path(root) if root else EODHD_ROOT
    if not root.exists():
        raise FileNotFoundError(f"EODHD archive not found at {root}")
    out: dict[str, Path] = {}
    dirs = {"active": ["active"], "delisted": ["delisted"],
            "all": ["delisted", "active"]}[universe]
    for d in dirs:  # active last so it wins collisions in 'all'
        for f in (root / d).glob("*.csv.gz"):
            out[f.name[: -len(".csv.gz")]] = f
    return out


def list_clean_symbols(universe: str = "all", root: Path | None = None,
                       exchanges: set[str] = CLEAN_EXCHANGES,
                       types: set[str] = CLEAN_TYPES) -> dict[str, Path]:
    """list_symbols restricted to major-exchange common stock via list metadata.

    A file whose symbol is missing from the metadata is EXCLUDED (unknown
    provenance is treated as dirty, the conservative direction).
    """
    root = Path(root) if root else EODHD_ROOT
    meta = load_symbol_metadata(root)
    out: dict[str, Path] = {}
    dirs = {"active": ["active"], "delisted": ["delisted"],
            "all": ["delisted", "active"]}[universe]
    for d in dirs:
        m = meta.get(d, {})
        for f in (root / d).glob("*.csv.gz"):
            sym = f.name[: -len(".csv.gz")]
            info = m.get(sym)
            if info and info["exchange"] in exchanges and info["type"] in types:
                out[sym] = f
    return out


def load_history(path: Path) -> pd.DataFrame:
    """Load one ticker's daily history. Returns empty frame on a corrupt file."""
    try:
        with gzip.open(path, "rt") as fh:
            df = pd.read_csv(fh, parse_dates=["Date"], index_col="Date")
    except Exception as exc:  # corrupt / empty member — skip, never crash a build
        logger.warning("unreadable history %s: %s", path.name, exc)
        return pd.DataFrame()
    if df.empty or "Adjusted_close" not in df.columns:
        return pd.DataFrame()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


@dataclass
class Panel:
    """Monthly wide panel: rows = month-end dates, cols = symbols."""

    monthly_ret: pd.DataFrame        # month-over-month adjusted total return
    month_end_price: pd.DataFrame    # unadjusted close at month end (for $1 floor)
    monthly_dollar_vol: pd.DataFrame # median daily Close*Volume within the month
    delist_month: dict[str, pd.Timestamp] = field(default_factory=dict)

    @property
    def symbols(self) -> list[str]:
        return list(self.monthly_ret.columns)

    def eligible(self, min_price: float = MIN_PRICE,
                 min_dollar_vol: float = MIN_MEDIAN_DOLLAR_VOLUME) -> pd.DataFrame:
        """Boolean formation-date eligibility mask (dates × symbols).

        Uses information available AT the formation month end only.
        """
        return (self.month_end_price >= min_price) & (
            self.monthly_dollar_vol >= min_dollar_vol
        )


def _monthly_from_daily(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """(monthly adjusted return, month-end close, monthly median dollar volume)."""
    adj = df["Adjusted_close"].replace(0.0, np.nan)
    close = df["Close"]
    dollar = (close * df["Volume"]).astype(float)
    m_adj = adj.resample("ME").last()
    ret = m_adj.pct_change()
    m_close = close.resample("ME").last()
    m_dollar = dollar.resample("ME").median()
    return ret, m_close, m_dollar


def build_panel(
    symbols: dict[str, Path],
    start: str = PANEL_START,
    end: str | None = None,
    min_months: int = 13,
    delist_return: float = DELIST_RETURN,
    progress: bool = False,
) -> Panel:
    """Assemble the monthly panel from per-ticker files.

    Args:
        symbols: symbol → path map (from list_symbols, possibly subset).
        start/end: panel window; names whose entire history falls outside are dropped.
        min_months: minimum monthly observations inside the window to include a
            name (13 = enough to compute a 12-1 momentum signal once).
        delist_return: applied in the month AFTER a name's last observation if
            that month is still inside the panel window (i.e., the name died,
            the window didn't end). np.nan disables the convention.
    """
    end_ts = pd.Timestamp(end) if end else None
    start_ts = pd.Timestamp(start)

    rets: dict[str, pd.Series] = {}
    prices: dict[str, pd.Series] = {}
    dollars: dict[str, pd.Series] = {}
    delist_month: dict[str, pd.Timestamp] = {}

    items = symbols.items()
    if progress:
        from tqdm import tqdm
        items = tqdm(items, total=len(symbols), desc="panel")

    for sym, path in items:
        df = load_history(path)
        if df.empty:
            continue
        df = df.loc[df.index >= start_ts - pd.DateOffset(months=1)]
        if end_ts is not None:
            df = df.loc[df.index <= end_ts]
        if df.empty:
            continue
        ret, m_close, m_dollar = _monthly_from_daily(df)
        ret = ret.loc[ret.index >= start_ts]
        if ret.dropna().shape[0] < min_months:
            continue
        rets[sym] = ret
        prices[sym] = m_close.loc[m_close.index >= start_ts]
        dollars[sym] = m_dollar.loc[m_dollar.index >= start_ts]
        delist_month[sym] = ret.index.max()

    if not rets:
        raise ValueError("No symbols survived panel filters")

    monthly_ret = pd.DataFrame(rets).sort_index()
    # Impossible-return hygiene: null anything outside (RET_FLOOR, RET_CAP].
    bad = (monthly_ret <= RET_FLOOR) | (monthly_ret > RET_CAP)
    n_bad = int(bad.sum().sum())
    if n_bad:
        logger.warning("nulled %d impossible monthly returns (<=-100%% or >2000%%)", n_bad)
        monthly_ret = monthly_ret.mask(bad)
    month_end_price = pd.DataFrame(prices).reindex(monthly_ret.index)
    monthly_dollar_vol = pd.DataFrame(dollars).reindex(monthly_ret.index)

    # Delisting convention: if a name's series ends before the panel does,
    # stamp delist_return in the first month after its last observation.
    if delist_return is not None and not np.isnan(delist_return):
        panel_last = monthly_ret.index.max()
        idx = monthly_ret.index
        for sym, last in delist_month.items():
            if last < panel_last:
                pos = idx.searchsorted(last) + 1
                if pos < len(idx):
                    monthly_ret.loc[idx[pos], sym] = delist_return

    return Panel(
        monthly_ret=monthly_ret,
        month_end_price=month_end_price,
        monthly_dollar_vol=monthly_dollar_vol,
        delist_month=delist_month,
    )


def load_cached_panel(cache_dir: Path) -> Panel:
    """Reload a panel cached by scripts/build_panel_cache.py.

    The delisting stamp was applied at build time and is baked into the cached
    monthly_ret; delist_month is reconstructed as each column's last valid index.
    """
    cache_dir = Path(cache_dir)
    monthly_ret = pd.read_parquet(cache_dir / "monthly_ret.parquet")
    month_end_price = pd.read_parquet(cache_dir / "month_end_price.parquet")
    monthly_dollar_vol = pd.read_parquet(cache_dir / "monthly_dollar_vol.parquet")
    delist_month = {
        sym: monthly_ret[sym].last_valid_index() for sym in monthly_ret.columns
    }
    return Panel(
        monthly_ret=monthly_ret,
        month_end_price=month_end_price,
        monthly_dollar_vol=monthly_dollar_vol,
        delist_month=delist_month,
    )
