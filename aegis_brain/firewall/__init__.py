"""The one-way firewall — the buildable version of Murat's brain.

WHAT WAS ASKED FOR
    "every backtest should make the brain better ... every instance logs into
    the brain, and the brain catches patterns, makes weights"

WHY THE LITERAL VERSION DESTROYS THE PROGRAMME
    An LLM that sees an outcome and then writes a prose lesson into memory has
    not learned anything: no weights moved. What it produced is an
    unregularised prior fitted to the test set and expressed in fluent English -
    therefore unfalsifiable, and *more* persuasive the more overfitted it is.
    Two independent external reviews flagged this; NIGHT-3 already measured the
    downstream version of it (LLM stock selection, t 0.04 / 0.93 over 204
    months, REJECTED).

WHAT IS BUILT INSTEAD
    The same ambition, arranged so it cannot fool us. Three layers and one
    irreversible data boundary:

        Layer 1  EXTRACTION      LLM. Reads anonymised, standardised text and
                                 emits a fixed JSON schema with per-field
                                 confidence and full provenance.
                                 *** NEVER SEES PRICES, RETURNS, OR OUTCOMES ***
        ========================= THE FIREWALL - one way only ==================
        Layer 2  LEARNING        No LLM. Ridge / GBM under purged CV with an
                                 embargo. THE ONLY PLACE WEIGHTS EVER CHANGE.
        Layer 3  ADJUDICATION    LLM. Explains, red-flags, vetoes. Read-only.
                                 Scored on Brier / log-score, NEVER on P&L.

    "The brain learns" then has a precise meaning: the calibration map
        (feature_type x regime x model_version) -> realised skill
    which needs hundreds of SCORED PREDICTIONS, not hundreds of backtests. That
    is why the forward paper lanes are the asset and the backtest is not.

THE STANDING RULE THIS ENCODES
    P&L never writes beliefs. Procedural memory (which datasets leak, which
    controls catch fakes) updates freely from history. Calibration memory
    updates only from scored extractions. Return beliefs update only from
    forward evidence.

NOT YET LICENSED
    No self-improving memory loop runs until Layer 1 has a MEASURED calibration
    curve against external ground truth. The first registered target is the
    PRisk replication (Hassan et al. QJE 2019; free data 2002-2021q2 at
    firmlevelrisk.com, verified live 2026-08-10). If our extractor cannot
    reproduce a published measurement, everything downstream is noise.
"""

from aegis_brain.firewall.contracts import (
    CHANNELS,
    LLM_CHANNELS,
    VETO_REASONS,
    Adjudication,
    Extraction,
    ExtractionRequest,
    FirewallViolation,
    LearningSample,
    ProvenanceStamp,
    VetoProposal,
)

__all__ = [
    "CHANNELS",
    "LLM_CHANNELS",
    "VETO_REASONS",
    "Adjudication",
    "Extraction",
    "ExtractionRequest",
    "FirewallViolation",
    "LearningSample",
    "ProvenanceStamp",
    "VetoProposal",
]
