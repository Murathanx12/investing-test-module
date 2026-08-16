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
#:
#: R13d adds the pair below, and they are a DIFFERENT object from
#: `cross_sectional_n`:
#:
#: `cross_sectional_k`   — how many co-moving series the design actually holds.
#: `cross_sectional_rho` — the MEASURED average pairwise correlation of the
#:                         OUTCOME across them.
#:
#: `cross_sectional_n` is a divisor applied to a row count that already counts
#: every series. `(k, rho)` is a MULTIPLIER applied to a count of independent
#: time blocks. They answer the same question from opposite sides and a design
#: may declare one form or the other, never both — see `effective_sample`.
OPTIONAL_FIELDS = ("outcome_horizon_days", "dependence_unit",
                   "cross_sectional_n", "cluster_size",
                   "cross_sectional_k", "cross_sectional_rho")

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


def design_effect_n(k: float, rho_bar: float | None) -> float:
    """Independent-equivalent count of `k` series correlated at `rho_bar`.

    R13d, added 2026-08-16 after N21. The standard equicorrelated design
    effect:

        n_eff = k / (1 + (k - 1) * rho_bar)

    It has two properties that matter more than the formula:

    * It is BOUNDED BY `1 / rho_bar`. Eight equity ETFs whose 6-month log
      growth correlates at 0.488 are worth 1.81 observations, and adding more
      equity ETFs cannot get past about 2. Widening a co-moving cross-section
      is not a way to buy power.
    * It is a MULTIPLIER on the count of independent time blocks, never the
      whole sample. `k / (1 + (k-1) * rho)` answers "how many series is this
      cross-section worth **at one moment**". A 20-year design with 40
      non-overlapping blocks and an effective cross-section of 1.81 has about
      72 effective observations, not 1.81. Reading the design effect as the
      total is the mistake this function is documented to prevent, and it was
      made in this repo on 2026-08-16.

    `rho_bar` MUST be measured on a policy-free surrogate, not assumed.
    Undeclared returns 1.0 — the conservative reading that the cross-section
    adds nothing — because an assumed correlation is a free parameter pointing
    at whichever answer the author needs.
    """
    kk = float(k or 1.0)
    if kk <= 1.0:
        return 1.0
    if rho_bar is None:
        return 1.0
    r = min(max(float(rho_bar), 0.0), 1.0)
    if r <= 0.0:
        return kk
    return kk / (1.0 + (kk - 1.0) * r)


def effective_sample(freq_per_year: float, years: float, *,
                     horizon_days: float | None = None,
                     cross_sectional_n: float | None = None,
                     cluster_size: float | None = None,
                     cross_sectional_k: float | None = None,
                     cross_sectional_rho: float | None = None) -> dict:
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

    TWO FORMS FOR THE CROSS-SECTION, AND THEY ARE NOT INTERCHANGEABLE
    ================================================================
    `cross_sectional_n` is a **divisor**: use it when `freq_per_year` already
    counts every series, so 100 names screened weekly is 5,200/yr and the
    divisor takes it back down. `(cross_sectional_k, cross_sectional_rho)` is a
    **multiplier** on the temporal count: use it when `freq_per_year` counts
    episodes for the cross-section as a whole, so the question is how much the
    other k-1 series add. Declaring both is refused, because the two would then
    be applied to a base whose meaning is no longer determined.
    """
    n_raw = float(freq_per_year) * float(years)
    cap = max_independent_events_per_year(horizon_days)
    temporal = cap * float(years) if cap is not None else None
    after_temporal = min(n_raw, temporal) if temporal is not None else n_raw

    xs = max(float(cross_sectional_n), 1.0) if cross_sectional_n else 1.0
    cl = max(float(cluster_size), 1.0) if cluster_size else 1.0
    k = float(cross_sectional_k) if cross_sectional_k else None
    rho = (float(cross_sectional_rho)
           if cross_sectional_rho is not None else None)

    both = (cross_sectional_n is not None and float(cross_sectional_n) > 1.0
            and k is not None and k > 1.0)
    xs_eff = design_effect_n(k, rho) if k else 1.0
    effective = after_temporal * xs_eff / (xs * cl)

    return {
        "n_raw": n_raw,
        "max_independent_events_per_year": cap,
        "temporal_nonoverlap_n": temporal,
        "n_after_temporal": after_temporal,
        "cross_sectional_divisor": xs,
        "cross_sectional_k": k,
        "cross_sectional_rho": rho,
        "cross_sectional_effective": xs_eff,
        "cross_sectional_bound_1_over_rho": (
            (1.0 / rho) if rho else None),
        "declares_both_cross_sectional_forms": both,
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
                    "cluster_size", "cross_sectional_k", "cross_sectional_rho"):
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


#: The slice register's vocabulary, duplicated here rather than imported
#: because the linter lives in a different repository from the register. The
#: test `test_slice_purposes_match_the_register` pins them together.
SLICE_PURPOSES = ("EXPLORE", "TRANSFER", "FOREIGN", "CONFIRM", "REANALYSIS",
                  "PAIRED")

#: A CONFIRM claim must identify WHICH data it is claiming. Securities and
#: period alone are not an identity: two trials can share a price window and
#: differ in what they were allowed to know inside it, which is why the
#: information cutoff is required rather than implied by the end date.
CONFIRM_IDENTITY_FIELDS = ("slice_securities", "slice_period",
                           "information_cutoff")

_SLICE_RE = {
    f: re.compile(rf"^\s*[-*]?\s*\**{f}\**\s*[:=]\s*\**\s*(?P<v>[^\n|]+?)\**\s*$",
                  re.IGNORECASE | re.MULTILINE)
    for f in ("slice_purpose",) + CONFIRM_IDENTITY_FIELDS
}

_PLACEHOLDERS = ("", "n/a", "na", "none", "-", "--", "tbd", "todo", "?")


def check_slice_declaration(text: str) -> dict:
    """Which data does this trial claim, and for what?

    WHY THIS IS A LINT AND NOT A CONVENTION (2026-08-16)
    ====================================================
    `research_gym.slice_register` refuses a CONFIRM on data a prior trial has
    read. It can only refuse trials that call it. N9B was designed after
    information from N9's confirmation slice had entered the research process
    and consumed it a second time; nothing stopped that, because nothing was
    asked. A register that depends on the honest party calling it protects
    against everything except the case it exists for.

    So the claim moves to registration, where it is checked by the same gate
    that already refuses an unpowered design. `EXPLORE` is a perfectly good
    answer and costs nothing — the point is that the answer is on the record
    before the numbers exist, not that it is `CONFIRM`.
    """
    m = _SLICE_RE["slice_purpose"].search(text or "")
    raw = (m.group("v").strip() if m else "")
    if raw.startswith("<") or raw.strip().lower().strip(".") in _PLACEHOLDERS:
        raw = ""
    purpose = raw.upper().split()[0].strip(",.;") if raw else ""

    if not purpose:
        return {
            "verdict": "UNDECLARED_SLICE_PURPOSE", "blocked": True,
            "slice_purpose": None,
            "why": ("Declare `slice_purpose` — one of "
                    + " / ".join(SLICE_PURPOSES) + ". A trial that does not "
                    "say what it intends to do with its data cannot be "
                    "refused a slice it should not read, and the register "
                    "only sees the trials that choose to ask it. EXPLORE is a "
                    "fine answer; an absent answer is not."),
        }
    if purpose not in SLICE_PURPOSES:
        return {
            "verdict": "UNDECLARED_SLICE_PURPOSE", "blocked": True,
            "slice_purpose": purpose,
            "why": (f"`slice_purpose = {purpose}` is not one of "
                    + " / ".join(SLICE_PURPOSES) + "."),
        }

    if purpose != "CONFIRM":
        return {"verdict": "SLICE_DECLARED", "blocked": False,
                "slice_purpose": purpose,
                "why": (f"slice_purpose = {purpose}. This trial may revisit "
                        f"data freely and may NOT later be described as an "
                        f"independent confirmation.")}

    missing = [f for f in CONFIRM_IDENTITY_FIELDS
               if not (_SLICE_RE[f].search(text or "")
                       and _SLICE_RE[f].search(text).group("v").strip()
                       and not _SLICE_RE[f].search(text).group("v")
                       .strip().startswith("<")
                       and _SLICE_RE[f].search(text).group("v").strip().lower()
                       .strip(".") not in _PLACEHOLDERS)]
    if missing:
        return {
            "verdict": "UNIDENTIFIED_CONFIRMATION_SLICE", "blocked": True,
            "slice_purpose": purpose, "missing": missing,
            "why": ("A CONFIRM claim must identify the data it claims: "
                    + ", ".join(f"`{f}`" for f in missing) + " missing. "
                    "`information_cutoff` is required and is not implied by "
                    "the end date — two trials can share a price window and "
                    "differ in what they were allowed to know inside it, and "
                    "the register's slice identity is the four-tuple "
                    "universe x period x outcome x cutoff."),
        }
    return {"verdict": "SLICE_DECLARED", "blocked": False,
            "slice_purpose": purpose,
            "why": "CONFIRM slice identified; claim it in the register before "
                   "the first price is fetched, not while reading the result."}


# ═══════════════════════════════════════════════════════════════════════════
# R13e — calendar-disjointness, declared at registration
# ═══════════════════════════════════════════════════════════════════════════

#: The purposes that assert a rule survived contact with data it was not built
#: on. These must be calendar-disjoint from the selection window or the claim
#: is about the same market states under different tickers.
TRANSFER_CLAIMING_PURPOSES = ("CONFIRM", "TRANSFER")

#: FOREIGN is "still looking" — it does not claim transfer, so an overlap does
#: not block it. It is still recorded, so the result is born labelled instead
#: of being called a transfer three sessions later.
LINEAGE_DECLARING_PURPOSES = TRANSFER_CLAIMING_PURPOSES + ("FOREIGN",)

#: The literal a first-generation hypothesis declares when nothing was fitted:
#: the rule came from theory or literature, not from a window of this corpus.
NO_SELECTION_WINDOW = ("NONE", "NO_PRIOR_FIT")

#: Trading days -> calendar days, plus a holiday/weekend buffer.
#:
#: NOT a taste. `audit_temporal_lineage` measured the 1.5x calendar heuristic
#: failing on **15.7%** of 20-bar boundaries against the real NYSE calendar:
#: 20 trading days can span 28 calendar days before a single holiday, and the
#: heuristic allows 30. 7/5 is the exact weekend ratio and the 14-day buffer
#: covers the worst holiday cluster in the sample (Thanksgiving->New Year).
CALENDAR_DAYS_PER_TRADING_DAY = 7.0 / 5.0
HOLIDAY_BUFFER_DAYS = 14

_WINDOW_FIELDS = ("selection_period", "parent_trial")
_WINDOW_RE = {
    f: re.compile(rf"^\s*[-*]?\s*\**{f}\**\s*[:=]\s*\**\s*(?P<v>[^\n|]+?)\**\s*$",
                  re.IGNORECASE | re.MULTILINE)
    for f in _WINDOW_FIELDS + ("slice_period", "outcome_horizon_days")
}

#: ISO first, because a bare year is ambiguous about which end of it is meant
#: and the expansion below has to know which end it is filling in.
_ISO_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def _read_field(text: str, field: str) -> str:
    """Read a declared field, treating unfilled placeholders as absent.

    `selection_period` and `parent_trial` keep `none`, because there NONE is
    the answer — "nothing was fitted" — and mapping it to silence would refuse
    the one honest declaration a first-generation hypothesis can make. Every
    other evasion (`n/a`, `-`, `TBD`) still reads as unanswered.
    """
    m = _WINDOW_RE[field].search(text or "")
    if not m:
        return ""
    v = m.group("v").strip()
    blanks = _PLACEHOLDERS
    if field in _WINDOW_FIELDS:
        blanks = tuple(p for p in _PLACEHOLDERS if p != "none")
    if v.startswith("<") or v.lower().strip(".") in blanks:
        return ""
    return v


def parse_window(raw: str) -> tuple[str, str] | None:
    """Pull `(start, end)` as ISO dates out of a declared period.

    Accepts `1999-01-01 .. 2015-12-31`, `1999-01-01 to 2015-12-31`, and the
    year-only `1999-2015`, which expands to the WIDEST reading (Jan 1 of the
    first year to Dec 31 of the last). Widest on purpose: a declaration that
    is ambiguous about its edges should fail the disjointness test, not scrape
    past it on the narrow reading.

    Returns None when two dates cannot be found — the caller refuses rather
    than assuming, because a window nobody can parse is a window nobody
    checked.
    """
    if not raw:
        return None
    iso = _ISO_RE.findall(raw)
    if len(iso) >= 2:
        a = "-".join(iso[0])
        b = "-".join(iso[-1])
        return (a, b) if a <= b else (b, a)
    years = _YEAR_RE.findall(raw)
    if len(iso) == 1 and years:
        # One ISO date and a year: e.g. "1999-01-01 .. 2015".
        a = "-".join(iso[0])
        cand = [y for y in years if not a.startswith(y)] or years
        b = f"{max(cand)}-12-31"
        return (a, b) if a <= b else (b, a)
    if len(years) >= 2:
        return (f"{min(years)}-01-01", f"{max(years)}-12-31")
    if len(years) == 1:
        return (f"{years[0]}-01-01", f"{years[0]}-12-31")
    return None


def _days_between(a: str, b: str) -> int:
    """Calendar days from ISO date `a` to ISO date `b`, `a` <= `b`."""
    from datetime import date

    ya, ma, da = (int(x) for x in a.split("-"))
    yb, mb, db = (int(x) for x in b.split("-"))
    return (date(yb, mb, db) - date(ya, ma, da)).days


def required_gap_days(horizon_days: float | None) -> int:
    """Calendar days a confirmation window must start AFTER selection ends.

    Zero overlap is necessary and not sufficient: a confirmation beginning the
    day after selection ends still scores rules whose labels were formed from
    the same forward window. This is the registration-time version of what
    `research_gym.lineage` derives exactly from the index at run time, and it
    is deliberately the conservative one — clearing this lint does NOT excuse
    a design from the derived purge.
    """
    if not horizon_days or horizon_days <= 0:
        return 0
    return int(math.ceil(float(horizon_days) * CALENDAR_DAYS_PER_TRADING_DAY)
               + HOLIDAY_BUFFER_DAYS)


def check_calendar_disjointness(text: str) -> dict:
    """R13e. Does the confirmation window overlap the selection window?

    WHY THIS EXISTS (2026-08-16, from N9)
    =====================================
    N9 froze a rule set selected on SPY/XLF/XLE through 2015, then confirmed it
    on six securities *no prior slice had read* — over **1999-2026**. Different
    tickers, the same 2008, the same 2011, the same 2015. Split at the
    selection boundary with nothing else changed, the confirmation reads

        1999-2015, calendar-OVERLAPPING : lift 1.464, p = 0.010
        2016+,     calendar-disjoint    : lift 0.765, p = 0.771

    at H=20, and the same shape at H=60. The registered 1.271 is the average of
    a period that shares its market states with the selection window and a
    period that does not.

    `slice_register` stored the period all along and `check_slice_declaration`
    required it to be declared — but the identity that decides reuse is
    `shared securities AND overlapping period`, so a confirmation on fresh
    tickers over the same calendar was clean by construction. The register was
    built to stop securities being reused. **The binding axis was the
    calendar.**

    So the axis moves to registration, where it costs one line and one lint
    instead of three sessions and a withdrawn headline:

        holding out SECURITIES is not holding out DATA when they co-move.
    """
    m = _SLICE_RE["slice_purpose"].search(text or "")
    raw = (m.group("v").strip() if m else "")
    if raw.startswith("<") or raw.strip().lower().strip(".") in _PLACEHOLDERS:
        raw = ""
    purpose = raw.upper().split()[0].strip(",.;") if raw else ""

    base = {"slice_purpose": purpose or None, "verdict": "NOT_APPLICABLE",
            "blocked": False}
    if purpose not in LINEAGE_DECLARING_PURPOSES:
        return {**base, "why": (
            f"R13e applies to {' / '.join(LINEAGE_DECLARING_PURPOSES)}; "
            f"slice_purpose = {purpose or 'undeclared'} makes no transfer "
            f"claim to confound.")}

    claims_transfer = purpose in TRANSFER_CLAIMING_PURPOSES
    sel_raw = _read_field(text, "selection_period")
    parent = _read_field(text, "parent_trial")
    parent_named = bool(parent) and parent.upper().split()[0].strip(",.;") \
        not in NO_SELECTION_WINDOW

    if not sel_raw:
        return {**base, "verdict": "UNDECLARED_SELECTION_WINDOW",
                "blocked": True, "why": (
                    "R13e: declare `selection_period` — the calendar window the "
                    "thing being tested was chosen, fitted or tuned on, "
                    "INCLUDING the window its parent was selected on. N9's "
                    "confirmation held out six untouched securities over a "
                    "calendar that overlapped its own selection window; the "
                    "lift was 1.464 on the overlapping half and 0.765 on the "
                    "disjoint half. Nothing in the design said which coordinate "
                    "was being varied, so nothing could refuse it. Declare "
                    "`NONE` if the rule came from theory or literature rather "
                    "than a window of this corpus.")}

    declared_none = sel_raw.upper().split()[0].strip(",.;") in NO_SELECTION_WINDOW
    if declared_none:
        if parent_named:
            return {**base, "verdict": "SELECTION_WINDOW_CONTRADICTS_PARENT",
                    "blocked": True, "parent_trial": parent, "why": (
                        f"R13e: `selection_period = {sel_raw}` but "
                        f"`parent_trial = {parent}`. A descendant inherits its "
                        f"parent's selection window — that is what makes it a "
                        f"descendant. Declare the parent's window, or drop the "
                        f"parent claim.")}
        return {**base, "verdict": "CALENDAR_DISJOINT_BY_CONSTRUCTION",
                "why": (
                    "no prior fit declared, so there is no selection window to "
                    "overlap. This is a claim ON THE RECORD: if the rule, its "
                    "thresholds or its universe were in fact chosen after "
                    "looking at this corpus, the declaration is false and the "
                    "result is not a transfer.")}

    sel = parse_window(sel_raw)
    slice_raw = _read_field(text, "slice_period")
    sli = parse_window(slice_raw)
    if sel is None or sli is None:
        which = ("selection_period" if sel is None else "slice_period")
        return {**base, "verdict": "UNPARSEABLE_WINDOW", "blocked": True,
                "why": (
                    f"R13e: `{which}` does not yield two dates. Write it as "
                    f"`YYYY-MM-DD .. YYYY-MM-DD`. A window that cannot be "
                    f"parsed cannot be checked, and a guard that waves through "
                    f"what it could not read is not a guard.")}

    hz = _read_field(text, "outcome_horizon_days")
    hz_n = _NUM_RE.search(hz) if hz else None
    horizon = float(hz_n.group(1)) if hz_n else None
    need_gap = required_gap_days(horizon)

    lo, hi = max(sel[0], sli[0]), min(sel[1], sli[1])
    overlaps = lo <= hi
    detail = {"selection_period": sel, "slice_period": sli,
              "outcome_horizon_days": horizon,
              "required_gap_days": need_gap,
              "overlap_start": lo if overlaps else None,
              "overlap_end": hi if overlaps else None,
              "overlap_days": (_days_between(lo, hi) + 1) if overlaps else 0}

    if overlaps:
        if not claims_transfer:
            return {**base, **detail,
                    "verdict": "CALENDAR_OVERLAPPING_FOREIGN_SLICE",
                    "may_claim_transfer": False, "why": (
                        f"FOREIGN slice {sli[0]}..{sli[1]} overlaps the "
                        f"selection window {sel[0]}..{sel[1]} on "
                        f"{detail['overlap_days']} calendar days. Not blocked "
                        f"— FOREIGN is still looking — but this result may NOT "
                        f"be reported as transfer evidence, whatever it says.")}
        return {**base, **detail, "verdict": "CALENDAR_OVERLAPPING_CONFIRMATION",
                "blocked": True, "why": (
                    f"R13e: the {purpose} window {sli[0]}..{sli[1]} overlaps "
                    f"the selection window {sel[0]}..{sel[1]} on "
                    f"{detail['overlap_days']} calendar days. Holding out "
                    f"SECURITIES is not holding out DATA when the securities "
                    f"co-move: a rule chosen in 2008 and scored on other "
                    f"tickers through the same 2008 is being asked whether it "
                    f"fits the states it was chosen from. N9 answered 1.464 "
                    f"(p=0.010) that way and 0.765 (p=0.771) on the disjoint "
                    f"half. Either move the window past "
                    f"{sel[1]} + {need_gap}d, or declare the trial FOREIGN / "
                    f"REANALYSIS and give up the transfer claim.")}

    # Disjoint. Ordering matters: a window BEFORE the selection window is not
    # automatically safe either — labels run forward, so a confirmation that
    # ends inside the parent's forward-label reach shares outcome data with it.
    if sli[1] < sel[0]:
        gap = _days_between(sli[1], sel[0])
        direction = "precedes"
    else:
        gap = _days_between(sel[1], sli[0])
        direction = "follows"
    detail["gap_days"] = gap
    detail["direction"] = direction

    if gap < need_gap:
        return {**base, **detail, "verdict": "CONFIRMATION_WINDOW_ABUTS_SELECTION",
                "blocked": True, "why": (
                    f"R13e: the windows do not overlap, but the {purpose} "
                    f"window {direction} selection by only {gap} calendar days "
                    f"against a {horizon:.0f}-day outcome horizon, which needs "
                    f"{need_gap}. Labels run forward: the last selection rows "
                    f"carry outcomes formed inside the confirmation window. "
                    f"1.5x calendar days was measured failing on 15.7% of "
                    f"20-bar boundaries against the real NYSE calendar, so this "
                    f"gate uses 7/5 + {HOLIDAY_BUFFER_DAYS}d and STILL does not "
                    f"replace the purge `research_gym.lineage` derives from the "
                    f"index at run time.")}

    return {**base, **detail, "verdict": "CALENDAR_DISJOINT", "why": (
        f"{purpose} window {sli[0]}..{sli[1]} {direction} the selection window "
        f"{sel[0]}..{sel[1]} by {gap} calendar days (>= {need_gap} required at "
        f"H={horizon:.0f}). " if horizon else
        f"{purpose} window {sli[0]}..{sli[1]} {direction} the selection window "
        f"{sel[0]}..{sel[1]} by {gap} calendar days. ") + (
        "The declared windows are disjoint; the derived purge still runs.")}


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
    chain = effective_sample(
        freq, years, horizon_days=hz,
        cross_sectional_n=f.get("cross_sectional_n"),
        cluster_size=f.get("cluster_size"),
        cross_sectional_k=f.get("cross_sectional_k"),
        cross_sectional_rho=f.get("cross_sectional_rho"))
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

    # ── R13d: the two cross-sectional forms answer from opposite sides ─────
    if chain["declares_both_cross_sectional_forms"]:
        return {
            **base, "verdict": "AMBIGUOUS_CROSS_SECTIONAL_DECLARATION",
            "blocked": True,
            "why": (
                "R13d: `cross_sectional_n` (a divisor on a count that already "
                "includes every series) and `cross_sectional_k` (a multiplier "
                "on a count of independent time blocks) describe the same "
                "cross-section from opposite sides. Declaring both leaves the "
                "base of `event_frequency_per_year` undetermined, so the chain "
                "cannot be computed at all. Declare one."),
        }

    # ── R13d: k co-moving series with no MEASURED correlation ──────────────
    k_declared = chain["cross_sectional_k"]
    if (k_declared and k_declared > 1.0
            and chain["cross_sectional_rho"] is None):
        return {
            **base, "verdict": "UNMEASURED_CROSS_SECTIONAL_DEPENDENCE",
            "blocked": True,
            "why": (
                f"R13d: `cross_sectional_k = {k_declared:.0f}` is declared and "
                f"`cross_sectional_rho` is not. The effective width of a "
                f"co-moving cross-section is `k / (1 + (k-1) * rho)` and it is "
                f"MEASURABLE — on a policy-free surrogate, before the test — "
                f"not assumable. Measured on eight equity ETFs at a 6-month "
                f"horizon it was 0.488, making them 1.81 series and not 8, and "
                f"bounding any equity cross-section at about `1/rho = 2`. "
                f"Declaring k without rho asks the gate to take the width on "
                f"the honour system, which is the failure R13b was written for."),
        }

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
    if ((chain["total_reduction_factor"]
         and chain["total_reduction_factor"] > 1.01)
            or chain["cross_sectional_effective"] > 1.0):
        parts = []
        if overlap_factor is not None:
            parts.append(
                f"only {cap:.1f} non-overlapping {hz:.0f}-day windows fit in a "
                f"year against your declared {freq:.3g}/yr ({overlap_factor:.1f}x "
                "overlap)")
        if chain["cross_sectional_divisor"] > 1:
            parts.append(f"a {chain['cross_sectional_divisor']:.0f}-wide "
                         "co-moving cross-section")
        if chain["cross_sectional_effective"] > 1.0:
            parts.append(
                f"a cross-section of {chain['cross_sectional_k']:.0f} series "
                f"at rho={chain['cross_sectional_rho']:.3f}, worth "
                f"{chain['cross_sectional_effective']:.2f} independent series "
                f"(bounded by 1/rho = "
                f"{chain['cross_sectional_bound_1_over_rho']:.1f}) — this one "
                f"MULTIPLIES rather than divides")
        if chain["cluster_divisor"] > 1:
            parts.append(f"clusters of {chain['cluster_divisor']:.0f} correlated "
                         "events")
        caveat = (
            f" R13b/c/d: n_raw {chain['n_raw']:.0f} -> n_effective "
            f"{n_avail:.0f} ({chain['total_reduction_factor']:.1f}x), from "
            + "; ".join(parts) + ". The floor above is the adjusted one.")
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
