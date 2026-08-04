"""Stage 0 — seam audit + cost measurement (design §6, half a session).

Deliverables:
  1. Production-constants assertion passes (the §4.1 guard works).
  2. Timing table: scan_signal cost on the real cached CRSP panel, raw and
     with the §4.4 column-subset optimization, projected per-rep cost.
  3. sigma_hat: monthly vol of a NULL decile book's excess return — measured
     by scanning random-score signals through the production mechanics.
     Feeds the k = mu_m / 0.9 injection mapping (§3.2).
  4. Panel-substitution proof: a constructed Panel (perturbed returns) runs
     end-to-end through scan_signal and the output responds to the returns.

Kill criterion (pre-registered): one rep (40 scans) > 10 s after
optimizations -> the 1k grid is unaffordable; descope to n=250 (stated) or
fall back to DGP-B for the FDR alone.

Run:  .venv/Scripts/python.exe -m aegis_brain.calibration.stage0_seam
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from aegis_brain.calibration.config import (
    MAX_SECONDS_PER_REP,
    PRODUCTION,
    REAL_PANEL_DIR,
    RUNS_DIR,
    SEED_BASE,
    assert_production_constants,
)
from aegis_brain.data.eodhd_panel import Panel, load_cached_panel
from aegis_brain.factory.batch1_price import BATCH1
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.signals import FactorySignal


def subset_panel_to_eligible(panel: Panel) -> Panel:
    """§4.4 lever (a): drop columns never eligible in the scan window.

    Eligibility is formation-month information only, so this cannot change
    any scan output — asserted in main() by comparing summaries.
    """
    cfg = ScanConfig()
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    elig = panel.eligible()
    window = elig.loc[(elig.index >= lo - pd.DateOffset(months=1)) & (elig.index <= hi)]
    keep = window.columns[window.any(axis=0)]
    # float64 cast: the parquet loads as nullable dtypes whose .to_numpy() is
    # object — np.isnan and lstsq choke on it downstream, and plain float64
    # is also what the scan loop was profiled on.
    return Panel(
        monthly_ret=panel.monthly_ret[keep].astype("float64"),
        month_end_price=panel.month_end_price[keep].astype("float64"),
        monthly_dollar_vol=panel.monthly_dollar_vol[keep].astype("float64"),
        delist_month={s: m for s, m in panel.delist_month.items() if s in set(keep)},
    )


def random_signal(seed: int) -> FactorySignal:
    """A seeded pure-noise score — the null book generator for sigma_hat."""
    def compute(panel: Panel) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        return pd.DataFrame(
            rng.standard_normal(panel.monthly_ret.shape),
            index=panel.monthly_ret.index,
            columns=panel.monthly_ret.columns,
        )
    return FactorySignal(
        name=f"null_random_{seed}", hypothesis="stage-0 sigma_hat probe",
        compute=compute, direction=+1,
    )


def main() -> dict:
    t_start = time.time()
    print("STAGE 0 — seam audit + cost measurement")
    print("=" * 70)

    # 1 — the §4.1 guard
    assert_production_constants()
    print("1. production-constants assertion: PASS")

    # 2 — load + timing
    panel = load_cached_panel(REAL_PANEL_DIR)
    n_months, n_syms = panel.monthly_ret.shape
    print(f"   panel: {n_months} months x {n_syms:,} symbols")

    sub = subset_panel_to_eligible(panel)
    print(f"   eligible-subset panel: {sub.monthly_ret.shape[1]:,} symbols "
          f"(dropped {n_syms - sub.monthly_ret.shape[1]:,} never-eligible)")

    timing_signals = ["mom_6_1", "seasonality", "amihud_3m", "vol_12m_low"]
    sig_by_name = {s.name: s for s in BATCH1}
    rows = []
    baseline_summary = {}
    for name in timing_signals:
        sig = sig_by_name[name]
        for label, pnl in (("full", panel), ("subset", sub)):
            t0 = time.time()
            out = scan_signal(pnl, sig, "largemid")
            dt = time.time() - t0
            rows.append({"signal": name, "panel": label, "seconds": round(dt, 2),
                         "months": out["summary"]["months"]})
            if label == "full":
                baseline_summary[name] = out["summary"]
            else:
                # the optimization must be a no-op on results
                same = out["summary"] == baseline_summary[name]
                if not same:
                    raise RuntimeError(
                        f"column-subset changed scan output for {name}: "
                        f"{out['summary']} vs {baseline_summary[name]}"
                    )
    timing = pd.DataFrame(rows)
    print("2. timing (largemid, production ScanConfig):")
    print(timing.to_string(index=False))
    mean_subset = timing[timing.panel == "subset"]["seconds"].mean()
    per_rep_40 = mean_subset * 40
    per_rep_20 = mean_subset * 20  # largemid-only headline lever (§4.4c)
    print(f"   mean subset scan: {mean_subset:.2f}s -> per rep: "
          f"{per_rep_40:.1f}s (40 scans) / {per_rep_20:.1f}s (largemid-only 20)")

    # 3 — sigma_hat from null decile books
    sigmas = []
    for k in range(3):
        out = scan_signal(sub, random_signal(SEED_BASE + k), "largemid")
        sigmas.append(float(out["monthly"]["excess_net"].std(ddof=1)))
    sigma_hat = float(np.mean(sigmas))
    print(f"3. sigma_hat (null decile-book excess vol): {sigma_hat*100:.2f}%/mo "
          f"(3 seeds: {[f'{s*100:.2f}' for s in sigmas]})")

    # 4 — panel-substitution proof
    rng = np.random.default_rng(SEED_BASE)
    perturbed = Panel(
        monthly_ret=sub.monthly_ret + rng.normal(0, 1e-4, sub.monthly_ret.shape),
        month_end_price=sub.month_end_price.copy(),
        monthly_dollar_vol=sub.monthly_dollar_vol.copy(),
        delist_month=dict(sub.delist_month),
    )
    ref = scan_signal(sub, sig_by_name["mom_6_1"], "largemid")["summary"]
    alt = scan_signal(perturbed, sig_by_name["mom_6_1"], "largemid")["summary"]
    if alt == ref:
        raise RuntimeError(
            "perturbed panel produced byte-identical scan output — the seam "
            "is not actually consuming the constructed returns"
        )
    print("4. panel-substitution proof: constructed Panel runs end-to-end and "
          "output responds to returns — PASS")

    verdict = "AFFORDABLE" if per_rep_40 <= MAX_SECONDS_PER_REP else (
        "HEADLINE-AFFORDABLE (largemid-only)" if per_rep_20 <= MAX_SECONDS_PER_REP
        else "UNAFFORDABLE — registered descope applies (n=250, stated)"
    )
    print("=" * 70)
    print(f"STAGE 0 VERDICT vs {MAX_SECONDS_PER_REP:.0f}s/rep kill line: {verdict}")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "stage": 0,
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "panel_shape": [n_months, n_syms],
        "eligible_subset_symbols": int(sub.monthly_ret.shape[1]),
        "timing": timing.to_dict(orient="records"),
        "seconds_per_rep_40scans": round(per_rep_40, 1),
        "seconds_per_rep_largemid20": round(per_rep_20, 1),
        "sigma_hat_monthly": sigma_hat,
        "sigma_hat_seeds": sigmas,
        "verdict": verdict,
        "production": PRODUCTION.__dict__,
        "wall_seconds": round(time.time() - t_start, 1),
    }
    out_path = RUNS_DIR / "stage0_seam.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"report -> {out_path}")
    return report


if __name__ == "__main__":
    main()
