"""TRIAL-BRAIN-000-baseline — one execution, results final.

Run spec frozen in TRIALS/TRIAL-BRAIN-000-baseline.md BEFORE this ran.
Arms: A = noise control (expected null), B = GKX big-three PRICE_SIGNALS.
Each arm runs full-universe and largest-500 (survivorship bound).

Usage:
    .venv\\Scripts\\python -m scripts.run_trial_000
Output:
    runs/TRIAL-BRAIN-000/results.json  (+ per-arm monthly CSVs)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.gate.adoption import evaluate_candidate, survivorship_bound
from aegis_brain.harness.runner import WalkForwardConfig, run_walk_forward
from aegis_brain.signals.base import Signal
from aegis_brain.signals.price_signals import PRICE_SIGNALS

OUT = MODULE_ROOT / "runs" / "TRIAL-BRAIN-000"
PANEL_CACHE = MODULE_ROOT / "data" / "panel_2017"

BASE_CFG = dict(
    min_train_months=24, refit_every=3, top_frac=0.10, long_short=False,
    cost_bps_one_way=25.0, ranker_kind="gbm", min_names_per_month=50,
)


def noise_signal(seed: int = 12345) -> Signal:
    rng = np.random.default_rng(seed)

    def compute(panel):
        return pd.DataFrame(
            rng.normal(size=panel.monthly_ret.shape),
            index=panel.monthly_ret.index, columns=panel.monthly_ret.columns,
        )

    return Signal("noise_control", "Arm A: pure noise — expected null", compute)


def main() -> None:
    t0 = time.time()
    panel = load_cached_panel(PANEL_CACHE)
    print(f"panel: {panel.monthly_ret.shape[1]} symbols x {panel.monthly_ret.shape[0]} months", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)

    runs: dict[str, dict] = {}
    specs = {
        "armA_full": (dict(BASE_CFG), [noise_signal()]),
        "armB_full": (dict(BASE_CFG), PRICE_SIGNALS),
        "armA_500": (dict(BASE_CFG, largest_n_by_dollar_vol=500,
                          restrict_training_to_eligible=True), [noise_signal()]),
        "armB_500": (dict(BASE_CFG, largest_n_by_dollar_vol=500,
                          restrict_training_to_eligible=True), PRICE_SIGNALS),
    }
    for name, (cfg_kw, signals) in specs.items():
        print(f"--- {name} ---", flush=True)
        out = run_walk_forward(panel, signals, WalkForwardConfig(**cfg_kw))
        out["monthly"].to_csv(OUT / f"{name}_monthly.csv")
        runs[name] = out
        print(json.dumps(out["summary"], indent=2), flush=True)

    gate_b = evaluate_candidate(runs["armB_full"]["monthly"]["net"].values)
    bound = survivorship_bound(runs["armB_full"], runs["armB_500"])

    results = {
        "trial": "TRIAL-BRAIN-000-baseline",
        "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summaries": {k: v["summary"] for k, v in runs.items()},
        "gate_armB_full": gate_b,
        "survivorship_bound": bound,
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2), flush=True)


if __name__ == "__main__":
    main()
