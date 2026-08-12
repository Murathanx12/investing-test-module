"""EXPOSURE-ARENA-1 — the arithmetic of GRAND-ARENA-1 chunk 6.

Pre-registered `TRIALS/PREREG_EXPOSURE_ARENA_1.md` at commits 31a49f8 (spec) and
f36f321 (§11 clarifications), BOTH before this file existed.

THE ONE IDEA IN THIS MODULE. A policy that holds less of a positive equity
premium earns less without timing anything, and a policy that holds less of a
volatile thing draws down less without forecasting anything. Every metric here
is therefore computed twice: once for the controller, and once for the CONSTANT
policy at the controller's own realised mean exposure. The difference is the
only number that can be called timing.

WORLD-L is the reason. In a synthetic world containing no timing edge at all, an
evolutionary learner produced Sharpe 0.500 against a static 0.478 purely by
sitting at zero exposure 52% of the time. Matched-average-exposure comparison
and an MDE were the only two things that refused it.

ACCOUNTING. Exposure `w` sits in the book, `1 - w` sits in cash at the daily
risk-free rate, and `|Δw|` is charged the bed's one-way cost. A weight decided
from data at `t` is applied to the return of `t+1`, for every controller without
exception including the oracle. So

    net_t = w_t · r_t + (1 - w_t) · rf_t − cost·|Δw_t|

and the decomposition identity that §6 of the prereg asserts at runtime,

    net_X − net_FULL = avoided − missed − costs        (arithmetic, exact)

holds on EXCESS returns (prereg §11.1).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
FF_PATH = MODULE_ROOT / "data" / "wrds_raw" / "ff_factors_daily.parquet"
WG1_PANEL = MODULE_ROOT / "data" / "factory" / "wg1_panel.npz"
GPR_MONTHLY = (MODULE_ROOT / "data" / "macro" / "gpr_snapshots"
               / "data_gpr_export_snap20260726.xls")
GPR_DAILY = (MODULE_ROOT / "data" / "macro" / "gpr_snapshots"
             / "data_gpr_daily_recent_snap20260726.xls")
OUT_DIR = MODULE_ROOT / "data" / "factory"

# ── frozen constants (prereg §3-§6) ───────────────────────────────────────
SAMPLE_START = pd.Timestamp("1926-07-01")
SAMPLE_END = pd.Timestamp("2024-12-31")
BED3_START = pd.Timestamp("2002-01-02")
WARMUP_TD = 252                 # excluded from every evaluation window
PROXY_BETA = 2.15               # BED-2, the frozen NIGHT-13 proxy
LAG = 1

#: prereg §4 — the repo's own cost model, not a new one.
COST_BPS = {"BED1": 5.0,        # exit_lab_core.BENCH_BPS
            "BED2": 5.0,
            "BED3": 30.2}       # EXIT-LAB CS median 24.2 + slippage 5 + comm 1
COST_MULTIPLIERS = (0.0, 1.0, 2.0, 4.0)

#: prereg §5 — the matched-exposure frontier grid, frozen
FRONTIER_GRID = tuple(round(x, 2) for x in np.arange(0.0, 1.0001, 0.05))

#: prereg §6 — bootstrap
BLOCK = 21
N_BOOT = 2000
SEED = 20260812
RUIN_HORIZON_TD = 2520          # 10 years
RUIN_LEVEL = 0.50
CVAR_Q = 0.05

#: prereg §6 — regime blocks and halves
BLOCKS_LONG = [("1926-34", 1926, 1934), ("1935-44", 1935, 1944),
               ("1945-54", 1945, 1954), ("1955-64", 1955, 1964),
               ("1965-74", 1965, 1974), ("1975-84", 1975, 1984),
               ("1985-94", 1985, 1994), ("1995-04", 1995, 2004),
               ("2005-14", 2005, 2014), ("2015-24", 2015, 2024)]
HALF_SPLIT_LONG = pd.Timestamp("1975-12-31")
BLOCKS_BED3 = [("2002-03", 2002, 2003), ("2004-06", 2004, 2006),
               ("2007-09", 2007, 2009), ("2010-12", 2010, 2012),
               ("2013-15", 2013, 2015), ("2016-18", 2016, 2018),
               ("2019-21", 2019, 2021), ("2022-24", 2022, 2024)]
HALF_SPLIT_BED3 = pd.Timestamp("2013-06-30")

DERISK_EPS = 0.999              # "de-risked" means w < this
SPELL_W = 0.75                  # a de-risking SPELL is a run of w < this


# ══════════════════════════════════════════════════════════════════════════
# beds
# ══════════════════════════════════════════════════════════════════════════
def load_ff() -> pd.DataFrame:
    ff = pd.read_parquet(FF_PATH)
    ff["date"] = pd.to_datetime(ff["date"])
    ff = ff.set_index("date").sort_index()
    return ff[["mktrf", "rf"]].astype(float)


def build_bed3_book() -> pd.Series:
    """Equal-weighted daily return of the liquid top-1500 CRSP universe.

    Monthly reconstitution on the WINNER-GENOME-1 / EXIT-LAB-1 rule (price >= $5,
    >= 252 days of history, 63d median dollar volume >= $1m, top 1,500 by that
    median). CRSP delisting returns are spliced on the delisting day and the name
    then leaves the book — a death is a realised return, never a disappearance.

    This is the BOOK, shared by every arm. Its own rebalancing cost is NOT
    charged, because every controller trades the same book and the overlay is
    what is being measured; that is a declared simplification, and it cancels in
    every comparison in this trial.
    """
    z = np.load(WG1_PANEL, allow_pickle=True)
    dates = pd.to_datetime(z["dates"])
    RET = z["RET"]
    PRC = z["PRC"]
    DOLVOL = z["DOLVOL"]
    first_obs = z["first_obs"].astype(np.int64)
    last_obs = z["last_obs"].astype(np.int64)
    delist_ret = z["delist_ret"].astype(np.float64)
    delist_day = z["delist_day"].astype(np.int64)

    nD = len(dates)
    term = np.where(delist_day >= 0, delist_day, last_obs)

    # splice the delisting return onto its day
    R = RET.astype(np.float64).copy()
    has_dl = delist_day >= 0
    R[delist_day[has_dl], np.where(has_dl)[0]] = np.where(
        np.isfinite(delist_ret[has_dl]), delist_ret[has_dl], -0.30)

    month = pd.Series(dates).dt.to_period("M").to_numpy()
    rebal = np.where(np.r_[True, month[1:] != month[:-1]])[0]

    out = np.full(nD, np.nan)
    members = np.array([], dtype=np.int64)
    n_states = []
    for t in range(nD):
        if t in set(rebal.tolist()) and t >= 252:
            px = PRC[t]
            med_dv = np.nanmedian(DOLVOL[max(t - 62, 0):t + 1], axis=0)
            ok = (np.isfinite(px) & (px >= 5.0)
                  & (first_obs <= t - 252) & (term >= t)
                  & np.isfinite(med_dv) & (med_dv >= 1_000_000.0))
            idx = np.where(ok)[0]
            if len(idx) > 1500:
                order = np.argsort(-med_dv[idx], kind="mergesort")
                idx = np.sort(idx[order[:1500]])
            members = idx
        if len(members) == 0:
            continue
        alive = members[term[members] >= t]
        if len(alive) == 0:
            continue
        r = R[t, alive]
        r = r[np.isfinite(r)]
        if len(r) == 0:
            continue
        out[t] = float(r.mean())
        n_states.append(len(r))

    s = pd.Series(out, index=dates).dropna()
    s.attrs["mean_members"] = float(np.mean(n_states)) if n_states else 0.0
    s.attrs["delistings_spliced"] = int(has_dl.sum())
    return s


def make_bed(name: str, ff: pd.DataFrame) -> dict:
    """Returns dict with r_book, r_mkt, rf, all aligned, plus meta."""
    if name in ("BED1", "BED2"):
        sl = ff.loc[SAMPLE_START:SAMPLE_END]
        lev = 1.0 if name == "BED1" else PROXY_BETA
        r_book = lev * sl["mktrf"] + sl["rf"]
        return {"bed": name, "r_book": r_book,
                "r_mkt": sl["mktrf"] + sl["rf"], "rf": sl["rf"],
                "cost_bps": COST_BPS[name],
                "blocks": BLOCKS_LONG, "half_split": HALF_SPLIT_LONG,
                "meta": {"construction":
                         f"r = {lev}*mktrf + rf (CRSP VW market, FF daily)",
                         "n_days": int(len(r_book))}}
    if name == "BED3":
        book = build_bed3_book()
        book = book.loc[BED3_START:SAMPLE_END]
        rf = ff["rf"].reindex(book.index).ffill()
        r_mkt = (ff["mktrf"] + ff["rf"]).reindex(book.index).ffill()
        return {"bed": name, "r_book": book, "r_mkt": r_mkt, "rf": rf,
                "cost_bps": COST_BPS[name],
                "blocks": BLOCKS_BED3, "half_split": HALF_SPLIT_BED3,
                "meta": {"construction": "EW liquid top-1500 CRSP book, "
                                         "monthly reconstitution, delistings "
                                         "spliced",
                         "mean_members": book.attrs.get("mean_members"),
                         "delistings_spliced":
                             book.attrs.get("delistings_spliced"),
                         "n_days": int(len(book))}}
    raise ValueError(name)


def eval_index(bed: dict) -> pd.DatetimeIndex:
    """The frozen evaluation window: bed start + WARMUP_TD trading days."""
    return bed["r_book"].index[WARMUP_TD:]


# ══════════════════════════════════════════════════════════════════════════
# the overlay
# ══════════════════════════════════════════════════════════════════════════
def simulate(bed: dict, w_signal: pd.Series, cost_mult: float = 1.0,
             idx: pd.DatetimeIndex | None = None) -> dict:
    """Apply a decided-at-t weight to t+1 and return the net path + diagnostics.

    `w_signal` is indexed on the bed's full calendar; the evaluation window is
    sliced AFTER the lag so no arm is scored on days its own signal did not
    exist, and the first evaluated day's turnover is charged honestly against
    the weight actually held the day before.
    """
    idx = eval_index(bed) if idx is None else idx
    r = bed["r_book"]
    rf = bed["rf"]
    bps = bed["cost_bps"] * cost_mult / 1e4

    w_app = w_signal.shift(LAG)
    w_app.iloc[0] = 1.0
    w_app = w_app.ffill().fillna(1.0).clip(0.0, 1.0)
    traded = w_app.diff().abs().fillna(0.0)

    net = w_app * r + (1.0 - w_app) * rf - traded * bps
    ex = r - rf                                   # excess (prereg §11.1)
    gap = (1.0 - w_app)
    missed = (gap * ex).where(ex > 0, 0.0)
    avoided = (gap * (-ex)).where(ex < 0, 0.0)
    cost = traded * bps

    return {"net": net.loc[idx], "w": w_app.loc[idx],
            "traded": traded.loc[idx], "cost": cost.loc[idx],
            "missed": missed.loc[idx], "avoided": avoided.loc[idx],
            "r_book": r.loc[idx], "rf": rf.loc[idx], "ex": ex.loc[idx]}


def constant_path(bed: dict, wbar: float, cost_mult: float = 1.0,
                  idx: pd.DatetimeIndex | None = None) -> dict:
    """MATCH(w̄) — the control that decides (prereg §5).

    A pure function of `w̄` and the bed. No parameters, no fitting, no knowledge
    of any controller. One rebalancing trade from full exposure on the first
    evaluated day, then nothing.
    """
    idx = eval_index(bed) if idx is None else idx
    # full exposure until the evaluation window opens, then the constant weight,
    # so the control PAYS its one switching trade inside the window it is
    # scored on. The dumb cousin is not handed a free rebalance.
    w = pd.Series(1.0, index=bed["r_book"].index)
    start = bed["r_book"].index.get_loc(idx[0])
    w.iloc[max(start - LAG, 0):] = wbar
    return simulate(bed, w, cost_mult, idx)


# ══════════════════════════════════════════════════════════════════════════
# metrics (prereg §6 / §A10)
# ══════════════════════════════════════════════════════════════════════════
def _maxdd(r: np.ndarray) -> float:
    w = np.cumprod(1.0 + r)
    return float((w / np.maximum.accumulate(w) - 1.0).min())


def _cagr(net: np.ndarray, n_years: float) -> float:
    return float(np.log1p(net).sum() / n_years * 100.0)


def metrics(sim: dict, bed: dict) -> dict:
    net = sim["net"].to_numpy(float)
    w = sim["w"].to_numpy(float)
    ex = sim["ex"].to_numpy(float)
    rf = sim["rf"].to_numpy(float)
    n = len(net)
    yrs = n / 252.0
    net_ex = net - rf
    up = ex > 0
    dn = ex < 0
    monthly = (1 + sim["net"]).resample("ME").prod() - 1.0
    mvals = monthly.to_numpy(float)
    q = np.quantile(mvals, CVAR_Q)
    spells = _spell_stats(sim)
    return {
        "n_days": n, "years": round(yrs, 2),
        "terminal_wealth": round(float(np.prod(1 + net)), 4),
        "net_cagr_pp": round(_cagr(net, yrs), 4),
        "net_excess_cagr_pp": round(float(np.log1p(net_ex).sum() / yrs * 100), 4),
        "vol_ann_pct": round(float(np.std(net, ddof=1) * np.sqrt(252) * 100), 3),
        "max_drawdown": round(_maxdd(net), 4),
        "cvar5_monthly": round(float(mvals[mvals <= q].mean()), 4),
        "bull_capture": (round(float(net_ex[up].mean() / ex[up].mean()), 4)
                         if up.sum() >= 5 else None),
        "bear_capture": (round(float(net_ex[dn].mean() / ex[dn].mean()), 4)
                         if dn.sum() >= 5 else None),
        "missed_upside_pp_yr": round(float(sim["missed"].sum() / yrs * 100), 4),
        "avoided_loss_pp_yr": round(float(sim["avoided"].sum() / yrs * 100), 4),
        "costs_bps_yr": round(float(sim["cost"].sum() / yrs * 1e4), 2),
        "turnover_oneway_yr": round(float(sim["traded"].sum() / yrs), 4),
        "mean_exposure": round(float(w.mean()), 6),
        "min_exposure": round(float(w.min()), 4),
        "pct_days_derisked": round(float((w < DERISK_EPS).mean()), 4),
        "pct_days_below_half": round(float((w < 0.5).mean()), 4),
        **spells,
    }


def _spell_stats(sim: dict) -> dict:
    """Re-entry efficiency (prereg §6 item 12).

    A SPELL is a maximal run of days with applied exposure < 0.75. The statistic
    is the annualised book return DURING spells minus the annualised book return
    over the whole window. Negative = the controller was out while the book was
    genuinely bad.
    """
    w = sim["w"].to_numpy(float)
    ex = sim["ex"].to_numpy(float)
    inside = w < SPELL_W
    n_spells = int((np.diff(np.r_[0, inside.astype(int)]) == 1).sum())
    if inside.sum() < 21:
        return {"n_derisk_spells": n_spells, "spell_days": int(inside.sum()),
                "reentry_efficiency_pp_yr": None,
                "book_excess_in_spells_pp_yr": None}
    in_rate = float(np.log1p(ex[inside]).mean() * 252 * 100)
    all_rate = float(np.log1p(ex).mean() * 252 * 100)
    return {"n_derisk_spells": n_spells, "spell_days": int(inside.sum()),
            "book_excess_in_spells_pp_yr": round(in_rate, 3),
            "reentry_efficiency_pp_yr": round(in_rate - all_rate, 3)}


# ══════════════════════════════════════════════════════════════════════════
# bootstrap machinery (§19) — chunked so a 24,700-day sample fits in memory
# ══════════════════════════════════════════════════════════════════════════
def _block_idx(n: int, size: int, n_boot: int, rng) -> np.ndarray:
    nb = int(np.ceil(size / BLOCK))
    starts = rng.integers(0, n, (n_boot, nb), dtype=np.int64)
    offs = np.arange(BLOCK, dtype=np.int64)
    idx = (starts[:, :, None] + offs[None, None, :]).reshape(n_boot, -1) % n
    return idx[:, :size].astype(np.int32)


def mde_paired(net_a: np.ndarray, net_b: np.ndarray, n_boot: int = N_BOOT,
               seed: int = SEED, chunk: int = 200) -> dict:
    """80%-power MDE for the paired annualised log-wealth difference, pp/yr.

    Null = the demeaned paired daily log-return difference. A planted drift δ
    shifts every resampled mean by δ, so MDE = q95(null mean) − q20(null mean)
    (NIGHT-13's `mde_wealth`, reused, annualised).
    """
    d = np.log1p(net_a) - np.log1p(net_b)
    n = len(d)
    d0 = d - d.mean()
    rng = np.random.default_rng(seed + n)
    means = np.empty(n_boot)
    done = 0
    while done < n_boot:
        k = min(chunk, n_boot - done)
        idx = _block_idx(n, n, k, rng)
        means[done:done + k] = d0[idx].mean(axis=1)
        done += k
    mde_daily = float(np.quantile(means, 0.95) - np.quantile(means, 0.20))
    se_daily = float(means.std(ddof=1))
    point_daily = float(d.mean())
    return {"delta_pp_yr": round(point_daily * 252 * 100, 4),
            "mde80_pp_yr": round(mde_daily * 252 * 100, 4),
            "se_pp_yr": round(se_daily * 252 * 100, 4),
            "t": round(point_daily / se_daily, 3) if se_daily > 0 else None,
            # a degenerate arm (identical to its own control) has a zero ruler
            # AND a zero effect; 0 >= 0 must not read as a detection
            "detectable": bool(mde_daily > 0 and abs(point_daily) >= mde_daily),
            "note": "21td circular block bootstrap, N=%d, demeaned null; "
                    "MDE = q95-q20 of the null mean, annualised" % n_boot}


def mde_maxdd(net_a: np.ndarray, net_b: np.ndarray, n_boot: int = 500,
              seed: int = SEED, chunk: int = 50) -> dict:
    """Paired max-drawdown difference with a planted-shave 80%-power MDE.

    Planted effect = a constant exposure shave of the REFERENCE path (a cost-free
    probe, never a strategy), exactly `mde_dd_vs_bar` from NIGHT-13 but expressed
    as the smallest shave whose dd difference is detected 80% of the time against
    the paired null.
    """
    n = len(net_a)
    rng = np.random.default_rng(seed + 7 * n)
    diffs = np.empty(n_boot)
    planted = {c: np.empty(n_boot) for c in (0.05, 0.10, 0.20, 0.30, 0.50)}
    done = 0
    while done < n_boot:
        k = min(chunk, n_boot - done)
        idx = _block_idx(n, n, k, rng)
        A, B = net_a[idx], net_b[idx]
        WA = np.cumprod(1 + A, axis=1)
        WB = np.cumprod(1 + B, axis=1)
        ddA = (WA / np.maximum.accumulate(WA, axis=1) - 1).min(axis=1)
        ddB = (WB / np.maximum.accumulate(WB, axis=1) - 1).min(axis=1)
        diffs[done:done + k] = ddA - ddB
        for c in planted:
            S = np.cumprod(1 + (1 - c) * B, axis=1)
            planted[c][done:done + k] = (
                (S / np.maximum.accumulate(S, axis=1) - 1).min(axis=1) - ddB)
        done += k
    point = (_maxdd(net_a) - _maxdd(net_b)) * 100
    se = float(diffs.std(ddof=1)) * 100
    # smallest planted shave whose 20th percentile of the dd gain is still > 0
    mde = None
    for c in sorted(planted):
        true_size = (_maxdd((1 - c) * net_b) - _maxdd(net_b)) * 100
        power = float((planted[c] > np.quantile(diffs - diffs.mean(), 0.95)).mean())
        if power >= 0.80:
            mde = round(true_size, 3)
            break
    return {"dd_diff_pp": round(point, 3), "se_pp": round(se, 3),
            "mde80_pp": mde,
            "detectable": bool(mde is not None and abs(point) >= mde),
            "note": "positive = arm's drawdown SHALLOWER than the reference; "
                    "MDE by planted constant-exposure shave of the reference"}


def ruin_probability(net: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED,
                     chunk: int = 100) -> dict:
    """P(a 10-year path from this return distribution ever halves). Prereg §1."""
    n = len(net)
    size = min(RUIN_HORIZON_TD, n)
    rng = np.random.default_rng(seed + 13 * n)
    hits = 0
    p5 = []
    done = 0
    while done < n_boot:
        k = min(chunk, n_boot - done)
        idx = _block_idx(n, size, k, rng)
        W = np.cumprod(1 + net[idx], axis=1)
        hits += int((W.min(axis=1) < RUIN_LEVEL).sum())
        p5.append(W[:, -1])
        done += k
    term = np.concatenate(p5)
    return {"p_ruin": round(hits / n_boot, 4),
            "horizon_td": size, "level": RUIN_LEVEL,
            "terminal_p05": round(float(np.quantile(term, 0.05)), 4),
            "terminal_median": round(float(np.median(term)), 4),
            "note": "P(min wealth over a %dtd block-bootstrap path < %.2f x "
                    "start), N=%d, 21td blocks" % (size, RUIN_LEVEL, n_boot)}


# ══════════════════════════════════════════════════════════════════════════
# regime blocks and halves
# ══════════════════════════════════════════════════════════════════════════
def sign_consistency(net_a: pd.Series, net_b: pd.Series, bed: dict) -> dict:
    d = np.log1p(net_a) - np.log1p(net_b)
    yrs = d.index.year
    rows = {}
    pos = 0
    tot = 0
    for name, y0, y1 in bed["blocks"]:
        m = (yrs >= y0) & (yrs <= y1)
        if m.sum() < 63:
            rows[name] = None
            continue
        v = float(d[m].mean() * 252 * 100)
        rows[name] = round(v, 3)
        tot += 1
        pos += int(v > 0)
    sp = bed["half_split"]
    h1 = float(d[d.index <= sp].mean() * 252 * 100)
    h2 = float(d[d.index > sp].mean() * 252 * 100)
    point = float(d.mean() * 252 * 100)
    same = ((np.sign(h1) == np.sign(point)) and (np.sign(h2) == np.sign(point)))
    n_same = sum(1 for v in rows.values()
                 if v is not None and np.sign(v) == np.sign(point))
    return {"blocks": rows, "n_blocks": tot, "n_blocks_same_sign": n_same,
            "n_blocks_positive": pos,
            "half1_pp_yr": round(h1, 3), "half2_pp_yr": round(h2, 3),
            "both_halves_same_sign": bool(same)}


# ══════════════════════════════════════════════════════════════════════════
# controller features (all causal: value at t uses data <= t)
# ══════════════════════════════════════════════════════════════════════════
def book_features(bed: dict) -> pd.DataFrame:
    r = bed["r_book"]
    rf = bed["rf"]
    ex = r - rf
    lg = np.log1p(r)
    cum = lg.cumsum()
    f = pd.DataFrame(index=r.index)
    for wdw in (21, 63, 252):
        f[f"vol_{wdw}"] = r.rolling(wdw).std(ddof=1) * np.sqrt(252)
    f["vol_ratio"] = f["vol_21"] / f["vol_252"]
    for ma in (50, 100, 200):
        f[f"trend_{ma}"] = cum - cum.rolling(ma).mean()
    f["dd_252"] = cum - cum.rolling(252).max()
    f["mom_252"] = cum - cum.shift(252)
    f["mom_21"] = cum - cum.shift(21)
    down = ex.where(ex < 0, 0.0)
    upp = ex.where(ex > 0, 0.0)
    f["semi_ratio"] = (down.rolling(63).std(ddof=1)
                       / upp.rolling(63).std(ddof=1))
    f["rf_level"] = rf * 252
    f["rf_chg63"] = (rf - rf.shift(63)) * 252
    return f


def rolling_beta(bed: dict, window: int = 63) -> pd.Series:
    rb, rm = bed["r_book"], bed["r_mkt"]
    cov = rb.rolling(window).cov(rm)
    var = rm.rolling(window).var(ddof=1)
    return cov / var


def load_gpr_monthly() -> pd.Series:
    """Caldara-Iacoviello historical GPR, monthly. NON-PIT (prereg §7)."""
    d = pd.read_excel(GPR_MONTHLY, usecols=["month", "GPRH"])
    d = d.dropna(subset=["month"])
    d["month"] = pd.to_datetime(d["month"], errors="coerce")
    d = d.dropna(subset=["month"]).set_index("month")["GPRH"].astype(float)
    return d.dropna()


def load_gpr_daily() -> pd.Series:
    d = pd.read_excel(GPR_DAILY, usecols=["DAY", "GPRD"])
    d = d.dropna(subset=["DAY"])
    d["date"] = pd.to_datetime(d["DAY"].astype("Int64").astype(str),
                               format="%Y%m%d", errors="coerce")
    d = d.dropna(subset=["date"]).set_index("date")["GPRD"].astype(float)
    d = d.dropna()
    return d[d > 0]          # 2 zero rows in the 2026-07 vintage; log-safe


# ══════════════════════════════════════════════════════════════════════════
# the controllers (prereg §7). Each returns a weight decided at t.
# ══════════════════════════════════════════════════════════════════════════
def ctrl_full(bed: dict, **_) -> pd.Series:
    return pd.Series(1.0, index=bed["r_book"].index)


def ctrl_static(bed: dict, w: float = 0.5, **_) -> pd.Series:
    return pd.Series(w, index=bed["r_book"].index)


def ctrl_vol_target(bed: dict, sigma_star: float = 0.15, window: int = 63,
                    **_) -> pd.Series:
    vol = bed["r_book"].rolling(window).std(ddof=1) * np.sqrt(252)
    w = (sigma_star / vol).clip(upper=1.0)
    return w.where(vol.notna(), 1.0).fillna(1.0)


def ctrl_beta_target(bed: dict, beta_star: float = 1.5, window: int = 63,
                     **_) -> pd.Series:
    b = rolling_beta(bed, window)
    w = pd.Series(np.where(b > 0, np.minimum(1.0, beta_star / b), 1.0),
                  index=b.index)
    return w.where(b.notna(), 1.0).fillna(1.0)


def ctrl_ladder(bed: dict, sigma_star: float = 0.15, d_star: float = 0.10,
                beta_star: float = 1.5, dwell: int = 10,
                hyst: float = 0.05, **_) -> pd.Series:
    """The NIGHT-13 book-keyed ladder, imported verbatim and NOT re-tuned."""
    r = bed["r_book"]
    w_vol = ctrl_vol_target(bed, sigma_star, 63)
    w_beta = ctrl_beta_target(bed, beta_star, 63)
    lc = np.log1p(r).cumsum()          # log space: a 98-year levered cumprod
    dd = np.expm1(lc - lc.cummax()).to_numpy(float)   # overflows float64
    cap = np.ones(len(dd))
    capped, dw = False, 0
    for i, x in enumerate(dd):
        if capped:
            dw += 1
            if dw >= dwell and x > -(d_star - hyst):
                capped = False
        elif x < -d_star:
            capped, dw = True, 0
        cap[i] = 0.5 if capped else 1.0
    w_dd = pd.Series(cap, index=r.index)
    return pd.concat([w_vol, w_beta, w_dd], axis=1).min(axis=1)


REGIME_MAP_2X2 = {(1, 0): 1.0, (1, 1): 0.7, (0, 0): 0.6, (0, 1): 0.3}
REGIME_MAP_TREND = {(1, 0): 1.0, (1, 1): 1.0, (0, 0): 0.5, (0, 1): 0.5}


def ctrl_regime(bed: dict, ma: int = 200, mapping: str = "2x2", **_) -> pd.Series:
    r = bed["r_book"]
    cum = np.log1p(r).cumsum()
    trend = (cum > cum.rolling(ma).mean()).astype(int)
    vol = r.rolling(63).std(ddof=1) * np.sqrt(252)
    ref = vol.rolling(1260, min_periods=252).median()      # prereg §11.2
    hi = (vol > ref).astype(int)
    m = REGIME_MAP_2X2 if mapping == "2x2" else REGIME_MAP_TREND
    w = pd.Series(1.0, index=r.index)
    for (t_, v_), val in m.items():
        w[(trend == t_) & (hi == v_)] = val
    warm = cum.rolling(ma).mean().isna() | ref.isna()
    w[warm] = 1.0
    return w


def ctrl_event(bed: dict, gpr_z: pd.Series | None = None,
               threshold: float = 1.0, floor: float = 0.5, **_) -> pd.Series:
    """GPR-conditioned exposure. NON-PIT: the GPR series is revised/backfilled."""
    z = gpr_z.reindex(bed["r_book"].index).ffill()
    w = pd.Series(np.where(z.to_numpy(float) > threshold, floor, 1.0),
                  index=bed["r_book"].index)
    w[z.isna()] = 1.0
    return w


def gpr_z_monthly(index: pd.DatetimeIndex) -> pd.Series:
    """z-score of log GPRH on a trailing 10y window, lagged ONE FULL MONTH."""
    g = np.log(load_gpr_monthly())
    z = (g - g.rolling(120, min_periods=36).mean()) / g.rolling(
        120, min_periods=36).std(ddof=1)
    z = z.shift(1)                       # publication lag: one full month
    z.index = z.index + pd.offsets.MonthEnd(1)
    return z.reindex(index.union(z.index)).ffill().reindex(index)


def gpr_z_daily(index: pd.DatetimeIndex) -> pd.Series:
    g = np.log(load_gpr_daily())
    z = (g - g.rolling(2520, min_periods=252).mean()) / g.rolling(
        2520, min_periods=252).std(ddof=1)
    z = z.shift(1)
    return z.reindex(index.union(z.index)).ffill().reindex(index)


def ctrl_oracle(bed: dict, k: int = 21, **_) -> pd.Series:
    """DIAGNOSTIC ONLY — IMPOSSIBLE. Perfect foresight of the next k days.

    Labelled impossible everywhere it appears; it exists to bound how much
    timing value is available at all, so that a null on A-G can be read as a
    statement about observability rather than about availability.
    """
    ex = (bed["r_book"] - bed["rf"]).to_numpy(float)
    n = len(ex)
    csum = np.r_[0.0, np.cumsum(np.log1p(ex))]
    t = np.arange(n)
    # a weight decided at t is APPLIED at t+1 (LAG), so the foresight window
    # this arm is allowed to see is exactly days t+1 .. t+k — never day t,
    # which would make it a momentum rule rather than an oracle.
    lo = np.minimum(t + 1, n)
    hi = np.minimum(t + 1 + k, n)
    fwd = csum[hi] - csum[lo]
    w = np.where(fwd > 0, 1.0, 0.0)
    if k > 1:                            # decide only every k days
        keep = np.zeros(n, dtype=bool)
        keep[::k] = True
        ws = pd.Series(np.where(keep, w, np.nan), index=bed["r_book"].index)
        return ws.ffill().fillna(1.0)
    return pd.Series(w, index=bed["r_book"].index)


# ══════════════════════════════════════════════════════════════════════════
# causality
# ══════════════════════════════════════════════════════════════════════════
def perturbation_proof(bed: dict, fn, kwargs: dict, probe: pd.Timestamp,
                       seed: int = 1) -> dict:
    """The weight decided at `probe` must be bit-identical after every return
    strictly after `probe` is corrupted. Returns the comparison; the caller
    decides whether identity is required (controllers) or forbidden (oracle)."""
    idx = bed["r_book"].index
    cand = idx[idx <= probe]
    t = cand[-1]
    base = float(fn(bed, **kwargs).loc[t])
    rng = np.random.default_rng(seed)
    b2 = dict(bed)
    after = idx > t
    rb = bed["r_book"].copy()
    rm = bed["r_mkt"].copy()
    rb.loc[after] = ((1 + rb.loc[after].to_numpy(float))
                     * rng.uniform(0.3, 3.0, int(after.sum())) - 1)
    rm.loc[after] = ((1 + rm.loc[after].to_numpy(float))
                     * rng.uniform(0.3, 3.0, int(after.sum())) - 1)
    b2["r_book"], b2["r_mkt"] = rb, rm
    shocked = float(fn(b2, **kwargs).loc[t])
    return {"probe": str(t.date()), "w_base": base, "w_shocked": shocked,
            "identical": bool(base == shocked)}


def lookahead_tripwire(bed: dict, fn, kwargs: dict,
                       probe: pd.Timestamp) -> dict:
    """The proof that the perturbation harness can SEE look-ahead at all.

    A CORRECT-NULL from a causality proof is worthless if the harness could not
    have produced a violation in the first place — the same argument WORLD-I
    makes about null verdicts. So the oracle is run through a perturbation
    designed to be detected: every excess return strictly after the probe is
    NEGATED (`r -> 2*rf - r`), which flips the sign of any forward sum that
    depends on post-probe data. A controller that reads the future must move.

    Recorded honestly: the ordinary RANDOM multiplicative perturbation is NOT a
    reliable tripwire for the k=21 and k=63 oracles. At those horizons a probe
    can sit 20 days after its own decision date, so only one of twenty-one days
    in the foresight window is post-probe, and a random rescaling of one day
    need not flip the sign of the window's sum. The first version of this
    runner asserted that it would, and BED-3 refused — an assertion that is
    wrong is worse than no assertion, so the tripwire was rebuilt rather than
    the failing bed being quietly dropped.
    """
    idx = bed["r_book"].index
    t = idx[idx <= probe][-1]
    base = float(fn(bed, **kwargs).loc[t])
    b2 = dict(bed)
    after = idx > t
    rb = bed["r_book"].copy()
    rb.loc[after] = (2 * bed["rf"].loc[after] - rb.loc[after])
    b2["r_book"] = rb
    shocked = float(fn(b2, **kwargs).loc[t])
    return {"probe": str(t.date()), "w_base": base, "w_shocked": shocked,
            "differs": bool(base != shocked),
            "perturbation": "excess returns after the probe NEGATED"}
