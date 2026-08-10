"""The citation ledger, with the qualifier as a required field.

NIGHT-7's T1 gate established that this programme's citation failure is not
fabrication. Reviews quoted numbers that were real, published, and correctly
transcribed — with the qualifier that made them true removed. A long-short alpha
became a long-only expectation. A rebalancing premium measured against
buy-and-hold became alpha against a rebalanced benchmark. A 131.83% return
appeared without its Sharpe of 0.31, which inverts what the paper found.

Prose cannot enforce a qualifier: T1 was a prose gate and the very night it was
written, three reviews still arrived carrying stripped numbers. So the qualifier
is a field, `transfers_to_aegis` is a field, and a citation that omits either
does not load.

The one thing this module cannot do is check that a qualifier is *honest*. It
checks that one was written and that the direction of transfer was declared.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from aegis_brain.config import MODULE_ROOT

LEDGER = MODULE_ROOT / "docs" / "CITATIONS.json"

REQUIRED = ("id", "claim", "source", "verdict", "qualifier",
            "transfers_to_aegis")
VERDICTS = {"V", "V-C", "V-M", "P", "U", "X"}
#: Verdicts whose numbers may never appear in an Aegis claim.
UNQUOTABLE = {"U", "X"}
#: A qualifier this short is a placeholder, not a qualifier.
MIN_QUALIFIER_CHARS = 40


class CitationError(ValueError):
    """A citation that cannot be used as written."""


@dataclass(frozen=True)
class Citation:
    id: str
    claim: str
    source: str
    verdict: str
    qualifier: str
    transfers_to_aegis: bool
    value: float | None = None
    units: str | None = None
    how: str | None = None
    why_not: str | None = None

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise CitationError(
                f"{self.id}: verdict {self.verdict!r} not in {sorted(VERDICTS)}")
        if len(self.qualifier.strip()) < MIN_QUALIFIER_CHARS:
            raise CitationError(
                f"{self.id}: qualifier is {len(self.qualifier.strip())} chars. "
                "A qualifier states the population, the leg, the benchmark or "
                "the window that makes the number true — the thing whose "
                "absence caused every citation failure NIGHT-7 found.")
        if self.transfers_to_aegis and not (self.how or "").strip():
            raise CitationError(
                f"{self.id}: transfers_to_aegis is true but `how` is empty. "
                "Declaring that a number transfers is the claim; saying how it "
                "transfers is the evidence for it.")
        if not self.transfers_to_aegis and not (self.why_not or "").strip():
            raise CitationError(
                f"{self.id}: transfers_to_aegis is false but `why_not` is "
                "empty. A blocked citation must record what blocks it, or the "
                "next session re-quotes it.")

    @property
    def quotable(self) -> bool:
        return self.verdict not in UNQUOTABLE


def load(path: Path | None = None) -> dict[str, Citation]:
    """Read the ledger. Raises on the first citation that is not usable."""
    p = path or LEDGER
    body = json.loads(p.read_text(encoding="utf-8"))
    out: dict[str, Citation] = {}
    for raw in body["citations"]:
        missing = [f for f in REQUIRED if f not in raw]
        if missing:
            raise CitationError(
                f"{raw.get('id', '<no id>')}: missing required field(s) "
                f"{missing}")
        c = Citation(**{k: v for k, v in raw.items()
                        if k in Citation.__dataclass_fields__})
        if c.id in out:
            raise CitationError(f"duplicate citation id {c.id}")
        out[c.id] = c
    return out


def check_use(cid: str, ledger: dict[str, Citation] | None = None) -> Citation:
    """Fetch a citation for use in a claim, refusing the ones that cannot be.

    Call this at the point a number enters a write-up, not at the point it is
    read. The failure being prevented is quoting an unverified or non-
    transferring figure, and that happens at the writing end.
    """
    led = ledger if ledger is not None else load()
    if cid not in led:
        raise CitationError(
            f"{cid} is not in the ledger. A number with no ledger entry has "
            "not been verified, and NIGHT-7 measured what that costs.")
    c = led[cid]
    if not c.quotable:
        raise CitationError(
            f"{cid} carries verdict {c.verdict} ({'unverifiable' if c.verdict == 'U' else 'invented'}) "
            f"and may not be quoted. {c.qualifier}")
    if not c.transfers_to_aegis:
        raise CitationError(
            f"{cid} does not transfer to Aegis and may not be used as an "
            f"expectation for this book. {c.why_not}")
    return c
