"""INSTR-REGIME-ANALOG phase 1 — descriptive belief engine.

Frozen in TRIALS/INSTR-REGIME-ANALOG.md (freeze commit 470ed0f) BEFORE this
was built. State estimation, not prediction: deterministic k-NN over a
15-feature daily macro descriptor vector -> 50 nearest historical analogs
(21-trading-day non-max suppression) -> episode clustering -> forward SPY
return/drawdown DISTRIBUTIONS at 3/6/12/24m, sector winners, crash
frequency. Never arms, never allocates. LLM narrates the output.

Contamination declaration (binding, from the registration): the engine
reads the FULL history; any future allocation rule derived from its output
inherits post-hoc provenance and must be a separate walled trial.

Disclosed data departures (registration amendment section): credit features
use DBAA-DGS10 (FRED truncated HY-OAS to a rolling ~3y window); gold uses
GC=F futures (FRED removed the LBMA fix). Disk SPY starts 2002-01, so the
first complete vector lands ~2002-07 (the registration's "~2000-12" was an
estimate that overlooked the disk-SPY constraint; disclosed).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT

ENGINE_VERSION = "analog-p1-2026-07-26"

MACRO_DIR = MODULE_ROOT / "data" / "macro"
FRED_SNAP = MACRO_DIR / "fred_macro_snap20260726.parquet"
SECTOR_SNAP = MACRO_DIR / "sector_etf_daily_close.parquet"
ETF_SNAP = MACRO_DIR / "etf_daily_close.parquet"
BELIEF_LEDGER = MODULE_ROOT / "ledger" / "belief_states.jsonl"

SECTORS = ["XLK", "XLE", "XLF", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB"]
DEFENSIVE = ["XLP", "XLU", "XLV"]
CYCLICAL = ["XLK", "XLY", "XLI"]

N_ANALOGS = 50
SELF_EXCLUSION_TD = 63
NMS_TD = 21
EPISODE_GAP_TD = 126
HORIZONS_TD = {"3m": 63, "6m": 126, "12m": 252, "24m": 504}


# ------------------------------------------------------------ descriptors
def build_descriptors() -> pd.DataFrame:
    """The 15 frozen features on SPY trading days. Rows with any NaN are
    incomplete vectors and excluded from retrieval."""
    fred = pd.read_parquet(FRED_SNAP).sort_index()
    sec = pd.read_parquet(SECTOR_SNAP).sort_index()
    etf = pd.read_parquet(ETF_SNAP).sort_index()

    idx = etf["SPY"].dropna().index                       # master trading days
    f = fred.reindex(idx).ffill(limit=5)
    sec = sec.reindex(idx).ffill(limit=5)
    spy = etf["SPY"].reindex(idx)

    # dollar splice: DTWEXM through 2019-12, DTWEXBGS after, ratio-spliced
    dxm, dxb = f["DTWEXM"], f["DTWEXBGS"]
    overlap = dxm.notna() & dxb.notna()
    ratio = (dxm[overlap] / dxb[overlap]).median() if overlap.any() else 1.0
    dollar = dxm.fillna(dxb * ratio)

    credit = f["DBAA"] - f["DGS10"]                       # disclosed HY-OAS substitute
    spy_ret = spy.pct_change()
    sec_r63 = sec.pct_change(63, fill_method=None)

    d = pd.DataFrame({
        "vix_log": np.log(f["VIXCLS"]),
        "vix_chg21": np.log(f["VIXCLS"]).diff(21),
        "credit": credit,
        "credit_chg63": credit.diff(63),
        "curve_10y2y": f["DGS10"] - f["DGS2"],
        "r10_chg63": f["DGS10"].diff(63),
        "rate_vol21": f["DGS10"].diff().rolling(21).std(),
        "dollar_ret63": dollar.pct_change(63, fill_method=None),
        "oil_ret63": f["DCOILWTICO"].pct_change(63, fill_method=None),
        "gold_ret63": f["GOLD_GCF"].pct_change(63, fill_method=None),
        "spy_ret126": spy.pct_change(126, fill_method=None),
        "spy_vol21": spy_ret.rolling(21).std() * np.sqrt(252),
        "sector_disp63": sec_r63[SECTORS].std(axis=1),
        "defensive_rs63": sec_r63[DEFENSIVE].mean(axis=1) - sec_r63[CYCLICAL].mean(axis=1),
        "breadth_200dma": (sec[SECTORS] > sec[SECTORS].rolling(200).mean())
                          .where(sec[SECTORS].notna()).mean(axis=1),
    }, index=idx)
    return d


def robust_z(d: pd.DataFrame) -> pd.DataFrame:
    """Full-sample robust z (median/IQR) — descriptive-only, declared."""
    med = d.median()
    iqr = d.quantile(0.75) - d.quantile(0.25)
    return (d - med) / iqr.replace(0, np.nan)


# --------------------------------------------------------------- retrieval
def retrieve_analogs(z: pd.DataFrame, query_date: pd.Timestamp,
                     n: int = N_ANALOGS) -> pd.DataFrame:
    """Deterministic k-NN: candidates are complete vectors at positions
    <= query_pos - SELF_EXCLUSION_TD; greedy nearest-first acceptance with
    NMS_TD-position suppression. Returns frame indexed by analog date with
    distance + distance percentile (vs all candidates)."""
    zc = z.dropna()
    if query_date not in zc.index:
        raise KeyError(f"{query_date.date()} has no complete descriptor vector")
    pos = zc.index.get_loc(query_date)
    cand = zc.iloc[: max(pos - SELF_EXCLUSION_TD + 1, 0)]
    if len(cand) < n:
        raise ValueError(f"only {len(cand)} candidate days before self-exclusion")
    q = zc.loc[query_date].to_numpy()
    dist = pd.Series(np.sqrt(((cand.to_numpy() - q) ** 2).sum(axis=1)),
                     index=cand.index)
    order = dist.sort_values(kind="mergesort")            # stable = deterministic
    accepted: list[pd.Timestamp] = []
    accepted_pos: list[int] = []
    cand_pos = {d_: i for i, d_ in enumerate(cand.index)}
    for d_ in order.index:
        p = cand_pos[d_]
        if all(abs(p - ap) >= NMS_TD for ap in accepted_pos):
            accepted.append(d_)
            accepted_pos.append(p)
            if len(accepted) == n:
                break
    out = pd.DataFrame({"distance": dist.loc[accepted]})
    out["dist_percentile"] = dist.rank(pct=True).loc[accepted]
    return out.sort_values("distance")


def cluster_episodes(analogs: pd.DataFrame, z: pd.DataFrame) -> list[dict]:
    """Merge analogs within EPISODE_GAP_TD trading-day positions into
    episodes (PMs reason in episodes, not dates)."""
    zc = z.dropna()
    pos = {d_: zc.index.get_loc(d_) for d_ in analogs.index}
    dates = sorted(analogs.index, key=lambda d_: pos[d_])
    episodes: list[list[pd.Timestamp]] = []
    for d_ in dates:
        if episodes and pos[d_] - pos[episodes[-1][-1]] <= EPISODE_GAP_TD:
            episodes[-1].append(d_)
        else:
            episodes.append([d_])
    out = []
    for ep in episodes:
        sub = analogs.loc[ep]
        out.append({
            "start": str(ep[0].date()), "end": str(ep[-1].date()),
            "n_analogs": len(ep),
            "mean_distance": round(float(sub["distance"].mean()), 3),
        })
    return sorted(out, key=lambda e: e["mean_distance"])


# ---------------------------------------------------------------- outcomes
def forward_outcomes(analog_dates: pd.Index) -> pd.DataFrame:
    """Forward SPY total return per horizon, fwd-12m max drawdown, and the
    fwd-6m winning sector, from each analog date. Right-edge truncation ->
    NaN (n reported per horizon, never imputed)."""
    spy = pd.read_parquet(ETF_SNAP).sort_index()["SPY"].dropna()
    sec = pd.read_parquet(SECTOR_SNAP).sort_index().reindex(spy.index).ffill(limit=5)
    pos_of = {d_: spy.index.get_loc(d_) for d_ in analog_dates}
    rows = {}
    for d_, p in pos_of.items():
        row = {}
        for name, h in HORIZONS_TD.items():
            row[f"fwd_{name}"] = (float(spy.iloc[p + h] / spy.iloc[p] - 1)
                                  if p + h < len(spy) else np.nan)
        if p + 252 < len(spy):
            path = spy.iloc[p: p + 253]
            row["fwd_12m_maxdd"] = float((path / path.cummax() - 1).min())
        else:
            row["fwd_12m_maxdd"] = np.nan
        if p + 126 < len(spy):
            s0, s1 = sec.iloc[p], sec.iloc[p + 126]
            r = (s1 / s0 - 1).dropna()
            row["sector_winner_6m"] = r.idxmax() if len(r) else None
        else:
            row["sector_winner_6m"] = None
        rows[d_] = row
    return pd.DataFrame(rows).T


def _dist_summary(s: pd.Series) -> dict:
    s = s.dropna().astype(float)
    if s.empty:
        return {"n": 0}
    return {"n": int(len(s)), "mean": round(float(s.mean()), 4),
            "median": round(float(s.median()), 4),
            "p10": round(float(s.quantile(0.10)), 4),
            "p90": round(float(s.quantile(0.90)), 4),
            "share_positive": round(float((s > 0).mean()), 3)}


# ------------------------------------------------------------- belief state
@dataclass
class BeliefState:
    """The new artifact class beside trials (round-10 adoption). Analog
    frequencies are labeled ESTIMATES-NOT-FORECASTS; never arms."""
    query_date: str
    run_timestamp: str
    engine_version: str
    state_probs: dict
    confidence: float
    evidence: dict
    backfill: bool = False
    note: str = ("descriptive analog frequencies over 50 nearest historical "
                 "periods; estimates-not-forecasts; never allocates")
    extras: dict = field(default_factory=dict)


def compute_belief(z: pd.DataFrame, query_date: pd.Timestamp,
                   run_timestamp: str, backfill: bool = False) -> tuple[BeliefState, dict]:
    analogs = retrieve_analogs(z, query_date)
    episodes = cluster_episodes(analogs, z)
    fwd = forward_outcomes(analogs.index)

    f6 = fwd["fwd_6m"].dropna()
    f12 = fwd["fwd_12m"].dropna()
    dd = fwd["fwd_12m_maxdd"].dropna()
    state_probs = {
        "fwd6m_positive": round(float((f6 > 0).mean()), 3) if len(f6) else None,
        "fwd12m_positive": round(float((f12 > 0).mean()), 3) if len(f12) else None,
        "crash12m_dd15": round(float((dd <= -0.15).mean()), 3) if len(dd) else None,
        "crash12m_dd20": round(float((dd <= -0.20).mean()), 3) if len(dd) else None,
    }
    # frozen formula: sign-agreement of analog fwd-6m x (1 - mean dist pctile)
    agree = max((f6 > 0).mean(), (f6 <= 0).mean()) if len(f6) else np.nan
    conf = float(agree * (1 - analogs["dist_percentile"].mean()))

    zq = z.dropna().loc[query_date]
    extreme = zq.abs().sort_values(ascending=False).head(5)
    winners = fwd["sector_winner_6m"].dropna()
    evidence = {
        "top5_extreme_features_today": [
            {"feature": k, "z": round(float(zq[k]), 2)} for k in extreme.index],
        "episodes": episodes,
        "sector_winners_6m": winners.value_counts().head(3).to_dict(),
    }
    belief = BeliefState(
        query_date=str(query_date.date()), run_timestamp=run_timestamp,
        engine_version=ENGINE_VERSION, state_probs=state_probs,
        confidence=round(conf, 3), evidence=evidence, backfill=backfill,
    )
    detail = {
        "analogs": [{"date": str(d_.date()),
                     "distance": round(float(r.distance), 3)}
                    for d_, r in analogs.iterrows()],
        "forward_distributions": {f"fwd_{h}": _dist_summary(fwd[f"fwd_{h}"])
                                  for h in HORIZONS_TD},
        "fwd_12m_maxdd": _dist_summary(fwd["fwd_12m_maxdd"]),
    }
    return belief, detail


def append_belief(belief: BeliefState, path: Path = BELIEF_LEDGER) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(belief)) + "\n")
