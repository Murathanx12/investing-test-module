"""INTERNET-INVESTIGATOR-FWD-1 — the frozen parameters.

Committed BEFORE the first prediction is emitted. Nothing here may change after
accrual begins; if something must, it is a NEW trial with a new name.

No value below was chosen by looking at an outcome. Two of them were chosen by
looking at a MEASUREMENT made before the trial existed, and those two are the
important ones:

  PRIMARY_OBSERVABLES  chosen from `iif1_sigma.py`, which measured that the
                       direction observables carry sigma_pi 0.0036-0.0061 while
                       magnitude at 5%/5d carries 0.1183 — a 20-30x difference
                       in how forecastable they are at all.
  TRIGGERS_PER_NIGHT   chosen from `iif1_power.py`, which measured that trigger
                       volume is worth 2-3x in time-to-detection while the
                       dollar ceiling is nowhere near binding.

Both receipts live in `runs/INTERNET-INVESTIGATOR-FWD-1/`.
"""

from __future__ import annotations

# ── arms ────────────────────────────────────────────────────────────────────
#: Every arm forecasts the SAME cells. The comparison is paired within the cell,
#: so the common variance of "what the market did that night" cancels before any
#: SE is taken (S18).
ARMS = (
    "A_snapshot",      #: engineered numerical snapshot only (current SWARM-1)
    "B_tools",         #: snapshot + investigation tools -- THE PRIMARY CONTRAST
    "C_tools_only",    #: tools only, no engine snapshot
    "D_all",           #: snapshot + tools + MARKET-GRAPH-1 semantic graph
    "B_anon",          #: B_tools with ticker identity masked (NEG_RESULTS S19)
)

#: The one comparison that decides H1. Everything else is secondary and is
#: deflated as such; naming it here stops the best-looking pair from becoming
#: "the" result after the fact.
PRIMARY_CONTRAST = ("A_snapshot", "B_tools")

# ── what is forecast ────────────────────────────────────────────────────────
#: (observable, horizon_days, threshold). Thresholds are decimal fractions.
#:
#: MAGNITUDE, not direction, and the reason is measured rather than argued:
#: `iif1_sigma.py` puts the sigma_pi lower bound at 0.1183 for 5%/5d and 0.0953
#: for 3%/1d, against 0.0036 for 1-day direction. Cross-referenced with
#: `iif1_power.py`, a direction-based primary NEVER reaches 80% power at any
#: trigger count or effect size, while these two resolve in 40-250 nights.
PRIMARY_OBSERVABLES = (
    ("abs_move_exceeds", 5, 0.05),
    ("abs_move_exceeds", 1, 0.03),
)

#: Recorded on every cell for the ledger and PRE-DECLARED UNABLE TO RESOLVE THIS
#: TRIAL. At sigma_pi 0.0036-0.0061 the power table says never, at any n. A null
#: on these is not evidence of anything and may not be reported as a kill (S19).
#: Declared here so it cannot be discovered afterwards and spun either way.
SECONDARY_OBSERVABLES_UNDERPOWERED = (
    ("return_sign", 5, None),
    ("beats_benchmark", 5, None),
)

BENCHMARK = "SPY"

# ── triggers ────────────────────────────────────────────────────────────────
#: k per night. 40 rather than 10 because time-to-detection improves 2-3x with
#: trigger volume and the dollar ceiling is not the binding constraint:
#: 5 arms x 40 triggers x ~5 microtasks ~= 1,000 calls/night, and at
#: MARKET-GRAPH-1's measured $0.00073/call on document-sized payloads that is
#: ~$0.75/night against a $10-15 ceiling.
TRIGGERS_PER_NIGHT = 40

#: The composite unusualness score. Point-in-time inputs only, NO LLM output --
#: a trigger rule containing model output would break the pairing, because the
#: arms would no longer see the same cells.
TRIGGER_WEIGHTS = {
    "abs_resid_return_z_1d": 1.0,
    "volume_z_20d": 1.0,
    "earnings_within_5d": 1.5,
    "filing_within_2d": 1.0,
}

#: Liquidity floor for trigger eligibility. A name that cannot be priced
#: reliably cannot be graded reliably.
MIN_PRICE = 5.0
MIN_DOLLAR_VOLUME_20D = 5_000_000.0

# ── inference ───────────────────────────────────────────────────────────────
#: Identical constants to mg1_config / gc1_config / arena_core. The ruler is not
#: re-derived per trial.
MDE_Z = 2.80
NW_LAGS = 2

#: The primary may NOT BE READ AT ALL below this many graded nights. Reading
#: earlier is peeking, and the power table says nothing below 40 could clear its
#: MDE anyway, so an early read can only mislead.
MIN_GRADED_NIGHTS_BEFORE_READ = 40

# ── the read SCHEDULE ───────────────────────────────────────────────────────
#: AMENDED 2026-08-14, BEFORE ANY ACCRUAL, on the referee's condition.
#:
#: The original design froze a read FLOOR and nothing else. A floor is not a
#: schedule: once past 40 nights, repeated looks are optional stopping, and a
#: trial free to look at 40, 80 and 120 and stop at whichever look is
#: favourable has three chances to clear a bar built for one.
#:
#: Measured, not asserted (`iif1_boundaries.py`, receipt
#: `runs/INTERNET-INVESTIGATOR-FWD-1/boundaries.json`): three looks at the house
#: constant spend a family-wise 0.1079 against a single look's 0.0501 — 2.2x the
#: declared rate.
#:
#: So each licensed look carries its OWN MDE constant, on an O'Brien-Fleming
#: shape solved by simulation to put the family-wise error at 0.05 across all
#: three. Conservative early, near-nominal at the end: an early peek can only
#: stop the trial for an effect so large that continuing to spend would be
#: irresponsible, while the final read — the one the design was powered for —
#: pays almost nothing for the two peeks (2.845 against the unadjusted 2.80).
#:
#: A read at any night count NOT in this table is not a licensed look and cannot
#: decide anything.
READ_SCHEDULE = (
    (40, 4.312),      #: information fraction 0.333, critical z 3.470
    (80, 3.295),      #: information fraction 0.667, critical z 2.453
    (120, 2.845),     #: information fraction 1.000, critical z 2.003
)

#: Cross-check: the last look's constant must be close to the house ruler, or
#: the shape has been mis-specified and the final read is being over-taxed.
assert abs(READ_SCHEDULE[-1][1] - MDE_Z) < 0.10
assert READ_SCHEDULE[0][0] == MIN_GRADED_NIGHTS_BEFORE_READ

# ── budget ──────────────────────────────────────────────────────────────────
#: Nightly ceiling, enforced by `research_budget.require()` before every wire
#: request INCLUDING retries, and logged from SERVED responses, never estimated.
NIGHTLY_MAX_USD = 12.00
NIGHTLY_MAX_CALLS = 3_000

#: The model asked for. The served model is read off every response body and
#: recorded; an arm silently served a different model VOIDS the comparison.
#: `deepseek-chat` and `deepseek-reasoner` are both silent aliases for
#: `deepseek-v4-flash` -- this programme has already run a model comparison that
#: compared a model to itself.
REQUEST_MODEL = "deepseek-v4-flash"
TEMPERATURE = 0.0

#: REGISTERED 2026-08-15, BEFORE the first valid night. It was an unregistered
#: implementation constant of 1600 and it was not a neutral one: on a reasoning
#: model `max_tokens` bounds thinking plus answer, so cells whose evidence
#: needed more reasoning were killed before emitting any JSON. Measured live
#: against the Night-1 snapshot, that was 15/40 of `A_snapshot` and 8/10 of
#: `B_tools` -- i.e. it silenced the PRIMARY CONTRAST's treatment arm roughly
#: four times as often as its control, because arms that gather evidence think
#: longer. A parameter capable of biasing the comparison belongs on the
#: registered surface where drift is a refusal, not in a module constant.
#:
#: 12000 is sized off a measured worst case of 7,186 output tokens on a
#: tool-bearing cell. Zero valid nights had accrued when this was set, so
#: nothing is invalidated by registering it now; after the first valid night it
#: is frozen like everything else here.
MAX_TOKENS = 12_000

# ── seeds ───────────────────────────────────────────────────────────────────
SEED = 20260814

CAMPAIGN = "brain_v3"
TRIAL = "INTERNET-INVESTIGATOR-FWD-1"
