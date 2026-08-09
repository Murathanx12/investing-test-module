"""Decision persistence: grading whether a belief moved by a defensible amount.

Design authority: `DESIGN_MEMORY_TAXONOMY_2026-08-09.md` §3.

Murat's requirement was consistency across re-reviews. The wrong implementation
is to prompt "be consistent" — that produces agreeable text and measures
nothing. The right one is to show the model the belief it actually held, let it
answer freely, and then grade the delta **deterministically here**, in engine
code the model never sees.

Two failure modes, deliberately separated because they have opposite fixes:

  * **OVERREACTION** — a large belief swing on evidence that did not warrant it.
  * **UNDERREACTION** — no movement at all on evidence that plainly did.

A grader that reported only "inconsistency" would collapse them into one number
and hide which way the model is broken.

Nothing in this file elicits an opinion. It takes the prior belief, the realized
evidence, and the new belief, and returns an enum.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Evidence thresholds, frozen. Expressed in abnormal return over one month.
STRONG_EVIDENCE = 0.05      # |abnormal| above this is hard to ignore
WEAK_EVIDENCE = 0.01        # |abnormal| below this warrants no revision
BIG_SWING = 0.35            # conviction move above this is a large revision
SMALL_SWING = 0.05          # conviction move below this is effectively none

VERDICTS = ("appropriate", "overreaction", "underreaction",
            "direction_inconsistent", "not_applicable")


@dataclass(frozen=True)
class Review:
    permno: str
    ts: str
    months_ago: int
    prior_direction: str
    prior_conviction: float
    prior_expected: float
    realized_abnormal: float      # what the prior belief's month actually did
    new_direction: str
    new_conviction: float
    stated_old_belief: str        # what the model SAYS it believed
    stated_update: str            # STRENGTHEN | MAINTAIN | WEAKEN | REVERSE
    verdict: str
    recall_correct: bool | None   # did it recall its own prior direction?


def _signed_evidence(prior_direction: str, abnormal: float) -> float:
    """Evidence in favour of the prior belief. Positive = the belief was right."""
    intent = {"BUY": 1.0, "SELL": -1.0}.get(prior_direction, 0.0)
    return intent * abnormal


def grade_review(*, permno: str, ts: str, months_ago: int,
                 prior_direction: str, prior_conviction: float,
                 prior_expected: float, realized_abnormal: float,
                 new_direction: str, new_conviction: float,
                 stated_old_belief: str = "", stated_update: str = "") -> Review:
    """Deterministic update-appropriateness verdict for one re-review."""
    ev = _signed_evidence(prior_direction, realized_abnormal)
    # signed conviction on a single axis, so a BUY→SELL flip is a large move
    def signed(d: str, c: float) -> float:
        return {"BUY": 1.0, "SELL": -1.0}.get(d, 0.0) * c
    swing = signed(new_direction, new_conviction) - signed(prior_direction,
                                                           prior_conviction)
    # a belief should move TOWARD the direction the evidence supports:
    # evidence against the prior belief (ev < 0) should shrink it
    moved_with_evidence = np.sign(swing) == np.sign(ev) if ev != 0 else True

    if prior_direction == "HOLD" and new_direction == "HOLD":
        verdict = "not_applicable"
    elif abs(ev) >= STRONG_EVIDENCE and abs(swing) < SMALL_SWING:
        verdict = "underreaction"
    elif abs(ev) <= WEAK_EVIDENCE and abs(swing) > BIG_SWING:
        verdict = "overreaction"
    elif not moved_with_evidence and abs(swing) > BIG_SWING:
        verdict = "direction_inconsistent"
    else:
        verdict = "appropriate"

    recall = (stated_old_belief == prior_direction) if stated_old_belief else None
    return Review(permno=permno, ts=ts, months_ago=months_ago,
                  prior_direction=prior_direction,
                  prior_conviction=round(float(prior_conviction), 4),
                  prior_expected=round(float(prior_expected), 4),
                  realized_abnormal=round(float(realized_abnormal), 4),
                  new_direction=new_direction,
                  new_conviction=round(float(new_conviction), 4),
                  stated_old_belief=stated_old_belief,
                  stated_update=stated_update, verdict=verdict,
                  recall_correct=recall)


def summarize(reviews: list[Review]) -> dict:
    """Aggregate. N8 is scored off `underreaction` vs `overreaction` counts."""
    if not reviews:
        return {"n": 0}
    counts: dict[str, int] = {v: 0 for v in VERDICTS}
    for r in reviews:
        counts[r.verdict] = counts.get(r.verdict, 0) + 1
    graded = [r for r in reviews if r.verdict != "not_applicable"]
    recalled = [r for r in reviews if r.recall_correct is not None]
    out = {
        "n": len(reviews), "n_graded": len(graded), "counts": counts,
        "frac_appropriate": (round(counts["appropriate"] / len(graded), 3)
                             if graded else None),
        "underreaction_minus_overreaction": counts["underreaction"] - counts["overreaction"],
        "self_recall_n": len(recalled),
        "self_recall_accuracy": (round(float(np.mean([r.recall_correct for r in recalled])), 3)
                                 if recalled else None),
    }
    stated: dict[str, int] = {}
    for r in reviews:
        if r.stated_update:
            stated[r.stated_update] = stated.get(r.stated_update, 0) + 1
    out["stated_updates"] = dict(sorted(stated.items(), key=lambda kv: -kv[1]))
    # does the stated update match the measured swing? a model that says
    # "STRENGTHEN" while cutting its conviction is narrating, not deciding
    pairs = [(r.stated_update, np.sign(
        ({"BUY": 1.0, "SELL": -1.0}.get(r.new_direction, 0.0) * r.new_conviction)
        - ({"BUY": 1.0, "SELL": -1.0}.get(r.prior_direction, 0.0) * r.prior_conviction)))
        for r in reviews if r.stated_update]
    want = {"STRENGTHEN": 1.0, "WEAKEN": -1.0, "MAINTAIN": 0.0, "REVERSE": -1.0}
    if pairs:
        ok = [1.0 if (s == "MAINTAIN" and g == 0.0) or
              (s != "MAINTAIN" and g == want[s]) else 0.0 for s, g in pairs]
        out["stated_update_matches_measured_swing"] = round(float(np.mean(ok)), 3)
        out["stated_update_n"] = len(pairs)
    return out
