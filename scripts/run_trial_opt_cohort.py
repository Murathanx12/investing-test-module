"""TRIAL-OPT-COHORT — ONE SHOT. Protocol: TRIALS/TRIAL-OPT-COHORT.md (frozen a84e5b1).

Seven arms, each a counted candidate (167-173). Explore 2004-01..2018-12 ONLY.
The confirm window is NOT read here under any outcome — a graduating arm stops
and is flagged, because the confirm read is one-use and spending it is Murat's
explicit authorisation (frozen in the registration).

Deciding cost arms: largemid @ flat 25 bps, small @ KO half-spread. Zero-cost
bound and flat-25 regression guard reported alongside every deciding number
(post-NEG_RESULTS-25 convention).

Graduation (explore, per segment, on the deciding arm):
    t_ic >= 2.0 AND t_excess_gross >= 1.5 AND t_excess_net >= 1.5

Frozen reporting, never deciding: turnover, maxDD, coverage, per-arm null rates
split by VIX tercile, and the always-covered robustness line for any arm whose
high-tercile drop rate exceeds 2x its low-tercile rate.

DSR reported at n_trials = 173.

Usage:  .venv\\Scripts\\python -m scripts.run_trial_opt_cohort
"""

from __future__ import annotations

import glob
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.discipline.overfitting import deflated_sharpe_from_returns
from aegis_brain.factory.explore import ScanConfig, scan_signal, segment_mask
from aegis_brain.factory.optsurf import (ARMS, DIRECTIONS, always_covered_syms,
                                         build_opt_frames, null_rate_by_vix)
from aegis_brain.factory.signals import FactorySignal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("opt_cohort")
OUT = MODULE_ROOT / "data" / "factory"

EXPLORE = ScanConfig()                       # 2004-01..2018-12, frozen
ZERO = ScanConfig(cost_bps_one_way=0.0)

T_IC_MIN, T_GROSS_MIN, T_NET_MIN = 2.0, 1.5, 1.5
N_TRIALS = 173                               # frozen in the registration

DESCRIPTIONS = {
    "iv_atm": "30-day ATM implied volatility (mean of +/-50 delta).",
    "riv_spread": "30-day ATM IV minus trailing 21-day annualised realised vol "
                  "(Alexiou-Rompolis 2021).",
    "skew_25d": "25-delta put IV minus 25-delta call IV, 30-day "
                "(Xing-Zhang-Zhao 2010).",
    "term_slope": "91-day minus 30-day ATM IV (Vasquez 2017, Kim 2020).",
    "os_ratio": "Option volume / stock volume, monthly mean of daily "
                "(Johnson-So 2012).",
    "pc_volume": "Put volume / call volume, monthly mean of daily "
                 "(Pan-Poteshman 2006).",
    "skew_resid": "Residual of skew_25d from a per-month cross-sectional OLS on "
                  "log(mktcap), 21d realised vol, mom_12_1, log(3m dollar vol) "
                  "(Wu-Tian 2023 style, our four regressors frozen).",
}


def bar(s: dict) -> bool:
    return bool(s["t_ic"] >= T_IC_MIN
                and s["t_excess_gross"] >= T_GROSS_MIN
                and s["t_excess_net"] >= T_NET_MIN)


def _t(x: pd.Series) -> float:
    x = x.dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else 0.0


def banked_sr_variance() -> float:
    """H0 Sharpe spread from the banked explore cross-section (precedent:
    scripts/run_confirm_gpsmall.py)."""
    srs = []
    for f in sorted(glob.glob(str(OUT / "batch*_summary.csv"))):
        t = pd.read_csv(f)
        t = t[t["months"] > 0]
        srs.extend((pd.to_numeric(t["t_excess_net"], errors="coerce")
                    / np.sqrt(t["months"])).dropna().tolist())
    return float(np.var(srs, ddof=1))


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    spreads = build_spread_frame(panel)

    frames, diag = build_opt_frames(panel)
    log.info("construction diagnostics: %s", json.dumps(diag, default=str))

    signals = [FactorySignal(a, DESCRIPTIONS[a], (lambda p, f=frames[a]: f),
                             DIRECTIONS[a]) for a in ARMS]

    plan = [
        ("largemid", "flat25", EXPLORE, None, True),
        ("largemid", "zero_cost_bound", ZERO, None, False),
        ("largemid", "ko_half_reported", EXPLORE, spreads, False),
        ("small", "ko_half", EXPLORE, spreads, True),
        ("small", "zero_cost_bound", ZERO, None, False),
        ("small", "flat25_regression_guard", EXPLORE, None, False),
    ]

    rows, monthly_keep = [], {}
    for sig in signals:
        for seg, arm, cfg, frame, deciding in plan:
            r = scan_signal(panel, sig, seg, cfg, cost_frame=frame)
            s = r["summary"]
            s.update({"window": "explore", "cost_arm": arm, "deciding": deciding})
            rows.append(s)
            if deciding:
                monthly_keep[(sig.name, seg)] = r["monthly"]

    ex = pd.DataFrame(rows)
    show = ["signal", "segment", "cost_arm", "deciding", "months",
            "mean_excess_net_bps", "t_excess_net", "t_excess_gross", "t_ic",
            "turnover_1way", "max_dd", "cagr_net"]
    print("\n=== TRIAL-OPT-COHORT — EXPLORE 2004-2018 (one shot) ===")
    print(ex[show].to_string(index=False))

    # ── frozen reporting: drop rates by VIX tercile ─────────────────────────
    masks = {seg: panel.eligible() & segment_mask(panel, seg)
             for seg in ("largemid", "small")}
    nr = null_rate_by_vix(frames, panel, masks)
    print("\n=== drop rate by VIX tercile (frozen reporting requirement) ===")
    print(nr.to_string(index=False))

    # ── frozen robustness line (only for arms that trigger it) ──────────────
    robustness = []
    for _, row in nr[nr["robustness_line_required"]].iterrows():
        arm, seg = row["arm"], row["segment"]
        syms = always_covered_syms(frames[arm], masks[seg])
        if len(syms) < 50:
            robustness.append({"arm": arm, "segment": seg,
                               "note": f"only {len(syms)} always-covered names"})
            continue
        sub = frames[arm].reindex(columns=syms)
        sig = FactorySignal(f"{arm}_alwayscov", DESCRIPTIONS[arm],
                            (lambda p, f=sub: f.reindex(columns=p.monthly_ret.columns)),
                            DIRECTIONS[arm])
        s = scan_signal(panel, sig, seg, EXPLORE)["summary"]
        robustness.append({"arm": arm, "segment": seg, "n_names": len(syms),
                           "ic_mean": s["ic_mean"], "t_ic": s["t_ic"]})
    if robustness:
        print("\n=== always-covered robustness line (never deciding) ===")
        print(pd.DataFrame(robustness).to_string(index=False))
    else:
        print("\n=== robustness line: NOT TRIGGERED for any arm "
              "(no high/low drop ratio above 2.0) ===")

    # ── graduation on the deciding arms only ────────────────────────────────
    grads = []
    for name in ARMS:
        for seg, arm in (("largemid", "flat25"), ("small", "ko_half")):
            row = ex[(ex["signal"] == name) & (ex["segment"] == seg)
                     & (ex["cost_arm"] == arm)]
            if len(row) and bar(row.iloc[0].to_dict()):
                grads.append({"signal": name, "segment": seg, "cost_arm": arm})
    print("\nGRADUATES (deciding arms):",
          [(g["signal"], g["segment"]) for g in grads] or "NONE")

    # ── DSR at n_trials = 173, on the deciding arms ─────────────────────────
    sr_var = banked_sr_variance()
    dsr = []
    for (name, seg), m in monthly_keep.items():
        rep = deflated_sharpe_from_returns(
            m["excess_net"].dropna().values, n_trials=N_TRIALS, sr_variance=sr_var)
        dsr.append({"signal": name, "segment": seg, **rep})
    print(f"\n=== DSR at n_trials={N_TRIALS} (sr_variance={sr_var:.6f}) ===")
    print(pd.DataFrame(dsr)[["signal", "segment", "observed_sharpe",
                             "expected_max_sharpe_h0", "psr", "dsr"]]
          .to_string(index=False))

    if grads:
        verdict = ("EXPLORE GRADUATE(S) — STOPPED BEFORE CONFIRM. The confirm "
                   "read is one-use and needs Murat's explicit authorisation.")
    else:
        verdict = ("NO EXPLORE GRADUATE — all seven arms rejected; the "
                   "option-implied cross-sectional family CLOSES (level, spread, "
                   "skew, term structure, flow and residual all covered).")
    print("\nVERDICT:", verdict)

    results = {
        "trial": "TRIAL-OPT-COHORT",
        "protocol_commit": "a84e5b1",
        "candidates": list(range(167, 174)),
        "window": "explore 2004-01..2018-12 (confirm NOT read)",
        "construction_diagnostics": diag,
        "explore_runs": rows,
        "null_rate_by_vix": nr.to_dict("records"),
        "robustness_line": robustness,
        "dsr": dsr,
        "sr_variance_banked": round(sr_var, 6),
        "graduates": grads,
        "confirm_runs": [],
        "verdict": verdict,
    }
    (OUT / "trial_opt_cohort.json").write_text(
        json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
