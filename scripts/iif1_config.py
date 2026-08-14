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

# ── seeds ───────────────────────────────────────────────────────────────────
SEED = 20260814

CAMPAIGN = "brain_v3"
TRIAL = "INTERNET-INVESTIGATOR-FWD-1"
