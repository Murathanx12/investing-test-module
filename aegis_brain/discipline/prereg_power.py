"""R13 — an effect-size floor enforced at REGISTRATION, not after adjudication.

WHY THIS EXISTS (2026-08-16, from N8 + N2 + N4)
==============================================
Three measurements taken on the same night say one thing together:

* **N8.** `n_required` scales as `1/d²`. At the dispersion of the Gym's crisis
  slices (~17.7pp) a **3pp** edge needs **273** independent episodes, a 5pp edge
  needs **98**, and a **10pp** edge needs **25**.
* **N2.** Twelve markets over thirty-six years supply **25 to 80** independent
  crisis episodes. That is the world's entire stock, not this decade's.
* **N4.** The six mechanisms adjudicated against that stock address roughly
  nothing — coverage lift indistinguishable from the library's own base rate.

So the programme spent a month adjudicating claims whose samples could never
have resolved them. **Rare states do not accumulate sample.** Twenty-five crisis
episodes is all there will ever be.

The guard is cheap because it is arithmetic, and it runs at the only moment when
it can still save the compute: registration. A pre-registration must now declare

    event_frequency_per_year:   how often the CONDITIONING STATE occurs,
                                counted as INDEPENDENT episodes, not days
    declared_effect_size:       the smallest effect worth acting on, in pp
    outcome_dispersion:         the sd of the outcome IN that state — a number
                                in pp, or one of the measured presets below

and if `n_required(effect, dispersion)` exceeds the sample the corpus can ever
supply, the proposal is **UNPOWERED_AT_REGISTRATION** *before* compute rather
than NOT_DETECTABLE after it.

WHAT THIS GUARD IS NOT
======================
It does not say the mechanism is false — nothing here is evidence about the
world. It says *this design cannot resolve this claim*, which leaves exactly two
honest moves: declare a larger effect (and defend it economically), or find a
conditioning unit with more sample (R14: events, not regimes).

And the effect size must come from **economics** — turnover, cost, capacity,
drawdown consequence, probability of ruin — never from what the available sample
happens to be able to see. Choosing 10pp *because* 25 episodes can resolve 10pp
is the same error in the opposite direction, and it is the one this module is
most likely to be used to commit.
"""
from __future__ import annotations

import math
import re

#: Two-sided 5%, 80% power — the same constants the Gym's `power.py` freezes, so
#: a claim cannot be resolvable here and unresolvable there.
Z_ALPHA_TWO_SIDED_05 = 1.959963984540054
Z_POWER_80 = 0.8416212335729143

#: Outcome dispersion measured on the Gym's own slices, 2026-08-16 (N8). These
#: are presets, not laws: a proposal about a different outcome owes its own
#: number and may pass one in place of a name.
DISPERSION_PRESETS_PP: dict[str, float] = {
    "crisis": 17.7,
    "stress": 17.7,
    "calm": 1.5,
    "normal": 1.5,
    # Cross-sectional single-name dispersion is far wider than an index's and
    # is the reason R14 points at events: the same edge is cheaper to resolve
    # per observation only because there are thousands of observations.
    "single_name": 12.0,
}

#: The whole recorded supply, from N2: twelve markets, thirty-six years. A
#: proposal may declare fewer years; it may not declare more without saying
#: where the history comes from.
DEFAULT_CORPUS_YEARS = 36.0

REQUIRED_FIELDS = ("event_frequency_per_year", "declared_effect_size",
                   "outcome_dispersion")

#: Trading days per year. The overlap check below is in trading days because
#: `outcome_horizon_days` is quoted in them everywhere in this programme.
TRADING_DAYS_PER_YEAR = 252.0

#: Optional. Declaring it turns on the overlap check (R13b) — see
#: `max_independent_events_per_year`. It is optional rather than required so
#: that registrations predating this check still lint; a proposal that omits it
#: is told, in the PASS text, that its `n_available` is assuming independence.
OPTIONAL_FIELDS = ("outcome_horizon_days",)

_FIELD_RE = {
    f: re.compile(rf"^\s*[-*]?\s*\**{f}\**\s*[:=]\s*\**\s*(?P<v>[^\n|]+?)\**\s*$",
                  re.IGNORECASE | re.MULTILINE)
    for f in REQUIRED_FIELDS + OPTIONAL_FIELDS + ("corpus_years",)
}


def max_independent_events_per_year(horizon_days: float) -> float | None:
    """How many NON-OVERLAPPING `horizon_days` windows fit in a year.

    R13b, added 2026-08-16 after N20. R13's docstring asks for
    `event_frequency_per_year` "counted as INDEPENDENT episodes, not days", and
    then trusts the author to have done that. N20 declared 40.3/yr — the rate
    the precursor fires on DAYS — for a 20-day outcome, and R13 passed it:
    claimed floor 0.46pp against a declared 0.642pp, while the block
    bootstrap's honest MDE was 0.895-1.306pp. The design was unpowered and the
    gate said it was fine.

    The declaration was wrong and the gate could not see it. This is the
    arithmetic that can: at a 20-day horizon a year holds at most 252/20 = 12.6
    non-overlapping episodes, so a declared 40.3 is *proof* the episodes
    overlap, with no knowledge of the data required. `n_available` is then
    capped at the non-overlapping count rather than taken on trust.

    This is SS41 (`n_effective = n`) in the gate built to prevent SS41 — and
    inverted: there it manufactured false kills, here false passes.
    """
    if not horizon_days or float(horizon_days) <= 0:
        return None
    return TRADING_DAYS_PER_YEAR / float(horizon_days)

#: "3pp", "3 pp", "0.03", "3%", "300bps" all mean the same thing and a linter
#: that accepts only one of them will be routed around within a week.
_NUM_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(pp|%|bps|bp)?", re.IGNORECASE)


def _to_pp(raw: str) -> float | None:
    """Parse a declared magnitude into percentage points."""
    m = _NUM_RE.search(raw or "")
    if not m:
        return None
    v = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in ("bps", "bp"):
        return v / 100.0
    if unit in ("pp", "%"):
        return v
    # Bare number: a value below 1 is almost certainly a fraction (0.03), and a
    # value at or above 1 is almost certainly already in pp (3). Guessing is
    # unavoidable here; guessing LOUDLY is not, so the caller gets the parsed
    # value back and prints it.
    return v * 100.0 if abs(v) < 1.0 else v


def parse_power_fields(text: str) -> dict:
    """Pull R13's declared fields out of a pre-registration document."""
    out: dict = {"missing": [], "raw": {}}
    for f in REQUIRED_FIELDS + OPTIONAL_FIELDS + ("corpus_years",):
        m = _FIELD_RE[f].search(text or "")
        if not m:
            if f in REQUIRED_FIELDS:
                out["missing"].append(f)
            continue
        v = m.group("v").strip()
        # An UNFILLED placeholder must not parse. `<e.g. 10pp — the smallest
        # effect ...>` contains a number, and a parser that reads it hands the
        # template itself a clean bill of resolvability. The whole guard would
        # then pass every proposal that copied the template and changed nothing.
        if v.startswith("<"):
            if f in REQUIRED_FIELDS:
                out["missing"].append(f)
            continue
        out["raw"][f] = v

    freq = out["raw"].get("event_frequency_per_year")
    if freq is not None:
        n = _NUM_RE.search(freq)
        out["event_frequency_per_year"] = float(n.group(1)) if n else None
        if out["event_frequency_per_year"] is None:
            out["missing"].append("event_frequency_per_year")

    eff = out["raw"].get("declared_effect_size")
    if eff is not None:
        out["declared_effect_size_pp"] = _to_pp(eff)
        if out["declared_effect_size_pp"] is None:
            out["missing"].append("declared_effect_size")

    disp = out["raw"].get("outcome_dispersion")
    if disp is not None:
        key = disp.strip().lower()
        if key in DISPERSION_PRESETS_PP:
            out["outcome_dispersion_pp"] = DISPERSION_PRESETS_PP[key]
            out["dispersion_source"] = f"preset:{key}"
        else:
            out["outcome_dispersion_pp"] = _to_pp(disp)
            out["dispersion_source"] = "declared"
            if out["outcome_dispersion_pp"] is None:
                out["missing"].append("outcome_dispersion")

    hz = out["raw"].get("outcome_horizon_days")
    if hz is not None:
        n = _NUM_RE.search(hz)
        out["outcome_horizon_days"] = float(n.group(1)) if n else None

    yrs = out["raw"].get("corpus_years")
    if yrs is not None:
        n = _NUM_RE.search(yrs)
        out["corpus_years"] = float(n.group(1)) if n else DEFAULT_CORPUS_YEARS
    else:
        out["corpus_years"] = DEFAULT_CORPUS_YEARS
        out["corpus_years_defaulted"] = True

    out["missing"] = sorted(set(out["missing"]))
    return out


def n_required(effect_pp: float, dispersion_pp: float) -> float | None:
    """Independent observations needed to detect `effect_pp` at 80% power."""
    if not effect_pp or not dispersion_pp or dispersion_pp <= 0:
        return None
    return ((Z_ALPHA_TWO_SIDED_05 + Z_POWER_80) * float(dispersion_pp)
            / abs(float(effect_pp))) ** 2


def resolvable_effect(n_available: float, dispersion_pp: float) -> float | None:
    """The smallest effect this corpus could ever resolve — R13's other face.

    Printed alongside every refusal so the answer is never just "no": it names
    the effect size that WOULD be registrable, which the proposer then has to
    either defend economically or walk away from.
    """
    if n_available is None or n_available < 2 or not dispersion_pp:
        return None
    return ((Z_ALPHA_TWO_SIDED_05 + Z_POWER_80) * float(dispersion_pp)
            / math.sqrt(float(n_available)))


def check_resolvability(text: str) -> dict:
    """R13's gate. `blocked` is True when the sample can never resolve the claim."""
    f = parse_power_fields(text)
    if f["missing"]:
        return {
            "verdict": "MISSING_POWER_FIELDS", "blocked": True, "fields": f,
            "why": ("R13: a pre-registration conditioned on any state must "
                    "declare " + ", ".join(f"`{m}`" for m in f["missing"]) +
                    ". Without them nobody — including the author — can tell "
                    "whether this design could ever resolve its own claim, and "
                    "the answer arrives months later dressed as a null."),
        }

    freq = f["event_frequency_per_year"]
    eff = f["declared_effect_size_pp"]
    sd = f["outcome_dispersion_pp"]
    years = f["corpus_years"]
    n_declared = float(freq) * float(years)

    # ── R13b: the overlap cap ──────────────────────────────────────────────
    # `freq` is supposed to count INDEPENDENT episodes. Whether it does is on
    # the honour system, and N20 showed the honour system failing in the
    # direction that matters. When the outcome horizon is declared, a year
    # cannot hold more than 252/horizon non-overlapping episodes, so a declared
    # frequency above that is arithmetic proof of overlap.
    hz = f.get("outcome_horizon_days")
    cap = max_independent_events_per_year(hz)
    overlap_factor = None
    if cap is not None and float(freq) > cap:
        overlap_factor = float(freq) / cap
        n_avail = cap * float(years)
    else:
        n_avail = n_declared

    need = n_required(eff, sd)
    floor = resolvable_effect(n_avail, sd)

    base = {"fields": f, "n_available": n_avail,
            "n_declared": n_declared, "n_required": need,
            "outcome_horizon_days": hz,
            "max_independent_events_per_year": cap,
            "overlap_factor": overlap_factor,
            "independence_assumed": cap is None,
            "smallest_resolvable_effect_pp": floor}

    if need is None:
        return {**base, "verdict": "MISSING_POWER_FIELDS", "blocked": True,
                "why": "R13: effect size or dispersion parsed to nothing usable."}

    if need > n_avail:
        return {
            **base, "verdict": "UNPOWERED_AT_REGISTRATION", "blocked": True,
            "why": (
                f"R13: resolving a {eff:.3g}pp effect at dispersion "
                f"{sd:.3g}pp needs **{need:.0f}** independent observations. "
                f"At {freq:.3g} per year over {years:.0f} years the corpus can "
                f"ever supply **{n_avail:.0f}**"
                + (f" (R13b: capped from {n_declared:.0f} — your "
                   f"{freq:.3g} events/yr overlap {overlap_factor:.1f}x at a "
                   f"{hz:.0f}-day horizon, where only {cap:.1f} independent "
                   f"windows fit in a year)" if overlap_factor else "")
                + ". This design cannot resolve "
                f"this claim, and running it would produce a NOT_DETECTABLE "
                f"that says nothing about the world. The smallest effect this "
                f"corpus could resolve is "
                + (f"**{floor:.2g}pp**" if floor else "not computable") +
                " — either declare an effect at least that large AND defend it "
                "from turnover, cost, capacity and drawdown consequence, or "
                "change the conditioning unit (R14: events, not regimes)."),
        }

    caveat = ""
    if overlap_factor is not None:
        caveat = (
            f" R13b: you declared {freq:.3g} events/yr against a {hz:.0f}-day "
            f"outcome, but only {cap:.1f} non-overlapping {hz:.0f}-day windows "
            f"fit in a year — the declared episodes overlap by {overlap_factor:.1f}x, "
            f"so n_available was CAPPED at {n_avail:.0f} (declared "
            f"{n_declared:.0f}). The floor above is the capped one.")
    elif cap is None:
        caveat = (
            " R13b: no `outcome_horizon_days` declared, so n_available assumes "
            "every episode is INDEPENDENT. If the outcome window overlaps or "
            "the cross-section co-moves, this floor is optimistic — N20 was "
            "passed at 0.46pp against a true MDE of 0.895-1.306pp for exactly "
            "this reason. Declare the horizon and the check runs.")

    return {
        **base, "verdict": "RESOLVABLE", "blocked": False,
        "why": (f"R13: {need:.0f} independent observations required, "
                f"{n_avail:.0f} available. Registrable. Note this says the "
                f"design CAN resolve the declared effect — it says nothing "
                f"about whether {eff:.3g}pp is the right effect to have "
                f"declared, which is an economic question." + caveat),
    }
