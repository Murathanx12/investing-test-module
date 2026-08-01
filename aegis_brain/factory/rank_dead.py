"""INSTR-RANK-DEAD — where does the rank information go? (the replication bridge)

Spec frozen 2026-08-02 (TRIALS/INSTR-RANK-DEAD.md, module commit 98c99e2,
BEFORE this file existed). Instrument, one shot, cumulative candidate 174.

The question this answers is the program's standing methodological challenge:
published, well-documented cross-sectional results conflict with our rejections.
Three receipts now show the same shape — huge rank IC, dead long-only book:

    io_level   (small)             IC t 11.29   banked gross t +0.02   (NEG 26)
    skew_25d   (optionable small)  IC t  8.34   banked gross t ~ +1    (NEG 27)
    skew_resid (optionable small)  IC t  7.90   banked gross t ~ +1    (NEG 27)

The hypothesis is not about the signals; it is about the CONSTRUCTION CLASS.
Papers report long-short decile spreads, equal- AND value-weighted, gross. Our
graduation bar reads a long-only, cost-charged, top-decile book. If the
information lives in the short leg or below tradability, both facts are true at
once and no one is wrong. If it does not, our harness has an anomaly of its own
and the frozen doc commits the program to a harness audit (reading R4).

Everything here is GROSS. No cost model is imported, referenced or applied
anywhere in this module, so no cost dispute (NEG_RESULTS 25) can touch the
result. Nothing here can revive, graduate or seed anything: the short legs and
spreads exist to EXPLAIN, and the program is long-only by mandate.

THE LADDER (per signal, small segment, explore 2004-01..2018-12)

  L1  published conditions   D10 - D1 decile spread, equal-weighted AND
                             value-weighted, monthly, gross.
  L2  leg split              top-minus-universe (exactly the banked book's
                             gross leg) vs universe-minus-bottom (the short
                             leg's long-only mirror), EW, gross.
  L3  tradability split      rank-IC computed separately inside the upper and
                             lower halves of the segment by dollar-volume rank.

MECHANICAL PLUMBING (spec silent, precedent followed, disclosed):

  * The month set, eligibility, segment mask and minimum-cross-section rule are
    taken from `factory.explore.ScanConfig` UNCHANGED, so every rung is scored
    on exactly the months the banked book was scored on. A rung that quietly
    scored a different month set would answer a different question.
  * Decile size is `max(int(n * 0.10), 10)` — the same count the banked book
    uses for its top decile, applied symmetrically to the bottom. Using a
    different decile rule for D1 than the book uses for D10 would make L1 and
    L2 non-comparable, which is the whole point of running them together.
  * The L2 top leg is not re-implemented: it is `scan_signal(...)`'s own
    `excess_gross` series, and the bottom leg is the SAME code path with the
    frozen direction negated. This is not a sign flip in the banned sense (a
    banned sign flip revives a rejected candidate as a tradable claim); it is
    how the mirror leg is defined in the frozen ladder, and this instrument
    cannot graduate anything under any outcome.
  * Value weights are lagged market cap: price x shares outstanding at the
    FORMATION month-end, which is one month before the return being weighted.
  * Missing realised returns are skipped inside a leg mean (pandas skipna), the
    same convention `scan_signal` uses for its equal-weighted universe leg.
  * The liquidity halves in L3 split the eligible segment cross-section at its
    own median dollar-volume rank each month, so the halves are equal-sized by
    construction and the split is PIT (formation-month volume only).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.explore import ScanConfig, scan_signal, segment_mask
from aegis_brain.factory.signals import FactorySignal

logger = logging.getLogger(__name__)
RAW = MODULE_ROOT / "data" / "wrds_raw"

# ── FROZEN: the banked numbers this instrument must reproduce ────────────────
# NEG_RESULTS 26 (io_level, small, ko_half) and 27 (skew_25d, small, ko_half).
# Reproducing these to within rounding IS the guard that the frozen builders
# were rebuilt UNCHANGED. If it fails, the run is void, not "close enough".
BANKED_IC_T = {"io_level": 11.29, "skew_25d": 8.34}
BANKED_GROSS_T = {"io_level": 0.02, "skew_25d": 1.01}
REPRODUCTION_TOL = 0.005          # "to within rounding" on a 2-dp banked number

# ── FROZEN: the pre-declared readings (TRIALS/INSTR-RANK-DEAD.md) ────────────
R1_SPREAD_T = 3.0                 # L1 spread t at/above which R1 can fire
R1_BOOK_T_MAX = 0.5               # ...while the banked long-only gross t is <=
R2_RATIO = 2.0                    # bottom leg t >= 2x top leg t
R2_BOTTOM_T, R2_TOP_T = 2.0, 1.0  # ...or bottom >= 2.0 while top < 1.0
R3_RATIO = 2.0                    # lower-half IC t >= 2x upper-half IC t
R4_SPREAD_T = 1.5                 # L1 dead in BOTH weightings

DECILE_FRAC = 0.10
MIN_IC_NAMES = 30                 # scan_signal's own rule, reused verbatim


def t_stat(x: pd.Series) -> float:
    """Newey-free iid t of a monthly series mean — `scan_signal`'s own `_t`."""
    x = pd.Series(x).dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 and len(x) > 1 else 0.0


def reproduction_ok(measured: float, banked: float,
                    tol: float = REPRODUCTION_TOL) -> bool:
    """Does a rebuilt signal reproduce its banked, 2-dp explore IC t?

    The banked number is quoted to two decimals, so equality "within rounding"
    means the rebuilt value rounds to the same two decimals. Kept as a named
    function so the guard is unit-testable without a five-minute rebuild.
    """
    return bool(abs(round(float(measured), 2) - float(banked)) <= tol)


# ── market cap for the value-weighted rung ───────────────────────────────────
def market_cap_frame(panel: Panel) -> pd.DataFrame:
    """[month x sym] market cap = |month-end price| x shrout x 1000.

    Same construction abio.py and optsurf.py use for `log_mktcap`; CRSP shrout
    is in thousands of shares. Read at the FORMATION month-end, which is what
    makes the weights lagged relative to the return they weight.
    """
    idx, cols = panel.monthly_ret.index, panel.monthly_ret.columns
    sh = pd.read_parquet(RAW / "crsp_msf_shrout.parquet")
    sh = sh.dropna(subset=["shrout"])
    sh = sh[sh["shrout"] > 0].copy()
    sh["sym"] = sh["permno"].astype("Int64").astype(str)
    sh["m"] = pd.to_datetime(sh["date"]).dt.to_period("M").dt.to_timestamp("M")
    shr = (sh.sort_values("date").drop_duplicates(["sym", "m"], keep="last")
           .pivot_table(index="m", columns="sym", values="shrout", aggfunc="last")
           .reindex(index=idx, columns=cols))
    return panel.month_end_price.abs() * shr * 1000.0


# ── the monthly scoring loop, identical to scan_signal's ─────────────────────
def _months(panel: Panel, cfg: ScanConfig) -> list[tuple[pd.Timestamp,
                                                         pd.Timestamp]]:
    months = panel.monthly_ret.index
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    out = []
    for test_m in [m for m in months if lo <= m <= hi]:
        pos = months.get_loc(test_m)
        if pos == 0:
            continue
        out.append((test_m, months[pos - 1]))
    return out


def _cross_section(panel: Panel, score: pd.DataFrame, eligible: pd.DataFrame,
                   formation_m: pd.Timestamp, cfg: ScanConfig) -> pd.Series | None:
    elig = eligible.loc[formation_m]
    s = score.loc[formation_m].dropna()
    s = s[s.index.isin(elig[elig].index)]
    return None if len(s) < cfg.min_names_per_month else s


# ── L1: decile long-short spread, EW and VW ──────────────────────────────────
def ladder_l1(panel: Panel, sig: FactorySignal, segment: str,
              cfg: ScanConfig | None = None,
              mktcap: pd.DataFrame | None = None) -> pd.DataFrame:
    """Monthly D10 - D1 gross spread, equal- and value-weighted.

    This is the construction class the literature reports: a long-short decile
    portfolio, no costs, no incumbency band, both weightings.
    """
    cfg = cfg or ScanConfig()
    score = sig.compute(panel) * float(sig.direction)   # higher = better
    eligible = panel.eligible() & segment_mask(panel, segment)
    mc = market_cap_frame(panel) if mktcap is None else mktcap

    rows = []
    for test_m, formation_m in _months(panel, cfg):
        s = _cross_section(panel, score, eligible, formation_m, cfg)
        if s is None:
            continue
        realized = panel.monthly_ret.loc[test_m]
        n_dec = max(int(len(s) * DECILE_FRAC), 10)
        top = s.nlargest(n_dec).index
        bot = s.nsmallest(n_dec).index

        ew_top = float(realized.reindex(top).mean())
        ew_bot = float(realized.reindex(bot).mean())

        w = mc.loc[formation_m]

        def vw(names: pd.Index) -> float:
            r = realized.reindex(names)
            cap = w.reindex(names)
            ok = r.notna() & cap.notna() & (cap > 0)
            if not ok.any():
                return np.nan
            cap = cap[ok]
            return float((r[ok] * cap / cap.sum()).sum())

        rows.append({"month": test_m, "n_universe": len(s), "n_decile": n_dec,
                     "ew_top": ew_top, "ew_bottom": ew_bot,
                     "ew_spread": ew_top - ew_bot,
                     "vw_top": vw(top), "vw_bottom": vw(bot),
                     "vw_spread": vw(top) - vw(bot)})
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError(f"L1 produced no months for {sig.name}/{segment}")
    return out.set_index("month")


# ── L2: leg split (top-minus-universe vs universe-minus-bottom) ──────────────
def ladder_l2(panel: Panel, sig: FactorySignal, segment: str,
              cfg: ScanConfig | None = None) -> pd.DataFrame:
    """Monthly gross legs of the LONG-ONLY book and its mirror.

    `top` is `scan_signal`'s own `excess_gross` — the banked book's gross leg,
    hold-band and all. `bottom` is the identical code path with the frozen
    direction negated, reported as universe-minus-bottom so a positive number
    means "the bottom decile underperformed", i.e. information a long-only
    mandate could only use defensively.
    """
    cfg = cfg or ScanConfig()
    top = scan_signal(panel, sig, segment, cfg)["monthly"]["excess_gross"]

    mirror = FactorySignal(f"{sig.name}__mirror", f"mirror leg of {sig.name}",
                           sig.compute, -int(sig.direction))
    bot_book = scan_signal(panel, mirror, segment, cfg)["monthly"]["excess_gross"]

    return pd.DataFrame({"top_minus_universe": top,
                         "universe_minus_bottom": -bot_book})


# ── L3: tradability split ────────────────────────────────────────────────────
def ladder_l3(panel: Panel, sig: FactorySignal, segment: str,
              cfg: ScanConfig | None = None) -> pd.DataFrame:
    """Monthly rank-IC inside the upper and lower dollar-volume halves.

    "Upper" = the more liquid half (better dollar-volume rank). The split is at
    the median of the eligible cross-section that month, so the halves are
    equal-sized and the comparison is not confounded by sample size.
    """
    cfg = cfg or ScanConfig()
    score = sig.compute(panel) * float(sig.direction)
    eligible = panel.eligible() & segment_mask(panel, segment)
    dvol_rank = panel.monthly_dollar_vol.rank(axis=1, ascending=False)

    rows = []
    for test_m, formation_m in _months(panel, cfg):
        s = _cross_section(panel, score, eligible, formation_m, cfg)
        if s is None:
            continue
        realized = panel.monthly_ret.loc[test_m].reindex(s.index)
        rk = dvol_rank.loc[formation_m].reindex(s.index)
        cut = rk.median()
        upper, lower = rk <= cut, rk > cut

        def ic(mask: pd.Series) -> float:
            a, b = s[mask], realized[mask]
            ok = b.notna()
            if ok.sum() < MIN_IC_NAMES:
                return np.nan
            return float(a[ok].rank().corr(b[ok].rank()))

        rows.append({"month": test_m, "ic_upper": ic(upper), "ic_lower": ic(lower),
                     "n_upper": int(upper.sum()), "n_lower": int(lower.sum())})
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError(f"L3 produced no months for {sig.name}/{segment}")
    return out.set_index("month")


# ── the four pre-declared readings, each scored independently ────────────────
def score_readings(l1: pd.DataFrame, l2: pd.DataFrame,
                   l3: pd.DataFrame) -> dict:
    """Score R1-R4 exactly as frozen. No reading is derived from another."""
    t_ew = t_stat(l1["ew_spread"])
    t_vw = t_stat(l1["vw_spread"])
    t_top = t_stat(l2["top_minus_universe"])
    t_bot = t_stat(l2["universe_minus_bottom"])
    t_up = t_stat(l3["ic_upper"])
    t_low = t_stat(l3["ic_lower"])

    r1 = bool(max(t_ew, t_vw) >= R1_SPREAD_T and t_top <= R1_BOOK_T_MAX)
    r2 = bool(t_bot >= R2_RATIO * t_top
              or (t_bot >= R2_BOTTOM_T and t_top < R2_TOP_T))
    r3 = bool(t_low >= R3_RATIO * t_up)
    r4 = bool(t_ew < R4_SPREAD_T and t_vw < R4_SPREAD_T)

    return {
        "t_spread_ew": round(t_ew, 2), "t_spread_vw": round(t_vw, 2),
        "t_top_minus_universe": round(t_top, 2),
        "t_universe_minus_bottom": round(t_bot, 2),
        "t_ic_upper_half": round(t_up, 2), "t_ic_lower_half": round(t_low, 2),
        "R1_conditions_not_code": r1,
        "R2_information_is_short_side": r2,
        "R3_below_tradability": r3,
        "R4_the_puzzle_stands": r4,
    }
