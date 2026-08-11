"""Layer 1: does the information exist? -- measured on the cross-section.

WHY THIS MODULE EXISTS
======================

This programme has one instrument for the question "does signal X predict
returns": build an equal-weighted top-50 book, rebalance it monthly, subtract
the market, and test the mean of the resulting 252 monthly numbers. NIGHT-10
measured what that instrument can resolve and the answer was 6.5 to 24.8 %/yr at
80% power (`scripts/audit_power_hac.py`). No credible equity anomaly is that
large. 195 experiments were killed by a ruler coarser than the thing it was
measuring, and the graveyard recorded "we could not see it" identically to "it
is not there".

The fix is not a lower evidence bar. It is a finer ruler. The top-50 design
throws away almost everything it was given:

  * **breadth.** ~3,000 eligible names become 50 held names. The other 2,950
    stock-months carry information about the same hypothesis and are discarded.
  * **the ranking below the cut.** Whether the signal orders names 51 through
    3,000 correctly is invisible to a book that holds the top 50.
  * **the sign of the answer at the bottom.** A signal that works mainly by
    identifying names to AVOID cannot register at all.
  * most importantly, **the systematic component is left in the standard
    error.** Most of a top-50 book's monthly variance is its incidental size and
    sector tilt against the market, not disagreement about the signal. That
    variance carries no information about the hypothesis and it sits in the
    denominator of every t-stat this programme has computed.

So this module estimates on the panel instead of on one portfolio's returns:
~900,000 stock-months rather than 252 portfolio-months, with the cross-sectional
mean removed each period, which is where the market factor goes.

WHAT THIS MODULE MAY AND MAY NOT CONCLUDE
=========================================

**It may conclude that information exists. It may NOT conclude that money can
be made.** These are different claims and this programme has repeatedly killed
the first for failing the second.

The long-short spread reported here is dollar-neutral and unconstrained. Round
16 measured that 88 to 99.9% of a comparable spread lived in the SHORT leg -- the
leg a long-only book cannot hold. A Layer-1 result is therefore a licence to run
Layer 2 (does it help at the portfolio's actual decision boundary) and then
Layer 3 (does it survive turnover, spreads, capacity), and nothing else. Every
result carries `licenses` saying exactly this, so a downstream reader cannot
quote an information t-stat as a return.

The verdict vocabulary is three-valued for the same reason:

    INFORMATION_PRESENT   the cross-section predicts, above this design's MDE
    UNRESOLVED            below the MDE -- absence of evidence, not evidence of absence
    NO_INFORMATION        below the MDE *and* the MDE is small enough that a
                          worthwhile effect would have shown -- an equivalence
                          claim, which needs the design to be powered to make it

`NO_INFORMATION` is the only kill this module can issue, and it requires the
design to demonstrate its own adequacy first. That is CANON §19 applied at the
point of the verdict rather than printed beside it.

ESTIMATOR
=========

Fama-MacBeth. Each month the eligible cross-section is standardised (rank ->
normal scores by default, so a fat tail in the raw signal cannot become a fat
tail in the estimate) and regressed on forward returns; the slope lambda_t is
one observation. The time series of lambda_t is then tested with Newey-West.
Cross-sectional correlation within a month -- the thing that makes a naive
pooled panel regression lie -- is handled exactly, because each month
contributes exactly one number. This is date-clustering, done the oldest way.

Units are stated on every field. `lambda` is return per one cross-sectional
standard deviation of the signal, annualised by x12. `decile_spread` and
`long_short_spread` are %/yr and are the only fields comparable to a portfolio
result.

OVERLAP. At horizon h > 1 the monthly lambda series overlaps by h-1 months and
is autocorrelated by construction. The Newey-West lag length is set to at least
2h for that reason, and `non_overlapping` re-estimates on every h-th month as a
cross-check that does not rely on the HAC correction being right.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats as sps

from aegis_brain.harness.benchmark import newey_west_tstat

logger = logging.getLogger(__name__)

#: z(0.975) + z(0.80). An MDE is DEFINED against a 5% significance test: at a
#: true effect of MDE_Z standard errors, the rule "reject when |t| >= 1.96"
#: fires 80% of the time. That is the promise CANON §19 makes.
#:
#: **The verdict rule here is deliberately stricter than that promise.**
#: INFORMATION_PRESENT requires |effect| >= MDE, i.e. 2.8 SE, not the 1.96 SE
#: the MDE is defined against. At a true effect of exactly the MDE the estimate
#: lands above it about half the time, so this instrument finds a
#: just-at-the-MDE effect ~50% of the time, not 80%. That is not a fault and it
#: is measured rather than assumed: `information_calibration.json` reports both
#: rates side by side, and the calibration harness fails if they are ever equal.
#:
#: The extra strictness is the winner's-curse guard. Among low-powered studies
#: the results that clear mere significance systematically overstate their
#: effects, and NIGHT-10 found 21 of 21 configurations sitting in exactly that
#: region. An instrument built to end that failure may not itself promote on it.
MDE_Z = 2.8
SIG_Z = 1.96
MONTHS = 12

#: Below this many names a cross-sectional slope is not an estimate of anything.
MIN_NAMES = 30

#: The largest per-year effect this programme treats as economically credible
#: for a single equity signal, gross. A design whose MDE exceeds this cannot
#: issue NO_INFORMATION however clean its null looks -- it simply cannot see the
#: range where real effects live. Frozen here rather than passed in, so that a
#: caller cannot widen it to make its own null look decisive.
LARGEST_CREDIBLE_EFFECT_ANN = 0.05


def _normal_scores(row: pd.Series) -> pd.Series:
    """Cross-sectional rank -> normal scores, mean 0, sd ~1.

    Ranking first is not cosmetic. Raw accounting and analyst signals have tails
    that a least-squares slope will happily be determined by; NIGHT-10 found a
    market cap of $61tn sitting in a live feed. A rank cannot do that, and the
    cost -- a monotone relabelling of the signal -- is one this programme has
    already accepted everywhere else it ranks names.
    """
    n = len(row)
    if n < 3:
        return pd.Series(np.nan, index=row.index)
    r = row.rank(method="average")
    z = sps.norm.ppf((r - 0.5) / n)
    return pd.Series(z, index=row.index)


def forward_return(monthly_ret: pd.DataFrame, h: int) -> pd.DataFrame:
    """Compounded h-month forward simple return, aligned to the FORMATION month.

    `out.loc[t, i]` is what name i returned over months t+1 .. t+h. A signal
    observed at t is therefore compared against `out.loc[t]` with no further
    shifting, which is the alignment mistake this function exists to prevent.
    """
    if h < 1:
        raise ValueError("horizon must be at least one month")
    r = monthly_ret.astype(float)
    fwd = (1.0 + r).shift(-1)
    for k in range(2, h + 1):
        fwd = fwd * (1.0 + r).shift(-k)
    return fwd - 1.0


@dataclass
class InformationResult:
    """One signal, one horizon, one instrument. Self-describing by contract."""
    signal: str
    horizon_months: int
    n_months: int
    n_obs: int
    mean_names_per_month: float
    lambda_ann: float
    lambda_se_ann: float
    lambda_t: float | None
    lambda_mde_ann: float
    rank_ic_mean: float
    rank_ic_t: float | None
    decile_spread_ann: float
    decile_spread_t: float | None
    decile_spread_mde_ann: float
    long_short_spread_ann: float
    long_short_spread_t: float | None
    long_short_spread_mde_ann: float
    verdict: str
    reading: str
    units: dict = field(default_factory=dict)
    licenses: str = ""
    diagnostics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        return {k: (round(v, 6) if isinstance(v, float) else v)
                for k, v in d.items()}


def _series_stats(x: pd.Series, lags: int, *, annualize_by: float) -> dict:
    """Mean, HAC t and 80%-power MDE of a monthly series, in annual units.

    `annualize_by` is 12 for a per-month quantity that accumulates (a return)
    and 12/h for an h-month overlapping quantity, so that a 12-month-horizon
    spread is not quoted twelve times over.
    """
    s = pd.Series(x).dropna().astype(float)
    n = len(s)
    if n < 12:
        return {"mean_ann": float("nan"), "t": None, "se_ann": float("nan"),
                "mde_ann": float("nan"), "n": n}
    nw = newey_west_tstat(s, lags=lags)
    se_iid = float(s.std(ddof=1) / np.sqrt(n))
    se_hac = float(nw["se"]) if nw.get("se") else se_iid
    # Same rule as scorecard._power_block: inference on HAC, the MDE on the
    # conservative one, because an MDE licenses a null.
    se_bind = max(se_hac, se_iid)
    return {
        "mean_ann": float(s.mean()) * annualize_by,
        "t": None if nw.get("t") is None else float(nw["t"]),
        "se_ann": se_hac * annualize_by,
        "se_ann_iid": se_iid * annualize_by,
        "mde_ann": MDE_Z * se_bind * annualize_by,
        "n": n,
    }


def cross_sectional_information(
    signal: pd.DataFrame,
    monthly_ret: pd.DataFrame,
    *,
    eligible: pd.DataFrame | None = None,
    horizon: int = 1,
    name: str = "signal",
    lags: int | None = None,
    min_names: int = MIN_NAMES,
    n_quantiles: int = 10,
    non_overlapping: bool = False,
) -> InformationResult:
    """Estimate whether `signal` orders forward returns in the cross-section.

    `signal` and `monthly_ret` are month x permno frames on the same axes. The
    signal is used at its own month against `forward_return(..., horizon)`,
    which is already aligned to the formation month.

    Set `non_overlapping=True` to sample every h-th month instead of correcting
    an overlapping series with HAC. The two should agree; when they do not, the
    HAC correction is doing more work than it should be trusted with.
    """
    sig = signal.astype(float)
    ret = monthly_ret.astype(float)
    cols = sig.columns.intersection(ret.columns)
    idx = sig.index.intersection(ret.index)
    sig, ret = sig.loc[idx, cols], ret.loc[idx, cols]
    if eligible is not None:
        elig = eligible.reindex(index=idx, columns=cols).fillna(False)
        sig = sig.where(elig.astype(bool))

    fwd = forward_return(ret, horizon)
    if lags is None:
        lags = max(MONTHS, 2 * horizon)

    months = list(idx)
    if non_overlapping:
        months = months[::horizon]

    lam, ics, dec, ls, counts = [], [], [], [], []
    keep_months = []
    for m in months:
        s_row = sig.loc[m].dropna()
        if len(s_row) < min_names:
            continue
        y_row = fwd.loc[m].reindex(s_row.index).dropna()
        if len(y_row) < min_names:
            continue
        s_row = s_row.reindex(y_row.index)
        z = _normal_scores(s_row)
        y = y_row.astype(float)
        # Cross-sectionally demean the return: this is where the market factor
        # goes, and it is the single largest term in the top-50 design's SE.
        y = y - y.mean()
        zz = float((z * z).sum())
        if zz <= 0:
            continue
        lam.append(float((z * y).sum() / zz))
        ics.append(float(sps.spearmanr(s_row.to_numpy(), y.to_numpy()).statistic))

        q = min(n_quantiles, max(2, len(y) // min_names))
        try:
            bucket = pd.qcut(s_row.rank(method="first"), q, labels=False)
        except ValueError:
            continue
        top = y[bucket == q - 1].mean()
        bot = y[bucket == 0].mean()
        dec.append(float(top - bot))
        # breadth-weighted dollar-neutral spread: weight proportional to the
        # normal score, scaled so each side sums to 1.
        w = z / z.abs().sum() * 2.0
        ls.append(float((w * y).sum()))
        counts.append(len(y))
        keep_months.append(m)

    if len(lam) < 12:
        return InformationResult(
            signal=name, horizon_months=horizon, n_months=len(lam), n_obs=0,
            mean_names_per_month=float(np.mean(counts)) if counts else 0.0,
            lambda_ann=float("nan"), lambda_se_ann=float("nan"), lambda_t=None,
            lambda_mde_ann=float("nan"), rank_ic_mean=float("nan"),
            rank_ic_t=None, decile_spread_ann=float("nan"),
            decile_spread_t=None, decile_spread_mde_ann=float("nan"),
            long_short_spread_ann=float("nan"), long_short_spread_t=None,
            long_short_spread_mde_ann=float("nan"),
            verdict="TOO_SHORT",
            reading=f"{len(lam)} usable months is too few to estimate anything",
            licenses="nothing")

    ann = MONTHS / horizon      # an h-month quantity is earned h months at a time
    li = pd.Series(lam, index=keep_months)
    di = pd.Series(dec, index=keep_months)
    si = pd.Series(ls, index=keep_months)
    ii = pd.Series(ics, index=keep_months)

    L = _series_stats(li, lags, annualize_by=ann)
    D = _series_stats(di, lags, annualize_by=ann)
    S = _series_stats(si, lags, annualize_by=ann)
    I = _series_stats(ii, lags, annualize_by=1.0)   # a correlation is not annualisable

    # The verdict is taken on the long-short spread, because that is the field
    # in %/yr and the one an economic threshold can be stated against.
    #
    # NO_INFORMATION is an EQUIVALENCE claim and is tested as one. The first
    # version of this rule issued it whenever the effect missed the MDE and the
    # MDE was small — and on real data it promptly labelled an arm with t = 2.21
    # "evidence of absence". An effect that is significantly different from zero
    # cannot be evidence of absence, however small the design's MDE is; a
    # non-significant t never establishes a zero either. The honest form is a
    # one-sided equivalence bound: the whole 95% interval must lie inside the
    # region we have already declared economically uninteresting.
    eff, mde = S["mean_ann"], S["mde_ann"]
    se = mde / MDE_Z if mde > 0 else float("nan")
    upper_abs = abs(eff) + SIG_Z * se       # upper 95% bound on the magnitude
    detectable = bool(abs(eff) >= mde)
    significant = bool(S["t"] is not None and abs(S["t"]) >= SIG_Z)
    equivalent_to_zero = bool(
        np.isfinite(upper_abs) and upper_abs < LARGEST_CREDIBLE_EFFECT_ANN
        and not significant)
    if detectable:
        verdict = "INFORMATION_PRESENT"
        reading = (f"the cross-section orders forward returns: "
                   f"{100*eff:+.2f}%/yr breadth-weighted spread against an MDE "
                   f"of {100*mde:.2f}%/yr (t {S['t']:+.2f}). This is an "
                   f"INFORMATION result and licenses a Layer-2 test, not a "
                   f"money claim.")
    elif equivalent_to_zero:
        verdict = "NO_INFORMATION"
        reading = (f"no information: the spread is {100*eff:+.2f}%/yr and its "
                   f"95% interval reaches only {100*upper_abs:.2f}%/yr in "
                   f"magnitude, entirely inside the "
                   f"{100*LARGEST_CREDIBLE_EFFECT_ANN:.0f}%/yr that would be "
                   f"worth having. An effect large enough to matter is ruled "
                   f"OUT here, so this is evidence of absence rather than "
                   f"absence of evidence.")
    else:
        why = ("it is significantly non-zero but below the threshold at which "
               "this design finds effects reliably, which is where significant "
               "findings systematically overstate themselves"
               if significant else
               f"its 95% interval still reaches {100*upper_abs:.2f}%/yr, so an "
               f"effect worth having is not ruled out")
        verdict = "UNRESOLVED"
        reading = (f"UNRESOLVED: the spread is {100*eff:+.2f}%/yr against an "
                   f"MDE of {100*mde:.2f}%/yr — {why}. This is absence of "
                   f"evidence and may NOT be recorded as a kill (CANON §19).")

    return InformationResult(
        signal=name, horizon_months=horizon, n_months=len(lam),
        n_obs=int(np.sum(counts)),
        mean_names_per_month=float(np.mean(counts)),
        lambda_ann=L["mean_ann"], lambda_se_ann=L["se_ann"], lambda_t=L["t"],
        lambda_mde_ann=L["mde_ann"],
        rank_ic_mean=I["mean_ann"], rank_ic_t=I["t"],
        decile_spread_ann=D["mean_ann"], decile_spread_t=D["t"],
        decile_spread_mde_ann=D["mde_ann"],
        long_short_spread_ann=S["mean_ann"], long_short_spread_t=S["t"],
        long_short_spread_mde_ann=S["mde_ann"],
        verdict=verdict, reading=reading,
        units={
            "lambda_ann": "forward return per 1 cross-sectional sd of signal, x12/h",
            "rank_ic_mean": "Spearman correlation — NOT annualisable, no /yr reading",
            "decile_spread_ann": "top minus bottom decile, %/yr, equal-weighted",
            "long_short_spread_ann": "breadth-weighted dollar-neutral spread, %/yr",
            "estimator": f"Fama-MacBeth, Newey-West({lags}) on the monthly slopes",
            "sampling": "non-overlapping" if non_overlapping else "overlapping monthly",
        },
        licenses=(
            "LAYER 1 ONLY. This says the cross-section carries information. It "
            "does NOT say a long-only book can earn it: the spread is "
            "dollar-neutral and unconstrained, and Round 16 measured 88-99.9% "
            "of a comparable spread living in the short leg. Licenses a Layer-2 "
            "decision-boundary test; licenses no money claim and no position."),
        diagnostics={
            "hac_lags": lags,
            "lambda_se_ann_iid": L.get("se_ann_iid"),
            "decile_quantiles": n_quantiles,
            "largest_credible_effect_ann": LARGEST_CREDIBLE_EFFECT_ANN,
            # a kill needs the whole 95% interval inside the uninteresting
            # region, not merely a fine-looking MDE — see the verdict block
            "upper_95_bound_on_magnitude_ann": (
                round(upper_abs, 6) if np.isfinite(upper_abs) else None),
            "significant_at_5pct": significant,
            "equivalent_to_zero": equivalent_to_zero,
            "powered_to_issue_a_kill": bool(
                np.isfinite(upper_abs)
                and upper_abs < LARGEST_CREDIBLE_EFFECT_ANN),
            "min_names": min_names,
        },
    )


def top_n_long_only_excess(
    signal: pd.DataFrame,
    monthly_ret: pd.DataFrame,
    benchmark: pd.Series,
    *,
    eligible: pd.DataFrame | None = None,
    top_n: int = 50,
    clock: int = 1,
    min_names: int = 20,
) -> pd.Series:
    """The programme's INCUMBENT instrument, reproduced here for comparison.

    Equal-weighted top-N, rebalanced every `clock` months, minus the benchmark.
    This is what every kill in the graveyard was measured with. It is here so
    that the claim "the cross-sectional instrument is more powerful" is a
    measurement on the same signal rather than an assertion.
    """
    sig, ret = signal.astype(float), monthly_ret.astype(float)
    cols = sig.columns.intersection(ret.columns)
    idx = sig.index.intersection(ret.index)
    sig, ret = sig.loc[idx, cols], ret.loc[idx, cols]
    if eligible is not None:
        sig = sig.where(eligible.reindex(index=idx, columns=cols).fillna(False)
                        .astype(bool))
    months, out, held = list(idx), [], None
    for k in range(len(months) - 1):
        m_prev, m_now = months[k], months[k + 1]
        if held is None or k % clock == 0:
            row = sig.loc[m_prev].dropna()
            if len(row) < min_names:
                continue
            held = row.nlargest(min(top_n, len(row))).index
        r = ret.loc[m_now, held].dropna()
        b = benchmark.get(m_now, float("nan"))
        if r.empty or not np.isfinite(b):
            continue
        out.append((m_now, float(r.mean()) - float(b)))
    return pd.Series(dict(out)).sort_index() if out else pd.Series(dtype=float)


def instrument_comparison(
    signal: pd.DataFrame,
    monthly_ret: pd.DataFrame,
    benchmark: pd.Series,
    *,
    eligible: pd.DataFrame | None = None,
    name: str = "signal",
    horizon: int = 1,
    top_n: int = 50,
) -> dict:
    """Put the incumbent and the cross-sectional instrument side by side.

    Returns both MDEs and the ratio. The claim being tested is that the
    cross-sectional design resolves a smaller effect on the SAME signal over the
    SAME months; a ratio at or below 1 would refute it, and the function is
    written to report that outcome as readily as the other one.
    """
    xs = cross_sectional_information(
        signal, monthly_ret, eligible=eligible, horizon=horizon, name=name)
    inc = top_n_long_only_excess(signal, monthly_ret, benchmark,
                                 eligible=eligible, top_n=top_n)
    I = _series_stats(inc, MONTHS, annualize_by=MONTHS)
    ratio = (I["mde_ann"] / xs.long_short_spread_mde_ann
             if xs.long_short_spread_mde_ann else float("nan"))
    return {
        "signal": name,
        "horizon_months": horizon,
        "incumbent_top_n_long_only": {
            "design": f"EW top-{top_n}, monthly, minus benchmark",
            "n_months": I["n"],
            "effect_ann": I["mean_ann"],
            "mde_ann": I["mde_ann"],
            "t": I["t"],
            "unit": "%/yr excess vs benchmark",
        },
        "cross_sectional": {
            "design": "Fama-MacBeth on the full eligible cross-section",
            "n_months": xs.n_months,
            "n_obs": xs.n_obs,
            "mean_names_per_month": xs.mean_names_per_month,
            "effect_ann": xs.long_short_spread_ann,
            "mde_ann": xs.long_short_spread_mde_ann,
            "t": xs.long_short_spread_t,
            "unit": "%/yr breadth-weighted dollar-neutral spread",
        },
        "mde_ratio_incumbent_over_cross_sectional": ratio,
        "reading": (
            f"the incumbent design resolves {100*I['mde_ann']:.2f}%/yr; the "
            f"cross-sectional design resolves "
            f"{100*xs.long_short_spread_mde_ann:.2f}%/yr on the same signal and "
            f"months — a factor of {ratio:.2f}"
            if np.isfinite(ratio) else "comparison unavailable"),
        "caveat": (
            "The two effects are NOT the same quantity: one is a long-only book "
            "against a benchmark, the other a dollar-neutral spread. Comparing "
            "their MDEs compares what each design can RESOLVE, which is the "
            "question here; it does not make their point estimates "
            "interchangeable."),
    }
