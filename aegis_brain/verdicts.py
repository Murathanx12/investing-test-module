"""Verdict taxonomy v2 — and the epistemic guards, as code rather than prose.

NIGHT-4 retracted a headline because a report whose statistics said UNRESOLVED
printed the word REJECT. `POWER_CHECK.json` had already said, in writing, "the
verdict must be UNRESOLVED, not REJECT". The rule existed. It was prose, so
nothing enforced it, and the prose lost to the author.

This module is that rule with teeth. A verdict is a state with a declared set of
words it may not use, and `check_language` raises rather than warns. The point is
narrow and worth stating: it cannot make a conclusion correct. It can only stop
the *write-up* from claiming more than the *statistics* granted, which is the
specific failure that actually happened, twice.

Two states in v2 do work the old FAILED/REJECTED pair could not:

  FACTOR_EXPLAINED — the return is real and is already paid by a known factor.
    This is NOT "no edge", and the taxonomy refuses to let it be written that
    way. PF-PROF-COMPOSITE-150 is the worked example: +4.23%/yr of incremental
    alpha that a properly built small-cap profitability factor absorbs to
    +1.04%. There is money there; it is just not ours to name.

  POWER_FAILED — the experiment could not have detected the effect the standard
    requires, so its null says nothing about the idea. 72% of the closed
    179-signal search is in this state at the standard's own +3%/yr bar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """The nine states. Every closed experiment lands in exactly one."""

    CONFIRMED = "CONFIRMED"
    UNRESOLVED = "UNRESOLVED"
    FACTOR_EXPLAINED = "FACTOR_EXPLAINED"
    IMPLEMENTATION_FAILED = "IMPLEMENTATION_FAILED"
    DATA_FAILED = "DATA_FAILED"
    POWER_FAILED = "POWER_FAILED"
    PLACEBO_FAILED = "PLACEBO_FAILED"
    LEAKAGE_FAILED = "LEAKAGE_FAILED"
    REJECTED = "REJECTED"


#: What each state means, in one sentence, and what it does NOT mean.
MEANING: dict[Verdict, str] = {
    Verdict.CONFIRMED: (
        "the primary metric cleared its pre-registered bar. Does not mean the "
        "effect is large, tradable, or novel."),
    Verdict.UNRESOLVED: (
        "the interval contains both the null and the bar. The idea is neither "
        "supported nor refuted; it is unmeasured at this power."),
    Verdict.FACTOR_EXPLAINED: (
        "the return is real but is spanned by a known factor. A harvest, not a "
        "discovery. NEVER 'no edge'."),
    Verdict.IMPLEMENTATION_FAILED: (
        "the information is present but this construction cannot monetise it — "
        "costs, turnover, capacity, or a long-only constraint. The idea is not "
        "refuted; this build of it is."),
    Verdict.DATA_FAILED: (
        "the experiment did not produce a usable number — missing inputs, a "
        "truncated window, or a run that never completed. It is not evidence "
        "of anything and must not be counted as a test of the idea."),
    Verdict.POWER_FAILED: (
        "the design could not have detected the effect the standard requires. "
        "Its null is uninformative about the idea."),
    Verdict.PLACEBO_FAILED: (
        "a control that shares everything except the hypothesised mechanism "
        "performed as well. The measured effect is not attributable to the "
        "mechanism claimed."),
    Verdict.LEAKAGE_FAILED: (
        "the result depended on information unavailable at decision time. The "
        "number is void, not small."),
    Verdict.REJECTED: (
        "adequately powered, correctly implemented, and the bar is excluded by "
        "the interval. The idea is refuted at this bar on this data."),
}

#: States whose write-up may not use the language of a settled negative.
_NOT_A_NEGATIVE = {Verdict.UNRESOLVED, Verdict.POWER_FAILED,
                   Verdict.DATA_FAILED, Verdict.FACTOR_EXPLAINED,
                   Verdict.IMPLEMENTATION_FAILED}

#: States whose write-up may not use the language of a settled positive.
_NOT_A_POSITIVE = set(Verdict) - {Verdict.CONFIRMED}

_NEGATIVE_WORDS = [
    r"\breject(?:ed|s)?\b", r"\brefut(?:e|ed|es)\b", r"\bno edge\b",
    r"\bnothing there\b", r"\bdoes ?n[o']t work\b", r"\bdisproved?\b",
    r"\bdead\b", r"\bfailed to work\b", r"\bhas no (?:skill|value|alpha)\b",
]
_POSITIVE_WORDS = [
    r"\bconfirm(?:ed|s)?\b", r"\bprov(?:e|ed|es|en)\b", r"\bdemonstrat(?:e|ed|es)\b",
    r"\bestablish(?:ed|es)\b", r"\bworks\b", r"\bwinner\b",
]
#: Never allowed, in ANY state. Statistics do not prove things.
_ABSOLUTE_WORDS = [r"\bprov(?:e|ed|es|en)\b", r"\bguarantee(?:d|s)?\b",
                   r"\bcertain(?:ly)?\b", r"\brisk-?free\b"]

#: FACTOR_EXPLAINED additionally may not deny that a return exists.
_DENIES_RETURN = [r"\bno (?:return|premium|money)\b", r"\bzero (?:return|alpha)\b",
                  r"\bworthless\b"]


class VerdictLanguageError(AssertionError):
    """Raised when a write-up claims more than its verdict state grants."""


@dataclass
class Finding:
    """A closed experiment. `state` is set by the statistics, never by prose."""

    name: str
    state: Verdict
    primary_metric: str
    point_estimate: float | None = None
    mde: float | None = None
    bar: float | None = None
    notes: str = ""
    evidence: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.state in (Verdict.UNRESOLVED, Verdict.POWER_FAILED) \
                and self.mde is None:
            raise VerdictLanguageError(
                f"{self.name}: {self.state.value} must carry an MDE. A null "
                "without the size it could have seen is the NIGHT-4 error.")


def _hits(text: str, patterns: list[str]) -> list[str]:
    low = text.lower()
    return sorted({m.group(0) for p in patterns
                   for m in re.finditer(p, low)})


def check_language(state: Verdict, text: str) -> list[str]:
    """Return the violations in `text` for `state`. Empty list == clean."""
    bad: list[str] = []
    for w in _hits(text, _ABSOLUTE_WORDS):
        bad.append(f"{state.value}: '{w}' — statistics never prove or guarantee")
    if state in _NOT_A_NEGATIVE:
        for w in _hits(text, _NEGATIVE_WORDS):
            bad.append(f"{state.value}: '{w}' asserts a settled negative that "
                       f"this state does not grant ({MEANING[state]})")
    if state in _NOT_A_POSITIVE:
        for w in _hits(text, _POSITIVE_WORDS):
            bad.append(f"{state.value}: '{w}' asserts a settled positive that "
                       f"this state does not grant ({MEANING[state]})")
    if state is Verdict.FACTOR_EXPLAINED:
        for w in _hits(text, _DENIES_RETURN):
            bad.append(f"FACTOR_EXPLAINED: '{w}' denies a return that the "
                       "spanning test did not deny — the return is real and "
                       "already paid by a known factor")
    return sorted(set(bad))


def enforce(state: Verdict, text: str) -> str:
    """`check_language`, but it raises. Use this in report writers."""
    bad = check_language(state, text)
    if bad:
        raise VerdictLanguageError(
            f"{len(bad)} language violation(s) for {state.value}:\n  - "
            + "\n  - ".join(bad))
    return text


#: A net t below this is "the money leg did not show up". Both implementation
#: tests compare against it. Written as a named constant because the first
#: version used a Python chained comparison, `ic_t >= 3.0 > net_t`, which reads
#: `net_t < 3.0` and therefore labelled a t 2.31 result IMPLEMENTATION_FAILED.
NET_T_ABSENT = 1.5


def classify(*, months: int, point: float | None, mde: float | None,
             bar: float, gross_t: float | None = None,
             net_t: float | None = None, ic_t: float | None = None,
             min_months: int = 24) -> tuple[Verdict, str]:
    """Assign a state from statistics alone. Deterministic, no judgement.

    The order is not arbitrary: a result that never ran cannot be underpowered,
    and a result that could not have seen the bar cannot be said to have
    excluded it. Each test is only reached when the ones above it do not apply.
    """
    if months < min_months or point is None or mde is None:
        return (Verdict.DATA_FAILED,
                f"{months} usable months (< {min_months}) or no usable "
                "estimate — this never produced a number to judge")

    # information present, this build cannot keep it
    if gross_t is not None and net_t is not None \
            and gross_t >= 1.5 and net_t < NET_T_ABSENT:
        return (Verdict.IMPLEMENTATION_FAILED,
                f"gross t {gross_t:.2f} vs net t {net_t:.2f} — costs and "
                "turnover consumed the measured gross edge")
    if ic_t is not None and net_t is not None \
            and ic_t >= 3.0 and net_t < NET_T_ABSENT:
        return (Verdict.IMPLEMENTATION_FAILED,
                f"rank-IC t {ic_t:.2f} with net t {net_t:.2f} — the signal "
                "carries cross-sectional information that this long-only "
                "decile book does not convert into money")

    upper = point + mde
    if upper < bar:
        return (Verdict.REJECTED,
                f"upper interval {upper:+.2f} excludes the {bar:+.2f} bar — "
                "refuted at this bar on this data")
    if mde > bar:
        return (Verdict.POWER_FAILED,
                f"MDE {mde:.2f} exceeds the {bar:+.2f} bar — this design could "
                "not have detected the effect the standard requires, so its "
                "null says nothing about the idea")
    return (Verdict.UNRESOLVED,
            f"interval [{point - mde:+.2f}, {upper:+.2f}] contains the "
            f"{bar:+.2f} bar — unmeasured, not zero")
