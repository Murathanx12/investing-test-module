"""TRIAL-COHERENCE-BATTERY-1 — does the reasoner keep its own directions straight?

Design authority: `DESIGN_MEMORY_TAXONOMY_2026-08-09.md` §4. Registry row
`TRIAL-COHERENCE-BATTERY-1`, committed 2026-08-09 before this file existed.

The cheapest possible test of an LLM decision layer, and the one that should run
first: perturb exactly ONE variable in a scenario, hold everything else byte-
identical, and check the answer moves in the pre-registered direction. A reasoner
that says a company is more attractive when its earnings MISS is not making a
subtle judgement call — it is incoherent, and no amount of return-based testing
downstream can repair that.

Scenarios are SYNTHETIC (fabricated company, fabricated far-future date), which
AMNESIA measured as behaviourally equivalent to masked real ones (ΔBrier 0.0004)
while being provably absent from any training corpus.

**Passing this battery is not evidence of alpha.** It means the model is
coherent, not that it is right. It is a gate, and gates only ever remove things.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, replace

import numpy as np

logger = logging.getLogger(__name__)

SYSTEM = ("You are a careful equity analyst. You answer only with strict JSON "
          "matching the requested schema. You never invent facts that were not "
          "given to you.")

FAKE_PREFIX = ["Arden", "Belmar", "Corvin", "Dalmoor", "Elstree", "Fennick",
               "Garvey", "Halcyon", "Iverson", "Jandra", "Kestrel", "Lindow",
               "Marrow", "Norhaven", "Orrick", "Pellham", "Quarry", "Ridgeley",
               "Selwyn", "Tarnish", "Umbrey", "Vardon", "Wexler", "Yarrow"]
FAKE_SUFFIX = ["Industries", "Holdings", "Systems", "Group", "Works",
               "Partners", "Corporation", "Enterprises", "Technologies"]
SECTORS = ["manufacturing", "retail trade", "services", "transport or utilities",
           "mining", "construction", "wholesale trade"]

# ── the five perturbations and their PRE-REGISTERED required directions ─────
# (field, low-value rendering, high-value rendering, required sign of
#  expected_excess_return(high) − expected_excess_return(low))
DIRECTIONS: dict[str, dict] = {
    "valuation": {
        "field": "valuation",
        "low": "expensive — book-to-market in the 15th percentile of peers",
        "high": "cheap — book-to-market in the 85th percentile of peers",
        "required_sign": +1,
        "meaning": "cheaper should be more attractive, all else equal",
    },
    "earnings": {
        "field": "earnings",
        "low": "the most recent quarterly earnings MISSED consensus by 8%",
        "high": "the most recent quarterly earnings BEAT consensus by 8%",
        "required_sign": +1,
        "meaning": "a beat should be more attractive than a miss",
    },
    "regime": {
        "field": "regime",
        "low": "the broad market is in a sustained bear phase, down 22% from "
               "its high, with rising realised volatility",
        "high": "the broad market is in a sustained bull phase, up 18% over the "
                "past year, with falling realised volatility",
        "required_sign": +1,
        "meaning": "a bull regime should not lower an equity's expected return",
    },
    "geopolitical": {
        "field": "geopolitical",
        "low": "geopolitical risk affecting this company's main markets is "
               "severe and escalating",
        "high": "geopolitical risk affecting this company's main markets is "
                "low and stable",
        "required_sign": +1,
        "meaning": "less geopolitical risk should not lower expected return",
    },
    "revisions": {
        "field": "revisions",
        "low": "analysts have cut next-year earnings estimates by 6% over the "
               "past three months",
        "high": "analysts have raised next-year earnings estimates by 6% over "
                "the past three months",
        "required_sign": +1,
        "meaning": "upward revisions should be more attractive than cuts",
    },
}

NEUTRAL = {
    "valuation": "book-to-market in the 50th percentile of peers",
    "earnings": "the most recent quarterly earnings were in line with consensus",
    "regime": "the broad market is flat over the past year with average volatility",
    "geopolitical": "geopolitical risk affecting this company's main markets is "
                    "unremarkable",
    "revisions": "analysts have left next-year earnings estimates broadly unchanged",
}


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    company: str
    ticker: str
    date: str
    sector: str
    profitability: int
    momentum: int
    volatility: int
    valuation: str
    earnings: str
    regime: str
    geopolitical: str
    revisions: str

    def render(self) -> str:
        return (
            "[SIMULATED SCENARIO — this company and date are fictional; no "
            "real-world facts about them exist]\n\n"
            f"Company: {self.company} (ticker {self.ticker}), {self.sector}.\n"
            f"Simulation date: {self.date}.\n\n"
            "Facts as of the simulation date:\n"
            f"- Gross profitability: {self.profitability}th percentile of peers\n"
            f"- 12-1 month momentum: {self.momentum}th percentile\n"
            f"- Trailing volatility: {self.volatility}th percentile "
            "(higher = more volatile)\n"
            f"- Valuation: {self.valuation}\n"
            f"- Earnings: {self.earnings}\n"
            f"- Market regime: {self.regime}\n"
            f"- Geopolitics: {self.geopolitical}\n"
            f"- Analyst revisions: {self.revisions}\n")


ASK = ('Return JSON exactly: {"expected_excess_return": <decimal, e.g. 0.03 '
       'means you expect this stock to beat the broad market by 3% over the '
       'next 12 months; negative means you expect it to lag>, "conviction": '
       '<0.0-1.0>}\nGive a specific number, not zero, unless you genuinely '
       'have no view.')


def build_scenarios(n: int, seed: int = 20260809) -> list[Scenario]:
    """n neutral base scenarios. Everything perturbable starts at NEUTRAL, so a
    pair differs in exactly one rendered line."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        h = int(hashlib.sha256(f"coh-{seed}-{i}".encode()).hexdigest()[:8], 16)
        pre = FAKE_PREFIX[h % len(FAKE_PREFIX)]
        name = f"{pre} {FAKE_SUFFIX[(h // 7) % len(FAKE_SUFFIX)]}"
        out.append(Scenario(
            scenario_id=f"COH{i:03d}", company=name,
            ticker=(pre[:3] + chr(65 + h % 26)).upper(),
            date=f"{2100 + (h % 40)}-{1 + (h // 13) % 12:02d}",
            sector=SECTORS[h % len(SECTORS)],
            profitability=int(rng.integers(10, 91)),
            momentum=int(rng.integers(10, 91)),
            volatility=int(rng.integers(10, 91)),
            **NEUTRAL))
    return out


def perturb(s: Scenario, dimension: str, side: str) -> Scenario:
    spec = DIRECTIONS[dimension]
    return replace(s, **{spec["field"]: spec[side]})


def prompt(s: Scenario) -> tuple[str, str]:
    return SYSTEM, s.render() + "\n" + ASK


def grade(pairs: list[dict]) -> dict:
    """Per-direction pass rates. A tie counts as a FAILURE to move, reported
    separately from moving the wrong way — the two are different defects."""
    out: dict[str, dict] = {}
    for dim in DIRECTIONS:
        rows = [p for p in pairs if p["dimension"] == dim and p["ok"]]
        if not rows:
            out[dim] = {"n": 0, "pass_rate": None, "reason": "no usable pairs"}
            continue
        req = DIRECTIONS[dim]["required_sign"]
        deltas = np.array([p["high"] - p["low"] for p in rows], dtype=float)
        correct = int(np.sum(np.sign(deltas) == req))
        ties = int(np.sum(deltas == 0))
        wrong = len(rows) - correct - ties
        out[dim] = {
            "n": len(rows),
            "pass_rate": round(correct / len(rows), 3),
            "n_correct": correct, "n_tied": ties, "n_wrong": wrong,
            "mean_delta": round(float(np.mean(deltas)), 4),
            "median_delta": round(float(np.median(deltas)), 4),
            "required_sign": req,
            "meaning": DIRECTIONS[dim]["meaning"],
        }
    passed = [d for d, v in out.items()
              if v.get("pass_rate") is not None and v["pass_rate"] >= 0.70]
    out["_summary"] = {
        "directions_tested": len(DIRECTIONS),
        "directions_passing_at_0.70": len(passed),
        "passing": sorted(passed),
        "failing": sorted(set(DIRECTIONS) - set(passed)),
        "verdict": ("COHERENT" if len(passed) >= 4 else
                    "INCOHERENT — return-based testing of the failing "
                    "variables is not warranted until fixed"),
    }
    return out
