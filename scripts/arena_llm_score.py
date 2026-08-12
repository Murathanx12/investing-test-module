"""The rule that turns forecasts into ONE number per (date, security).

**Frozen and committed before any forward return was joined to any forecast.**
A scoring rule chosen after seeing which mapping ranks best is not a scoring
rule, it is a search, and the search would not be in the denominator.

THE MAPPING
-----------
Only DIRECTIONAL observables contribute to the directional score:

    return_sign        p = P(return > 0)          contribution  +(2p − 1)
    beats_benchmark    p = P(beats benchmark)     contribution  +(2p − 1)
    drawdown_exceeds   p = P(drawdown exceeds x)  contribution  −(2p − 1)
    abs_move_exceeds   NOT directional            contribution   0

`abs_move_exceeds` is the swarm's most common observable and it says nothing
about sign — a 0.8 credence on "moves more than 15%" is compatible with either
direction. Folding it into a directional score would be a units error dressed
as an aggregate. It is kept, separately, as the **dispersion** score, which is
what it actually measures.

Horizons are weighted EQUALLY. A horizon weighting is a free parameter, and the
narrow-domain question ("does it work only at short horizons?") is answered by
splitting the score, not by fitting the weights.

Specialists are weighted EQUALLY — **Amendment A5**. The 20,073-record ledger is
unresolved; a specialist weight estimated from it would be invented authority
dressed as learning. Hierarchical partial-pooled updating begins when forward
records resolve, first on 2026-08-16.

The only permitted non-neutral weight today is the model's own **stated
confidence**, which is an output of the call and not an earned reliability. It
produces a SEPARATE score (`score_conf`), used by the arena's P8 and by nothing
else, so the difference P8 − P7 measures exactly one thing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DIRECTIONAL_SIGN = {"return_sign": +1.0, "beats_benchmark": +1.0,
                    "drawdown_exceeds": -1.0}
SHORT_HORIZONS = (1, 2, 5, 20)
LONG_HORIZONS = (60, 120, 252)


def _explode(calls: pd.DataFrame) -> pd.DataFrame:
    """One row per forecast, carrying its call's arm/role/confidence."""
    out = []
    for r in calls.itertuples():
        for f in (r.forecasts or []):
            out.append({
                "arm": r.arm, "specialist": r.specialist,
                "date_ix": r.date_ix, "permno": r.permno,
                "observable": f["observable"], "horizon_days": f["horizon_days"],
                "probability": float(f["probability"]),
                "threshold": f.get("threshold"),
                "confidence": (float(r.confidence)
                               if r.confidence is not None else np.nan),
            })
    return pd.DataFrame(out)


def score_frame(calls: pd.DataFrame) -> pd.DataFrame:
    """(arm, date_ix, permno) → directional, dispersion and confidence scores."""
    f = _explode(calls)
    if f.empty:
        return pd.DataFrame(columns=["arm", "date_ix", "permno", "score",
                                     "score_conf", "dispersion", "n_forecasts",
                                     "n_specialists", "mean_confidence"])
    f["sign"] = f["observable"].map(DIRECTIONAL_SIGN).fillna(0.0)
    f["dir"] = f["sign"] * (2.0 * f["probability"] - 1.0)
    f["is_dir"] = f["sign"] != 0.0
    f["disp"] = np.where(f["observable"] == "abs_move_exceeds",
                         f["probability"], np.nan)
    f["horizon_band"] = np.where(f["horizon_days"].isin(SHORT_HORIZONS),
                                 "short", "long")

    # specialist first (equal weight within a specialist's own forecasts),
    # then across specialists — so a role that emitted three forecasts does not
    # outvote a role that emitted two.
    per_spec = (f[f["is_dir"]]
                .groupby(["arm", "date_ix", "permno", "specialist"])
                .agg(dir_mean=("dir", "mean"),
                     conf=("confidence", "mean")).reset_index())
    agg = (per_spec.groupby(["arm", "date_ix", "permno"])
           .agg(score=("dir_mean", "mean"),
                n_specialists=("specialist", "nunique"),
                mean_confidence=("conf", "mean")).reset_index())

    w = per_spec.copy()
    w["cw"] = w["conf"].fillna(w["conf"].mean())
    w["num"] = w["dir_mean"] * w["cw"]
    cs = (w.groupby(["arm", "date_ix", "permno"])
          .agg(num=("num", "sum"), den=("cw", "sum")).reset_index())
    cs["score_conf"] = np.where(cs["den"] > 0, cs["num"] / cs["den"], np.nan)
    agg = agg.merge(cs[["arm", "date_ix", "permno", "score_conf"]],
                    on=["arm", "date_ix", "permno"], how="left")

    disp = (f.groupby(["arm", "date_ix", "permno"])
            .agg(dispersion=("disp", "mean"),
                 n_forecasts=("dir", "size")).reset_index())
    agg = agg.merge(disp, on=["arm", "date_ix", "permno"], how="left")

    for band in ("short", "long"):
        b = (f[f["is_dir"] & (f["horizon_band"] == band)]
             .groupby(["arm", "date_ix", "permno", "specialist"])["dir"].mean()
             .groupby(level=[0, 1, 2]).mean().rename(f"score_{band}")
             .reset_index())
        agg = agg.merge(b, on=["arm", "date_ix", "permno"], how="left")
    return agg
