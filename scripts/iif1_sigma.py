"""INTERNET-INVESTIGATOR-FWD-1 — measure `sigma_pi`, don't assume it.

    python -m scripts.iif1_sigma

WHY
===
`iif1_power.py` says the whole trial hinges on one number: `sigma_pi`, the
standard deviation of the TRUE probability of the graded event around its base
rate. At `sigma_pi = 0.02` the trial is never detectable at any trigger count or
effect size; at `0.10-0.15` it resolves in 40-90 nights. Choosing the observable
is therefore a POWER decision, and the honest way to make it is to measure how
much true-probability variation each candidate observable actually has.

WHAT IS MEASURED, AND WHY IT IS A LOWER BOUND
---------------------------------------------
`sigma_pi` is not directly observable — the true probability is never seen. But
it is bounded below by the dispersion of the REALISED rate across buckets formed
on information available beforehand: if conditioning on a point-in-time
covariate already moves the realised rate from 0.15 to 0.60, then the true
probability varies at least that much.

The bound is taken against BINOMIAL NOISE, which is the trap here. With `n` days
in a bucket the realised rate wobbles by `sqrt(p(1-p)/n)` even if the true
probability is constant, so raw dispersion across buckets OVERSTATES
`sigma_pi`. The variance decomposition below subtracts that sampling term:

    Var(realised rate across buckets) = Var(true prob) + E[p(1-p)/n]
    sigma_pi^2 >= Var(realised) - E[p(1-p)/n]

Reported as `sigma_pi_lower_bound`. It is a lower bound in the other direction
too: an investigator with a filing calendar knows things no trailing-volatility
bucket does, so the achievable variation is larger than what this measures.

WHAT THIS DOES NOT DO
---------------------
It does not say the LLM can capture any of this. It sizes the BUDGET both arms
compete over. Arm A (the engineered numerical snapshot) already carries trailing
volatility and options data, so it should capture much of what is measured here;
what the trial is trying to see is the part left over. That distinction is
stated in the pre-registration rather than blurred.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT              # noqa: E402

PANELF = MODULE_ROOT / "data" / "factory" / "wg1_panel.npz"
OUT = MODULE_ROOT / "runs" / "INTERNET-INVESTIGATOR-FWD-1"

#: Candidate observables, as (name, horizon in trading days, threshold).
#: Thresholds are chosen so the unconditional base rate lands in a gradeable
#: band rather than at 0.02 or 0.98 — an observable that almost never fires
#: carries no information no matter how well it is forecast.
CANDIDATES = (
    ("abs_move_exceeds_3pct_1d", 1, 0.03),
    ("abs_move_exceeds_5pct_1d", 1, 0.05),
    ("abs_move_exceeds_5pct_5d", 5, 0.05),
    ("abs_move_exceeds_8pct_5d", 5, 0.08),
    ("return_sign_1d", 1, None),
    ("return_sign_5d", 5, None),
)

#: Buckets are formed on TRAILING information only: the realised volatility of
#: the previous 20 trading days, in deciles, computed per name per day.
TRAIL_VOL_DAYS = 20
N_BUCKETS = 10
MIN_BUCKET_OBS = 500
SEED = 20260814

#: Sub-sample so this stays a minutes-long diagnostic rather than an hour.
MAX_NAMES = 400
MAX_DAYS = 2500


def sigma_lower_bound(hit: np.ndarray, bucket: np.ndarray) -> dict:
    """Var(true prob) >= Var(realised rate) - E[binomial sampling variance]."""
    rows = []
    for b in np.unique(bucket):
        m = bucket == b
        n = int(m.sum())
        if n < MIN_BUCKET_OBS:
            continue
        p = float(hit[m].mean())
        rows.append({"bucket": int(b), "n": n, "rate": p,
                     "sampling_var": p * (1.0 - p) / n})
    if len(rows) < 3:
        return {"error": f"only {len(rows)} usable buckets"}
    r = pd.DataFrame(rows)
    var_observed = float(r["rate"].var(ddof=1))
    var_sampling = float(r["sampling_var"].mean())
    var_true = max(var_observed - var_sampling, 0.0)
    return {
        "n_buckets": len(r), "n_obs": int(r["n"].sum()),
        "base_rate": float(np.average(r["rate"], weights=r["n"])),
        "rate_min": float(r["rate"].min()), "rate_max": float(r["rate"].max()),
        "var_observed": var_observed, "var_sampling_noise": var_sampling,
        "sigma_pi_lower_bound": float(np.sqrt(var_true)),
        "brier_ceiling_lower_bound": var_true,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    z = np.load(PANELF, allow_pickle=False)
    dates = pd.DatetimeIndex(z["dates"].astype("datetime64[ns]"))
    RET = z["RET"].astype(np.float64)
    MCAP = z["MCAP"].astype(np.float64)

    # Most-recent slice, and the largest names on the last day with data —
    # the population a live trigger would actually fire on.
    RET = RET[-MAX_DAYS:]
    MCAP = MCAP[-MAX_DAYS:]
    dates = dates[-MAX_DAYS:]
    last = np.nan_to_num(MCAP[-1], nan=-1.0)
    cols = np.argsort(-last)[:MAX_NAMES]
    R = RET[:, cols]
    print(f"panel {R.shape}  {dates[0].date()}..{dates[-1].date()}", flush=True)

    # trailing realised vol, strictly before the graded window
    df = pd.DataFrame(R)
    trail = df.rolling(TRAIL_VOL_DAYS).std().shift(1).to_numpy()

    report = {"panel": {"n_days": int(R.shape[0]), "n_names": int(R.shape[1]),
                        "first": str(dates[0].date()),
                        "last": str(dates[-1].date()),
                        "trail_vol_days": TRAIL_VOL_DAYS,
                        "n_buckets": N_BUCKETS},
              "observables": {}}

    print(f"\n{'observable':<28s} {'base':>7s} {'rate range':>16s} "
          f"{'sigma_pi(LB)':>13s} {'Brier ceil':>11s} {'n':>10s}")
    print("-" * 92)
    for name, h, thr in CANDIDATES:
        # forward h-day cumulative return, aligned so row t is (t, t+h]
        fwd = (pd.DataFrame(R).rolling(h).sum().shift(-h)).to_numpy()
        hit = (np.abs(fwd) > thr) if thr is not None else (fwd > 0)
        ok = np.isfinite(fwd) & np.isfinite(trail)
        hv = hit[ok].astype(float)
        tv = trail[ok]
        # deciles of trailing vol, computed on the pooled sample
        q = np.quantile(tv, np.linspace(0, 1, N_BUCKETS + 1)[1:-1])
        bucket = np.searchsorted(q, tv)
        res = sigma_lower_bound(hv, bucket)
        report["observables"][name] = {
            "horizon_days": h, "threshold": thr, **res}
        if "error" in res:
            print(f"{name:<28s} {res['error']}")
            continue
        print(f"{name:<28s} {res['base_rate']:>7.3f} "
              f"{res['rate_min']:>7.3f}-{res['rate_max']:<8.3f} "
              f"{res['sigma_pi_lower_bound']:>13.4f} "
              f"{res['brier_ceiling_lower_bound']:>11.5f} "
              f"{res['n_obs']:>10,d}")

    del rng
    (OUT / "sigma_pi.json").write_text(json.dumps(report, indent=2),
                                       encoding="utf-8")
    print(f"\nwrote {OUT / 'sigma_pi.json'}")
    print("\nRead: `sigma_pi(LB)` is the BUDGET both arms compete over, bounded "
          "below and measured from trailing volatility alone. An observable "
          "whose bound is near 0.02 cannot be the primary — the power table "
          "says it never resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
