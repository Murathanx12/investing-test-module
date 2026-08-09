"""T3 — what each gate can and cannot see, computed rather than asserted.

The standard states t-bars per gate and never states the EFFECT SIZE each bar
corresponds to at the sample size the gate actually gets. That is how a gate
becomes decoration: it either always binds or never can. Two gates were singled
out by external review and both charges check out arithmetically:

  G2 (the 24-month one-shot holdout) is low-powered enough that a binary
  pass/fail read would kill a TRUE strategy a large fraction of the time — and
  the adverse regime is known IN ADVANCE, which makes an irreversible binary
  read indefensible.

  G9 (positive excess in >= 4 of 5 sub-samples) is calibrated to pass large
  effects; its false-negative rate against a true +2.5 %/yr effect is large and
  has never been printed.

This script prints both, from the strategy's own realized series, and saves the
monthly book so no later stage has to re-run it.
"""
from __future__ import annotations

import json
import logging
import sys
from itertools import combinations
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.WARNING)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "PF4"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"

HOLDOUT_MONTHS = 24
# The pre-stated hypotheses the graded read compares. Frozen here, before the
# holdout is read, and unchangeable afterwards.
H_NULL = 0.0
H_PRODUCT = 0.03
H_CLAIM = 0.0467
# The regime headwind disclosed in the dossier: a mega-cap-led tape is adverse
# to an equal-weight small-cap book by roughly this much per year.
KNOWN_HEADWIND = 0.03


def main() -> int:
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = tuple(d.get("tags", ()))
    spec = StrategySpec(**d)

    f = Factory()
    elig = f.eligible(spec.segment)
    score, _ = composite_score(f.lib, spec.signals, elig)
    out = run_book(f.spine.panel, score, elig, spec, f.spine.rf)
    net = out["monthly"]["net"].dropna()
    bench = f.spine.mkt.reindex(net.index)
    ex = (net - bench).dropna()
    pd.DataFrame({"net": net, "gross": out["monthly"]["gross"].reindex(net.index),
                  "bench": bench}).to_csv(OUT / "base_monthly.csv")

    te_ann = float(ex.std(ddof=1) * np.sqrt(12))
    se_24 = te_ann / np.sqrt(HOLDOUT_MONTHS / 12.0)

    def p_pass(true_excess: float, bar: float) -> float:
        return float(1 - stats.norm.cdf((bar - true_excess) / se_24))

    g2 = {
        "gate": "G2 — one-shot 24-month holdout (2023-01..2024-12)",
        "tracking_error_annual_from_full_history": round(te_ann, 4),
        "standard_error_of_24m_annualized_excess": round(se_24, 4),
        "mde_at_80pct_power_two_sided": round(2.80 * se_24, 4),
        "binary_gate_pass_probabilities": {
            "true_+4.67pct_vs_bar_0": round(p_pass(H_CLAIM, 0.0), 3),
            "true_+4.67pct_vs_bar_+3pct": round(p_pass(H_CLAIM, H_PRODUCT), 3),
            "true_+4.67pct_minus_headwind_vs_bar_0": round(
                p_pass(H_CLAIM - KNOWN_HEADWIND, 0.0), 3),
            "true_+4.67pct_minus_headwind_vs_bar_+3pct": round(
                p_pass(H_CLAIM - KNOWN_HEADWIND, H_PRODUCT), 3)},
        "reading": ("a binary read of this gate discards a TRUE strategy with "
                    "probability 1 minus each number above. The regime headwind "
                    "is known in advance, which makes an irreversible binary "
                    "read on 24 months a coin flip dressed as rigour."),
    }

    # G9: positive excess in >= 4 of 5 sub-samples. Each sub-sample gets about a
    # fifth of the months, so each has about sqrt(5) times the standard error.
    n5 = len(ex) // 5
    se_block = te_ann / np.sqrt(n5 / 12.0)
    g9 = {"gate": "G9 — positive net excess in >= 4 of 5 sub-samples",
          "months_per_block": n5,
          "standard_error_per_block_annualized": round(se_block, 4),
          "false_negative_rate": {}}
    for true_ex in (0.0467, 0.03, 0.025, 0.02, 0.01):
        p1 = float(1 - stats.norm.cdf((0.0 - true_ex) / se_block))
        p_pass_gate = sum(comb(5, k) * p1 ** k * (1 - p1) ** (5 - k)
                          for k in (4, 5))
        g9["false_negative_rate"][f"true_{true_ex:+.2%}"] = {
            "p_block_positive": round(p1, 3),
            "p_gate_passes": round(p_pass_gate, 3),
            "false_negative_rate": round(1 - p_pass_gate, 3)}
    g9["reading"] = ("G9 is calibrated to pass large effects. Against a true "
                     "+2.5%/yr it rejects a real strategy at the rate printed "
                     "above. That is defensible if stated and misleading if not.")

    # Which gate actually binds? Report the effect size each bar corresponds to.
    binding = {
        "G1_excess_cagr_bar_+3pct": {
            "observed": banked["headline"]["excess_cagr_net"],
            "slack": round(banked["headline"]["excess_cagr_net"] - 0.03, 4)},
        "t_bar_2.0_on_full_history": {
            "observed_nw": banked["headline"]["t_excess_newey_west"],
            "effect_size_the_bar_implies": round(2.0 * te_ann
                                                 / np.sqrt(len(ex) / 12.0), 4)},
        "harvey_liu_zhu_t_3.0_new_factor_bar": {
            "excess_t_nw": banked["headline"]["t_excess_newey_west"],
            "clears_on_excess": bool(
                (banked["headline"]["t_excess_newey_west"] or 0) > 3.0),
            "ff5_umd_alpha_t": banked["factor_alpha"]["ff5_umd"]["t_alpha"],
            "clears_on_alpha": bool(
                banked["factor_alpha"]["ff5_umd"]["t_alpha"] > 3.0),
            "note": ("the verdict must say which statistic it stands on. The "
                     "excess-return t does NOT clear the HLZ bar for a newly "
                     "claimed factor; the alpha t does — and only if the "
                     "EW-universe control does not absorb it.")},
    }

    res = {"trial": "TRIAL-PF4-DECOMPOSITION-1", "component": "gate power",
           "strategy": spec.name, "months": len(ex),
           "G2": g2, "G9": g9, "binding_gate_analysis": binding}
    (OUT / "GATE_POWER.json").write_text(json.dumps(res, indent=2),
                                         encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
