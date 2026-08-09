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

    mid = (d.askhi + d.bidlo) / 2.0
    hs = ((d.askhi - d.bidlo) / 2.0 / mid * 1e4)
    d["hs"] = hs.where(np.isfinite(hs) & (hs > 0)).clip(
        upper=cfg.max_half_spread_bps)

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

    return DailyData(ret=piv("ret"), prc=piv("prc"), opn=piv("openprc"),
                     dvol=piv("dv"), half_spread=piv("hs"),
                     rf=ff.astype("float64").fillna(0.0), delist_ret=dmap)


def simulate(targets: list[dict], data: DailyData,
             cfg: SimConfig | None = None) -> dict:
    """Run the book day by day.

    `targets` is a list of {"effective": Timestamp, "weights": Series} — the
    monthly harness's own holdings. Feeding G7 the SAME target book the monthly
    scorecard used is the point: any difference in the result is attributable to
    daily reality, not to a different strategy.
    """
    cfg = cfg or SimConfig()
    days = data.ret.index.sort_values()
    tgt = sorted(targets, key=lambda t: t["effective"])
    ti = 0
    want: pd.Series = pd.Series(dtype=float)     # target weights, current
    shares: dict[int, float] = {}
    cash = cfg.start_nav
    nav_hist, rows = [], []
    pending: pd.Series = pd.Series(dtype=float)  # unfilled dollar orders
    gone: set[int] = set()
    traded_total = 0.0
    cost_total = 0.0
    capped_days = 0

    prc_ff = data.prc.ffill(limit=cfg.stale_days)
    prev_px: pd.Series | None = None
    div_cash_total = 0.0

    for day in days:
        px = prc_ff.loc[day]

        # ── dividends ─────────────────────────────────────────────────────
        # Positions are marked at PRICE, but `ret` is a TOTAL return. The
        # difference is the distribution, and dropping it would understate the
        # book by roughly the dividend yield every year — a slow, invisible
        # leak that would show up only as an unexplained gap against the
        # monthly harness. Accrued to cash on the day it is earned.
        if prev_px is not None and shares:
            held = list(shares)
            r_t = data.ret.loc[day].reindex(held)
            p0 = prev_px.reindex(held)
            p1 = px.reindex(held)
            price_ret = (p1 / p0 - 1.0)
            div_yield = (r_t - price_ret)
            base = pd.Series({p: shares[p] for p in held}, dtype=float) * p0
            dcash = float((base * div_yield).replace(
                [np.inf, -np.inf], np.nan).fillna(0.0).sum())
            cash += dcash
            div_cash_total += dcash

        # ── mark to market ────────────────────────────────────────────────
        pos_val = {p: s * px.get(p, np.nan) for p, s in shares.items()}
        # delistings effective today
        for p in list(shares):
            if p in data.delist_ret and data.delist_ret[p][0] <= day \
                    and p not in gone:
                dt, dr = data.delist_ret[p]
                base = pos_val.get(p)
                if base is None or not np.isfinite(base):
                    last = prc_ff[p].loc[:day].dropna()
                    base = shares[p] * (last.iloc[-1] if len(last) else 0.0)
                cash += base * (1.0 + dr)
                shares.pop(p, None)
                pos_val.pop(p, None)
                gone.add(p)
        # names with no price for too long: liquidate at last known
        for p in list(shares):
            v = pos_val.get(p)
            if v is None or not np.isfinite(v):
                last = prc_ff[p].loc[:day].dropna()
                cash += shares[p] * (last.iloc[-1] if len(last) else 0.0)
                shares.pop(p, None)
                pos_val.pop(p, None)

        equity = float(np.nansum(list(pos_val.values())))
        cash *= 1.0 + float(data.rf.get(day, 0.0))
        nav = equity + cash

        # ── new target book effective today ───────────────────────────────
        # (`while ... else` would run the else clause on every normal exit and
        # reset the flag it had just set; the flag is kept explicitly instead.)
        newbook = False
        while ti < len(tgt) and tgt[ti]["effective"] <= day:
            want = tgt[ti]["weights"].astype(float)
            want = want[want > 0]
            pending = pd.Series(dtype=float)     # a new book replaces the old
            ti += 1
            newbook = True

        if len(want):
            cur = pd.Series({p: pos_val.get(p, 0.0)
                             for p in set(want.index) | set(shares)},
                            dtype=float).fillna(0.0)
            desired = (want * nav).reindex(cur.index).fillna(0.0)
            gap = desired - cur
            if newbook or not len(pending):
                pending = gap
            # ── participation-capped fills, residual carried to tomorrow ──
            adv = data.dvol.loc[day].reindex(pending.index)
            cap = (adv * cfg.participation).fillna(0.0)
            fill = pending.clip(lower=-cap, upper=cap)
            fill = fill[fill.abs() > 1.0]
            if len(fill):
                blocked = (pending.abs() - cap).clip(lower=0)
                if float(blocked.sum()) > 0.01 * nav:
                    capped_days += 1
                op = data.opn.loc[day].reindex(fill.index)
                op = op.where(op > 0, px.reindex(fill.index))
                hs = data.half_spread.loc[day].reindex(fill.index).fillna(50.0)
                bps = hs + cfg.slippage_bps + cfg.commission_bps
                val = fill.abs()
                cost = float((val * bps / 1e4).sum())
                dsh = (fill / op).replace([np.inf, -np.inf], np.nan).fillna(0.0)
                for p, s in dsh.items():
                    if s:
                        shares[p] = shares.get(p, 0.0) + float(s)
                cash -= float(fill.sum()) + cost
                traded_total += float(val.sum())
                cost_total += cost
                pending = (pending - fill).where(lambda s: s.abs() > 1.0).dropna()

        # Positions carry to tomorrow as SHARES; the price path marks them and
        # the dividend block above accrues the rest of the total return. There
        # is deliberately no per-name return loop here.
        prev_px = px
        nav_hist.append((day, nav))
        rows.append({"date": day, "nav": nav, "equity": equity, "cash": cash,
                     "names": len(shares), "pending_abs": float(
                         pending.abs().sum()) if len(pending) else 0.0})

    nav = pd.Series({d: v for d, v in nav_hist}).sort_index()
    ret = nav.pct_change().dropna()
    dd = nav / nav.cummax() - 1.0
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    return {
        "nav": nav,
        "daily": pd.DataFrame(rows).set_index("date"),
        "diag": {
            "days": int(len(nav)),
            "years": round(years, 2),
            "cagr": round(float((nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1), 4),
            "vol_annualized": round(float(ret.std() * np.sqrt(252)), 4),
            "max_drawdown_daily": round(float(dd.min()), 4),
            "max_drawdown_monthend": round(float(
                (lambda m: (m / m.cummax() - 1).min())(nav.resample("ME").last())),
                4),
            "turnover_dollars": round(traded_total, 0),
            "cost_dollars": round(cost_total, 0),
            "cost_bps_of_traded": round(cost_total / traded_total * 1e4, 1)
            if traded_total else None,
            "days_with_capped_orders": capped_days,
            "dividend_cash_accrued": round(div_cash_total, 0),
            "delistings_handled": len(gone),
            "participation_cap": cfg.participation,
            "start_nav": cfg.start_nav,
        },
    }
