"""Evaluate one genome. Vectorised, cost-charged, and honest about what it is.

TWO TIERS, DELIBERATELY. The full `pf.run.Factory` scorecard is the adjudication
instrument — controls, placebo bands, factor regressions, bootstrap — and it
costs ~45 seconds a book. Four hundred genomes through it is five hours, which
is a night. So the Arena screens every genome with this cheaper evaluator and
sends only the finalists to the Factory.

That is a real methodological choice with a real cost, and it is stated rather
than hidden: **an Arena rank is not a verdict.** This module computes a book's
net return series honestly (same eligibility, same monthly clock, same cost
charge as the Factory) but it does NOT compute a placebo band, a factor alpha,
or a multiple-testing deflation. Nothing here may be quoted as evidence that a
strategy works. It exists to order 400 candidates so the 8 that matter can be
adjudicated properly.

WHAT IS CHARGED. Turnover is charged both ways at the genome's cost model. A
genome that trades monthly at 400% annual turnover pays for it here, which is
the whole reason the cheap screen is worth trusting for ORDERING: the thing
that kills most of this programme's candidates is cost, and cost is in.

WHAT IS NOT MODELLED. Market impact (G8's square-root term), delisting stubs,
and the incumbency band the Factory uses. The first two make small-cap,
high-turnover genomes look BETTER here than they are, so the screen is
optimistic exactly where the programme's history says to be suspicious. The
report says so beside every small-cap winner.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

#: One-way basis points by cost model, matching aegis_brain.pf.engine.FLAT_BPS
#: so the screen and the adjudicator charge the same thing.
FLAT_BPS = {"flat0": 0.0, "flat25": 25.0}

MIN_MONTHS = 60


@dataclass
class ArenaResult:
    genome_id: str
    genome_hash: str
    status: str = "OK"
    error: str = ""
    # money
    cagr_net: Optional[float] = None
    cagr_gross: Optional[float] = None
    excess_cagr_net: Optional[float] = None
    t_excess: Optional[float] = None
    # risk
    ann_vol: Optional[float] = None
    downside_vol: Optional[float] = None
    max_drawdown: Optional[float] = None
    worst_rolling_12m: Optional[float] = None
    # shape
    hit_rate: Optional[float] = None
    payoff_ratio: Optional[float] = None
    best_month_share: Optional[float] = None
    top5_months_share: Optional[float] = None
    # implementation
    turnover_1way_annual: Optional[float] = None
    cost_drag_annual_bps: Optional[float] = None
    mean_n_held: Optional[float] = None
    months: Optional[int] = None
    # stability
    first_half_excess: Optional[float] = None
    second_half_excess: Optional[float] = None
    n_regime_blocks_won: Optional[int] = None
    n_regime_blocks: Optional[int] = None

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def _weights(scores: np.ndarray, vols: np.ndarray, genome) -> np.ndarray:
    """Pick top_k by score, then weight them per the genome's rule."""
    k = min(genome.top_k, int(np.isfinite(scores).sum()))
    if k < 3:
        return np.zeros_like(scores)
    idx = np.argpartition(-np.nan_to_num(scores, nan=-np.inf), k - 1)[:k]

    if genome.weighting == "equal_weight":
        raw = np.ones(k)
    elif genome.weighting == "score_weight":
        s = scores[idx]
        # Scores are cross-sectional percentile ranks in [0,1]; shifting to
        # strictly positive keeps a bottom-of-the-book name from getting a
        # zero or negative weight and silently shrinking the portfolio.
        raw = np.clip(s - np.nanmin(s) + 0.05, 1e-6, None)
    elif genome.weighting == "inverse_vol":
        v = vols[idx]
        v = np.where(np.isfinite(v) & (v > 1e-4), v, np.nanmedian(v[np.isfinite(v)])
                     if np.isfinite(v).any() else 1.0)
        raw = 1.0 / v
    elif genome.weighting == "reliability_shrunk":
        s = scores[idx]
        s = np.clip(s - np.nanmin(s) + 0.05, 1e-6, None)
        lam = float(getattr(genome, "reliability_floor", 0.0) or 0.5)
        raw = lam * (s / s.sum()) + (1.0 - lam) * (np.ones(k) / k)
    elif genome.weighting == "fractional_kelly":
        # mu proxied by the cross-sectional score, sigma^2 by realised
        # variance. This is the PM's own sizing rule, put in the Arena so the
        # construction Murat's book uses is measured rather than assumed.
        s = np.clip(scores[idx] - 0.5, 0.0, None)
        v = vols[idx]
        v = np.where(np.isfinite(v) & (v > 1e-4), v, 0.5)
        raw = s / (v ** 2)
        if raw.sum() <= 0:
            raw = np.ones(k)
    else:
        raise ValueError(f"unknown weighting {genome.weighting!r}")

    raw = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)
    if raw.sum() <= 0:
        raw = np.ones(k)
    w = raw / raw.sum()

    # Cap-and-redistribute. Iterated, because one pass can push another name
    # over the cap; without the loop the book quietly sums to less than 1.
    cap = float(genome.max_weight)
    for _ in range(12):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        room = ~over
        if not room.any() or w[room].sum() <= 0:
            break
        w[room] += excess * (w[room] / w[room].sum())

    full = np.zeros_like(scores)
    full[idx] = w * (1.0 - float(genome.cash_floor))
    return full


def evaluate(genome, *, score: pd.DataFrame, ret: pd.DataFrame,
             eligible: pd.DataFrame, vol: pd.DataFrame,
             benchmark: pd.Series) -> ArenaResult:
    """Run one genome over the panel and score it. No look-ahead anywhere.

    `score` must already be shifted so that month t's weights are formed from
    information available at t-1; the caller owns that, because it is the one
    property no downstream check can recover.
    """
    res = ArenaResult(genome_id=genome.genome_id,
                      genome_hash=genome.genome_hash())
    months = ret.index
    bps = FLAT_BPS.get(genome.cost_model)
    if bps is None:
        res.status = "FAILED"
        res.error = f"unknown cost_model {genome.cost_model!r}"
        return res

    sc = score.to_numpy(dtype=np.float32)
    rt = ret.to_numpy(dtype=np.float32)
    el = eligible.to_numpy(dtype=bool)
    vl = vol.to_numpy(dtype=np.float32)

    n_months = len(months)
    w_prev = np.zeros(sc.shape[1], dtype=np.float64)
    gross_rows, net_rows, traded_rows, held_rows = [], [], [], []
    kept = []

    for i in range(n_months):
        r = rt[i]
        alive = np.isfinite(r)
        # Drift last month's book forward before deciding whether to trade.
        if w_prev.sum() > 0:
            drifted = w_prev * (1.0 + np.nan_to_num(r, nan=0.0))
            gross = float((w_prev * np.nan_to_num(r, nan=0.0)).sum())
            tot = drifted.sum()
            w_now = drifted / tot if tot > 0 else drifted
        else:
            gross, w_now = 0.0, w_prev

        rebalance = (i % max(1, genome.rebalance_months)) == 0
        traded = 0.0
        if rebalance:
            s = np.where(el[i] & alive, sc[i], np.nan)
            if np.isfinite(s).sum() >= max(genome.top_k, 20):
                target = _weights(s, vl[i], genome)
                traded = float(np.abs(target - w_now).sum())
                w_now = target
        cost = traded * bps / 1e4
        net = gross - cost

        if i > 0:                      # month 0 has no prior book to earn on
            gross_rows.append(gross)
            net_rows.append(net)
            traded_rows.append(traded)
            held_rows.append(float((w_now > 1e-9).sum()))
            kept.append(months[i])
        w_prev = w_now

    if len(kept) < MIN_MONTHS:
        res.status = "POWER"
        res.error = f"only {len(kept)} months of book returns"
        return res

    net = pd.Series(net_rows, index=pd.DatetimeIndex(kept))
    gross = pd.Series(gross_rows, index=net.index)
    bench = benchmark.reindex(net.index).astype(float)
    if bench.isna().mean() > 0.05:
        res.status = "DATA"
        res.error = "benchmark missing for >5% of months"
        return res
    bench = bench.fillna(0.0)

    yrs = len(net) / 12.0
    res.months = len(net)
    res.cagr_net = float((1 + net).prod() ** (1 / yrs) - 1)
    res.cagr_gross = float((1 + gross).prod() ** (1 / yrs) - 1)
    bench_cagr = float((1 + bench).prod() ** (1 / yrs) - 1)
    res.excess_cagr_net = res.cagr_net - bench_cagr

    d = net - bench
    sd = float(d.std(ddof=1))
    res.t_excess = float(d.mean() / (sd / np.sqrt(len(d)))) if sd > 0 else 0.0

    res.ann_vol = float(net.std(ddof=1) * np.sqrt(12))
    neg = net[net < 0]
    res.downside_vol = float(neg.std(ddof=1) * np.sqrt(12)) if len(neg) > 2 else None

    curve = (1 + net).cumprod()
    res.max_drawdown = float((curve / curve.cummax() - 1).min())
    if len(net) >= 12:
        roll = (1 + net).rolling(12).apply(lambda x: x.prod() - 1, raw=True)
        res.worst_rolling_12m = float(roll.min())

    res.hit_rate = float((d > 0).mean())
    win, loss = net[net > 0], net[net < 0]
    res.payoff_ratio = (float(win.mean() / abs(loss.mean()))
                        if len(win) and len(loss) and loss.mean() != 0 else None)

    # How much of the whole result is a handful of months? A strategy that is
    # one month is a story about that month.
    total = float(net.sum())
    if abs(total) > 1e-9:
        srt = net.sort_values(ascending=False)
        res.best_month_share = float(srt.iloc[0] / total)
        res.top5_months_share = float(srt.iloc[:5].sum() / total)

    res.turnover_1way_annual = float(np.sum(traded_rows)) / 2 / yrs
    res.cost_drag_annual_bps = float(res.cagr_gross - res.cagr_net) * 1e4
    res.mean_n_held = float(np.mean(held_rows))

    half = len(d) // 2
    res.first_half_excess = float((1 + net.iloc[:half]).prod()
                                  ** (12 / max(1, half)) - 1) - \
        float((1 + bench.iloc[:half]).prod() ** (12 / max(1, half)) - 1)
    res.second_half_excess = float((1 + net.iloc[half:]).prod()
                                   ** (12 / max(1, len(d) - half)) - 1) - \
        float((1 + bench.iloc[half:]).prod() ** (12 / max(1, len(d) - half)) - 1)

    # Non-overlapping 3-year blocks: breadth, not just total.
    block = 36
    blocks = [slice(i, min(i + block, len(d))) for i in range(0, len(d), block)]
    blocks = [b for b in blocks if (b.stop - b.start) >= 24]
    res.n_regime_blocks = len(blocks)
    res.n_regime_blocks_won = sum(1 for b in blocks if float(d.iloc[b].sum()) > 0)
    return res
