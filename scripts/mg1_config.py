"""MARKET-GRAPH-1 — the frozen parameters.

WHY THIS FILE EXISTS SEPARATELY
===============================
`PREREG_MARKET_GRAPH_1.md` (commit 57cf834) declares under "Frozen parameters":

    Universe, `t` cut dates, horizons, edge taxonomy above, confidence field,
    co-movement definition (residual return correlation after market and
    sector), and the matching procedure for H2's control pairs.

It NAMES those as frozen; it does not ENUMERATE them. The taxonomy and the
co-movement definition it does give in words. The rest — which universe, which
dates, which horizon, which threshold — had to be chosen by whoever ran it.

That is a weaker commitment than a fully enumerated pre-registration and the
report says so in those words. This file is the mitigation: every free
parameter is fixed HERE, committed BEFORE a single forward correlation is
computed or a single edge is graded, so the choice is dated rather than
defensible-in-hindsight. Nothing in this file may change after the first
grading run. If something must change, it is a NEW trial with a new name.

No value below was chosen by looking at an outcome.
"""

from __future__ import annotations

# ── the eight edge types, verbatim from the prereg ──────────────────────────
#: Fixed by the prereg. The extractor may emit no other type; anything else is
#: dropped at parse time and counted as a schema violation.
EDGE_TYPES = (
    "supplier",
    "customer",
    "competitor",
    "commodity_input",
    "shared_technology",
    "shared_end_market",
    "regulatory_exposure",
    "geographic_exposure",
)

#: Types where direction is meaningful and therefore where the reversed-
#: direction control (prereg control 5) has something to test. The other five
#: are symmetric by construction and a "direction" on them is noise.
DIRECTED_TYPES = ("supplier", "customer")

# ── universe ────────────────────────────────────────────────────────────────
#: Top-N by CRSP market cap at each cut date. 300 is a compromise fixed in
#: advance: large enough that a counterparty named in a 10-K has a chance of
#: being IN the universe (resolution rate is the binding constraint on this
#: whole trial), small enough that O(N^2) pairs stay tractable at 38 dates.
UNIVERSE_N = 300
MIN_PRICE = 5.0                 #: CRSP PRC floor, |PRC| — bid/ask midpoints are negative
SHRCD_OK = (10, 11)             #: US common shares only

#: A name is an extraction SUBJECT only if a 10-K was filed within this many
#: days BEFORE t. 15 months is the same staleness limit TRIAL-TEXT-LAZY froze,
#: for the same reason: past it the document is not describing the current
#: business.
#:
#: AMENDED 2026-08-12 (recorded, not quietly): this used to gate UNIVERSE
#: MEMBERSHIP as well. It no longer does. The EDGAR<->CRSP CIK bridge is an
#: exact match on normalised names and CRSP abbreviates, so requiring a linked
#: 10-K to be IN the universe silently deleted IBM — rank 24 by market cap —
#: from all 38 cut dates, and 46 of every 300 names with it (measured overlap
#: against the true top-300-eligible: 84.6%). Membership is now market cap
#: alone; the document is required only to make a name a SUBJECT, because a
#: name with no 10-K can still be the TARGET of somebody else's edge.
#: Per-date document coverage is written to `panel_meta.json:attrition`.
#: The amendment was decided from composition (a named megacap was missing),
#: not from any outcome; see the block comment in `mg1_panel.main`.
MAX_FILING_AGE_DAYS = 460

# ── clock ───────────────────────────────────────────────────────────────────
#: Quarter-end cut dates. The last one must leave a full forward window inside
#: the CRSP panel (which ends 2024-12-31), so it stops in 2024-06.
FIRST_CUT = "2015-03-31"
LAST_CUT = "2024-06-30"
CUT_FREQ = "Q"

TRAIL_DAYS = 252                #: trailing window for betas and rho_trail
HORIZON_DAYS = 126              #: h, the (t, t+h] grading window. ~6 months.

#: Walk-forward: the model is fitted on cut dates strictly before the graded
#: one, and predicts it out of sample. Nothing is graded until this many prior
#: dates exist, so the first few dates are training-only.
MIN_TRAIN_DATES = 4

# ── co-movement, defined once ───────────────────────────────────────────────
#: Residual return = r_i - a - b_mkt*r_mkt - b_sec*r_sec_excl_self, with a,
#: b_mkt, b_sec fitted by OLS on the TRAILING window only. The forward window
#: reuses the trailing betas: fitting betas inside the grading window would let
#: the target's own window choose its own market model.
#:
#: r_mkt is the CRSP value-weighted return of the whole panel (the house
#: benchmark). r_sec is the equal-weighted return of the name's FF12 group
#: within the universe, EXCLUDING the name itself — including it would put a
#: 1/n piece of r_i on both sides and manufacture correlation.
SECTOR_SCHEME = "ff12"

#: numeric YES = trailing residual correlation at or above this within-date
#: quantile of the pair distribution. Fixed in advance; never tuned.
NUMERIC_YES_Q = 0.90

# ── H2 matching, fixed in advance ───────────────────────────────────────────
#: A `semantic YES / numeric NO` pair is matched to controls drawn from
#: `semantic NO / numeric NO` on EXACT agreement in all three of:
#:   (1) cut date, (2) same-FF12-sector indicator, (3) rho_trail decile
#: within that date. Up to H2_CONTROLS_PER_CASE controls per case, drawn
#: without replacement by a seeded RNG.
H2_CONTROLS_PER_CASE = 5

# ── the estimator ───────────────────────────────────────────────────────────
#: Ridge, fixed alpha, standardised features. Deliberately NOT a gradient
#: booster: the arms differ only by which feature block is present, and a
#: high-capacity learner would let "the model got bigger" masquerade as "the
#: relationships carried information". Capacity is held constant on purpose.
RIDGE_ALPHA = 1.0

#: 80%-power MDE at 5% two-sided: 1.96 + 0.84. Identical constant to
#: `scripts/arena_core.MDE_Z`; the ruler is not re-derived per trial.
MDE_Z = 2.80

# ── seeds ───────────────────────────────────────────────────────────────────
SEED = 20260812
SEED_SHUFFLE = 202608121                             #: shuffled-semantic placebo
SEED_RANDOM_EDGES = 202608122                        #: random-edge control
SEED_H2_MATCH = 202608123                            #: H2 control draw

# ── extraction ──────────────────────────────────────────────────────────────
#: One extraction per (permno, 10-K). Edges are attached to the FILING DATE and
#: are visible at every cut date from the filing date until superseded. They
#: are therefore always strictly older than the window they are graded on.
EXTRACT_MAX_DOC_CHARS = 28_000   #: business-section excerpt handed to the model
EXTRACT_MAX_EDGES = 20           #: per document; a longer list is truncated
EXTRACT_MODEL = "deepseek-chat"  #: served model is READ OFF THE RESPONSE, never assumed
EXTRACT_TEMPERATURE = 0.0        #: extraction, not generation
#: RAISED from 2000 to 6000 on 2026-08-12, after measurement, not caution.
#: On the first full pass 41 of 1,636 replies (2.5%) failed to parse, and ALL
#: 41 had `tokens_out` exactly 2000 — every single parse failure was the cap,
#: none was a refusal or a malformed answer. v4-flash spends reasoning tokens
#: from the same budget, so a 20-edge answer with 20 verbatim quotes does not
#: fit. The loss is not random: it falls entirely on the documents with the
#: MOST relationships in them, which is the worst possible 2.5% to lose, and it
#: is invisible unless you cross-tabulate parse failures against output length.
#: Output tokens are billed on what is generated, not on the cap, so the higher
#: ceiling costs nothing on the 97.5% that never approach it.
#: `mg1_extract --repair` re-runs exactly the truncated documents.
EXTRACT_MAX_TOKENS = 6000

#: This session's slice of the campaign ceiling. `research_budget.require()`
#: still gates every wire request against the global 40k/$40; these are the
#: tighter numbers this run additionally holds itself to and halts on.
SESSION_MAX_CALLS = 20_000
SESSION_MAX_USD = 12.00

CAMPAIGN = "grand_arena_1"
