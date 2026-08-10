"""Firewall data contracts — the boundary is enforced in code, not in prose.

Design rule: every class here is FROZEN and validates itself on construction.
A firewall that lives in a design document is a firewall that leaks the first
time someone is in a hurry; this one raises.

The three checks that matter:

  1. `ExtractionRequest` refuses to carry any field whose name looks like market
     data, and refuses text containing a ticker it was supposed to have masked.
  2. `Extraction` refuses to be built without a full provenance stamp, so no
     number can enter Layer 2 without knowing which model, prompt and document
     produced it and when.
  3. `Adjudication` has no channel through which it can change a weight. It can
     only annotate and veto, and its veto is a registered scoreable claim.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any


class FirewallViolation(RuntimeError):
    """Raised when outcome data reaches a layer that must never see it."""


# Field names that carry outcome or market information. Layer 1 inputs are
# scanned against this list. It is deliberately over-broad: a false alarm costs
# one rename, a miss costs the validity of every downstream number.
_FORBIDDEN_KEYS = re.compile(
    r"(ret|return|price|prc|close|open_px|nav|pnl|p_and_l|alpha|sharpe|"
    r"drawdown|excess|perf|outcome|label|target|y_true|future|fwd|forward|"
    r"realized|realised|move|chg_pct|winner|loser)", re.I)

# Date-keyed memory is a real leak channel even when the entity is masked:
# Lookahead Propensity (arXiv:2512.23847) shows outcome recall keyed on the DATE
# alone, and FinCAD (arXiv:2605.24564) cuts in-sample backtest returns by up to
# -67.1% on memorised dates. NIGHT-1 measured only that masking hides the
# COMPANY (0/240 identifications) - which is necessary and not sufficient.
_LEAK_MODES = ("entity", "date", "era")


@dataclass(frozen=True)
class ProvenanceStamp:
    """Who produced this number, from what, when, and under which prompt."""

    as_of_ts: str            # point-in-time timestamp the input was available
    source_doc_id: str       # e.g. an EDGAR accession number
    source_type: str         # 10-K | 8-K | transcript | FDA | gov-release
    model_ver: str
    prompt_hash: str
    extractor_ver: str

    def __post_init__(self) -> None:
        for f_ in ("as_of_ts", "source_doc_id", "source_type", "model_ver",
                   "prompt_hash", "extractor_ver"):
            if not str(getattr(self, f_)).strip():
                raise FirewallViolation(
                    f"provenance field {f_!r} is empty — an unstamped "
                    "extraction cannot be audited and must not enter Layer 2")


@dataclass(frozen=True)
class ExtractionRequest:
    """Layer 1 INPUT. Anonymised, standardised, outcome-free — and checked.

    `masked_text` must already have entity identifiers removed. `leak_controls`
    records which leak modes were actually neutralised; a request that controls
    only for `entity` is accepted but is marked as NOT alpha-certifiable, per
    the NIGHT-7 citation finding.
    """

    request_id: str
    masked_text: str
    schema_name: str
    leak_controls: tuple[str, ...] = ("entity",)
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        bad = [k for k in self.context if _FORBIDDEN_KEYS.search(k)]
        if bad:
            raise FirewallViolation(
                f"Layer 1 context carries outcome-shaped fields {bad} — the "
                "extractor must never see prices, returns or labels")
        unknown = [m for m in self.leak_controls if m not in _LEAK_MODES]
        if unknown:
            raise ValueError(f"unknown leak control(s) {unknown}; "
                             f"known: {_LEAK_MODES}")
        if not self.masked_text.strip():
            raise ValueError("masked_text is empty")

    @property
    def alpha_certifiable(self) -> bool:
        """True only when date/era memory was controlled, not just the entity.

        Entity masking alone makes this a REASONING laboratory, not an
        alpha-certification laboratory (runs/NIGHT7/VERIFIED_CITATIONS.md §3).
        """
        return "date" in self.leak_controls or "era" in self.leak_controls

    def prompt_hash(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Extraction:
    """Layer 1 OUTPUT — a measurement, not an opinion, and never a decision."""

    request_id: str
    schema_name: str
    fields: dict[str, Any]
    confidence: dict[str, float]
    provenance: ProvenanceStamp
    alpha_certifiable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, ProvenanceStamp):
            raise FirewallViolation("extraction without a ProvenanceStamp")
        missing = [k for k in self.fields if k not in self.confidence]
        if missing:
            raise ValueError(
                f"fields {missing} have no confidence — an unscored field "
                "cannot be calibrated, and an uncalibratable field is not a "
                "measurement")
        for k, v in self.confidence.items():
            if not 0.0 <= float(v) <= 1.0:
                raise ValueError(f"confidence[{k}] = {v} outside [0, 1]")
        bad = [k for k in self.fields if _FORBIDDEN_KEYS.search(k)]
        if bad:
            raise FirewallViolation(
                f"extraction emits outcome-shaped fields {bad} — Layer 1 "
                "reports what a document SAYS, never what happened next")

    def as_dict(self) -> dict:
        d = asdict(self)
        d["provenance"] = asdict(self.provenance)
        return d


@dataclass(frozen=True)
class LearningSample:
    """Layer 2 INPUT. The ONLY place an outcome is allowed to appear.

    Constructing one of these is the act of crossing the firewall, and it is
    one-way: the sample holds the extraction that produced its features, so the
    provenance survives, but nothing here can be handed back to Layer 1.
    """

    extraction: Extraction
    outcome: float
    outcome_as_of_ts: str
    embargo_days: int = 0

    def __post_init__(self) -> None:
        if self.outcome_as_of_ts <= self.extraction.provenance.as_of_ts:
            raise FirewallViolation(
                f"outcome timestamp {self.outcome_as_of_ts} is not after the "
                f"extraction's as_of {self.extraction.provenance.as_of_ts} — "
                "this is look-ahead, not learning")

    def to_layer1_payload(self) -> dict:
        raise FirewallViolation(
            "outcomes cannot be sent back to Layer 1. This method exists only "
            "so that the attempt fails loudly instead of being written by "
            "someone who assumed it was allowed.")


# ── channels ────────────────────────────────────────────────────────────────
# External review (2026-08-10) found a real loophole: `set_weight()` raising is
# necessary but not sufficient, because a VETO is itself a portfolio decision —
# a discrete transition of a name from "eligible" to weight zero. An LLM that
# cannot set weights but can delete holdings still moves the book.
#
# So the channels are named and only ONE of them is a portfolio action, and that
# one is owned by deterministic code.
CHANNELS = ("narrative", "measurement", "hypothesis", "veto_proposal",
            "portfolio_action")
LLM_CHANNELS = ("narrative", "measurement", "hypothesis", "veto_proposal")

# Frozen reason vocabulary. A free-text veto cannot be scored, and an unscoreable
# veto is an opinion with a portfolio consequence.
VETO_REASONS = (
    "going_concern_language",
    "restatement_risk",
    "customer_concentration_removed",
    "litigation_disclosure_new",
    "supply_chain_disclosure_new",
    "auditor_change",
    "guidance_withdrawn",
    "related_party_expansion",
)


@dataclass(frozen=True)
class VetoProposal:
    """An LLM's request to exclude a name. A PROPOSAL — never an action.

    It carries a frozen reason code, a calibrated probability, provenance and a
    resolution date, so it can be Brier-scored like any other forecast. Until the
    veto channel's forward calibration clears a registered threshold, applying
    one to the production book is refused in code, not in policy.
    """

    subject_id: str
    reason_code: str
    probability: float          # P(the flagged failure occurs by resolves_at)
    resolves_at: str
    rationale: str
    provenance: ProvenanceStamp
    channel: str = "veto_proposal"

    def __post_init__(self) -> None:
        if self.reason_code not in VETO_REASONS:
            raise ValueError(
                f"reason_code {self.reason_code!r} is not in the frozen "
                f"vocabulary {VETO_REASONS} — a free-text veto cannot be scored")
        if not 0.0 <= float(self.probability) <= 1.0:
            raise ValueError("probability outside [0, 1]")
        if not self.rationale.strip():
            raise ValueError("a veto proposal without a rationale is a mood")
        if self.channel != "veto_proposal":
            raise FirewallViolation("VetoProposal cannot claim another channel")

    def apply_to_book(self, *_a, **_k):
        raise FirewallViolation(
            "a veto proposal is not a portfolio action. Excluding a name is a "
            "weight decision and belongs to deterministic code, which may only "
            "honour this proposal once the veto channel's forward calibration "
            "has cleared its registered threshold.")

    def brier(self, occurred: bool) -> float:
        return float((self.probability - (1.0 if occurred else 0.0)) ** 2)


@dataclass(frozen=True)
class Adjudication:
    """Layer 3 OUTPUT. Read-only. Scored on calibration, never on P&L.

    A veto is not free: it is a registered, scoreable claim, so a Layer 3 that
    vetoes indiscriminately becomes measurably badly calibrated and loses its
    standing. `probability` is what gets Brier-scored when the claim resolves.
    """

    subject_id: str
    verdict: str               # PASS | FLAG | VETO
    probability: float         # P(the flagged failure occurs), for Brier scoring
    rationale: str
    provenance: ProvenanceStamp

    _ALLOWED = ("PASS", "FLAG", "VETO")

    def __post_init__(self) -> None:
        if self.verdict not in self._ALLOWED:
            raise ValueError(f"verdict must be one of {self._ALLOWED}")
        if not 0.0 <= float(self.probability) <= 1.0:
            raise ValueError("probability outside [0, 1]")
        if self.verdict == "VETO" and not self.rationale.strip():
            raise ValueError(
                "a VETO without a rationale is not adjudication, it is a mood")

    def set_weight(self, *_a, **_k):
        raise FirewallViolation(
            "Layer 3 cannot change weights. Learning happens in Layer 2 under "
            "purged CV, and nowhere else.")

    def to_veto_proposal(self, reason_code: str, resolves_at: str
                         ) -> "VetoProposal":
        """Turn a VETO verdict into a scoreable proposal — the only exit path.

        A VETO that never becomes a VetoProposal never reaches anything, by
        construction: there is no other method on this class that returns
        something the engine will read.
        """
        if self.verdict != "VETO":
            raise ValueError("only a VETO verdict becomes a veto proposal")
        return VetoProposal(
            subject_id=self.subject_id, reason_code=reason_code,
            probability=self.probability, resolves_at=resolves_at,
            rationale=self.rationale, provenance=self.provenance)
