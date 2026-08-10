"""N6 — the verdict referee: this programme's own failure checklist, as code.

Every night ends with a write-up, and the write-up is where the errors have
actually lived. Not in the arithmetic — in the sentence around it. The record:

  NIGHT-4  a report whose statistics said UNRESOLVED printed the word REJECT.
           The rule against it existed, in prose, and lost to the author.
  NIGHT-7  five reviews quoted real published numbers with the qualifier that
           made them true removed.
  NIGHT-7  the DSR was described as a posterior probability, which it is not.
  NIGHT-7B a turnover claim was quoted from the monthly panel the same night
           CANON 15 was written forbidding exactly that.
  NIGHT-8  a cost comparison in dollars flattered the arm that compounded less.

Each one was caught by a reader afterwards. This module runs the checks the
readers ran, before the document ships. It is deliberately mechanical: it flags
what can be flagged from text and receipts, and it says plainly what it cannot
see — a qualifier's honesty, a mechanism's plausibility, an idea's worth.

A finding here is a reading list, never a verdict.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from aegis_brain.discipline.citations import CitationError, check_use, load
from aegis_brain.discipline.manifest import claim_coverage
from aegis_brain.verdicts import Verdict, check_language

#: States whose write-up must carry the size it could have seen. A null without
#: an MDE is the NIGHT-4 error in its purest form.
NEEDS_MDE = {"UNRESOLVED", "POWER_FAILED"}

_STATE = re.compile(
    r"\b(CONFIRMED|UNRESOLVED|FACTOR_EXPLAINED|IMPLEMENTATION_FAILED|"
    r"DATA_FAILED|POWER_FAILED|PLACEBO_FAILED|LEAKAGE_FAILED|REJECTED)\b")
_MDE = re.compile(r"\bMDE\b", re.IGNORECASE)
_CITATION_ID = re.compile(r"`([A-Z][A-Z0-9-]{6,})`")
#: Phrases that assert a cost/return comparison. CANON 16: these need a
#: denominator that is not the winner's.
_DOLLAR_COMPARISON = re.compile(
    r"(cheaper|more expensive|costs? (?:more|less)|saves?)\b[^.\n]{0,80}"
    r"\$[\d,]+", re.IGNORECASE)
#: What counts as a size-normalised cost figure. It must be about COST: a bare
#: "/yr" anywhere nearby is not a denominator, and accepting one let NIGHT-7B's
#: "the ensemble is CHEAPER by $19,390" pass because an unrelated CAGR gap four
#: lines below happened to end in "/yr".
_NORMALISED = re.compile(
    r"(cost drag|of average nav|bps of traded|per dollar traded|"
    r"cost per dollar)", re.IGNORECASE)
#: Lines either side that count as "beside the claim". Tight on purpose.
_WINDOW = 2


@dataclass
class Finding:
    check: str
    severity: str            # blocker | question | note
    line: int
    detail: str

    def as_dict(self) -> dict:
        return {"check": self.check, "severity": self.severity,
                "line": self.line, "detail": self.detail}


def _lines(doc: str) -> list[tuple[int, str]]:
    return list(enumerate(doc.splitlines(), 1))


def check_verdict_language(doc: str) -> list[Finding]:
    """A paragraph may not claim more than the state named in it grants."""
    out = []
    for i, line in _lines(doc):
        m = _STATE.search(line)
        if not m:
            continue
        try:
            state = Verdict(m.group(1))
        except ValueError:
            continue
        for bad in check_language(state, line):
            out.append(Finding("verdict-language", "blocker", i, bad))
    return out


def check_mde_present(doc: str) -> list[Finding]:
    """UNRESOLVED and POWER_FAILED must say what they could have seen."""
    out = []
    for i, line in _lines(doc):
        m = _STATE.search(line)
        if not m or m.group(1) not in NEEDS_MDE:
            continue
        window = "\n".join(l for j, l in _lines(doc) if abs(j - i) <= 3)
        if not _MDE.search(window):
            out.append(Finding(
                "mde-missing", "blocker", i,
                f"{m.group(1)} stated with no MDE within three lines. A null "
                "without the size it could have detected is the NIGHT-4 error."))
    return out


def check_citations(doc: str) -> list[Finding]:
    """Any citation id invoked must be in the ledger and must transfer."""
    out, ledger = [], load()
    for i, line in _lines(doc):
        for cid in _CITATION_ID.findall(line):
            if cid not in ledger:
                continue                    # not every backtick is a citation
            try:
                check_use(cid, ledger)
            except CitationError as e:
                out.append(Finding("citation-does-not-transfer", "blocker", i,
                                   str(e)))
    return out


def check_cost_denominator(doc: str) -> list[Finding]:
    """CANON 16 — a dollar cost comparison needs a size-normalised one beside it.

    Two arms that start at the same NAV do not end at the same NAV, so totalling
    cost in dollars rewards whichever arm made less money. This is the check
    that would have caught NIGHT-7B's 'the ensemble is cheaper'.
    """
    out = []
    for i, line in _lines(doc):
        if not _DOLLAR_COMPARISON.search(line):
            continue
        window = "\n".join(l for j, l in _lines(doc) if abs(j - i) <= _WINDOW)
        if not _NORMALISED.search(window):
            out.append(Finding(
                "cost-denominator", "blocker", i,
                "a cost comparison in DOLLARS with no size-normalised figure "
                "nearby (cost drag per year against average NAV, or bps of "
                "traded). CANON 16: the arm that compounded less trades fewer "
                "dollars for the same turnover rate."))
    return out


def check_unbacked_numbers(doc: str, scalars: dict, prior: dict | None = None,
                           **kw) -> list[Finding]:
    cc = claim_coverage(doc, scalars, prior=prior, **kw)
    return [Finding("unbacked-number", "question", u["line"],
                    f"{u['raw']} is backed by no receipt in the programme")
            for u in cc["unbacked"]]


def check_branch_accounting(doc: str, expected_new_branches: int | None,
                            denominator_before: int | None) -> list[Finding]:
    """Did the write-up count its own branches and move the denominator?"""
    out = []
    if expected_new_branches is None or denominator_before is None:
        return [Finding("branch-accounting", "question", 0,
                        "no branch count supplied to the referee, so trial-count "
                        "accounting was not checked")]
    after = denominator_before + expected_new_branches
    if not re.search(rf"\b{after}\b", doc):
        out.append(Finding(
            "branch-accounting", "blocker", 0,
            f"{expected_new_branches} branches were registered but the updated "
            f"denominator {after} does not appear in the document. Every "
            "examination leaves a ledger entry (CANON 11)."))
    return out


def review(doc: str, *, scalars: dict | None = None,
           prior: dict | None = None,
           expected_new_branches: int | None = None,
           denominator_before: int | None = None,
           collision_draws: int = 40) -> dict:
    """Run every mechanical check. Returns findings plus what was NOT checked."""
    findings: list[Finding] = []
    findings += check_verdict_language(doc)
    findings += check_mde_present(doc)
    findings += check_citations(doc)
    findings += check_cost_denominator(doc)
    findings += check_branch_accounting(doc, expected_new_branches,
                                        denominator_before)
    if scalars is not None:
        findings += check_unbacked_numbers(doc, scalars, prior,
                                           collision_draws=collision_draws)

    by_sev = {s: [f.as_dict() for f in findings if f.severity == s]
              for s in ("blocker", "question", "note")}
    return {
        "findings": [f.as_dict() for f in findings],
        "counts": {k: len(v) for k, v in by_sev.items()},
        "blockers": by_sev["blocker"],
        "clean": not by_sev["blocker"],
        "not_checked": [
            "whether a qualifier attached to a number is HONEST — the NIGHT-7 "
            "failure was true numbers in true-looking sentences, and no regex "
            "reaches that",
            "whether a mechanism is plausible or an idea is worth running",
            "whether the statistics behind a state were computed correctly — "
            "this reads the write-up, not the arithmetic",
            "leakage in the experiment itself; the purge is checked by the "
            "trial's own leak arm, not here",
        ],
    }
