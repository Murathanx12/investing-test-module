"""G7 — the sequential daily simulator.

G7 is the last gate between a backtest and a paper lane. Everything upstream of
it runs on a monthly panel, and a monthly panel quietly grants four things no
real account gets:

  1. **A month-end fill.** The monthly harness forms on the month-end close and
     earns the next month's return from that same close. Nobody trades at a
     price they used to make the decision. Here the decision is made on the
     month-end close and the trade happens on the NEXT trading day's open.

  2. **Infinite liquidity.** A 150-name small-cap book at $10m is a different
     animal from the same book at $500m. The monthly harness cannot tell them
     apart. Here every order is capped at a share of that day's dollar volume,
     and unfilled quantity is CARRIED to the next day — which is what makes the
     simulator sequential rather than a prettier vectorised backtest.

  3. **Month-end drawdowns.** Reporting the worst month-end mark understates
     what a holder actually lived through. Daily marks fix that, and the gap
     between the two is reported rather than smoothed.

  4. **Tidy delistings.** A name that stops trading mid-month is handled here on
     the day it stops, at the CRSP delisting return.

Nothing in this module decides anything. It produces a NAV series and a
diagnostic block; the comparison to the monthly harness is the deliverable, and
a large gap is a finding about the strategy, not a bug in the simulator.
"""

from __future__ import annotations

import glob
import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import impact as impact_mod

logger = logging.getLogger(__name__)

DSF_DIR = MODULE_ROOT / "data" / "wrds_raw" / "dsf_full"
DELIST = MODULE_ROOT / "data" / "wrds_raw" / "crsp_dsedelist.parquet"
FF_DAILY = MODULE_ROOT / "data" / "wrds_raw" / "ff_factors_daily.parquet"

#: CRSP delisting codes 400-591 are performance-related or liquidations.
PERF_DELIST = range(400, 592)
#: dlstcd 100 means the issue is STILL ACTIVE — DSEDELIST carries a status row
#: for live securities, and its `dlstdt` is simply the last date on file. Of the
#: 846 names this book has held since 2002, 358 carry a code-100 row; treating
#: those as delistings would liquidate live positions at an invented price. A
#: real delisting is dlstcd >= 200.
FIRST_REAL_DELIST_CODE = 200

#: Last-resort daily volatility when a book trades before any history exists.
#: ~32%/yr. Only reachable on the very first order of a sample; counted and
#: printed as `impact_warmup_orders` so it can never be silent.
DEFAULT_DAILY_SIGMA = 0.02


@dataclass
class SimConfig:
    """Everything the simulator is allowed to assume, in one place."""

    start_nav: float = 1_000_000.0
    #: max share of a day's dollar volume one order may take
    participation: float = 0.05
    #: extra slippage on top of the half-spread, in bps of traded value
    slippage_bps: float = 5.0
    #: commission in bps of traded value
    commission_bps: float = 1.0
    #: cap on the half-spread estimate; CRSP hi/lo on illiquid days is noisy
    max_half_spread_bps: float = 300.0
    #: a name with no quote for this many days is treated as gone
    stale_days: int = 20
    #: Shumway (1997) imputation when a performance delisting has no DLRET
    missing_delist_return: float = -0.30
    seed: int = 20260809
    #: G8 price impact. **0.0 is G7** and reproduces every published G7 number
    #: bit for bit — the impact arithmetic is skipped entirely, not multiplied by
    #: zero. Any positive value makes the run G8 and the receipt says so. See
    #: `aegis_brain/pf/impact.py` for the law and for what it does not model.
    impact_coef: float = 0.0
    #: exponent on execution urgency; 0.0 means horizon is NOT priced (declared)
    impact_urgency_exp: float = 0.0

    @property
    def execution_model(self) -> str:
        return "G8" if self.impact_coef > 0 else "G7"


@dataclass
class DailyData:
    ret: pd.DataFrame          # date x permno, total return
    prc: pd.DataFrame          # date x permno, close (abs; CRSP signs bid/ask avg)
    opn: pd.DataFrame          # date x permno, open
    dvol: pd.DataFrame         # date x permno, dollar volume
    half_spread: pd.DataFrame  # date x permno, bps
    rf: pd.Series              # date, daily risk-free
    delist_ret: dict = field(default_factory=dict)   # permno -> (date, ret)


def load_daily(first: str, last: str, permnos: set[int] | None = None,
               cfg: SimConfig | None = None) -> DailyData:
    """Load the daily spine. Memory-conscious: one year at a time, filtered."""
    cfg = cfg or SimConfig()
    lo, hi = pd.Timestamp(first), pd.Timestamp(last)
    frames = []
    for f in sorted(glob.glob(str(DSF_DIR / "*.parquet"))):
        yr = int(f.rsplit("_", 1)[-1][:4])       # dsf_YYYY.parquet
        if yr < lo.year or yr > hi.year:
            continue
        d = pd.read_parquet(f, columns=["permno", "date", "ret", "prc", "vol",
                                        "askhi", "bidlo", "openprc"])
        if permnos is not None:
            d = d[d.permno.isin(permnos)]
        d = d[(d.date >= lo) & (d.date <= hi)]
        frames.append(d)
    if not frames:
        raise RuntimeError("no daily data in range")
    d = pd.concat(frames, ignore_index=True)
    d["prc"] = d["prc"].abs()          # CRSP negates bid/ask averages
    d["openprc"] = d["openprc"].abs()
    d["dv"] = d["prc"] * d["vol"]

    d["hi"] = d["askhi"].abs()
    d["lo"] = d["bidlo"].abs()

    def piv(col: str) -> pd.DataFrame:
        # float64, not the nullable dtypes the parquet carries: pd.NA raises
        # "boolean value of NA is ambiguous" the first time a missing price
        # meets an `if not np.isfinite(...)`, and a simulator that dies on a
        # missing quote is no use on a small-cap panel where quotes go missing.
        return d.pivot_table(index="date", columns="permno", values=col,
                             aggfunc="last").astype("float64")

    ff = pd.read_parquet(FF_DAILY, columns=["date", "rf"])
    ff = ff[(ff.date >= lo) & (ff.date <= hi)].set_index("date")["rf"]

    dl = pd.read_parquet(DELIST, columns=["permno", "dlstdt", "dlstcd", "dlret"])
    dl = dl[(dl.dlstdt >= lo) & (dl.dlstdt <= hi)]
    dl = dl[dl.dlstcd.astype(float) >= FIRST_REAL_DELIST_CODE]
    if permnos is not None:
        dl = dl[dl.permno.isin(permnos)]
    dmap = {}
    for _, r in dl.iterrows():
        v = r.dlret
        if pd.isna(v):
            v = (cfg.missing_delist_return
                 if int(r.dlstcd) in PERF_DELIST else 0.0)
        dmap[int(r.permno)] = (pd.Timestamp(r.dlstdt), float(v))

    prc = piv("prc")
    hs = corwin_schultz_half_spread_bps(piv("hi"), piv("lo"), cfg)
    # Corwin-Schultz is known to UNDERSTATE, and a bench check against a
    # synthetic 25 bps half-spread returned 5.8 bps (the naive high-low version
    # returned 128). A trade can never cross for less than half a tick, so the
    # mechanical floor is applied on top: post-decimalisation that is $0.005,
    # which is 5 bps on a $10 stock and 17 bps on a $3 one.
    floor = (0.005 / prc.where(prc > 0)) * 1e4
    hs = pd.concat([hs, floor]).groupby(level=0).max()
    return DailyData(ret=piv("ret"), prc=prc, opn=piv("openprc"),
                     dvol=piv("dv"), half_spread=hs,
                     rf=ff.astype("float64").fillna(0.0), delist_ret=dmap)


def corwin_schultz_half_spread_bps(hi: pd.DataFrame, lo: pd.DataFrame,
                                   cfg: SimConfig | None = None) -> pd.DataFrame:
    """Corwin & Schultz (2012) high-low spread estimator, in bps of half-spread.

    The obvious thing to do with CRSP `askhi`/`bidlo` is to call (high-low)/2 a
    half-spread. That is wrong and expensively so: for a stock that traded, those
    fields are the day's high and low TRADE prices, i.e. the intraday RANGE.
    Doing it that way charged this book ~200 bps per trade and made a +13.7%/yr
    strategy look like +7.7%.

    Corwin-Schultz separates the two: over two consecutive days the range grows
    with the square root of time but the spread component does not, so the two
    can be identified. Negative estimates — common and expected on quiet days —
    are floored at zero, and the series is smoothed with a 21-day rolling median
    because the daily estimator is far too noisy to charge a single day's trade.
    """
    cfg = cfg or SimConfig()
    k = 3.0 - 2.0 * np.sqrt(2.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        h = np.log(hi / lo) ** 2
        beta = h + h.shift(1)
        hi2 = pd.concat([hi, hi.shift(1)]).groupby(level=0).max()
        lo2 = pd.concat([lo, lo.shift(1)]).groupby(level=0).min()
        gamma = np.log(hi2 / lo2) ** 2
        alpha = ((np.sqrt(2.0 * beta) - np.sqrt(beta)) / k
                 - np.sqrt(gamma / k))
        s = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))

    s = s.where(np.isfinite(s)).clip(lower=0.0)
    half_bps = (s / 2.0) * 1e4
    half_bps = (half_bps.rolling(21, min_periods=5).median()
                .clip(upper=cfg.max_half_spread_bps))
    return half_bps.astype("float64")


def simulate(targets: list[dict], data: DailyData,
             cfg: SimConfig | None = None) -> dict:
    """Run the book day by day.

    `targets` is a list of {"effective": Timestamp, "weights": Series} — the
    monthly harness's own holdings, restricted to the months it actually traded.
    Feeding G7 the SAME target book the monthly scorecard used is the point: any
    difference in the result is attributable to daily reality, not to a
    different strategy having been simulated.

    ACCOUNTING: positions are carried as VALUE, grown by the daily TOTAL return.
    The first version held share counts and marked them at the raw CRSP close,
    which is wrong in a way that is invisible until it is not — `prc` in the
    daily file is unadjusted while `ret` is adjusted, so on a split the implied
    "dividend" (ret minus price return) explodes. It surfaced as a NEGATIVE
    $49m dividend accrual on the $100m rung. Total-return value accounting is
    split-safe and dividend-inclusive by construction.

    The one thing value accounting gives up is the open-to-close drift on the
    day a trade is worked, since that needs a share count. It is added back
    explicitly as a one-off adjustment on the traded notional, using the
    same-day open/close ratio — which is split-safe because both prices carry
    the same factor.
    """
    cfg = cfg or SimConfig()
    days = data.ret.index.sort_values()
    tgt = sorted(targets, key=lambda t: t["effective"])
    # ── G8 price impact, off by default ──────────────────────────────────
    # Charged on the METAORDER at creation and amortised across its fills, so
    # working an order down over more days does not escape it. That carry-
    # forward escape is precisely why G7 returned 31.00 bps at every liquidity
    # rung NIGHT-7 tried. At impact_coef == 0 nothing below executes.
    g8 = cfg.impact_coef > 0
    adv_tr = sigma_tr = None
    order_impact_bps: pd.Series = pd.Series(dtype=float)
    impact_total = 0.0
    impact_warmup_orders = 0
    if g8:
        adv_tr = impact_mod.trailing_adv(data.dvol)
        sigma_tr = impact_mod.trailing_sigma(data.ret)
    ti = 0
    want: pd.Series = pd.Series(dtype=float)
    val: dict[int, float] = {}
    cash = cfg.start_nav
    nav_hist, rows = [], []
    pending: pd.Series = pd.Series(dtype=float)
    gone: set[int] = set()
    traded_total = 0.0
    cost_total = 0.0
    exec_drift_total = 0.0
    capped_days = 0
    stale_liquidations = 0

    prc_ff = data.prc.ffill(limit=cfg.stale_days)
    last_seen: dict[int, pd.Timestamp] = {}

    for day in days:
        r_row = data.ret.loc[day]
        px = prc_ff.loc[day]

        # ── carry positions by the daily TOTAL return ─────────────────────
        for p in list(val):
            rv = r_row.get(p)
            if rv is not None and np.isfinite(rv):
                val[p] *= 1.0 + float(rv)
                last_seen[p] = day

        # ── delistings effective today ────────────────────────────────────
        for p in list(val):
            if p in data.delist_ret and data.delist_ret[p][0] <= day \
                    and p not in gone:
                _, dr = data.delist_ret[p]
                cash += val.pop(p) * (1.0 + dr)
                gone.add(p)

        # ── names that have gone quiet: liquidate at last known value ─────
        for p in list(val):
            seen = last_seen.get(p)
            if seen is not None and (day - seen).days > cfg.stale_days * 2:
                cash += val.pop(p)
                stale_liquidations += 1

        cash *= 1.0 + float(data.rf.get(day, 0.0))
        equity = float(sum(val.values()))
        nav = equity + cash

        # ── a new target book effective today ─────────────────────────────
        newbook = False
        while ti < len(tgt) and tgt[ti]["effective"] <= day:
            want = tgt[ti]["weights"].astype(float)
            want = want[want > 0]
            pending = pd.Series(dtype=float)
            ti += 1
            newbook = True

        # Orders are created ONLY when a new book arrives; the residual is
        # worked down on later days. Re-deriving the gap daily against a
        # drifting NAV converts an annual clock into a daily one — the first
        # version did that and lost 5.5%/yr to churn.
        if newbook and len(want):
            idx = sorted(set(want.index) | set(val))
            cur = pd.Series({p: val.get(p, 0.0) for p in idx}, dtype=float)
            pending = (want * nav).reindex(idx).fillna(0.0) - cur
            if g8 and len(pending):
                # WARM-UP, not missing data. A trailing window is undefined for
                # the first few days of any sample; charging those orders the
                # untradeable-name rate would make the opening trade — the
                # largest one in the run — dominate every impact number. Fall
                # back to the day's own volume, count it, and print the count.
                # A name with no volume TODAY either is still the expensive case.
                adv = adv_tr.loc[day].reindex(pending.index)
                today = data.dvol.loc[day].reindex(pending.index)
                warm = adv.isna() & today.notna() & (today > 0)
                impact_warmup_orders += int(warm.sum())
                adv = adv.where(~warm, today)
                sig = sigma_tr.loc[day].reindex(pending.index)
                fb = sig.median()
                if not np.isfinite(fb):
                    fb = data.ret.loc[:day].tail(60).std().median()
                if not np.isfinite(fb):
                    fb = DEFAULT_DAILY_SIGMA
                sig = sig.fillna(float(fb))
                order_impact_bps = pd.Series(
                    impact_mod.square_root_impact_bps(
                        pending.abs().to_numpy(), adv.to_numpy(),
                        sig.to_numpy(), cfg.impact_coef,
                        urgency_exp=cfg.impact_urgency_exp),
                    index=pending.index, dtype=float)

        if len(pending):
            adv = data.dvol.loc[day].reindex(pending.index)
            cap = (adv * cfg.participation).fillna(0.0)
            fill = pending.clip(lower=-cap, upper=cap)
            # a sell sized in dollars on rebalance day can exceed what is left
            # of a position that has since fallen; never go short
            held = pd.Series({p: float(val.get(p, 0.0)) for p in fill.index},
                             dtype=float)
            fill = fill.clip(lower=-held.clip(lower=0.0))
            fill = fill[fill.abs() > 1.0]
            if len(fill):
                if float((pending.abs() - cap).clip(lower=0).sum()) > 0.01 * nav:
                    capped_days += 1
                op = data.opn.loc[day].reindex(fill.index)
                cl = px.reindex(fill.index)
                ratio = (cl / op).replace([np.inf, -np.inf], np.nan)
                ratio = ratio.where((ratio > 0.5) & (ratio < 2.0)).fillna(1.0)

                hs = data.half_spread.loc[day].reindex(fill.index).fillna(50.0)
                bps = hs + cfg.slippage_bps + cfg.commission_bps
                notional = fill.abs()
                cost = float((notional * bps / 1e4).sum())
                if g8:
                    imp_bps = order_impact_bps.reindex(fill.index).fillna(
                        impact_mod.MAX_IMPACT_BPS)
                    imp = float((notional * imp_bps / 1e4).sum())
                    cost += imp
                    impact_total += imp
                # traded at the open, marked at the close: the traded notional
                # earns (close/open - 1) on the buy side and forgoes it on the
                # sell side
                drift = float((fill * (ratio - 1.0)).sum())

                for p, v in fill.items():
                    val[p] = val.get(p, 0.0) + float(v)
                    if abs(val[p]) < 1e-9:
                        val.pop(p, None)
                cash -= float(fill.sum()) + cost
                cash += drift
                traded_total += float(notional.sum())
                cost_total += cost
                exec_drift_total += drift
                pending = (pending - fill).where(
                    lambda s: s.abs() > 1.0).dropna()
                equity = float(sum(val.values()))
                nav = equity + cash

        nav_hist.append((day, nav))
        rows.append({"date": day, "nav": nav, "equity": equity, "cash": cash,
                     "names": len(val),
                     "pending_abs": float(pending.abs().sum())
                     if len(pending) else 0.0})

    nav = pd.Series(dict(nav_hist)).sort_index()
    ret = nav.pct_change().dropna()
    dd = nav / nav.cummax() - 1.0
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    me = nav.resample("ME").last()
    return {
        "nav": nav,
        "daily": pd.DataFrame(rows).set_index("date"),
        "diag": {
            "days": int(len(nav)),
            "years": round(years, 2),
            "cagr": round(float((nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1),
                          4),
            "vol_annualized": round(float(ret.std() * np.sqrt(252)), 4),
            "max_drawdown_daily": round(float(dd.min()), 4),
            "max_drawdown_monthend": round(float((me / me.cummax() - 1).min()), 4),
            "turnover_dollars": round(traded_total, 0),
            "cost_dollars": round(cost_total, 0),
            "cost_bps_of_traded": round(cost_total / traded_total * 1e4, 1)
            if traded_total else None,
            "execution_model": cfg.execution_model,
            "impact_dollars": round(impact_total, 0),
            "impact_warmup_orders": impact_warmup_orders,
            "impact_bps_of_traded": (round(impact_total / traded_total * 1e4, 2)
                                     if traded_total else None),
            "explicit_bps_of_traded": (
                round((cost_total - impact_total) / traded_total * 1e4, 2)
                if traded_total else None),
            "execution_drift_dollars": round(exec_drift_total, 0),
            "days_with_capped_orders": capped_days,
            "stale_liquidations": stale_liquidations,
            "delistings_handled": len(gone),
            "participation_cap": cfg.participation,
            "start_nav": cfg.start_nav,
            "final_nav": round(float(nav.iloc[-1]), 0),
        },
    }
