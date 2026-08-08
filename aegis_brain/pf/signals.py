"""Signal registry for the portfolio factory — panel-computable scores only.

Two families:

  osap:<ACRONYM>   Open Source Asset Pricing firm characteristics, loaded from
                   the LOCAL parquet (data/osap/firm_char.parquet). The wide
                   file is PRE-SIGNED (higher = higher predicted return), so
                   direction is ALWAYS +1 here — re-applying the doc Sign is
                   the double-flip defect corrected on 2026-08-08 (CORRIGENDUM
                   _OSAP_SIGNS). Any adapter change must be reconciled against
                   an internal implementation before use.

  native:<name>    Constructions computed from the panel itself, so they exist
                   for the full 63 years with no external dependency.

The backend's production signal_engine is deliberately NOT wired in: it reads
yfinance and current fundamentals, neither of which is point-in-time. The
factory's ENGINE-ALPHA strategy uses the panel-implementable proxy of the same
composite, and says so on its scorecard.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.osap import ScoreGridder

logger = logging.getLogger(__name__)

OSAP_PARQUET = MODULE_ROOT / "data" / "osap" / "firm_char.parquet"
INSIDER_PARQUET = MODULE_ROOT / "data" / "insider_panel.parquet"

NATIVE = {
    "native:mom_12_1": "12-1 momentum (Jegadeesh-Titman): cumulative return "
                       "t-12..t-2, skipping the reversal month",
    "native:rev_1m": "short-term reversal: negative of last month's return",
    "native:vol_12m_low": "low volatility: negative 12m std of monthly returns",
    "native:max_ret_low": "lottery-aversion: negative 12m max monthly return",
    "native:price_level": "log month-end price (penny-stock aversion)",
    "native:liq_high": "log median daily dollar volume (liquidity tilt)",
    "native:mom_36_13_low": "long-horizon reversal: negative return t-36..t-13",
}


def _native(panel: Panel, key: str) -> pd.DataFrame:
    ret, prc, dv = panel.monthly_ret, panel.month_end_price, panel.monthly_dollar_vol
    if key == "native:mom_12_1":
        logret = np.log1p(ret.clip(lower=-0.99))
        return logret.shift(1).rolling(11, min_periods=8).sum()
    if key == "native:rev_1m":
        return -ret
    if key == "native:vol_12m_low":
        return -ret.rolling(12, min_periods=9).std()
    if key == "native:max_ret_low":
        return -ret.rolling(12, min_periods=9).max()
    if key == "native:price_level":
        return np.log(prc.where(prc > 0))
    if key == "native:liq_high":
        return np.log(dv.where(dv > 0))
    if key == "native:mom_36_13_low":
        logret = np.log1p(ret.clip(lower=-0.99))
        return -logret.shift(13).rolling(24, min_periods=18).sum()
    raise KeyError(key)


def _insider_cluster(panel: Panel) -> pd.DataFrame:
    """Insider buying intensity: distinct opportunistic buyers over 12 months.

    PIT by construction — stamped on FILING date (when the market could see it),
    never transaction date. Non-classifiable and routine (10b5-1-style) buys are
    excluded per Cohen-Malloy-Pomorski. A name with no filings scores 0, which
    is an observation, not missing data; months before the SEC bulk archive
    begins are NaN so the signal cannot rank a universe of structural zeros.
    """
    cols = ["filing_date", "rptowner_cik", "permno", "is_classifiable",
            "is_routine"]
    df = pd.read_parquet(INSIDER_PARQUET, columns=cols)
    df = df[df["is_classifiable"].fillna(False).astype(bool)
            & ~df["is_routine"].fillna(False).astype(bool)]
    df = df.dropna(subset=["permno"])
    df["sym"] = df["permno"].astype("int64").astype(str)
    df["m"] = (pd.to_datetime(df["filing_date"]).dt.to_period("M")
               .dt.to_timestamp("M"))
    per_month = df.groupby(["m", "sym"])["rptowner_cik"].nunique().unstack()
    first_m = per_month.index.min()
    wide = (per_month.reindex(index=panel.monthly_ret.index,
                              columns=panel.monthly_ret.columns)
            .fillna(0.0))
    rolled = wide.rolling(12, min_periods=1).sum()
    rolled.loc[rolled.index < first_m + pd.DateOffset(months=11)] = np.nan
    return rolled


class SignalLibrary:
    """Materializes score frames once per panel; OSAP rows are read once."""

    def __init__(self, panel: Panel) -> None:
        self.panel = panel
        self._cache: dict[str, pd.DataFrame] = {}
        self._gridder: ScoreGridder | None = None
        self._osap_cols: list[str] | None = None

    # ── OSAP ────────────────────────────────────────────────────────────────
    def _ensure_osap(self, acronyms: list[str]) -> None:
        if self._gridder is not None:
            return
        import pyarrow.parquet as pq

        avail = {f.name for f in pq.ParquetFile(OSAP_PARQUET).schema_arrow}
        missing = [a for a in acronyms if a not in avail]
        if missing:
            raise KeyError(f"OSAP parquet lacks {missing} — refusing to run a "
                           "silently reduced signal set")
        cols = ["permno", "yyyymm"] + list(dict.fromkeys(acronyms))
        self._osap_long = pd.read_parquet(OSAP_PARQUET, columns=cols)
        self._gridder = ScoreGridder(self._osap_long, self.panel)

    def get(self, key: str) -> pd.DataFrame:
        if key in self._cache:
            return self._cache[key]
        if key.startswith("osap:"):
            acr = key.split(":", 1)[1]
            self._ensure_osap([acr])
            if acr not in self._osap_long.columns:  # second signal, new column
                raise KeyError(f"{acr} not preloaded; call preload() with the "
                               "full signal list before get()")
            frame = self._gridder.grid(self._osap_long[acr])
        elif key.startswith("native:"):
            frame = _native(self.panel, key)
        elif key == "insider:cluster12m":
            frame = _insider_cluster(self.panel)
        else:
            raise KeyError(f"unknown signal key {key!r}")
        frame = frame.astype(np.float32)
        cov = float(frame.notna().sum(axis=1).mean())
        if cov < 50:
            raise RuntimeError(f"signal {key}: mean coverage {cov:.0f} "
                               "names/month — too thin to build a book on "
                               "(fail loud, do not run a degenerate strategy)")
        logger.info("signal %s: coverage %.0f names/month", key, cov)
        self._cache[key] = frame
        return frame

    def preload(self, keys: list[str]) -> None:
        osap = [k.split(":", 1)[1] for k in keys if k.startswith("osap:")]
        if osap:
            self._ensure_osap(osap)
        for k in keys:
            self.get(k)


def composite_score(
    lib: SignalLibrary,
    weighted_keys: tuple[tuple[str, float], ...],
    eligible: pd.DataFrame,
    *,
    min_weight_coverage: float = 0.5,
) -> tuple[pd.DataFrame, dict]:
    """Weighted cross-sectional rank composite, computed inside the eligible set.

    Each signal is ranked to [0,1] per month across ELIGIBLE names only (ranking
    against ineligible names would let the excluded tail set the scale). Names
    missing a signal have that signal's weight renormalized away, and a name is
    scored only if the weight it does carry reaches `min_weight_coverage`.
    Returns (score frame, coverage diagnostics).
    """
    lib.preload([k for k, _ in weighted_keys])
    elig = eligible.reindex(index=lib.panel.monthly_ret.index,
                            columns=lib.panel.monthly_ret.columns).fillna(False)

    num = None
    den = None
    for key, wt in weighted_keys:
        f = lib.get(key).where(elig)
        r = f.rank(axis=1, pct=True)
        present = r.notna()
        contrib = (r.fillna(0.0) * wt)
        num = contrib if num is None else num + contrib
        w = present.astype(np.float32) * wt
        den = w if den is None else den + w

    total_w = float(sum(abs(w) for _, w in weighted_keys))
    ok = den >= (min_weight_coverage * total_w)
    score = (num / den).where(ok)
    diag = {
        "signals": [k for k, _ in weighted_keys],
        "weights": [w for _, w in weighted_keys],
        "mean_scored_names_per_month": round(
            float(score.notna().sum(axis=1).mean()), 1),
        "mean_eligible_names_per_month": round(float(elig.sum(axis=1).mean()), 1),
        "min_weight_coverage": min_weight_coverage,
    }
    if diag["mean_scored_names_per_month"] < 30:
        raise RuntimeError(f"composite scores only "
                           f"{diag['mean_scored_names_per_month']} names/month "
                           "— refusing to build a book on it")
    return score.astype(np.float32), diag


def random_score(panel: Panel, seed: int, rho: float) -> pd.DataFrame:
    """Persistent random score: AR(1) in the cross-section.

    rho controls how sticky the random ranking is, which is how a random
    control is turnover-matched to a real strategy (rho=0 churns every month,
    rho→1 buys and holds). Same shape/index as the panel.
    """
    rng = np.random.default_rng(seed)
    idx, cols = panel.monthly_ret.index, panel.monthly_ret.columns
    out = np.empty((len(idx), len(cols)), dtype=np.float32)
    prev = rng.standard_normal(len(cols)).astype(np.float32)
    out[0] = prev
    k = np.float32(np.sqrt(max(1.0 - rho * rho, 0.0)))
    for i in range(1, len(idx)):
        prev = np.float32(rho) * prev + k * rng.standard_normal(
            len(cols)).astype(np.float32)
        out[i] = prev
    return pd.DataFrame(out, index=idx, columns=cols)
