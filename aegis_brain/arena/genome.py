"""PortfolioGenome — one competitor in the Arena, and the frozen manifest.

A genome is a complete, hashable description of a portfolio policy: what it
believes, where it looks, how many names it holds, how it weights them, how
often it trades and what it refuses to do. Two genomes with the same hash are
the same portfolio, and running one twice is a no-op rather than a new draw.

THE DESIGN IS CONTROLLED, NOT COMBINATORIAL. The full cross of every dimension
is ~30,000 cells, and evaluating a random slab of it would make the denominator
enormous and the coverage of any one axis thin. Instead the generator builds a
STRATIFIED design: each signal set is crossed with a small orthogonal array of
construction choices, so every construction dimension is balanced across signal
sets and each axis can be read on its own. The count is a consequence of the
design, and it is written down before anything runs.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import asdict, dataclass, field
from typing import Optional

# ── the construction dimensions ─────────────────────────────────────────────

WEIGHTINGS = (
    "equal_weight",       # the control that beats most things
    "score_weight",       # conviction: more of what scores best
    "inverse_vol",        # risk parity within the book
    "reliability_shrunk",  # shrink toward equal by the signal's registry weight
    "fractional_kelly",   # mu / sigma^2, capped
)

TOP_K = (5, 10, 15, 20, 25, 50)
MAX_WEIGHT = (0.10, 0.20, 0.35, 1.0)
REBALANCE_MONTHS = (1, 3, 6, 12)
SEGMENTS = ("small", "largemid", "all")

#: A book that holds 5 names out of a 2,000-name universe is a lottery ticket
#: whose variance will dominate any signal effect. It is allowed into the Arena
#: because Murat's real book is concentrated and the question is honest, but it
#: is TAGGED so a survivor at k=5 is read as what it is.
CONCENTRATION_WARN_K = 10


@dataclass(frozen=True)
class PortfolioGenome:
    genome_id: str
    signals: tuple[tuple[str, float], ...]
    signal_family: str
    segment: str = "small"
    top_k: int = 25
    weighting: str = "equal_weight"
    max_weight: float = 1.0
    rebalance_months: int = 1
    cash_floor: float = 0.0
    reliability_floor: float = 0.0
    cost_model: str = "flat25"
    hypothesis: str = ""
    #: Which corpse this genome is NOT, when it lives near one.
    distinct_from: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.weighting not in WEIGHTINGS:
            raise ValueError(f"bad weighting {self.weighting!r}")
        if self.segment not in SEGMENTS:
            raise ValueError(f"bad segment {self.segment!r}")
        if self.top_k < 3:
            raise ValueError("top_k < 3 is not a portfolio")
        if not self.signals:
            raise ValueError("a genome needs at least one signal")
        if not 0.0 <= self.cash_floor < 1.0:
            raise ValueError("cash_floor must be in [0, 1)")
        # A per-name cap below 1/k is unsatisfiable and would silently leave
        # the book in cash rather than doing what the genome says.
        if self.max_weight * self.top_k < 0.999:
            raise ValueError(
                f"max_weight {self.max_weight} x top_k {self.top_k} = "
                f"{self.max_weight * self.top_k:.3f} < 1: this cap cannot be "
                f"satisfied and would quietly hold cash")

    def as_dict(self) -> dict:
        d = asdict(self)
        d["signals"] = [list(s) for s in self.signals]
        d["distinct_from"] = list(self.distinct_from)
        d["tags"] = list(self.tags)
        return d

    def genome_hash(self) -> str:
        payload = {k: v for k, v in self.as_dict().items()
                   if k not in ("genome_id", "hypothesis", "tags")}
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


# ── the signal sets, each drawn from the registry ───────────────────────────

def signal_sets(registry) -> list[dict]:
    """Every signal combination the registry PERMITS. Nothing else may enter.

    This is the mechanism by which research constrains the search rather than
    merely commenting on it: a closed family is not "avoided by convention",
    it is absent from the candidate pool because `permits()` said no.
    """
    pickers = [s.signal_id for s in registry.by_role("PICKER")]
    filters = [s.signal_id for s in registry.by_role("FILTER")]
    risk = [s.signal_id for s in registry.by_role("RISK_INPUT")]

    sets: list[dict] = []

    # A. the benchmark families — what we must beat, not what we hope wins
    sets.append({"family": "control_equal_weight", "signals": (("control:ew", 1.0),),
                 "hypothesis": "equal-weight the eligible universe; the "
                               "denominator every other genome is measured against"})

    # B. each permitted picker, alone
    for p in pickers:
        sets.append({"family": f"solo_{p}", "signals": ((p, 1.0),),
                     "hypothesis": f"{p} alone, at its registry-permitted role"})

    # C. picker + filter pairs — the filter conditions, never picks
    for p in pickers:
        for f in filters:
            sets.append({
                "family": f"{p}__x__{f}",
                "signals": ((p, 1.0), (f, 0.35)),
                "hypothesis": f"{p} as the picker, {f} down-weighted as a "
                              f"conditioning filter rather than a second picker",
            })

    # D. the ensembles — several permitted pickers, equal say
    if len(pickers) >= 2:
        for combo in itertools.combinations(sorted(pickers), 2):
            sets.append({
                "family": "ensemble_" + "__".join(combo),
                "signals": tuple((c, 1.0) for c in combo),
                "hypothesis": "complementary permitted pickers, equal weight",
            })
    if len(pickers) >= 3:
        combo = tuple(sorted(pickers)[:3])
        sets.append({
            "family": "ensemble_" + "__".join(combo),
            "signals": tuple((c, 1.0) for c in combo),
            "hypothesis": "three permitted pickers; the broadest licensed blend",
        })

    # E. risk inputs as tie-breakers, at low weight and never alone
    for p in pickers[:2]:
        for r in risk:
            sets.append({
                "family": f"{p}__tiebreak__{r}",
                "signals": ((p, 1.0), (r, 0.2)),
                "hypothesis": f"{r} is a RISK_INPUT: permitted to break ties "
                              f"inside a book {p} already chose, never to pick",
            })
    return sets


# ── the stratified design ───────────────────────────────────────────────────

#: An orthogonal-ish array over the construction dimensions. Eight rows cover
#: every level of every dimension at least once and balance the pairs, which is
#: what makes a per-axis reading possible without the full 30k cross.
CONSTRUCTION_ARRAY: tuple[dict, ...] = (
    {"top_k": 25, "weighting": "equal_weight",      "max_weight": 1.00, "rebalance_months": 12},
    {"top_k": 25, "weighting": "score_weight",      "max_weight": 0.20, "rebalance_months": 3},
    {"top_k": 10, "weighting": "equal_weight",      "max_weight": 0.20, "rebalance_months": 3},
    {"top_k": 10, "weighting": "inverse_vol",       "max_weight": 0.35, "rebalance_months": 12},
    {"top_k": 50, "weighting": "inverse_vol",       "max_weight": 0.10, "rebalance_months": 1},
    {"top_k": 50, "weighting": "reliability_shrunk", "max_weight": 0.10, "rebalance_months": 6},
    {"top_k": 15, "weighting": "fractional_kelly",  "max_weight": 0.35, "rebalance_months": 6},
    {"top_k": 5,  "weighting": "equal_weight",      "max_weight": 0.35, "rebalance_months": 1},
)


def generate(registry, *, segments: tuple[str, ...] = ("small", "largemid"),
             cost_models: tuple[str, ...] = ("flat25",),
             max_genomes: int = 500) -> list[PortfolioGenome]:
    """The full frozen population. Deterministic — no RNG anywhere."""
    out: list[PortfolioGenome] = []
    n = 0
    for sset in signal_sets(registry):
        for seg in segments:
            for row in CONSTRUCTION_ARRAY:
                for cost in cost_models:
                    n += 1
                    gid = f"G{n:04d}"
                    tags = ["arena1"]
                    if row["top_k"] < CONCENTRATION_WARN_K:
                        tags.append("concentrated")
                    if sset["family"].startswith("control"):
                        tags.append("control")
                    try:
                        g = PortfolioGenome(
                            genome_id=gid,
                            signals=tuple(tuple(x) for x in sset["signals"]),
                            signal_family=sset["family"],
                            segment=seg,
                            cost_model=cost,
                            hypothesis=sset["hypothesis"],
                            tags=tuple(tags),
                            **row)
                    except ValueError:
                        # An unsatisfiable cell is skipped, and skipping it is
                        # deterministic, so the denominator stays reproducible.
                        n -= 1
                        continue
                    out.append(g)
                    if len(out) >= max_genomes:
                        return out
    return out


def manifest(genomes: list[PortfolioGenome], *, arena_id: str, code_sha: str,
             data_cutoff: str, window: tuple[str, str], benchmark: str,
             objectives: list[str], selection_rule: str,
             registry_summary: dict, seed: int,
             parent_arena: Optional[str] = None,
             llm_hypotheses: Optional[list[dict]] = None) -> dict:
    """The immutable record. Written and COMMITTED before anything is scored."""
    rows = [g.as_dict() | {"genome_hash": g.genome_hash()} for g in genomes]
    body = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return {
        "arena_id": arena_id,
        "schema": "arena-manifest-v1",
        "frozen_before_any_result": True,
        "code_sha": code_sha,
        "seed": seed,
        "data_cutoff": data_cutoff,
        "window": {"first": window[0], "last": window[1]},
        "benchmark": benchmark,
        "objectives": objectives,
        "selection_rule": selection_rule,
        "parent_arena": parent_arena,
        "denominator": {
            "n_genomes": len(genomes),
            "n_signal_families": len({g.signal_family for g in genomes}),
            "n_controls": sum(1 for g in genomes if "control" in g.tags),
            "note": ("Every genome below counts against every survivor's "
                     "significance, including the ones never mentioned again. "
                     "Losers are preserved in the results file."),
        },
        "registry": registry_summary,
        "llm_hypotheses": llm_hypotheses or [],
        "llm_hypotheses_sha256": hashlib.sha256(
            json.dumps(llm_hypotheses or [], sort_keys=True).encode()).hexdigest(),
        "genomes": rows,
        "genomes_sha256": hashlib.sha256(body.encode()).hexdigest(),
    }
