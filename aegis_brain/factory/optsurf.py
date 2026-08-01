"""TRIAL-OPT-COHORT — option-implied cross-section. Spec frozen 2026-08-01
(TRIALS/TRIAL-OPT-COHORT.md, module commit a84e5b1, BEFORE this file existed).

Seven arms, each a counted candidate (167-173):

  iv_atm      30-day ATM IV (mean of +/-50 delta)                    -1
  riv_spread  iv_atm minus trailing 21-day annualised realised vol   -1
  skew_25d    25-delta put IV minus 25-delta call IV, 30-day         -1
  term_slope  91-day ATM IV minus 30-day ATM IV                      +1
  os_ratio    option volume / stock volume, monthly mean of daily    +1
  pc_volume   put volume / call volume, monthly mean of daily        -1
  skew_resid  residual of skew_25d on a per-month cross-sectional
              OLS on 4 frozen regressors                             -1

Nothing here is tunable. Directions, the null rule, the regressor set and the
bars are all frozen in the registration; this module is the mechanical
implementation of that text.

BUILD-TIME COVERAGE VERIFICATION (the TRIAL-ABIO-KIRK lesson, NEG_RESULTS 26:
that trial's frozen spec named a table holding 1980-2001 for a 2004-2018
window). Every input table was checked to actually span the explore window
BEFORE any construction code was written, and `assert_inputs_cover_explore()`
re-checks it at run time so the failure is loud rather than an empty frame:

  optionm_vsurf_me      23 files 2002-2024, 12 month-ends/yr, days {30, 91},
                        delta {+/-25, +/-50}, cp_flag {C, P}
  optionm_opvol_daily   23 files 2002-2024, ~1M rows/yr, 4.3-4.7k secids
  optionm_crsp_link     active links at 2004-01-31 / 2011-06-30 / 2018-12-31
                        = 6,979 / 8,654 / 10,511
  dsf_full              2002-2024; `vol` is in SHARES (AAPL 2010-06-30 =
                        27,301,121), which is the O/S denominator
  VIXCLS                180 explore month-ends, terciles 13.98 / 18.42

MECHANICAL PLUMBING (spec silent, precedent followed, disclosed):

  * `optionm_crsp_link.sdate/edate` are stored as STRINGS in the parquet and
    are parsed to datetimes before any comparison. Left as strings the
    date-validity filter raises rather than silently passing, but the failure
    mode of a near-miss here is an empty join, so it is pinned by a test.
  * The link is resolved at MONTH granularity (the unique permno valid at that
    month-end), because every arm is a month-end quantity. Ambiguous links are
    DROPPED in both directions (secid -> >1 permno, permno -> >1 secid) on the
    same no-discretion principle TRIAL-ABIO-KIRK used; counts are reported. No
    filter is applied on the link `score` column — the frozen spec does not
    mention one — but the score distribution of the links actually used is
    reported.
  * DAILY RATIO DENOMINATORS. 18.9% of secid-days carry zero option volume and
    (2010 alone) 43,016 carry call_vol = 0 with put_vol > 0, which makes the
    daily put/call ratio infinite. The frozen text says "monthly mean of daily",
    so the ratio is computed per day and averaged; a day whose denominator is
    zero has an UNDEFINED ratio and is excluded from that month's mean. This is
    the frozen null rule applied at daily resolution, not a new rule.
  * A name-month needs >= MIN_DAYS_PER_MONTH defined daily ratios or the
    month is null (and therefore dropped). 15 follows the existing house
    precedent in factory/altstores.py `load_daily_agg` ("thin months are
    noise"), which is the most recent applicable precedent.
  * O/S scaling: option volume is in CONTRACTS and stock volume in SHARES. We
    do NOT rescale by 100. Every arm is ranked cross-sectionally, so a constant
    multiplier is a monotone transform and cannot change a single decile, an
    IC or a t. Stated because the level is not comparable to published O/S
    numbers even though the ranking is.
  * The four `skew_resid` regressors are implemented HERE rather than imported
    from factory/abio.py, deliberately: a frozen trial's construction must not
    be mutable by a later edit to another trial's module.
"""

from __future__ import annotations

import glob
import logging
import re

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel

logger = logging.getLogger(__name__)
RAW = MODULE_ROOT / "data" / "wrds_raw"
VSURF_DIR = RAW / "optionm_vsurf_me"
OPVOL_DIR = RAW / "optionm_opvol_daily"

# ── FROZEN CONSTANTS (registration text; a change here is a new trial) ───────
ARMS = ("iv_atm", "riv_spread", "skew_25d", "term_slope",
        "os_ratio", "pc_volume", "skew_resid")
DIRECTIONS = {"iv_atm": -1, "riv_spread": -1, "skew_25d": -1, "term_slope": +1,
              "os_ratio": +1, "pc_volume": -1, "skew_resid": -1}
RESID_REGRESSORS = ["log_mktcap", "rv21", "mom_12_1", "log_dvol3m"]
WINSOR_LO, WINSOR_HI = 0.01, 0.99
RV_WINDOW = 21               # trailing trading days for realised vol
TRADING_DAYS = 252
TERM_LONG, TERM_SHORT = 91, 30    # term_slope = 91d - 30d, frozen

# plumbing constants (disclosed, precedent-following, not spec)
MIN_DAYS_PER_MONTH = 15
EXPLORE_START, EXPLORE_END = "2004-01-31", "2018-12-31"


# ── build-time coverage guard ────────────────────────────────────────────────
def assert_inputs_cover_explore() -> dict:
    """Fail LOUD if any input table does not span the explore window.

    Exists because TRIAL-ABIO-KIRK was frozen against a table that held
    1980-2001 for a 2004-2018 question (NEG_RESULTS 26). Cheap to run, and the
    failure it prevents voids a one-shot trial.
    """
    need = list(range(2003, 2019))          # 2003 for the first formation month
    report = {}
    for label, d, pat in (("vsurf", VSURF_DIR, "vsurf_me_{}.parquet"),
                          ("opvol", OPVOL_DIR, "opvol_{}.parquet"),
                          ("dsf", RAW / "dsf_full", "dsf_{}.parquet")):
        missing = [y for y in need if not (d / pat.format(y)).exists()]
        if missing:
            raise FileNotFoundError(f"{label}: missing years {missing}")
        report[label] = f"{need[0]}-{need[-1]} present"

    link = _raw_link()
    for probe in (EXPLORE_START, EXPLORE_END):
        t = pd.Timestamp(probe)
        n = int(((link["sdate"] <= t) & (link["edate"] >= t)).sum())
        if n == 0:
            raise ValueError(f"optionm_crsp_link: no active link at {probe}")
        report[f"link_active_{probe}"] = n

    vix = load_vix()
    w = vix.loc[EXPLORE_START:EXPLORE_END]
    if len(w) < 150:
        raise ValueError(f"VIXCLS: only {len(w)} explore observations")
    report["vix_explore_days"] = len(w)
    logger.info("input coverage verified: %s", report)
    return report


# ── link ─────────────────────────────────────────────────────────────────────
def _raw_link() -> pd.DataFrame:
    lk = pd.read_parquet(RAW / "optionm_crsp_link.parquet")
    lk = lk.dropna(subset=["permno", "secid"]).copy()
    # STRINGS in the parquet — parse before any comparison (see docstring)
    lk["sdate"] = pd.to_datetime(lk["sdate"])
    lk["edate"] = pd.to_datetime(lk["edate"])
    lk["secid"] = lk["secid"].astype("int64")
    lk["sym"] = lk["permno"].astype("Int64").astype(str)
    return lk[["secid", "sym", "sdate", "edate", "score"]]


def month_link(months: pd.DatetimeIndex,
               link: pd.DataFrame | None = None,
               data_bearing: pd.DataFrame | None = None) -> pd.DataFrame:
    """(ym, secid, sym) for month-ends where the link is date-valid and unique.

    Ambiguity is dropped, never resolved by discretion — but "ambiguous" is
    judged among the secids that actually CARRY DATA that month, which is the
    faithful reading of the rule and was measured before the run:

      At 2011-06-30, 1,041 permnos carried more than one secid. Of those, 660
      had NO secid with surface data (dead OptionMetrics link records, almost
      all link score 4 or 5), 379 had EXACTLY ONE secid with data (score 1),
      and only 2 had more than one. A blanket reverse-direction drop therefore
      discarded 379 perfectly resolvable names per month — about 11% of the
      usable cross-section — in order to disambiguate 2.

    So: the forward direction (one secid -> several permnos) is always dropped,
    because nothing can tell you which stock the option data belongs to. The
    reverse direction (one permno -> several secids) is dropped ONLY when more
    than one of those secids carries data in that month. `data_bearing` is a
    (ym, secid) frame; when omitted the reverse rule falls back to the blanket
    form, which is stricter, never looser.

    This distinction was settled BEFORE any signal number existed — it is
    outcome-independent, since which arms it helps or hurts is unknowable here.
    """
    lk = _raw_link() if link is None else link.copy()
    rows = []
    for m in months:
        act = lk[(lk["sdate"] <= m) & (lk["edate"] >= m)]
        if act.empty:
            continue
        rows.append(act.assign(ym=m.to_period("M"))[["ym", "secid", "sym", "score"]])
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        columns=["ym", "secid", "sym", "score"])
    out = out.drop_duplicates(["ym", "secid", "sym"])

    n_fwd = out.groupby(["ym", "secid"])["sym"].transform("nunique")
    dropped = {"ambiguous_secid_to_permno": int((n_fwd > 1).sum())}
    out = out[n_fwd == 1]

    if data_bearing is not None and len(data_bearing):
        db = data_bearing[["ym", "secid"]].drop_duplicates()
        db["_has_data"] = True
        out = out.merge(db, on=["ym", "secid"], how="left")
        out["_has_data"] = out["_has_data"].notna()
        n_live = out.groupby(["ym", "sym"])["_has_data"].transform("sum")
        # keep the single data-bearing secid; drop the name-month only when
        # two or more of its secids actually carry data
        keep = (out["_has_data"] & (n_live == 1))
        dropped["ambiguous_permno_to_secid_live"] = int(
            (out["_has_data"] & (n_live > 1)).sum())
        dropped["dead_duplicate_secids_pruned"] = int((~out["_has_data"]).sum())
        out = out[keep].drop(columns=["_has_data"])
    else:
        n_rev = out.groupby(["ym", "sym"])["secid"].transform("nunique")
        dropped["ambiguous_permno_to_secid_blanket"] = int((n_rev > 1).sum())
        out = out[n_rev == 1]

    logger.info("month link: %d (ym, secid) pairs, dropped %s", len(out), dropped)
    out.attrs["dropped"] = dropped
    return out


def data_bearing_pairs(surf: pd.DataFrame, years: range) -> pd.DataFrame:
    """(ym, secid) pairs that carry option data: a non-null 30-day ATM IV, or
    a positive option-volume day. Uniform across arms — no per-arm discretion."""
    parts = [surf.dropna(subset=["iv30"])[["ym", "secid"]]]
    for y in years:
        p = OPVOL_DIR / f"opvol_{y}.parquet"
        if not p.exists():
            continue
        o = pd.read_parquet(p, columns=["secid", "date", "opt_vol"])
        o = o[o["opt_vol"].fillna(0) > 0].dropna(subset=["secid", "date"])
        o["secid"] = o["secid"].astype("int64")
        o["ym"] = pd.to_datetime(o["date"]).dt.to_period("M")
        parts.append(o[["ym", "secid"]])
    return pd.concat(parts, ignore_index=True).drop_duplicates()


# ── volatility surface ───────────────────────────────────────────────────────
def load_surface() -> pd.DataFrame:
    """Long: (ym, secid, iv30, iv91, skew_25d). Month-end vol surface."""
    parts = []
    for f in sorted(glob.glob(str(VSURF_DIR / "*.parquet"))):
        y = int(re.search(r"(\d{4})\.parquet$", f.replace("\\", "/")).group(1))
        if not (2003 <= y <= 2024):
            continue
        parts.append(pd.read_parquet(
            f, columns=["secid", "date", "days", "delta", "cp_flag",
                        "impl_volatility"]))
    v = pd.concat(parts, ignore_index=True)
    v = v.dropna(subset=["secid", "date", "days", "delta"])
    v["secid"] = v["secid"].astype("int64")
    v["ym"] = pd.to_datetime(v["date"]).dt.to_period("M")
    v["iv"] = pd.to_numeric(v["impl_volatility"], errors="coerce")

    def leg(days: int, delta: float, cp: str, name: str) -> pd.DataFrame:
        s = v[(v["days"] == days) & (v["delta"] == delta) & (v["cp_flag"] == cp)]
        return (s.groupby(["ym", "secid"])["iv"].last().rename(name).reset_index())

    c50_30 = leg(30, 50.0, "C", "c50_30")
    p50_30 = leg(30, -50.0, "P", "p50_30")
    c50_91 = leg(91, 50.0, "C", "c50_91")
    p50_91 = leg(91, -50.0, "P", "p50_91")
    c25_30 = leg(30, 25.0, "C", "c25_30")
    p25_30 = leg(30, -25.0, "P", "p25_30")

    out = c50_30
    for f in (p50_30, c50_91, p50_91, c25_30, p25_30):
        out = out.merge(f, on=["ym", "secid"], how="outer")

    # both legs required for an ATM level (the frozen "mean of +/-50 delta")
    out["iv30"] = (out["c50_30"] + out["p50_30"]) / 2.0
    out["iv91"] = (out["c50_91"] + out["p50_91"]) / 2.0
    out["skew_25d"] = out["p25_30"] - out["c25_30"]
    logger.info("surface: %d (ym, secid) rows, iv30 non-null %.1f%%",
                len(out), 100 * out["iv30"].notna().mean())
    return out[["ym", "secid", "iv30", "iv91", "skew_25d"]]


# ── daily volume ratios and realised vol ─────────────────────────────────────
def _safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    """num/den where den > 0, NaN elsewhere — computed only on the valid rows."""
    num = pd.to_numeric(num, errors="coerce").astype(float)
    den = pd.to_numeric(den, errors="coerce").astype(float)
    ok = den > 0
    out = pd.Series(np.nan, index=num.index, dtype=float)
    out[ok] = num[ok] / den[ok]
    return out


def _dsf_year(y: int, cols: list[str]) -> pd.DataFrame:
    d = pd.read_parquet(RAW / "dsf_full" / f"dsf_{y}.parquet", columns=cols)
    d["permno"] = d["permno"].astype("int64")
    d["date"] = pd.to_datetime(d["date"])
    return d


def daily_ratios_and_rv(years: range, mlink: pd.DataFrame) -> pd.DataFrame:
    """Long: (ym, sym, os_ratio, pc_volume, rv21, n_days_os, n_days_pc).

    Processed year by year with a tail of the prior year so the 21-day realised
    vol window is never silently short at a January month-end.
    """
    out = []
    for y in years:
        stock = _dsf_year(y, ["permno", "date", "ret", "vol"])
        try:
            prev = _dsf_year(y - 1, ["permno", "date", "ret", "vol"])
            cutoff = sorted(prev["date"].unique())[-(RV_WINDOW * 2):][0]
            prev = prev[prev["date"] >= cutoff]
        except FileNotFoundError:
            prev = stock.iloc[:0]
        both = pd.concat([prev, stock], ignore_index=True).sort_values(
            ["permno", "date"])

        # ── realised vol: trailing 21 trading days, annualised
        both["rv"] = (both.groupby("permno", sort=False)["ret"]
                      .transform(lambda s: s.rolling(RV_WINDOW,
                                                     min_periods=RV_WINDOW).std())
                      * np.sqrt(TRADING_DAYS))
        both["ym"] = both["date"].dt.to_period("M")
        rv = (both[both["ym"].dt.year == y]
              .sort_values("date").groupby(["ym", "permno"])["rv"].last()
              .rename("rv21").reset_index())

        # ── option/stock daily ratios
        opt = pd.read_parquet(OPVOL_DIR / f"opvol_{y}.parquet")
        opt = opt.dropna(subset=["secid", "date"])
        opt["secid"] = opt["secid"].astype("int64")
        opt["date"] = pd.to_datetime(opt["date"])
        opt["ym"] = opt["date"].dt.to_period("M")
        opt = opt.merge(mlink[["ym", "secid", "sym"]], on=["ym", "secid"],
                        how="inner")
        opt["permno"] = opt["sym"].astype("int64")

        sv = stock[["permno", "date", "vol"]].rename(columns={"vol": "stock_vol"})
        j = opt.merge(sv, on=["permno", "date"], how="inner")

        # a zero denominator is an UNDEFINED daily ratio, not a zero one.
        # Masked rather than np.where'd: np.where evaluates BOTH branches, so
        # the discarded division still emits divide-by-zero warnings, and a run
        # log full of ignorable warnings is how a real one gets missed.
        j["os_d"] = _safe_div(j["opt_vol"], j["stock_vol"])
        j["pc_d"] = _safe_div(j["put_vol"], j["call_vol"])

        agg = j.groupby(["ym", "permno"]).agg(
            os_ratio=("os_d", "mean"), n_days_os=("os_d", "count"),
            pc_volume=("pc_d", "mean"), n_days_pc=("pc_d", "count"),
        ).reset_index()

        m = agg.merge(rv, on=["ym", "permno"], how="outer")
        m["sym"] = m["permno"].astype("Int64").astype(str)
        out.append(m[["ym", "sym", "os_ratio", "pc_volume", "rv21",
                      "n_days_os", "n_days_pc"]])
        logger.info("daily aggregates %d: %d name-months", y, len(m))

    res = pd.concat(out, ignore_index=True)
    # thin months are noise (house precedent) -> null, and therefore dropped
    res.loc[res["n_days_os"].fillna(0) < MIN_DAYS_PER_MONTH, "os_ratio"] = np.nan
    res.loc[res["n_days_pc"].fillna(0) < MIN_DAYS_PER_MONTH, "pc_volume"] = np.nan
    return res


# ── characteristics for skew_resid ───────────────────────────────────────────
def build_resid_characteristics(panel: Panel) -> pd.DataFrame:
    """Long: (month, sym, log_mktcap, mom_12_1, log_dvol3m).

    Implemented here rather than imported from factory/abio.py on purpose — a
    frozen trial's construction must not be mutable by an edit to another
    trial's module. `rv21` is joined in separately from the daily aggregates.
    """
    idx, cols = panel.monthly_ret.index, panel.monthly_ret.columns
    price = panel.month_end_price.abs()

    sh = pd.read_parquet(RAW / "crsp_msf_shrout.parquet")
    sh = sh.dropna(subset=["shrout"])
    sh = sh[sh["shrout"] > 0].copy()
    sh["sym"] = sh["permno"].astype("Int64").astype(str)
    sh["m"] = pd.to_datetime(sh["date"]).dt.to_period("M").dt.to_timestamp("M")
    shr = (sh.sort_values("date").drop_duplicates(["sym", "m"], keep="last")
           .pivot_table(index="m", columns="sym", values="shrout", aggfunc="last")
           .reindex(index=idx, columns=cols))
    mktcap = price * shr * 1000.0

    log1p = np.log1p(panel.monthly_ret)
    mom = np.expm1(log1p.rolling(11, min_periods=8).sum().shift(1))
    dvol3 = panel.monthly_dollar_vol.rolling(3, min_periods=3).mean()

    frames = {
        "log_mktcap": np.log(mktcap.where(mktcap > 0)),
        "mom_12_1": mom,
        "log_dvol3m": np.log(dvol3.where(dvol3 > 0)),
    }
    out = None
    for name, f in frames.items():
        s = f.stack().rename(name)
        s.index.names = ["month", "sym"]
        out = s.to_frame() if out is None else out.join(s, how="outer")
    return out.reset_index()


def winsorise_by(s: pd.Series, groups: pd.Series) -> pd.Series:
    """Clip to [1%, 99%] quantiles computed WITHIN each group (per month)."""
    lo = groups.map(s.groupby(groups).quantile(WINSOR_LO))
    hi = groups.map(s.groupby(groups).quantile(WINSOR_HI))
    return s.clip(lower=lo, upper=hi)


def residualise_per_month(df: pd.DataFrame) -> pd.Series:
    """Per-month cross-sectional OLS of skew_25d on the four frozen regressors.

    Refit every month, with an intercept. Names missing ANY regressor are
    dropped. Months are independent by construction.
    """
    d = df.dropna(subset=["skew_25d", *RESID_REGRESSORS]).copy()
    for c in RESID_REGRESSORS:
        d[c] = winsorise_by(d[c], d["month"])

    resid = pd.Series(np.nan, index=d.index, dtype=float)
    for _, g in d.groupby("month", sort=True):
        if len(g) <= len(RESID_REGRESSORS) + 1:
            continue
        X = np.column_stack([np.ones(len(g)), g[RESID_REGRESSORS].to_numpy(float)])
        y = g["skew_25d"].to_numpy(float)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid.loc[g.index] = y - X @ beta
    return resid


# ── VIX ──────────────────────────────────────────────────────────────────────
def load_vix() -> pd.Series:
    fx = pd.read_parquet(MODULE_ROOT / "data" / "macro" /
                         "fred_macro_snap20260726.parquet")
    return fx["VIXCLS"].dropna().astype(float)


def vix_terciles(months: pd.DatetimeIndex) -> pd.Series:
    """Month-end VIX tercile label (low/mid/high) over the EXPLORE window."""
    v = load_vix()
    me = v.resample("ME").last().reindex(months)
    w = me.loc[EXPLORE_START:EXPLORE_END]
    q1, q2 = w.quantile(1 / 3), w.quantile(2 / 3)
    return pd.Series(
        np.where(me <= q1, "low", np.where(me <= q2, "mid", "high")),
        index=months).where(me.notna())


# ── assembly ─────────────────────────────────────────────────────────────────
def build_opt_frames(panel: Panel) -> tuple[dict[str, pd.DataFrame], dict]:
    """{arm -> [month x sym] score frame}, plus a diagnostics dict."""
    diag: dict = {"coverage_check": assert_inputs_cover_explore()}
    idx, cols = panel.monthly_ret.index, panel.monthly_ret.columns

    years = range(int(idx.min().year), int(idx.max().year) + 1)
    surf_all = load_surface()
    mlink = month_link(idx, data_bearing=data_bearing_pairs(surf_all, years))
    diag["link_dropped"] = mlink.attrs.get("dropped", {})
    diag["link_score_counts"] = {str(k): int(v) for k, v in
                                 mlink["score"].value_counts().items()}

    surf = surf_all.merge(mlink[["ym", "secid", "sym"]],
                          on=["ym", "secid"], how="inner")
    daily = daily_ratios_and_rv(years, mlink)

    m = surf.merge(daily, on=["ym", "sym"], how="outer")
    m["month"] = m["ym"].dt.to_timestamp("M")

    chars = build_resid_characteristics(panel)
    m = m.merge(chars, on=["month", "sym"], how="left")

    m["iv_atm"] = m["iv30"]
    m["riv_spread"] = m["iv30"] - m["rv21"]
    m["term_slope"] = m["iv91"] - m["iv30"]
    m["skew_resid"] = residualise_per_month(m)

    frames = {}
    for a in ARMS:
        w = (m.dropna(subset=[a])
             .pivot_table(index="month", columns="sym", values=a, aggfunc="last")
             .reindex(index=idx, columns=cols))
        frames[a] = w
        cov = w.loc[EXPLORE_START:EXPLORE_END].notna().sum(axis=1)
        diag[f"coverage_{a}"] = round(float(cov.mean()), 1)
    logger.info("arm coverage: %s",
                {a: diag[f"coverage_{a}"] for a in ARMS})
    return frames, diag


def null_rate_by_vix(frames: dict[str, pd.DataFrame], panel: Panel,
                     segment_masks: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Per-arm drop rate inside the ranked universe, split by VIX tercile.

    This is the frozen reporting requirement: the missingness is
    stress-correlated (0.8% in 2004-06 vs 13.0% in 2020) and must be visible.
    """
    idx = panel.monthly_ret.index
    ter = vix_terciles(idx)
    rows = []
    for arm, f in frames.items():
        for seg, mask in segment_masks.items():
            w = mask.loc[EXPLORE_START:EXPLORE_END]
            have = f.loc[EXPLORE_START:EXPLORE_END].notna() & w
            t = ter.loc[EXPLORE_START:EXPLORE_END]
            rec = {"arm": arm, "segment": seg}
            for lab in ("low", "mid", "high"):
                sel = t == lab
                tot = int(w[sel].to_numpy().sum())
                got = int(have[sel].to_numpy().sum())
                rec[f"drop_{lab}"] = round(1 - got / tot, 4) if tot else np.nan
            hi, lo = rec["drop_high"], rec["drop_low"]
            rec["high_over_low"] = (round(hi / lo, 2)
                                    if lo and lo > 0 else np.nan)
            rec["robustness_line_required"] = bool(
                pd.notna(rec["high_over_low"]) and rec["high_over_low"] > 2.0)
            rows.append(rec)
    return pd.DataFrame(rows)


def always_covered_syms(frame: pd.DataFrame, mask: pd.DataFrame,
                        min_cov: float = 0.95) -> list[str]:
    """Names with >= min_cov surface coverage across their eligible months."""
    w = mask.loc[EXPLORE_START:EXPLORE_END]
    have = frame.loc[EXPLORE_START:EXPLORE_END].notna() & w
    elig_n = w.sum(axis=0)
    have_n = have.sum(axis=0)
    ratio = (have_n / elig_n.where(elig_n > 0))
    return sorted(ratio[ratio >= min_cov].dropna().index.tolist())
