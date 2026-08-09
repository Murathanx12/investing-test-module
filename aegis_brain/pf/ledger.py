"""The accumulating constraint ledger — how the factory gets HARDER over time.

Murat's ask was "a system where every run the engine picks up, learns and
improves". The tempting reading is that the engine should adapt its parameters
to what backtests reward. That reading is how research programmes destroy
themselves: it is fitting, one campaign at a time, and the more it "learns" the
less its numbers mean.

The version that survives contact with the evidence is the opposite. What
accumulates is CONSTRAINT, not parameters:

  * every spec ever run is counted, so the multiple-testing denominator is a
    programme-wide fact instead of a per-campaign one. External review's charge
    was precise: PF-PROF-COMPOSITE-150 was selected across hundreds of prior
    tests and then judged against a t-bar calibrated as though it were the first.

  * every campaign's bar is DEFLATED by that denominator and printed on the
    scorecard, so a t of 2.5 stops looking like the same evidence in campaign 1
    and campaign 12.

  * a spec whose near-twin has already been killed is flagged before it runs,
    so the factory cannot quietly re-litigate a dead family until noise finally
    hands it a pass.

  * the hit rate is reported next to what pure noise would produce at the same
    denominator, which is the closest thing this programme has to a stopping
    rule — the thing external review correctly noted it does not have.

Nothing here adjudicates or blocks. It annotates, loudly, and the annotation is
the point: the engine improves by becoming more expensive to fool.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from scipy import stats

from aegis_brain.config import MODULE_ROOT

logger = logging.getLogger(__name__)

RUNS = MODULE_ROOT / "runs"
PF_DIRS = ("PF", "PF2", "PF3", "PF4")
REGISTRY = MODULE_ROOT / "TRIALS" / "registry.jsonl"
ALPHA = 0.05

# Search-phase experiment count carried forward from the strategy factory's own
# close-out (docs/NEGATIVE_RESULTS.md and the 2026-08-08 night-1 record). It is
# cited, not recomputed here, and it is part of the denominator because those
# tests were run on the same data by the same people looking for the same thing.
PRIOR_SEARCH_EXPERIMENTS = 648


@dataclass(frozen=True)
class Denominator:
    specs_on_disk: int
    trials_registered: int
    prior_search_experiments: int

    @property
    def total(self) -> int:
        return (self.specs_on_disk + self.trials_registered
                + self.prior_search_experiments)

    def as_dict(self) -> dict:
        return {"specs_on_disk": self.specs_on_disk,
                "trials_registered": self.trials_registered,
                "prior_search_experiments": self.prior_search_experiments,
                "total": self.total,
                "note": "these are added, not maximized: a portfolio spec, a "
                        "registered trial and a factory search cell are all "
                        "tests of the same data by the same programme"}


def count_specs() -> int:
    seen: set[str] = set()
    for d in PF_DIRS:
        p = RUNS / d
        if not p.exists():
            continue
        for j in p.glob("*.json"):
            stem = j.stem
            if "__" in stem:
                seen.add(stem.rsplit("__", 1)[-1])
    return len(seen)


def count_trials() -> int:
    if not REGISTRY.exists():
        return 0
    return sum(1 for line in REGISTRY.read_text(encoding="utf-8").splitlines()
               if line.strip())


def denominator() -> Denominator:
    return Denominator(count_specs(), count_trials(), PRIOR_SEARCH_EXPERIMENTS)


def deflated_bars(n_tests: int, alpha: float = ALPHA) -> dict:
    """t-bars implied by n_tests, two-sided.

    Bonferroni controls the family-wise error rate and is the strictest
    defensible reading. Benjamini-Yekutieli controls the false discovery rate
    under arbitrary dependence, which is the right assumption when the tests are
    overlapping portfolios of the same names. Harvey-Liu-Zhu's 3.0 is the
    literature's practical bar for a newly claimed factor and is reported so the
    comparison is to a published standard rather than to our own arithmetic.
    """
    n = max(int(n_tests), 1)
    harmonic = sum(1.0 / i for i in range(1, n + 1))
    return {
        "n_tests": n,
        "bonferroni_t": round(float(stats.norm.ppf(1 - alpha / (2 * n))), 2),
        "benjamini_yekutieli_t_for_most_significant": round(
            float(stats.norm.ppf(1 - alpha / (2 * n * harmonic))), 2),
        "harvey_liu_zhu_rule_of_thumb_t": 3.0,
        "unadjusted_t": round(float(stats.norm.ppf(1 - alpha / 2)), 2),
    }


def _block(den: Denominator, bars: dict, t_obs: float | None,
           t_alpha: float | None) -> dict:
    def clears(t: float | None, bar: float) -> bool | None:
        return None if t is None else bool(abs(t) > bar)

    return {
        "denominator": den.as_dict(),
        "deflated_bars": bars,
        "t_excess_observed": t_obs,
        "t_alpha_observed": t_alpha,
        "clears": {
            "excess_vs_HLZ_3.0": clears(t_obs, 3.0),
            "excess_vs_bonferroni": clears(t_obs, bars["bonferroni_t"]),
            "alpha_vs_HLZ_3.0": clears(t_alpha, 3.0),
            "alpha_vs_bonferroni": clears(t_alpha, bars["bonferroni_t"]),
        },
        "reading": ("a verdict must say WHICH statistic it stands on and against "
                    "WHICH bar. Standing on an unadjusted t after this many "
                    "tests is the error the whole ledger exists to prevent."),
    }


def testing_block(t_observed: float | None,
                  t_alpha_observed: float | None = None,
                  alpha: float = ALPHA) -> dict:
    den = denominator()
    return _block(den, deflated_bars(den.total, alpha), t_observed,
                  t_alpha_observed)


def noise_expectation(n_tests: int, hits: int, alpha: float = ALPHA) -> dict:
    """What pure noise would have produced at this denominator.

    The closest thing to a stopping rule the programme has: if the observed hit
    rate is indistinguishable from what an unadjusted alpha-level screen would
    yield on random data, the honest conclusion is that the search has found
    nothing, and continuing costs more than it can return.
    """
    n = max(int(n_tests), 1)
    expected = n * alpha
    p_at_least = float(1 - stats.binom.cdf(hits - 1, n, alpha)) if hits else 1.0
    return {
        "tests": n, "declared_hits": hits,
        "expected_hits_under_pure_noise_at_alpha_0.05": round(expected, 1),
        "observed_hit_rate": round(hits / n, 4),
        "p_of_at_least_this_many_under_noise": round(p_at_least, 4),
        "reading": ("if declared hits are at or below the noise expectation, the "
                    "search has not distinguished itself from chance at this "
                    "denominator, whatever any individual t-stat says"),
    }


def prior_verdicts(family_or_name: str) -> list[dict]:
    """Everything already run whose name contains `family_or_name`.

    Called before a campaign so a dead family cannot be quietly re-litigated
    until noise hands it a pass.
    """
    out = []
    for d in PF_DIRS:
        p = RUNS / d
        if not p.exists():
            continue
        for j in sorted(p.glob("*.json")):
            if family_or_name.lower() not in j.stem.lower():
                continue
            try:
                card = json.loads(j.read_text(encoding="utf-8"))
            except Exception:                       # noqa: BLE001
                continue
            h = card.get("headline", {})
            out.append({"artifact": f"{d}/{j.name}",
                        "spec_hash": card.get("spec_hash"),
                        "excess_cagr_net": h.get("excess_cagr_net"),
                        "t_excess_newey_west": h.get("t_excess_newey_west")})
    return out


def summary() -> dict:
    den = denominator()
    return {"denominator": den.as_dict(),
            "deflated_bars": deflated_bars(den.total)}
