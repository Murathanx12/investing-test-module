"""R13 — the effect-size floor must refuse before compute, and must not refuse
everything.

The failure this guards is not hypothetical. The programme registered, ran and
adjudicated crisis-conditioned mechanisms for a month against a corpus that N8
later measured at 25 independent episodes, needing 273 for the effect sizes
being claimed. Every one of those adjudications was arithmetic that could not
have come out any other way.

Both directions are tested, because a gate that blocks everything is switched
off in a week and a gate that blocks nothing was never running.
"""
from __future__ import annotations

import pytest

from aegis_brain.discipline import prereg_lint as PL
from aegis_brain.discipline.prereg_power import (DISPERSION_PRESETS_PP,
                                                 check_resolvability,
                                                 n_required,
                                                 parse_power_fields,
                                                 resolvable_effect)

#: A crisis-conditioned claim at the effect size the programme kept declaring.
#: 0.7 crises/yr over 36 years = 25 episodes; 3pp at crisis dispersion needs 273.
UNRESOLVABLE = """
# TRIAL-EXAMPLE-CRISIS

- event_frequency_per_year: 0.7
- declared_effect_size: 3pp
- outcome_dispersion: crisis
"""

#: The same corpus, an effect ten times larger. 10pp needs 25 — exactly what
#: N8's curve says is the boundary, and exactly why R14 exists.
RESOLVABLE_CRISIS = """
- event_frequency_per_year: 0.7
- declared_effect_size: 10pp
- outcome_dispersion: crisis
"""

#: R14's point, expressed as arithmetic: the same 3pp claim conditioned on an
#: event class with real sample sails through.
RESOLVABLE_EVENT = """
- event_frequency_per_year: 4000
- declared_effect_size: 3pp
- outcome_dispersion: single_name
"""


def test_the_crisis_claim_the_programme_kept_registering_is_refused():
    r = check_resolvability(UNRESOLVABLE)
    assert r["blocked"] is True
    assert r["verdict"] == "UNPOWERED_AT_REGISTRATION"
    assert 270 < r["n_required"] < 276
    assert 24 < r["n_available"] < 26


def test_the_refusal_names_the_effect_that_would_be_registrable():
    """A refusal that only says no sends the author away with nothing."""
    r = check_resolvability(UNRESOLVABLE)
    floor = r["smallest_resolvable_effect_pp"]
    assert floor is not None
    # 25 episodes at 17.7pp dispersion resolves ~10pp — N8's curve, read the
    # other way round.
    assert 9.0 < floor < 11.5
    assert f"{floor:.2g}pp" in r["why"]


def test_the_same_corpus_passes_at_ten_percentage_points():
    r = check_resolvability(RESOLVABLE_CRISIS)
    assert r["blocked"] is False
    assert r["verdict"] == "RESOLVABLE"


def test_r14_moving_to_events_makes_a_three_point_claim_resolvable():
    r = check_resolvability(RESOLVABLE_EVENT)
    assert r["blocked"] is False
    assert r["n_available"] > r["n_required"]


def test_a_missing_declaration_is_a_refusal_not_a_default():
    """Defaulting a missing field is how a guard becomes decoration."""
    r = check_resolvability("- declared_effect_size: 3pp\n")
    assert r["blocked"] is True
    assert r["verdict"] == "MISSING_POWER_FIELDS"
    assert "event_frequency_per_year" in r["why"]
    assert "outcome_dispersion" in r["why"]


def test_an_unfilled_template_placeholder_does_not_parse_as_a_declaration():
    """`<e.g. 10pp>` contains a number. It must not count as one.

    Without this the template — and every copy of it that changed nothing —
    reads as a fully declared, fully resolvable proposal.
    """
    placeholder = """
    - event_frequency_per_year: <INDEPENDENT episodes per year, not days>
    - declared_effect_size: <e.g. 10pp, with the economic argument above it>
    - outcome_dispersion: <a number in pp, or a preset: crisis (17.7pp)>
    """
    f = parse_power_fields(placeholder)
    assert set(f["missing"]) == {"event_frequency_per_year",
                                 "declared_effect_size", "outcome_dispersion"}


@pytest.mark.parametrize("raw,expected_pp", [
    ("3pp", 3.0), ("3 pp", 3.0), ("3%", 3.0), ("300bps", 3.0),
    ("0.03", 3.0), ("10", 10.0),
])
def test_effect_sizes_are_accepted_in_the_units_people_actually_write(
        raw, expected_pp):
    f = parse_power_fields(
        f"- event_frequency_per_year: 1\n- declared_effect_size: {raw}\n"
        f"- outcome_dispersion: calm\n")
    assert f["declared_effect_size_pp"] == pytest.approx(expected_pp, rel=1e-6)


def test_dispersion_presets_carry_their_source():
    f = parse_power_fields(
        "- event_frequency_per_year: 1\n- declared_effect_size: 3pp\n"
        "- outcome_dispersion: crisis\n")
    assert f["outcome_dispersion_pp"] == DISPERSION_PRESETS_PP["crisis"]
    assert f["dispersion_source"] == "preset:crisis"


def test_n_required_scales_as_the_inverse_square_of_the_effect():
    """The whole reason rare-state work is hopeless: halve d, quadruple n."""
    a = n_required(3.0, 17.7)
    b = n_required(6.0, 17.7)
    assert a / b == pytest.approx(4.0, rel=1e-9)


def test_resolvable_effect_is_the_inverse_of_n_required():
    n = n_required(10.0, 17.7)
    assert resolvable_effect(n, 17.7) == pytest.approx(10.0, rel=1e-9)


def test_lint_defaults_the_power_gate_ON():
    """A guard that must be switched on is a guard that will not be."""
    corpus = PL.load_corpus()
    res = PL.lint("A proposal about supplier concentration in freight tariff "
                  "filings, with no declared frequency or effect size at all.",
                  corpus=corpus)
    assert res["verdict"] == "MISSING_POWER_FIELDS"


def test_an_unresolvable_design_is_refused_even_when_the_wording_is_novel():
    """Novelty does not make an unanswerable question answerable."""
    corpus = PL.load_corpus()
    res = PL.lint(
        "We propose measuring the dispersion of delivery lead times disclosed "
        "in freight-forwarder tariff filings as a proxy for inventory pipeline "
        "stress, evaluated only in crisis regimes.\n"
        "- event_frequency_per_year: 0.7\n"
        "- declared_effect_size: 3pp\n"
        "- outcome_dispersion: crisis\n", corpus=corpus)
    assert res["verdict"] == "UNPOWERED_AT_REGISTRATION"
    assert res["power"]["n_required"] > res["power"]["n_available"]
