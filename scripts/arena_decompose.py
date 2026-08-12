"""Amendment A10 — decompose the arena's final number, each term beside its MDE.

Every term is a PAIRED MONTHLY DIFFERENCE between two runs of the same system
that differ in exactly one thing, so the ruler applies to the term itself and
not to a difference of two independently-estimated CAGRs.

    selection   system(gross) − equally-concentrated random(gross)
    exposure    system(raw)   − system(beta-matched)
    sizing      system(K=10)  − system(K=40)
    execution   system(raw)   − system(turnover-matched)
    costs       system(1x)    − system(0x)
    beta/style  (realised beta − 1) × the market's own excess return
    timing      NOT MEASURED HERE — it is chunk 6's instrument, and claiming a
                timing term from a monthly-rebalanced always-invested arena
                would be inventing a measurement
    LLM         from ABLATION-1, not from this file

    python -m scripts.arena_decompose
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from scripts import arena_systems as S
from scripts.arena_core import cagr, ruler
from scripts.run_portfolio_arena_1 import (AUX, exante, load, load_lc, pick,
                                           run_system)

OUT = MODULE_ROOT / "data" / "factory" / "arena_decomposition.json"
SYSTEMS = {"P5_aegis_deterministic": S.aegis_deterministic,
           "P11_momentum_event": S.momentum_event,
           "P12_revision": S.revision,
           "P13_positive_skew": S.positive_skew}


def main() -> int:
    t0 = time.time()
    panel, mkt, by_date = load(False)
    dates_k = sorted(by_date)
    LC, dec_ix, mkt_log = load_lc()
    dec_dates = pd.DatetimeIndex(
        np.load(AUX, allow_pickle=False)["dec_dates"].astype("datetime64[ns]"))
    years_of = lambda kk: np.array([dec_dates[int(x)].year for x in kk])

    def R(scorer, K=20, wmax=0.10, **kw):
        return run_system("x", lambda k, d: pick(scorer(d), K, wmax), by_date,
                          mkt, dates_k, LC, dec_ix, mkt_log, **kw)

    def Rrand(K=20, wmax=0.10, **kw):
        return run_system("r", lambda k, d: pick(S.random_score(d, k), K, wmax),
                          by_date, mkt, dates_k, LC, dec_ix, mkt_log, **kw)

    def diff(a: pd.DataFrame, b: pd.DataFrame) -> dict:
        A = a.set_index("date_ix")["net"]
        B = b.set_index("date_ix")["net"]
        idx = A.index.intersection(B.index)
        d = (A.loc[idx] - B.loc[idx]).to_numpy()
        out = ruler(d, years_of(idx))
        out["geometric_gap_pct"] = round(
            (cagr(A.loc[idx].to_numpy()) - cagr(B.loc[idx].to_numpy())) * 100, 3)
        return out

    rand_gross = Rrand(cost_mult=0.0)
    tb = float(np.median([R(f).loc[:, "turnover_1way"].median()
                          for f in SYSTEMS.values()]))
    print(f"turnover budget {tb:.4f} ({time.time()-t0:.0f}s)", flush=True)

    out = {"turnover_budget_1way": round(tb, 4), "terms": {}}
    for name, f in SYSTEMS.items():
        raw = R(f)
        gross = R(f, cost_mult=0.0)
        bmatch = R(f, matching="beta")
        tmatch = R(f, matching="turnover", turnover_budget=tb)
        k10 = R(f, K=10, wmax=0.20)
        k40 = R(f, K=40, wmax=0.05)

        kk = raw["date_ix"].to_numpy()
        mm = mkt.loc[kk, "mkt_fwd_1m"].to_numpy()
        cc = mkt.loc[kk, "cash_fwd_1m"].to_numpy()
        X = np.column_stack([np.ones(len(mm)), mm - cc])
        b, *_ = np.linalg.lstsq(X, raw["net"].to_numpy() - cc, rcond=None)
        style = (float(b[1]) - 1.0) * (mm - cc)
        out["terms"][name] = {
            "selection_gross_vs_random": diff(gross, rand_gross),
            "exposure_raw_minus_betamatched": diff(raw, bmatch),
            "sizing_K10_minus_K40": diff(k10, k40),
            "execution_raw_minus_turnovermatched": diff(raw, tmatch),
            "costs_1x_minus_0x": diff(raw, gross),
            "beta_style_contribution": ruler(style, years_of(kk)),
            "realised_beta": round(float(b[1]), 3),
            "timing": "NOT_MEASURED — chunk 6's instrument, not this one",
            "llm": "NOT_MEASURED HERE — see ABLATION-1",
            "net_excess_cagr_pct": round(
                (cagr(raw["net"].to_numpy()) - cagr(mm)) * 100, 3),
        }
        print(f"  {name} done ({time.time()-t0:.0f}s)", flush=True)

    out["wall_seconds"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
