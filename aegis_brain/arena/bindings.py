"""How a registry signal becomes something the panel can actually compute.

The signal registry is written in the language of MECHANISMS ("opportunistic
insider purchase", "gross profitability in the small segment"). The panel
speaks in the language of COLUMNS (`osap:GP`, `insider:tieaware12m`). This
module is the join, and it is deliberately explicit rather than clever:

* A registry signal with no panel implementation is EXCLUDED FROM THE ARENA and
  the exclusion is reported with a reason. It is not silently skipped, because
  a genome pool that quietly lost half its signals would still produce a
  confident-looking winner over a much smaller denominator than the manifest
  claims.
* A registry signal that is CLOSED has no binding at all. Attempting to bind
  one raises, so the search cannot reach a corpse even by a typo.
* The SYNTHETIC binding is separate, because the known-answer test needs the
  Arena to look for the same *kind* of thing in a world where that kind of
  thing is what was planted.
"""

from __future__ import annotations

#: registry signal_id -> panel signal key. Direction is handled by the panel
#: side (OSAP is pre-signed; native keys are named for their sign).
PANEL: dict[str, str] = {
    "profitability_small": "osap:GP",
    "insider_opportunistic": "insider:tieaware12m",
    "fusion_insider_profitability": "insider:cluster12m",
    "low_volatility": "native:vol_12m_low",
    "issuance_payout": "osap:NetPayoutYield",
    "short_interest_level": "osap:ShortInterest",
    "earnings_surprise_monthly": "osap:EarningsSurprise",
    # RISK_INPUT signals, permitted only as low-weight tie-breakers by the
    # genome generator — never alone, and never as a picker.
    "analyst_target_level_haircut": "ibes:tgt_upside",
    "drawdown_trigger_information": "native:mom_36_13_low",
}

#: Why the rest are absent. Every one of these is a real coverage gap and the
#: Arena report prints them, because "we searched everything permitted" is only
#: honest if the things not searched are named.
NO_PANEL_IMPLEMENTATION: dict[str, str] = {
    "rating_drift_3m": (
        "counts yfinance recommendation rows for the live book; there is no "
        "point-in-time rating-count panel back to 2002. IBES recddet was pulled "
        "on 2026-08-11 and could support one — not built tonight."),
    "catalyst_proximity": (
        "the calendar is forward-looking only (Finnhub earnings, v0). A "
        "historical dated-event panel would need EDGAR + openFDA assembled "
        "PIT, which exists in fragments and is not wired to the monthly panel."),
    "llm_event_extraction": (
        "no historical LLM extraction exists, and generating one over 252 "
        "months would read the future of every month it extracts (NIGHT-3)."),
    "options_expectation_sensor": (
        "OptionMetrics entitlement was never established: 578 tables "
        "catalogued, zero readable."),
    "macro_regime_allocator": (
        "ALLOCATOR role — asset-class exposure, never stock selection. "
        "Including it in a stock-picking Arena would be a category error."),
    "crash_composite_descriptive": (
        "descriptive index-level risk with no promotion path, and the model "
        "behind it is currently not deployed (overlay: model_not_deployed)."),
}

#: registry signal_id -> the synthetic signal that plays its part. The Arena's
#: known-answer test asks whether the search finds the planted mechanism, so
#: each real signal needs a synthetic stand-in of the same character.
SYNTHETIC: dict[str, str] = {
    "profitability_small": "synth:quality",
    "insider_opportunistic": "synth:insider",
    "fusion_insider_profitability": "synth:insider",
    "low_volatility": "synth:reversal",
    "issuance_payout": "synth:quality",
    "short_interest_level": "synth:reversal",
    "earnings_surprise_monthly": "synth:momentum",
    "analyst_target_level_haircut": "synth:analyst_rev",
    "drawdown_trigger_information": "synth:reversal",
}


class BindingError(KeyError):
    """A signal cannot be evaluated, and the reason must reach the report."""


def panel_key(signal_id: str, registry) -> str:
    sig = registry.get(signal_id)
    if sig.is_closed:
        raise BindingError(
            f"{signal_id} is CLOSED and has no panel binding by design. If a "
            f"new mechanism needs it as a control arm, bind it explicitly in "
            f"that trial, not through the Arena's signal pool.")
    try:
        return PANEL[signal_id]
    except KeyError:
        raise BindingError(
            f"{signal_id} has no panel implementation: "
            f"{NO_PANEL_IMPLEMENTATION.get(signal_id, 'reason not recorded')}"
        ) from None


def synthetic_key(signal_id: str) -> str:
    try:
        return SYNTHETIC[signal_id]
    except KeyError:
        raise BindingError(f"{signal_id} has no synthetic stand-in") from None


def evaluable(registry) -> tuple[list[str], dict[str, str]]:
    """(signals the Arena can actually run, reasons the others cannot)."""
    ok, why = [], {}
    for sig in registry.pm_allowed():
        try:
            panel_key(sig.signal_id, registry)
        except BindingError as exc:
            why[sig.signal_id] = str(exc).split(": ", 1)[-1]
            continue
        ok.append(sig.signal_id)
    return sorted(ok), why
