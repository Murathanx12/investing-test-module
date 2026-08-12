"""PORTFOLIO-ARENA-1 — the simulator, the five risk matchings, and the ruler.

ONE SIMULATOR, FIFTEEN SYSTEMS
==============================
Every system produces the same object — a target weight vector over the names
eligible at that date — and then the SAME function turns weights into wealth.
That is the only way a comparison between complete systems means anything: if
each arm carried its own accounting, the arena would be measuring accountants.

THE COST MODEL IS G7, REUSED
----------------------------
Corwin-Schultz half-spread (already stamped at every decision date in
`exit_lab_1_aux.npz`, median 24.2 bps, p90 89.0 bps) + 5 bps slippage + 1 bp
commission, charged on the ONE-WAY traded fraction per name. Index legs pay a
declared 5 bps all-in. A name with no CS estimate pays that date's 90th
percentile — an unpriceable spread is an expensive spread, never a free one.

Impact is SEPARATE and DECLARED, because NIGHT-8 recorded that G7 cannot price
it: `impact_bps = 1e4 · C · σ_daily · sqrt(Q/ADV)` with **C = 1.0, declared,
never fitted**. It is switched on only for the notional sweep and it is labelled
a declared model everywhere it appears.

THE FIVE MATCHINGS (Amendment A3)
---------------------------------
`beta` and `vol` are implemented as a cash blend whose scale is computed from
the trailing 252-day window ENDING AT the decision date — an ex-ante number, so
the matching itself cannot look ahead. `gross` is verified rather than imposed:
in a long-only unlevered arena every raw system already sits at 1.00, and the
report prints the measured value rather than asserting it. `concentration` is
the position budget K, held identical across selection systems. `turnover` is a
partial rebalance toward the target, capped at a common one-way budget.

> A system that wins by carrying more beta has not won anything. The matched
> column is not a footnote to the raw column; it is the answer.

THE RULER (CANON §19)
---------------------
Sampling unit is the MONTH. MDE = 2.80 × max(Newey-West, IID) SE of the tested
monthly series, annualised ×12. Below its own MDE is NOT DETECTABLE and is
never reported as a kill.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

EXTRA_BPS = 6.0          # 5 bps slippage + 1 bp commission, from daily_sim
BENCH_BPS = 5.0          # index fund, all-in, declared
IMPACT_C = 1.0           # DECLARED square-root-law coefficient. Never fitted.
MDE_Z = 2.80
SCALE_CLIP = (0.20, 2.00)

REGIME_BLOCKS = [(2002, 2003), (2004, 2006), (2007, 2009), (2010, 2012),
                 (2013, 2015), (2016, 2018), (2019, 2021), (2022, 2024)]


# ── the ruler ───────────────────────────────────────────────────────────────

def newey_west_se(x: np.ndarray) -> float:
    """SE of the mean with a Newey-West correction. Identical to EXIT-LAB's."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 8:
        return float("nan")
    L = int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    d = x - x.mean()
    s = float(d @ d) / n
    for l in range(1, L + 1):
        s += 2.0 * (1.0 - l / (L + 1.0)) * (float(d[l:] @ d[:-l]) / n)
    return float(np.sqrt(max(s, 0.0) / n))


def ruler(x: np.ndarray, years: np.ndarray | None = None,
          periods: int = 12) -> dict:
    """Mean of a monthly series with its own 80%-power MDE, annualised.

    The tested statistic is the ARITHMETIC monthly mean, because that is what
    has a standard error. The geometric CAGR is reported beside it and is never
    the thing the MDE is applied to — a compounded number's ruler is not the
    same ruler.
    """
    d = np.asarray(x, dtype=float)
    ok = np.isfinite(d)
    d = d[ok]
    n = len(d)
    if n < 8:
        return {"n": n, "mean_ann_pct": None, "mde_ann_pct": None, "t": None,
                "detectable": False, "verdict": "NO_DATA"}
    iid = float(d.std(ddof=1) / np.sqrt(n))
    nw = newey_west_se(d)
    se = max(nw, iid) if np.isfinite(nw) else iid
    m = float(d.mean())
    det = bool(abs(m) > MDE_Z * se)
    out = {
        "n": n,
        "mean_ann_pct": round(m * periods * 100, 4),
        "mde_ann_pct": round(MDE_Z * se * periods * 100, 4),
        "t": round(m / se, 3) if se > 0 else None,
        "se_nw_ann_pct": round(nw * periods * 100, 4),
        "se_iid_ann_pct": round(iid * periods * 100, 4),
        "detectable": det,
    }
    if years is not None:
        yy = np.asarray(years)[ok]
        agree = blocks = 0
        for lo, hi in REGIME_BLOCKS:
            m_b = (yy >= lo) & (yy <= hi)
            if m_b.sum() >= 6:
                blocks += 1
                agree += int(np.sign(d[m_b].mean()) == np.sign(m))
        half = n // 2
        out["blocks"] = f"{agree}/{blocks}"
        out["blocks_agree_n"] = agree
        out["blocks_n"] = blocks
        out["halves_agree"] = bool(np.sign(d[:half].mean())
                                   == np.sign(d[half:].mean()))
        coverage = (blocks > 0 and agree >= max(5, 0)
                    and out["halves_agree"])
    else:
        coverage = True
    if not det:
        out["verdict"] = "NOT_DETECTABLE"
    elif m > 0:
        out["verdict"] = ("DETECTABLE_POSITIVE" if coverage
                          else "UNRESOLVED_UNSTABLE")
    else:
        out["verdict"] = ("DETECTABLE_NEGATIVE" if coverage
                          else "UNRESOLVED_UNSTABLE")
    return out


def cagr(r: np.ndarray, periods: int = 12) -> float:
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return float("nan")
    return float(np.expm1(np.log1p(r).sum() * periods / len(r)))


def max_drawdown(r: np.ndarray) -> float:
    c = np.cumsum(np.log1p(np.nan_to_num(np.asarray(r, dtype=float))))
    return float(np.expm1((c - np.maximum.accumulate(c)).min()))


# ── the simulator ───────────────────────────────────────────────────────────

class Book:
    """One system's wealth path. Weights in, dollars out, costs charged."""

    def __init__(self, notional: float = 0.0, whole_shares: bool = False,
                 impact: bool = False, cost_mult: float = 1.0):
        self.w: dict[int, float] = {}
        self.hs: dict[int, float] = {}          # last known half-spread per name
        self.notional = notional
        self.whole_shares = whole_shares
        self.impact = impact
        self.cost_mult = cost_mult
        self.nav = 1.0
        self.rows: list[dict] = []

    def step(self, k: int, target: pd.Series, scale: float, *,
             ret: pd.Series, hs_bps: pd.Series, sig_d: pd.Series,
             adv: pd.Series, price: pd.Series, r_cash: float,
             bench: bool = False) -> float:
        """One month. `target` sums to 1 over stocks; `scale` is the cash blend."""
        tgt = (target * scale).astype(float)
        tgt = tgt[np.isfinite(tgt) & (tgt.abs() > 1e-12)]

        if self.whole_shares and self.notional > 0:
            px = price.reindex(tgt.index).astype(float)
            sh = np.floor((tgt * self.nav * self.notional)
                          / px.where(px > 0)).fillna(0.0)
            tgt = (sh * px / (self.nav * self.notional)).fillna(0.0)
            tgt = tgt[tgt > 0]

        names = tgt.index.union(pd.Index(list(self.w)))
        prev = pd.Series({n: self.w.get(n, 0.0) for n in names})
        cur = tgt.reindex(names).fillna(0.0)
        trade = (cur - prev).abs()

        if bench:
            cost = float((trade * BENCH_BPS / 1e4).sum())
        else:
            h = pd.Series({n: float(hs_bps.get(n, self.hs.get(n, np.nan)))
                           for n in names})
            fallback = float(np.nanpercentile(hs_bps.to_numpy(), 90)) \
                if len(hs_bps) else 50.0
            h = h.fillna(fallback)
            bps = h + EXTRA_BPS
            if self.impact and self.notional > 0:
                q = trade * self.nav * self.notional
                a = pd.Series({n: float(adv.get(n, np.nan)) for n in names})
                s = pd.Series({n: float(sig_d.get(n, np.nan)) for n in names})
                part = (q / a.where(a > 0)).clip(upper=1.0)
                bps = bps + (1e4 * IMPACT_C * s * np.sqrt(part)).fillna(0.0)
            cost = float((trade * bps / 1e4).sum())
        cost *= self.cost_mult

        r = ret.reindex(cur.index).astype(float).fillna(0.0)
        w_stock = float(cur.sum())
        gross_ret = float((cur * r).sum()) + (1.0 - w_stock) * r_cash
        net = gross_ret - cost
        self.nav *= (1.0 + net)

        newv = cur * (1.0 + r)
        denom = float(newv.sum()) + (1.0 - w_stock) * (1.0 + r_cash)
        self.w = {n: float(v / denom) for n, v in newv.items() if abs(v) > 1e-14}
        for n, v in hs_bps.items():
            if np.isfinite(v):
                self.hs[n] = float(v)

        self.rows.append({
            "date_ix": k, "net": net, "gross": gross_ret, "cost": cost,
            "turnover_1way": float(trade.sum()) / 2.0,
            "gross_exposure": w_stock, "cash_weight": 1.0 - w_stock,
            "n_names": int((cur.abs() > 1e-9).sum()),
            "eff_n": _eff_n(cur),
            "scale": scale,
        })
        return net

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def _eff_n(w: pd.Series) -> float:
    """1/sum(wbar^2) on weights NORMALISED to the stock sleeve.

    Computed on the raw weights it is not a concentration measure at all: a
    vol-matched sleeve at scale 0.4 shrinks every weight by 0.4 and inflates
    the number by 1/0.4^2, which is how a 20-name portfolio printed
    "effective 106.7 names" in the first run.
    """
    tot = float(w.sum())
    if tot <= 0:
        return float("nan")
    wb = w / tot
    ss = float((wb ** 2).sum())
    return float(1.0 / ss) if ss > 0 else float("nan")


def partial_rebalance(target: pd.Series, current: dict[int, float],
                      budget: float) -> pd.Series:
    """Move toward the target only as far as a common turnover budget allows."""
    names = target.index.union(pd.Index(list(current)))
    cur = pd.Series({n: current.get(n, 0.0) for n in names})
    tgt = target.reindex(names).fillna(0.0)
    full = float((tgt - cur).abs().sum()) / 2.0
    if full <= budget or full <= 0:
        return target
    lam = budget / full
    out = cur + lam * (tgt - cur)
    return out[out.abs() > 1e-12]
