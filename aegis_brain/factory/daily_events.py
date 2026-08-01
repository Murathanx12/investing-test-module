"""Daily event-study harness — control-armed, delisting-aware, cluster-robust.

The admissible successor for the event families the ledger has already killed or
queued: PEAD (NEG_RESULTS 14), 8-K (20), FDA (11/16), and the queued 13D/13G
family. This module is the HARNESS ONLY. It registers nothing and decides
nothing; every event family still needs its own pre-registration before it is
run against data.

Three things here are load-bearing, and each exists because a specific past
result demanded it.

1. THE CONTROL ARM IS THE TEST (NEG_RESULTS 20). Distress-8-K "drift" turned out
   to be selection, not information: the names that file distress 8-Ks are small,
   illiquid and falling anyway, so their post-event returns look dramatic next to
   *nothing*. Every CAR here is differenced against a matched non-event name —
   same segment, same calendar month, nearest dollar-volume rank — and the event
   leg and control leg are BOTH reported so the reader can see which one carries
   the number. An event study without a control arm is not evidence.

2. DELISTING RETURNS ARE NOT IN dsf.ret — VERIFIED, NOT ASSUMED. Measured on
   this data 2026-08-01: permno 11713 delisted 2008-10-02 with dlret -0.69697,
   while its last crsp.dsf return that day is -0.09589; permno 21960 dlret
   -0.53333 vs dsf -0.21053. The monthly file (crsp.msf) carries dlret as its own
   column, the DAILY file does not. Any daily CAR spanning a delisting is
   therefore biased UPWARD unless crsp.dsedelist is joined — and the bias falls
   hardest on exactly the distressed names an event study selects. We append the
   delisting return as an extra observation on the first trading day after the
   name's last quote. Names whose dlret is missing are counted and reported, not
   silently dropped or silently zeroed (`missing_dlret` is an explicit knob; the
   Shumway 1997 -30% convention for performance delists is available but OFF by
   default, because substituting a number is a research choice a trial must
   register, not a default the harness makes for you).

3. t-STATS ARE CLUSTERED BY EVENT-MONTH. Events cluster in time — earnings
   arrive in four waves a year, 8-K and 13D filings pile into the same weeks,
   and every name in a given month shares that month's market shock. Treating N
   overlapping events as N independent observations INFLATES the naive iid t,
   often by 2-3x, which is enough to manufacture significance out of one bad
   month. The reported t uses a cluster-robust variance on the event month with
   the standard G/(G-1) finite-sample correction. The iid t is also reported,
   purely so the gap between them is visible.

CAR convention: arithmetic sum of daily differenced returns over trading days
+1..+k relative to the event date (day 0 excluded — the event date itself is
never tradable on information released that day). Windows are TRADING days, not
calendar days.

NON-POSITIVE WINDOWS ARE SUPPORTED AND ARE NEVER TRADABLE. A window such as
-1..0 spans the announcement itself, so it can only ever be a DIAGNOSTIC: it is
the live check that the event dates are real, because a filing that moved
nothing on its own announcement day is more likely a broken date than a
non-event. Any trial that reports one must declare it non-deciding at
registration — the harness will compute it, but no CAR containing day 0 or
earlier is a return an account could have earned. Default windows remain
+1-and-later only, so this capability is opt-in per trial.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT

logger = logging.getLogger(__name__)
RAW = MODULE_ROOT / "data" / "wrds_raw"
DSF_DIR = RAW / "dsf_full"

DEFAULT_WINDOWS: tuple[tuple[int, int], ...] = ((1, 5), (1, 20), (1, 60))
CONTROL_EXCLUSION_DAYS = 60      # no event within +/- this many CALENDAR days
LARGEMID_MAX_RANK = 1000         # same segment bounds as factory/explore.py
SMALL_MAX_RANK = 3000
SHUMWAY_PERFORMANCE_DLRET = -0.30


# ── loading ──────────────────────────────────────────────────────────────────
def load_delist(path: str | None = None) -> pd.DataFrame:
    d = pd.read_parquet(path or RAW / "crsp_dsedelist.parquet",
                        columns=["permno", "dlstdt", "dlstcd", "dlret"])
    d["dlstdt"] = pd.to_datetime(d["dlstdt"])
    return d


def load_daily(years: range | list[int]) -> pd.DataFrame:
    """Long daily frame: permno, date, ret, dollar_vol. Raw — no delist join."""
    parts = []
    for y in years:
        p = DSF_DIR / f"dsf_{y}.parquet"
        if not p.exists():
            raise FileNotFoundError(f"daily file missing: {p}")   # fail loud
        d = pd.read_parquet(p, columns=["permno", "date", "ret", "prc", "vol"])
        d["dollar_vol"] = d["prc"].abs() * d["vol"]
        parts.append(d[["permno", "date", "ret", "dollar_vol"]])
    out = pd.concat(parts, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    logger.info("daily: %d rows, %s..%s", len(out), out["date"].min().date(),
                out["date"].max().date())
    return out


def apply_delisting_returns(daily: pd.DataFrame, delist: pd.DataFrame,
                            calendar: pd.DatetimeIndex,
                            missing_dlret: str | None = None) -> pd.DataFrame:
    """Append each delisted name's delisting return as one extra observation.

    Placed on the first trading day strictly after that name's last quote, which
    is when the liquidation proceeds are actually received.

    missing_dlret: None (default) leaves a missing dlret missing; "shumway"
    substitutes -30% for performance delists (codes 500 and 520-584) per Shumway
    (1997). Substitution is a research choice — a trial registers it, the
    harness does not assume it.
    """
    last = daily.groupby("permno")["date"].max().rename("last_date")
    d = delist.merge(last, on="permno", how="inner")

    if missing_dlret == "shumway":
        perf = (d["dlstcd"] == 500) | d["dlstcd"].between(520, 584)
        d.loc[perf & d["dlret"].isna(), "dlret"] = SHUMWAY_PERFORMANCE_DLRET
    d = d.dropna(subset=["dlret"])
    # the delisting must not precede the last quote we hold
    d = d[d["dlstdt"] >= d["last_date"]]

    pos = calendar.searchsorted(d["last_date"].to_numpy(), side="right")
    ok = pos < len(calendar)
    d = d[ok].copy()
    d["date"] = calendar[pos[ok]]

    add = pd.DataFrame({"permno": d["permno"].to_numpy(), "date": d["date"],
                        "ret": d["dlret"].to_numpy(dtype=float),
                        "dollar_vol": np.nan})
    logger.info("delisting: appended %d delisting returns", len(add))
    return pd.concat([daily, add], ignore_index=True).sort_values(
        ["permno", "date"], ignore_index=True)


def trading_calendar(path: str | None = None) -> pd.DatetimeIndex:
    d = pd.read_parquet(path or RAW / "crsp_dsi.parquet", columns=["date"])
    return pd.DatetimeIndex(pd.to_datetime(d["date"]).sort_values().unique())


# ── the panel ────────────────────────────────────────────────────────────────
@dataclass
class DailyEventPanel:
    """Daily returns on a trading-day index, plus monthly liquidity ranks."""

    ret: pd.Series                  # MultiIndex (permno, tidx) -> return
    calendar: pd.DatetimeIndex
    ranks: pd.DataFrame             # permno, ym, dollar_vol, rank, segment

    @classmethod
    def build(cls, daily: pd.DataFrame,
              calendar: pd.DatetimeIndex) -> "DailyEventPanel":
        d = daily[daily["date"].isin(calendar)].copy()
        # parquet hands back pandas' nullable Int64; normalise to plain int64 so
        # the (permno, tidx) MultiIndex aligns and can be cast against numpy
        d["permno"] = d["permno"].astype("int64")
        d["tidx"] = calendar.searchsorted(d["date"].to_numpy())
        d = d.drop_duplicates(["permno", "tidx"], keep="last")

        ret = (d.set_index(["permno", "tidx"])["ret"].astype(float)
               .sort_index())

        d["ym"] = d["date"].dt.to_period("M")
        ranks = (d.groupby(["permno", "ym"], as_index=False)["dollar_vol"]
                 .mean().dropna(subset=["dollar_vol"]))
        ranks["rank"] = ranks.groupby("ym")["dollar_vol"].rank(
            ascending=False, method="first")
        ranks["segment"] = np.where(
            ranks["rank"] <= LARGEMID_MAX_RANK, "largemid",
            np.where(ranks["rank"] <= SMALL_MAX_RANK, "small", "micro"))
        return cls(ret=ret, calendar=calendar, ranks=ranks)

    @classmethod
    def from_disk(cls, years: range | list[int],
                  missing_dlret: str | None = None) -> "DailyEventPanel":
        cal = trading_calendar()
        daily = load_daily(years)
        cal = cal[(cal >= daily["date"].min()) & (cal <= daily["date"].max())]
        daily = apply_delisting_returns(daily, load_delist(), cal, missing_dlret)
        return cls.build(daily, cal)


# ── control matching ─────────────────────────────────────────────────────────
def match_controls(events: pd.DataFrame, panel: DailyEventPanel,
                   exclusion_days: int = CONTROL_EXCLUSION_DAYS) -> pd.DataFrame:
    """Attach a control permno to every event.

    Same segment, same calendar month, nearest dollar-volume rank, and — the
    part that matters — the control must have NO event of its own within
    +/- `exclusion_days` calendar days, so the control leg is genuinely a
    non-event name rather than a quietly contaminated one.
    """
    ev = events.copy()
    ev["event_date"] = pd.to_datetime(ev["event_date"])
    ev["ym"] = ev["event_date"].dt.to_period("M")
    ev = ev.merge(panel.ranks[["permno", "ym", "rank", "segment"]],
                  on=["permno", "ym"], how="left")

    ev_dates = (events.assign(event_date=pd.to_datetime(events["event_date"]))
                .groupby("permno")["event_date"].apply(list).to_dict())
    excl = pd.Timedelta(days=exclusion_days)

    out = []
    for (ym, seg), grp in ev.groupby(["ym", "segment"], dropna=True):
        pool = panel.ranks[(panel.ranks["ym"] == ym)
                           & (panel.ranks["segment"] == seg)]
        if pool.empty:
            out.append(grp.assign(control_permno=np.nan))
            continue
        pool = pool.sort_values("rank")
        p_permno = pool["permno"].to_numpy()
        p_rank = pool["rank"].to_numpy(float)

        ctrls = []
        for _, r in grp.iterrows():
            order = np.argsort(np.abs(p_rank - r["rank"]), kind="stable")
            pick = np.nan
            for j in order:
                cand = p_permno[j]
                if cand == r["permno"]:
                    continue
                dates = ev_dates.get(cand)
                if dates is not None and any(
                        abs(dt - r["event_date"]) <= excl for dt in dates):
                    continue                     # contaminated control
                pick = cand
                break
            ctrls.append(pick)
        out.append(grp.assign(control_permno=ctrls))

    res = pd.concat(out, ignore_index=True) if out else ev.assign(
        control_permno=np.nan)
    logger.info("controls matched for %d/%d events",
                int(res["control_permno"].notna().sum()), len(res))
    return res


# ── CARs ─────────────────────────────────────────────────────────────────────
def _leg_returns(permnos: np.ndarray, t0: np.ndarray, max_day: int,
                 panel: DailyEventPanel, min_day: int = 1) -> np.ndarray:
    """[n_events x (max_day - min_day + 1)] daily returns for trading days
    +min_day..+max_day relative to the event date.

    min_day defaults to 1, so the positive-window path is unchanged.
    """
    n = len(permnos)
    rel = np.arange(min_day, max_day + 1)
    k = len(rel)
    pn = np.repeat(np.asarray(permnos, dtype="int64"), k)
    tt = (t0[:, None] + rel[None, :]).ravel()
    idx = pd.MultiIndex.from_arrays([pn, tt])
    vals = panel.ret.reindex(idx).to_numpy(dtype=float)
    return vals.reshape(n, k)


def window_label(a: int, b: int) -> str:
    """'+1..+5' for tradable windows, '-1..0' for a diagnostic one."""
    return f"+{a}..+{b}" if a > 0 else f"{a}..{b}"


def compute_cars(matched: pd.DataFrame, panel: DailyEventPanel,
                 windows: tuple[tuple[int, int], ...] = DEFAULT_WINDOWS
                 ) -> pd.DataFrame:
    """Per-event CARs: event leg, control leg, and the difference (the test).

    A return missing inside a window (the name delisted mid-window, so the
    position is already in cash) contributes 0 to the sum. The fraction filled
    this way is logged rather than hidden.
    """
    m = matched.dropna(subset=["control_permno"]).copy()
    if m.empty:
        return pd.DataFrame()
    m["event_date"] = pd.to_datetime(m["event_date"])
    t0 = panel.calendar.searchsorted(m["event_date"].to_numpy(), side="left")
    keep = t0 < len(panel.calendar)
    m, t0 = m[keep].copy(), t0[keep]

    max_day = max(b for _, b in windows)
    min_day = min(min(a, b) for a, b in windows)
    if min_day > 1:
        min_day = 1                       # keep the positive path byte-identical
    ev = _leg_returns(m["permno"].to_numpy(dtype="int64"), t0, max_day, panel,
                      min_day)
    ct = _leg_returns(m["control_permno"].to_numpy(dtype="int64"),
                      t0, max_day, panel, min_day)
    logger.info("CAR fill: %.3f%% of event-days and %.3f%% of control-days "
                "were missing and treated as 0 (post-delisting cash)",
                100 * np.isnan(ev).mean(), 100 * np.isnan(ct).mean())
    ev, ct = np.nan_to_num(ev), np.nan_to_num(ct)

    m = m.reset_index(drop=True)
    m["event_month"] = m["event_date"].dt.to_period("M")
    for a, b in windows:
        sl = slice(a - min_day, b - min_day + 1)
        m[f"car_event_{a}_{b}"] = ev[:, sl].sum(axis=1)
        m[f"car_control_{a}_{b}"] = ct[:, sl].sum(axis=1)
        m[f"car_{a}_{b}"] = m[f"car_event_{a}_{b}"] - m[f"car_control_{a}_{b}"]
    return m


# ── inference ────────────────────────────────────────────────────────────────
def clustered_t(x: pd.Series, clusters: pd.Series) -> dict:
    """Mean of x with a cluster-robust t on `clusters` (here: event month).

    CRVE for a regression on a constant:
        SE = sqrt( sum_g ( sum_{i in g} (x_i - xbar) )^2 ) / N,
    times the usual G/(G-1) finite-sample correction. The iid t is returned
    alongside so the inflation from ignoring clustering is visible.
    """
    d = pd.DataFrame({"x": x, "g": clusters}).dropna()
    n = len(d)
    if n < 2:
        return {"n": n, "mean": np.nan, "t_clustered": np.nan, "t_iid": np.nan,
                "n_clusters": 0}
    xbar = d["x"].mean()
    dev = d["x"] - xbar
    g_sums = dev.groupby(d["g"]).sum()
    G = len(g_sums)
    se_iid = d["x"].std(ddof=1) / np.sqrt(n)
    var = float((g_sums ** 2).sum()) / (n ** 2)
    if G > 1:
        var *= G / (G - 1)
    se = np.sqrt(var)
    return {
        "n": n, "n_clusters": G, "mean": float(xbar),
        "t_clustered": float(xbar / se) if se > 0 else np.nan,
        "t_iid": float(xbar / se_iid) if se_iid > 0 else np.nan,
    }


def summarise(cars: pd.DataFrame,
              windows: tuple[tuple[int, int], ...] = DEFAULT_WINDOWS
              ) -> pd.DataFrame:
    """One row per window: event leg, control leg, difference + clustered t."""
    rows = []
    for a, b in windows:
        diff = clustered_t(cars[f"car_{a}_{b}"], cars["event_month"])
        rows.append({
            "window": window_label(a, b),
            "tradable": a > 0,
            "n_events": diff["n"], "n_months": diff["n_clusters"],
            "car_event_bps": round(cars[f"car_event_{a}_{b}"].mean() * 1e4, 1),
            "car_control_bps": round(cars[f"car_control_{a}_{b}"].mean() * 1e4, 1),
            "car_diff_bps": round(diff["mean"] * 1e4, 1),
            "t_clustered": round(diff["t_clustered"], 2),
            "t_iid": round(diff["t_iid"], 2),
        })
    return pd.DataFrame(rows)


def run_event_study(events: pd.DataFrame, panel: DailyEventPanel,
                    windows: tuple[tuple[int, int], ...] = DEFAULT_WINDOWS,
                    exclusion_days: int = CONTROL_EXCLUSION_DAYS
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(summary table, per-event CARs). `events` needs permno + event_date."""
    for c in ("permno", "event_date"):
        if c not in events.columns:
            raise ValueError(f"events needs a {c!r} column")
    matched = match_controls(events, panel, exclusion_days)
    cars = compute_cars(matched, panel, windows)
    if cars.empty:
        raise ValueError("no event produced a CAR — check permno/date coverage")
    return summarise(cars, windows), cars
