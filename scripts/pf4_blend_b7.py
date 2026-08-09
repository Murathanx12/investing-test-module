"""B7 — the blend NIGHT-3 never tested. Zero new LLM calls.

NIGHT-3 reported that the LLM's ordering is orthogonal to the engine's (mean
Spearman 0.014 over 204 months) and then treated the arms as competitors. Two
deciders whose REALIZED RETURNS are imperfectly correlated combine to a higher
information ratio even when neither beats the other - "no better than" is not
"adds nothing". The rank correlation is not the relevant statistic for that
question; the return correlation is, and it was never printed.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aegis_brain.config import MODULE_ROOT
from aegis_brain.harness.benchmark import newey_west_tstat
from aegis_brain.pf.panel63 import annualize, max_drawdown

RUN = MODULE_ROOT / "runs" / "NIGHT3"

def nw(x):
    r = newey_west_tstat(pd.Series(x).dropna(), lags=12)
    return None if r.get("t") is None else round(float(r["t"]), 2)

def stat(s, b):
    ex = (s - b).dropna()
    return {"cagr": round(annualize(s.dropna()), 4),
            "excess_cagr": round(annualize(s.dropna()) - annualize(b.dropna()), 4),
            "t_excess_nw": nw(ex),
            "ann_vol": round(float(s.std(ddof=1) * np.sqrt(12)), 4),
            "tracking_error": round(float(ex.std(ddof=1) * np.sqrt(12)), 4),
            "information_ratio": round(float(ex.mean() / ex.std(ddof=1) * np.sqrt(12)), 3),
            "max_drawdown": round(max_drawdown(s.dropna()), 4)}

def main() -> int:
    a = pd.read_csv(RUN / "arm_monthly_returns.csv", index_col=0, parse_dates=True)
    esh = pd.read_csv(RUN / "arm_Eshuffled_monthly.csv", index_col=0,
                      parse_dates=True).iloc[:, 0].rename("E_SHUF")
    a = a.join(esh)
    b = a["benchmark"]
    arms = [c for c in a.columns if c != "benchmark"]

    res = {"diagnostic": "DIAG-PF4-B7-BLEND-1", "is_gate": False,
           "source": "cached NIGHT-3 monthly arm returns; no new LLM calls",
           "n_months": int(len(a)),
           "why": "NIGHT-3 reported rank correlation 0.014 and never reported "
                  "the RETURN correlation or the combination."}
    res["standalone"] = {c: stat(a[c], b) for c in arms}
    ex = a[arms].sub(b, axis=0)
    res["correlation_of_returns"] = {
        "levels": json.loads(a[arms].corr().round(3).to_json()),
        "excess_over_benchmark": json.loads(ex.corr().round(3).to_json())}

    blends = {}
    for w in (0.25, 0.5, 0.75):
        for llm in ("A", "E"):
            s = w * a["ENGINE"] + (1 - w) * a[llm]
            blends[f"{int(w*100)}ENGINE_{int((1-w)*100)}{llm}"] = stat(s, b)
    res["blends"] = blends
    res["_cost_caveat"] = (
        "blend returns are combinations of the arms' own NET series. A real "
        "blended book would trade the UNION of two name lists and pay costs on "
        "it, so these are an upper bound on a blend's net return - the blend "
        "gets each arm's costs but not the cost of holding both.")
    best = max(blends.items(), key=lambda kv: kv[1]["information_ratio"])
    res["read"] = {
        "best_blend_by_IR": best[0], "best_IR": best[1]["information_ratio"],
        "engine_IR": res["standalone"]["ENGINE"]["information_ratio"],
        "A_IR": res["standalone"]["A"]["information_ratio"],
        "beats_both_standalone_IRs": bool(
            best[1]["information_ratio"] > max(
                res["standalone"]["ENGINE"]["information_ratio"],
                res["standalone"]["A"]["information_ratio"],
                res["standalone"]["E"]["information_ratio"]))}
    (RUN / "B7_BLEND.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
