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
from aegis_brain.discipline import prereg_power as PP
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
- dependence_unit: one globally distinct crisis episode, counted once no
  matter how many markets it touches
- cross_sectional_n: 1
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


# ── R13b: the overlap cap (added 2026-08-16, from N20) ─────────────────────
# These tests exist because R13 passed N20 — declared effect 0.642pp, claimed
# floor 0.46pp — and the block bootstrap then measured an honest MDE of
# 0.895-1.306pp. The design was unpowered and the gate said it was fine.


def test_max_independent_events_is_the_non_overlapping_window_count():
    assert PP.max_independent_events_per_year(20) == pytest.approx(12.6)
    assert PP.max_independent_events_per_year(252) == pytest.approx(1.0)
    assert PP.max_independent_events_per_year(0) is None
    assert PP.max_independent_events_per_year(None) is None


def test_r13b_refuses_the_exact_design_that_fooled_r13():
    """N20, as actually registered. The regression this guard exists for.

    Without the horizon the gate returned RESOLVABLE at a 0.46pp floor. With
    it, n_available is capped 1451 -> 454 and the design is refused.
    """
    res = PP.check_resolvability(
        "declared_effect_size = 0.642pp\n"
        "event_frequency_per_year = 40.3\n"
        "outcome_dispersion = 6.20pp\n"
        "outcome_horizon_days = 20\n")
    assert res["verdict"] == "UNPOWERED_AT_REGISTRATION"
    assert res["blocked"] is True
    assert res["n_declared"] == pytest.approx(1451, abs=1)
    assert res["n_available"] == pytest.approx(454, abs=1)
    assert res["overlap_factor"] == pytest.approx(3.2, abs=0.05)
    # the capped floor must land near the bootstrap's measured 0.895-1.306pp,
    # not near R13's original 0.46pp
    assert 0.7 < res["smallest_resolvable_effect_pp"] < 1.0


def test_the_same_design_passes_without_the_horizon_which_is_the_defect():
    """Pins the hole R13b closes, so it cannot silently reopen.

    This asserts the OLD behaviour on purpose: omit the horizon and R13b's
    calendar cap cannot see the overlap, so `n_available` stays the declared
    count and the floor stays optimistic. That hole is real and this path does
    not close it.

    R13c closes the same design by a SECOND route — 1451 available against
    ~734 required is under 20x headroom, so silence about the dependence unit
    refuses it whatever the horizon says. Both facts are pinned: the R13b hole
    is still open, and the design no longer gets through it.
    """
    res = PP.check_resolvability(
        "declared_effect_size = 0.642pp\n"
        "event_frequency_per_year = 40.3\n"
        "outcome_dispersion = 6.20pp\n")
    assert res["independence_assumed"] is True
    assert res["n_available"] == res["n_declared"]      # the R13b hole, open
    assert res["smallest_resolvable_effect_pp"] < 0.5   # the optimistic floor
    assert res["verdict"] == "UNDECLARED_DEPENDENCE_UNIT"    # caught anyway
    assert res["blocked"] is True


def test_a_genuinely_non_overlapping_declaration_is_not_capped():
    """The cap must not punish designs that declared honestly.

    Twelve 20-day episodes a year do not overlap, so nothing is capped and the
    guard is silent. R13c's declaration is supplied because the design is thin
    enough for a cross-section to matter — which is the point of R13c, not an
    exception to it.
    """
    res = PP.check_resolvability(
        "declared_effect_size = 3pp\n"
        "event_frequency_per_year = 12\n"
        "outcome_dispersion = 6.20pp\n"
        "outcome_horizon_days = 20\n"
        "dependence_unit = one 20-day window on a single index\n"
        "cross_sectional_n = 1\n")
    assert res["overlap_factor"] is None
    assert res["n_available"] == res["n_declared"]
    assert res["verdict"] == "RESOLVABLE"


def test_the_cap_reports_itself_in_the_refusal_text():
    """A cap the reader cannot see is a cap that gets argued with."""
    res = PP.check_resolvability(
        "declared_effect_size = 0.642pp\n"
        "event_frequency_per_year = 40.3\n"
        "outcome_dispersion = 6.20pp\n"
        "outcome_horizon_days = 20\n")
    assert "R13b" in res["why"]
    assert "1451" in res["why"] and "454" in res["why"]


# ── R13c: temporal non-overlap is necessary, not sufficient ────────────────

def _doc(**kw) -> str:
    """A minimal prereg body with the declared fields substituted in."""
    lines = "\n".join(f"{k} = {v}" for k, v in kw.items())
    return f"# PREREG — synthetic\n\n```\n{lines}\n```\n"


def test_a_cross_section_reduces_the_effective_sample():
    """100 securities on one window are 100 rows and not 100 events."""
    from aegis_brain.discipline.prereg_power import effective_sample

    alone = effective_sample(12.0, 20.0, horizon_days=20)
    pooled = effective_sample(12.0, 20.0, horizon_days=20,
                              cross_sectional_n=18)
    assert pooled["n_available_effective"] == pytest.approx(
        alone["n_available_effective"] / 18.0)
    assert pooled["total_reduction_factor"] > alone["total_reduction_factor"]


def test_clusters_reduce_it_too_and_the_reductions_compose():
    from aegis_brain.discipline.prereg_power import effective_sample

    ch = effective_sample(50.0, 10.0, horizon_days=20,
                          cross_sectional_n=6, cluster_size=5)
    # temporal cap first: 252/20 = 12.6/yr over 10 years = 126
    assert ch["temporal_nonoverlap_n"] == pytest.approx(126.0)
    assert ch["n_after_temporal"] == pytest.approx(126.0)
    assert ch["n_available_effective"] == pytest.approx(126.0 / 30.0)
    assert ch["n_raw"] == pytest.approx(500.0)


def test_effective_sample_never_inflates_a_declaration():
    """Divisors below 1 must not be usable to manufacture sample."""
    from aegis_brain.discipline.prereg_power import effective_sample

    ch = effective_sample(10.0, 10.0, cross_sectional_n=0.1, cluster_size=0.0)
    assert ch["n_available_effective"] == pytest.approx(100.0)


def test_a_thin_design_without_a_declared_dependence_unit_is_refused():
    """The R13c block: below 20x headroom, silence is not a declaration."""
    from aegis_brain.discipline.prereg_power import check_resolvability

    # 12.6/yr at a 20d horizon over 36y = 453 available; a 2.0pp effect at
    # 6.2pp dispersion needs ~76 => ~6x headroom, under the threshold
    r = check_resolvability(_doc(
        event_frequency_per_year=12.6, declared_effect_size="2.0pp",
        outcome_dispersion="6.2pp", outcome_horizon_days=20))
    assert r["verdict"] == "UNDECLARED_DEPENDENCE_UNIT"
    assert r["blocked"] is True
    assert "NECESSARY, NOT SUFFICIENT" in r["why"]


def test_declaring_the_unit_unblocks_the_same_design():
    """The mutation control for the block above — one field is the difference."""
    from aegis_brain.discipline.prereg_power import check_resolvability

    r = check_resolvability(_doc(
        event_frequency_per_year=12.6, declared_effect_size="2.0pp",
        outcome_dispersion="6.2pp", outcome_horizon_days=20,
        dependence_unit="one non-overlapping 20-day window on a single index",
        cross_sectional_n=1, cluster_size=1))
    assert r["verdict"] == "RESOLVABLE"
    assert r["blocked"] is False
    assert r["dependence_unit"]


def test_a_placeholder_is_not_a_declaration():
    """'n/a' is how a required field gets satisfied without being answered."""
    from aegis_brain.discipline.prereg_power import check_resolvability

    for junk in ("n/a", "TBD", "-", "?"):
        r = check_resolvability(_doc(
            event_frequency_per_year=12.6, declared_effect_size="2.0pp",
            outcome_dispersion="6.2pp", outcome_horizon_days=20,
            dependence_unit=junk))
        assert r["verdict"] == "UNDECLARED_DEPENDENCE_UNIT", junk


def test_an_enormous_design_is_not_blocked_for_silence():
    """Do not manufacture a crisis: 20x headroom cannot be flipped by an
    undeclared cross-section this programme has ever pooled."""
    from aegis_brain.discipline.prereg_power import check_resolvability

    r = check_resolvability(_doc(
        event_frequency_per_year=252, declared_effect_size="10pp",
        outcome_dispersion="6.2pp", outcome_horizon_days=1,
        corpus_years=36))
    assert r["verdict"] == "RESOLVABLE"
    assert r["headroom"] >= 20.0


def test_the_declared_cross_section_can_itself_push_a_design_under():
    """Declaring dependence honestly must be able to REFUSE the design, or the
    field is decorative."""
    from aegis_brain.discipline.prereg_power import check_resolvability

    kw = dict(event_frequency_per_year=12.6, declared_effect_size="2.0pp",
              outcome_dispersion="6.2pp", outcome_horizon_days=20,
              dependence_unit="one 20-day window across the whole panel")
    ok = check_resolvability(_doc(**kw, cross_sectional_n=1))
    bad = check_resolvability(_doc(**kw, cross_sectional_n=18))
    assert ok["verdict"] == "RESOLVABLE"
    assert bad["verdict"] == "UNPOWERED_AT_REGISTRATION"
    assert bad["n_available"] < ok["n_available"]
