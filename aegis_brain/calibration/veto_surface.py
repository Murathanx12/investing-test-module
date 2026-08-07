"""REPLAY-2 §3 — the correlation-surface veto diagnostic (pre-registered).

Question: does a signal's correlation with the sigma-family axes (12m vol,
price level), measured on the REAL panel over the explore window, predict its
simulator family-null p95? If R² >= 0.7, the replay's veto is indexed by the
correlation surface (a candidate's bar = max(semantic-family p95,
empirical-neighbor p95)). If not, the veto reverts to a flat real-data floor
for every candidate (PREREG_REPLAY_2.md §3).

The 20 batch-1 signals are the calibration set: their null p95s are measured
(bank a0.0/base, n=1250 reps) and their real-panel correlations are computable
without touching any confirm window or any of the 179 candidates' rows.

Run:  python -m aegis_brain.calibration.veto_surface --tag r1
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from aegis_brain.calibration.bank import load_bank
from aegis_brain.calibration.config import REAL_PANEL_DIR, RUNS_DIR
from aegis_brain.calibration.stage0_seam import subset_panel_to_eligible
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.batch1_price import BATCH1
from aegis_brain.factory.explore import ScanConfig, segment_mask

SIGMA_AXES = ("vol_12m_low", "price_level")
R2_SHIP_GATE = 0.70
MIN_NAMES = 100


def null_p95_from_bank(reps: list[dict]) -> dict[tuple[str, str], float]:
    """Per-(signal, segment) p95 of explore t_ic in the a0.0/base cell."""
    samples: dict[tuple[str, str], list[float]] = {}
    for r in reps:
        cell = r["cells"].get("a0.0/base")
        if cell is None:
            continue
        for seg in ("largemid", "small"):
            for name, stat in cell["explore"][seg].items():
                samples.setdefault((name, seg), []).append(stat["t_ic"])
    if not samples:
        raise SystemExit("no a0.0/base cells in the bank — wrong tag?")
    return {k: float(np.percentile(np.array(v), 95.0))
            for k, v in samples.items()}


def mean_abs_spearman(score: pd.DataFrame, axis_score: pd.DataFrame,
                      elig: pd.DataFrame, months: list[pd.Timestamp]) -> float:
    """Mean |cross-sectional Spearman| of score vs axis over formation months,
    among that month's eligible names. NaN months (<MIN_NAMES) are skipped."""
    rhos = []
    for m in months:
        e = elig.loc[m]
        idx = e[e].index
        s = score.loc[m].reindex(idx).dropna()
        a = axis_score.loc[m].reindex(s.index).dropna()
        s = s.reindex(a.index)
        if len(s) < MIN_NAMES:
            continue
        rho = s.rank().corr(a.rank())
        if np.isfinite(rho):
            rhos.append(abs(float(rho)))
    if not rhos:
        raise RuntimeError("no valid months for correlation — panel problem")
    return float(np.mean(rhos))


def ols_r2(y: np.ndarray, X: np.ndarray) -> float:
    """R² of y on [1, X]."""
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ beta
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="r1")
    args = ap.parse_args()

    reps = load_bank(args.tag, "all")
    p95 = null_p95_from_bank(reps)
    n_base = sum(1 for r in reps if "a0.0/base" in r["cells"])
    print(f"bank: {n_base} a0.0/base reps -> p95 table for "
          f"{len(p95)} (signal, segment) pairs")

    panel = subset_panel_to_eligible(load_cached_panel(REAL_PANEL_DIR))
    cfg = ScanConfig()
    months_all = panel.monthly_ret.index
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    # formation months = month before each test month, explore window only
    form = [months_all[months_all.get_loc(m) - 1]
            for m in months_all if lo <= m <= hi and months_all.get_loc(m) > 0]

    sigs = {s.name: s for s in BATCH1}
    scores = {name: sig.compute(panel) for name, sig in sigs.items()}
    axes = {a: scores[a] for a in SIGMA_AXES}
    base_elig = panel.eligible()

    rows = []
    for seg in ("largemid", "small"):
        elig = base_elig & segment_mask(panel, seg)
        for name in sigs:
            feats = {f"abs_rho_{a}": (1.0 if name == a else mean_abs_spearman(
                scores[name], axes[a], elig, form)) for a in SIGMA_AXES}
            rows.append({"signal": name, "segment": seg,
                         "p95_null_t_ic": round(p95[(name, seg)], 3),
                         **{k: round(v, 4) for k, v in feats.items()}})
    df = pd.DataFrame(rows)

    result: dict = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tag": args.tag, "n_base_reps": n_base,
        "ship_gate_r2": R2_SHIP_GATE, "rows": df.to_dict("records"),
    }
    print(df.to_string(index=False))

    verdicts = {}
    for scope, sub in (("largemid", df[df.segment == "largemid"]),
                       ("small", df[df.segment == "small"]),
                       ("pooled", df)):
        y = sub["p95_null_t_ic"].to_numpy(dtype=float)
        x1 = sub["abs_rho_vol_12m_low"].to_numpy(dtype=float)
        x2 = sub[["abs_rho_vol_12m_low",
                  "abs_rho_price_level"]].to_numpy(dtype=float)
        verdicts[scope] = {"r2_vol": round(ols_r2(y, x1[:, None]), 4),
                           "r2_vol_price": round(ols_r2(y, x2), 4),
                           "n": int(len(sub))}
    result["r2"] = verdicts

    # the pre-registered gate reads the segment surfaces, not the pooled fit:
    # the replay applies the veto within a candidate's own segment
    gate_pass = all(v["r2_vol_price"] >= R2_SHIP_GATE
                    for k, v in verdicts.items() if k != "pooled")
    result["verdict"] = ("CORRELATION-INDEXED VETO SHIPS" if gate_pass
                         else "GATE FAILED -> FLAT REAL-DATA FLOOR")
    print(json.dumps(verdicts, indent=2))
    print("VERDICT:", result["verdict"])

    out_dir = RUNS_DIR.parent / "REPLAY-2"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "veto_surface.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"written -> {out}")


if __name__ == "__main__":
    main()
