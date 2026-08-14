"""GRAPH-COVARIANCE-1 — the frozen parameters.

WHY THIS FILE EXISTS SEPARATELY
===============================
Same reason as `mg1_config.py`, and the same discipline. The pre-registration
NAMES the frozen parameters; this file ENUMERATES them, and it is committed
BEFORE a single covariance matrix is built or graded, so every choice is dated
rather than defensible-in-hindsight.

Nothing here may change after the first grading run. If something must change,
it is a NEW trial with a new name.

WHAT IS INHERITED RATHER THAN RE-CHOSEN
---------------------------------------
The universe, the cut dates, the trailing/forward windows, the residual
definition, the ridge alpha, the MDE constant, the placebo seeds and the edge
corpus all come from `mg1_config` by reference. Re-choosing any of them here
would silently make this a different panel from the one MARKET-GRAPH-1 graded,
and the whole point of this trial is that it inherits that panel exactly.

No value below was chosen by looking at an outcome.
"""

from __future__ import annotations

from scripts import mg1_config as MG1

# ── inherited by reference, never re-chosen ─────────────────────────────────
TRAIL_DAYS = MG1.TRAIL_DAYS              #: 252
HORIZON_DAYS = MG1.HORIZON_DAYS          #: 126
MIN_TRAIN_DATES = MG1.MIN_TRAIN_DATES    #: 4
RIDGE_ALPHA = MG1.RIDGE_ALPHA            #: 1.0
MDE_Z = MG1.MDE_Z                        #: 2.80 — the ruler is not re-derived
SEED_SHUFFLE = MG1.SEED_SHUFFLE
SEED_RANDOM_EDGES = MG1.SEED_RANDOM_EDGES

#: Newey-West lags for the per-cut-date series. Cut dates are one quarter apart
#: while the holding window is two quarters, so consecutive windows overlap by
#: half. Two lags covers that overlap. Identical to MARKET-GRAPH-1 stage 5.
NW_LAGS = 2

#: Purge depth for the walk-forward ridge fit: drop the last PURGE training cut
#: dates before each fit. Cut dates are one quarter apart while the label window
#: is two quarters, so the most recent training date's outcome reaches INSIDE
#: the test window; 2 removes the overlap outright.
#:
#: MARKET-GRAPH-1's HEADLINE arm ran unpurged and its section 8C measured that
#: purging moves the answer essentially not at all (9.49e-04 against 9.68e-04).
#: This trial takes the purged setting anyway, because CLAUDE.md's standing rule
#: is purged CV with an embargo and the measurement says it costs nothing to
#: obey it. Chosen here, before any covariance matrix exists, for a stated
#: reason that is not an outcome.
PURGE = 2

# ── the feature blocks, verbatim from MARKET-GRAPH-1 stage 5 ────────────────
#: Changing either list would make `model_numeric`/`model_semantic` something
#: other than the arms whose difference MARKET-GRAPH-1 H1 measured.
BASE_FEATS = ("rho_trail", "rho_trail2", "same_sector")
SEM_FEATS = ("has_edge", "log_n_edges", "max_conf")

# ── PSD repair, applied IDENTICALLY in every arm ────────────────────────────
#: A ridge predicts each entry independently, so the predicted matrix is not
#: guaranteed positive semi-definite. The repair is: clip entries to
#: [-CORR_CLIP, CORR_CLIP], symmetrise, force a unit diagonal, floor the
#: eigenvalues, rescale back to a unit diagonal. Applied to EVERY arm including
#: the context arms, so no arm gets its own treatment.
#:
#: ── AMENDMENT 2026-08-14, recorded rather than quietly applied ─────────────
#: The first values here were EIG_FLOOR = 1e-8 absolute and no entry clipping.
#: Both were wrong, and the first gate run proved it from MATRIX DIAGNOSTICS,
#: which are pre-declared as reported-never-deciding and contain no outcome:
#:
#:   calibration ratio (realised / predicted portfolio vol) = 4,519
#:   mean condition number after repair                     = 7.1e8
#:   mean pre-repair minimum eigenvalue                     = -0.126
#:   predicted annualised portfolio vol                     = 0.0013
#:   realised annualised portfolio vol                      = 0.027
#:
#: A matrix that forecasts 0.13% annualised volatility for a portfolio that
#: realises 2.7% is not a risk model; the run was void on that number alone,
#: independent of what any arm scored against any other. The mechanism is
#: exact: the ridge is unconstrained and predicted correlations up to 1.0119,
#: the assembled matrix had a minimum eigenvalue of -0.344, and flooring those
#: at 1e-8 does not repair them — it manufactures near-zero-variance directions
#: that a minimum-variance solve finds and levers into without bound. The
#: repair ran green and destroyed the object, which is this project's house
#: failure mode wearing a linear-algebra costume.
#:
#: The replacement floor is RELATIVE to the mean eigenvalue of a correlation
#: matrix, which is exactly 1 by construction, so EIG_FLOOR_REL is "one tenth
#: of the average eigenvalue". Chosen from the SPECTRUM of the predicted
#: matrices (min -0.344, 1st percentile +0.120, 10th +0.343, median +0.720,
#: max 11.3) — a property of the matrices, containing no forward return and no
#: comparison between arms — so that it removes the pathological tail and
#: leaves the healthy body of the spectrum untouched. It binds on roughly the
#: bottom 1% of eigenvalues and on nothing else.
#:
#: Because this IS a judgement call, the primary is additionally reported at
#: EIG_FLOOR_SENSITIVITY. That sensitivity can only DEMOTE a verdict: if the
#: sign or the detectability of the headline moves across floors, the result is
#: fragile and must be reported as fragile. It can never promote.
CORR_CLIP = 0.99
EIG_FLOOR_REL = 0.10
EIG_FLOOR_SENSITIVITY = (0.05, 0.10, 0.20)

#: Additional ridge shrink toward the identity, applied identically to every
#: arm. ZERO on purpose: the eigenvalue floor above already bounds the
#: conditioning, and a second regulariser would be a free parameter sitting
#: directly in the decision path with nothing left for it to do.
SHRINK_TO_IDENTITY = 0.0

#: RUNTIME VOID ASSERTION. If an arm's mean calibration ratio (realised /
#: predicted portfolio volatility) falls outside this band, that arm's matrices
#: are numerically degenerate and the arm is VOID — reported as void, never
#: compared. This exists because the defect above was caught by a human reading
#: a diagnostic, and a check that depends on somebody looking is not a check.
CALIBRATION_VOID_BAND = (0.2, 5.0)

# ── the portfolios ──────────────────────────────────────────────────────────
#: PRIMARY (H1): residual-space global minimum variance, fully invested, no
#: sign constraint. In residual space this is a real, holdable, market- and
#: sector-neutral long-short portfolio: w'r_resid is exactly what it earns.
GMV_FULLY_INVESTED = True

#: SECONDARY (H2): long-only, fully invested, per-name cap on total-return
#: covariance. The cap is the standard diversification constraint and exists so
#: that "minimum variance" cannot degenerate into two utilities. It sits in the
#: SECONDARY statistic only, never in the primary.
LONGONLY_MAX_WEIGHT = 0.10

#: Iterations for the projected-gradient long-only solve, and its convergence
#: tolerance. Fixed in advance; the same budget is given to every arm, so an
#: arm cannot win by being solved harder.
LONGONLY_MAX_ITERS = 5000
LONGONLY_TOL = 1e-10

# ── grading ─────────────────────────────────────────────────────────────────
#: A cut date is graded only if the forward window has at least this share of
#: finite residual observations for the held names. Below it the realised
#: variance is an estimate of something else.
MIN_FWD_OBS_FRAC = 0.8

#: Realised volatilities are annualised at this many trading days so the
#: reported numbers are readable. Annualisation is a monotone rescaling and
#: cannot change any verdict.
ANNUALISE_DAYS = 252

# ── the power gate ──────────────────────────────────────────────────────────
#: `oracle_on_edges` overwrites exactly the edge-carrying entries of the
#: `model_numeric` matrix with the TRUE realised forward correlation. It is the
#: ceiling on any edge-based correction at this coverage. If its improvement
#: over `model_numeric` is inside its own MDE, the trial is
#: UNDERPOWERED_BY_CONSTRUCTION and no null from a real arm is a kill.
#:
#: This runs FIRST and its result is written before the real arms are graded,
#: so the gate cannot be read after the answer is known.
ORACLE_GATE_REQUIRED = True

# ── the stratified placebo (MARKET-GRAPH-1 section 8B) ──────────────────────
#: Edge labels permuted WITHIN each (cut date x same_sector x rho_trail decile)
#: cell. This reproduces the real edge set's position in the pair distribution
#: exactly and destroys only WHICH pair inside the cell carries the edge. It is
#: the load-bearing placebo for a minimum-variance objective, because the solve
#: weights high-correlation pairs most and edge-carrying pairs sit at mean
#: rho_trail 0.103 against 0.0003 overall.
SEED_STRATIFIED = 202608141

CAMPAIGN = "brain_v3"
TRIAL = "GRAPH-COVARIANCE-1"
