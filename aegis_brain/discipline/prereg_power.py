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

#: Optional. Declaring them turns on the dependence checks (R13b/R13c) — see
#: `effective_sample`. Optional rather than required so registrations predating
#: the checks still lint; a proposal that omits them is told, in the PASS text,
#: what its `n_available` is assuming.
#:
#: `dependence_unit`  — one sentence naming what ONE independent observation is.
#: `cross_sectional_n`— how many co-moving series contribute per episode.
#: `cluster_size`     — how many correlated events arrive per independent shock.
OPTIONAL_FIELDS = ("outcome_horizon_days", "dependence_unit",
                   "cross_sectional_n", "cluster_size")

#: R13c. Below this ratio of available-to-required sample, an undeclared
#: dependence unit BLOCKS rather than warns.
#:
#: Rationale, and it is not a taste: the widest cross-section this programme has
#: pooled is 18 (WM0's ETF panel), and event clusters run 2-5. So an undeclared
#: dependence can plausibly cost about 20x. A design with more headroom than
#: that cannot be flipped by one, and blocking it would be manufacturing a
#: crisis; a design with less can be flipped, and passing it is how N20 got
#: through. The threshold is where those two errors meet.
DEPENDENCE_DECLARATION_HEADROOM = 20.0

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


def effective_sample(freq_per_year: float, years: float, *,
                     horizon_days: float | None = None,
                     cross_sectional_n: float | None = None,
                     cluster_size: float | None = None) -> dict:
    """Reduce a declared event rate to independent observations, step by step.

    R13c, added 2026-08-16. **Temporal non-overlap is necessary, not
    sufficient.** R13b caps by `252/H` and stops there, which is correct about
    calendar overlap and silent about everything else:

    * 100 securities screened on the same 20-day window are 100 rows and
      nowhere near 100 independent events.
    * Ten insider filings from one company on one day are one disclosure.
    * Six ETFs through one macro shock are closer to one observation than six.

    Hardcoding `n_effective = n_nonoverlap` would build SS41 into R13 a second
    time — the same mistake at a different level, which is precisely the shape
    this programme keeps repeating. So each reduction is **declared** and
    applied separately, and the result is the product of all of them.

    Every intermediate count is returned rather than just the final one,
    because a single number cannot be argued with and a chain can.
    """
    n_raw = float(freq_per_year) * float(years)
    cap = max_independent_events_per_year(horizon_days)
    temporal = cap * float(years) if cap is not None else None
    after_temporal = min(n_raw, temporal) if temporal is not None else n_raw

    xs = float(cross_sectional_n) if cross_sectional_n else 1.0
    cl = float(cluster_size) if cluster_size else 1.0
    xs = max(xs, 1.0)
    cl = max(cl, 1.0)
    effective = after_temporal / (xs * cl)

    return {
        "n_raw": n_raw,
        "max_independent_events_per_year": cap,
        "temporal_nonoverlap_n": temporal,
        "n_after_temporal": after_temporal,
        "cross_sectional_divisor": xs,
        "cluster_divisor": cl,
        "n_available_effective": effective,
        "overlap_factor": (float(freq_per_year) / cap
                           if cap is not None and float(freq_per_year) > cap
                           else None),
        "total_reduction_factor": (n_raw / effective) if effective > 0 else None,
    }

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

    for numeric in ("outcome_horizon_days", "cross_sectional_n",
                    "cluster_size"):
        raw = out["raw"].get(numeric)
        if raw is not None:
            n = _NUM_RE.search(raw)
            out[numeric] = float(n.group(1)) if n else None

    du = out["raw"].get("dependence_unit")
    # A declaration must say something. "n/a", "-", "TBD" are the ways an
    # author satisfies a required field without answering it, and a guard that
    # accepts them is a guard that has been routed around.
    if du is not None and du.strip().lower().strip(".") not in (
            "", "n/a", "na", "none", "-", "--", "tbd", "todo", "?"):
        out["dependence_unit"] = du.strip()

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

    # ── R13b/R13c: reduce the declared rate to independent observations ────
    # `freq` is on the honour system and N20 showed the honour system failing
    # in the direction that matters. The reductions are applied mechanically
    # and reported as a chain, never as one number.
    hz = f.get("outcome_horizon_days")
    chain = effective_sample(freq, years, horizon_days=hz,
                             cross_sectional_n=f.get("cross_sectional_n"),
                             cluster_size=f.get("cluster_size"))
    cap = chain["max_independent_events_per_year"]
    overlap_factor = chain["overlap_factor"]
    n_avail = chain["n_available_effective"]
    unit = f.get("dependence_unit")

    need = n_required(eff, sd)
    floor = resolvable_effect(n_avail, sd)

    base = {"fields": f, "n_available": n_avail,
            "n_declared": n_declared, "n_required": need,
            "outcome_horizon_days": hz,
            "max_independent_events_per_year": cap,
            "overlap_factor": overlap_factor,
            "dependence_unit": unit,
            "dependence_chain": chain,
            "independence_assumed": cap is None,
            "smallest_resolvable_effect_pp": floor}

    # ── R13c: an undeclared dependence unit blocks when it could matter ────
    if need is not None and unit is None:
        headroom = (n_avail / need) if need > 0 else float("inf")
        base["headroom"] = headroom
        if headroom < DEPENDENCE_DECLARATION_HEADROOM and need <= n_avail:
            return {
                **base, "verdict": "UNDECLARED_DEPENDENCE_UNIT", "blocked": True,
                "why": (
                    f"R13c: this design has {n_avail:.0f} available against "
                    f"{need:.0f} required — {headroom:.1f}x headroom. Below "
                    f"{DEPENDENCE_DECLARATION_HEADROOM:.0f}x, an undeclared "
                    "dependence can flip the answer on its own: pooling an "
                    "18-wide cross-section or a 5-event cluster costs an order "
                    "of magnitude, and R13b's calendar cap does not see either. "
                    "Declare `dependence_unit` — one sentence naming what ONE "
                    "independent observation is — plus `cross_sectional_n` and "
                    "`cluster_size` where they are above 1. If they genuinely "
                    "are 1, say so and say why; that is a claim the design has "
                    "to own rather than inherit by silence. "
                    "Temporal non-overlap is NECESSARY, NOT SUFFICIENT."),
            }

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
    if chain["total_reduction_factor"] and chain["total_reduction_factor"] > 1.01:
        parts = []
        if overlap_factor is not None:
            parts.append(
                f"only {cap:.1f} non-overlapping {hz:.0f}-day windows fit in a "
                f"year against your declared {freq:.3g}/yr ({overlap_factor:.1f}x "
                "overlap)")
        if chain["cross_sectional_divisor"] > 1:
            parts.append(f"a {chain['cross_sectional_divisor']:.0f}-wide "
                         "co-moving cross-section")
        if chain["cluster_divisor"] > 1:
            parts.append(f"clusters of {chain['cluster_divisor']:.0f} correlated "
                         "events")
        caveat = (
            f" R13b/c: n_raw {chain['n_raw']:.0f} -> n_effective {n_avail:.0f} "
            f"({chain['total_reduction_factor']:.1f}x reduction), from "
            + "; ".join(parts) + ". The floor above is the reduced one.")
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
