"""Orchestration: spec in → scorecard on disk.

One process can run many specs; the expensive objects (63-year panel, OSAP
grids, KO cost frame) are built once and shared. Every run writes:

    runs/PF/<name>__<spec_hash>.json     full scorecard + controls
    runs/PF/<name>__<spec_hash>.md       the one-page receipt

Write-once: an existing artifact for the same spec hash is NOT overwritten.
Re-running a spec you already ran is either a no-op or a new spec.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.harness.benchmark import load_ff_factors
from aegis_brain.pf import controls as ctrl
from aegis_brain.pf.blend import blend_monthly
from aegis_brain.pf.engine import buy_and_hold_universe, run_book
from aegis_brain.pf.panel63 import Spine, eligibility, load_spine
from aegis_brain.pf.regimes import trailing_12m_risk_on
from aegis_brain.pf.scorecard import scorecard
from aegis_brain.pf.signals import SignalLibrary, composite_score
from aegis_brain.pf.spec import StrategySpec

logger = logging.getLogger(__name__)
OUT_DIR = MODULE_ROOT / "runs" / "PF"


class Factory:
    """Shared context for a campaign of strategy runs."""

    def __init__(self, first: str = "1963-07-31", last: str = "2022-12-31",
                 *, allow_holdout: bool = False,
                 out_dir: Path | None = None) -> None:
        t0 = time.time()
        self.out_dir = out_dir or OUT_DIR
        self.spine: Spine = load_spine(first, last, allow_holdout=allow_holdout)
        self.lib = SignalLibrary(self.spine.panel)
        self.factors = load_ff_factors(MODULE_ROOT / "data")
        self._elig: dict[str, pd.DataFrame] = {}
        self._ew: dict[str, pd.Series] = {}
        self._score: dict[tuple, tuple[pd.DataFrame, dict]] = {}
        self._cost_frame: pd.DataFrame | None = None
        self._cost_tried = False
        # monthly books kept in memory so a meta-portfolio can treat the
        # strategies as assets without re-running or re-reading them
        self._monthly: dict[str, pd.DataFrame] = {}
        self.risk_on = trailing_12m_risk_on(self.spine.mkt)
        logger.info("factory ready in %.1fs — %s", time.time() - t0,
                    self.spine.provenance)

    def eligible(self, segment: str) -> pd.DataFrame:
        if segment not in self._elig:
            self._elig[segment] = eligibility(self.spine, segment)
        return self._elig[segment]

    def cost_frame(self) -> pd.DataFrame | None:
        """KO half-spread frame; None (with a loud log) when unavailable."""
        if not self._cost_tried:
            self._cost_tried = True
            try:
                from aegis_brain.costs import build_spread_frame
                self._cost_frame = build_spread_frame(self.spine.panel)
                cov = self._cost_frame.notna().sum(axis=1)
                first_ok = cov[cov > 100].index.min()
                logger.info("KO cost frame: coverage starts %s, mean %.0f names",
                            first_ok, cov.mean())
            except Exception as exc:
                logger.warning("KO cost frame unavailable (%s) — specs asking "
                               "for cost_model='ko' will fail loudly", exc)
                self._cost_frame = None
        return self._cost_frame

    def run(self, spec: StrategySpec, *, placebo_draws: int = 0,
            write: bool = True) -> dict:
        t0 = time.time()
        elig = self.eligible(spec.segment)
        # the OAT grid re-uses one composite across its 7 configurations
        skey = (spec.signals, spec.segment)
        if skey not in self._score:
            self._score[skey] = composite_score(self.lib, spec.signals, elig)
        score, sdiag = self._score[skey]
        cost_frame = self.cost_frame() if spec.cost_model == "ko" else None
        regime_on = self.risk_on if spec.regime_rule == "bull_risk_on" else None
        if spec.regime_rule not in ("", "bull_risk_on"):
            raise ValueError(f"unknown regime_rule {spec.regime_rule!r}")

        out = run_book(self.spine.panel, score, elig, spec, self.spine.rf,
                       cost_frame, regime_on)
        monthly, diag = out["monthly"], out["diag"]
        diag.update({"signal_coverage": sdiag,
                     "regime_rule": spec.regime_rule or "none",
                     "risk_on_frac": (round(float(monthly["risk_on"].mean()), 3)
                                      if regime_on is not None else 1.0)})
        if spec.blend_market > 0:
            monthly, bdiag = blend_monthly(monthly, self.spine.mkt,
                                           spec.blend_market,
                                           spec.blend_fee_bps)
            diag.update(bdiag)
            diag["turnover_1way_annual"] = round(
                float(monthly["traded"].sum()) / 2 / (len(monthly) / 12), 3)
            diag["cost_drag_annual_bps"] = round(
                float(monthly["cost"].sum()) / (len(monthly) / 12) * 1e4, 1)
        self._monthly[spec.name] = monthly

        key = f"{spec.segment}|{spec.first_month}|{spec.last_month}|{spec.min_names}"
        if key not in self._ew:
            self._ew[key] = buy_and_hold_universe(self.spine.panel, elig, spec,
                                                  self.spine.rf)
        card = scorecard(monthly, self.spine.mkt, diag=diag,
                         spec_dict=spec.as_dict(), ew_universe=self._ew[key],
                         factors=self.factors, rf=self.spine.rf, seed=spec.seed)
        card["spec_hash"] = spec.spec_hash()
        card["provenance"] = dict(self.spine.provenance)
        card["runtime_secs"] = round(time.time() - t0, 1)

        if placebo_draws:
            band = ctrl.placebo_band(
                self.spine.panel, elig, spec, self.spine.rf, cost_frame,
                self.spine.mkt, diag["turnover_1way_annual"],
                n_draws=placebo_draws)
            card["placebo"] = band
            card["placebo_verdict"] = ctrl.placebo_verdict(
                card["headline"]["excess_cagr_net"], band)
            card["runtime_secs"] = round(time.time() - t0, 1)

        if write:
            write_artifacts(spec, card, out_dir=self.out_dir)
        logger.info("%s: excess CAGR %.2f%% t=%.2f (%.0fs)", spec.name,
                    100 * card["headline"]["excess_cagr_net"],
                    card["headline"]["t_excess_monthly"], card["runtime_secs"])
        return card


def write_artifacts(spec: StrategySpec, card: dict,
                    out_dir: Path | None = None) -> Path:
    d = out_dir or OUT_DIR
    d.mkdir(parents=True, exist_ok=True)
    stem = f"{spec.name}__{spec.spec_hash()}"
    j = d / f"{stem}.json"
    if j.exists():
        logger.warning("%s exists — write-once; not overwriting", j.name)
        return j
    j.write_text(json.dumps(card, indent=2, default=str), encoding="utf-8")
    (d / f"{stem}.md").write_text(render_markdown(card), encoding="utf-8")
    return j


def render_markdown(card: dict) -> str:
    h, r, d = card["headline"], card["risk"], card["distribution"]
    s, w, im = card["spec"], card["window"], card["implementation"]
    L = [f"# {s['name']} — factory scorecard",
         "",
         f"spec hash `{card.get('spec_hash')}` · {w['first']}..{w['last']} "
         f"({w['months']} months, {w['years']}y) · segment {s['segment']} · "
         f"top {s['top_n']} · rebalance {s['rebalance_months']}m · "
         f"costs {s['cost_model']}",
         "",
         f"**Signals:** " + ", ".join(f"{k} ({v:+g})" for k, v in s["signals"]),
         "",
         "## Headline",
         "",
         "| metric | value |",
         "|---|---|",
         f"| net CAGR | {h['cagr_net']:.2%} |",
         f"| benchmark CAGR | {h['benchmark_cagr']:.2%} |",
         f"| **net excess CAGR** | **{h['excess_cagr_net']:+.2%}** |",
         f"| terminal wealth vs benchmark | {h['terminal_wealth_multiple_vs_benchmark']}× |",
         f"| t(excess), monthly | {h['t_excess_monthly']} |",
         f"| t(excess), Newey-West 12 | {h['t_excess_newey_west']} |",
         f"| max drawdown | {r['max_drawdown']:.1%} (benchmark {r['benchmark_max_drawdown']:.1%}) |",
         f"| ann vol | {r['ann_vol']:.1%} |",
         f"| Sharpe / Sortino / Calmar | {r['sharpe_net']} / {r['sortino_net']} / {r['calmar']} |",
         f"| years beating benchmark | {d['years_beating_benchmark']} |",
         f"| turnover (1-way, ann) | {im['turnover_1way_annual']} |",
         f"| cost drag | {im['cost_drag_cagr']:.2%}/yr |",
         ""]
    if "placebo_verdict" in card:
        pv, pb = card["placebo_verdict"], card["placebo"]
        L += ["## Placebo gate (random selection, turnover-matched)", "",
              f"- {pb['n_draws']} random books, ρ={pb['rho']}, "
              f"turnover {pb['placebo_turnover_mean']} vs strategy "
              f"{pb['strategy_turnover']}",
              f"- placebo excess CAGR: mean {pb['excess_cagr']['mean']:+.2%}, "
              f"p95 {pb['excess_cagr']['p95']:+.2%}, "
              f"max {pb['excess_cagr']['max']:+.2%}",
              f"- strategy {pv['strategy_excess_cagr']:+.2%} → "
              f"empirical p = {pv['empirical_p_value']} → "
              f"**{'PASS' if pv['PASS'] else 'FAIL'}**", ""]
    L += ["## Regime blocks (gate set)", "",
          "| block | months | strategy | benchmark | excess |", "|---|---|---|---|---|"]
    for k, v in card["regimes_gate"].items():
        if k == "_summary" or "excess_cagr" not in v:
            continue
        L.append(f"| {k} | {v['months']} | {v['strategy_cagr']:.2%} | "
                 f"{v['benchmark_cagr']:.2%} | {v['excess_cagr']:+.2%} |")
    sm = card["regimes_gate"].get("_summary", {})
    L += ["", f"positive-excess blocks: {sm.get('blocks_positive_excess')}/"
              f"{sm.get('blocks_evaluated')} evaluated "
              f"(holdout block not read)", ""]
    t = card.get("tail", {})
    if "p_maxdd_worse_than_60pct" in t:
        tw = t["terminal_wealth_strategy"]
        L += ["## Tail / ruin (paired block bootstrap)", "",
              f"- P(max DD worse than 60%) = {t['p_maxdd_worse_than_60pct']:.2%}; "
              f"worse than 40% = {t['p_maxdd_worse_than_40pct']:.2%}",
              f"- P(underperform benchmark over the same horizon) = "
              f"{t['p_underperform_benchmark']:.1%}",
              f"- terminal wealth p05/median/p95 = {tw['p05']}× / {tw['median']}× "
              f"/ {tw['p95']}× (benchmark median "
              f"{t['terminal_wealth_benchmark_median']}×)",
              f"- excess CAGR p05/median/p95 = {t['excess_cagr']['p05']:+.2%} / "
              f"{t['excess_cagr']['median']:+.2%} / {t['excess_cagr']['p95']:+.2%}",
              ""]
    if "factor_alpha" in card:
        L += ["## Factor alpha", "", "| model | ann alpha | t |", "|---|---|---|"]
        for k, v in card["factor_alpha"].items():
            L.append(f"| {k} | {v['ann_alpha']:.2%} | {v['t_alpha']} |")
        L.append("")
    if "controls" in card:
        c = card["controls"]
        L += ["## Universe control", "",
              f"- equal-weight eligible universe CAGR {c['ew_universe_cagr']:.2%}; "
              f"strategy excess vs it {c['excess_vs_ew_universe_cagr']:+.2%} "
              f"(t {c['t_excess_vs_ew_universe']})", ""]
    L += ["## Implementation", "",
          f"- months {im['months']}, rebalances {im['rebalances']}, "
          f"mean names held {im['mean_n_held']}, mean cash {im['mean_cash_weight']:.1%}",
          f"- forced liquidations (delist/no-return): {im['forced_liquidations']}; "
          f"months skipped for thin universe: {im['months_skipped_thin_universe']}",
          f"- gross CAGR {im['gross_cagr']:.2%} → net {h['cagr_net']:.2%}",
          f"- benchmark: {card['provenance']['benchmark']}",
          f"- holdout `{card['provenance']['holdout_first']}+` read: "
          f"{card['provenance']['holdout_read']}",
          ""]
    return "\n".join(L)
