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

# ── the feature blocks, verbatim from MARKET-GRAPH-1 stage 5 ────────────────
#: Changing either list would make `model_numeric`/`model_semantic` something
#: other than the arms whose difference MARKET-GRAPH-1 H1 measured.
BASE_FEATS = ("rho_trail", "rho_trail2", "same_sector")
SEM_FEATS = ("has_edge", "log_n_edges", "max_conf")

# ── PSD repair, applied IDENTICALLY in every arm ────────────────────────────
#: A ridge predicts each entry independently, so the predicted matrix is not
#: guaranteed positive semi-definite. The repair is: symmetrise, force a unit
#: diagonal, clip eigenvalues at EIG_FLOOR, rescale back to a unit diagonal.
#: It is applied to EVERY arm including the context arms, so no arm gets its
#: own treatment. The pre-repair minimum eigenvalue is recorded per arm.
EIG_FLOOR = 1e-8

#: Additional ridge shrink toward the identity, applied identically to every
#: arm. ZERO on purpose: a non-zero value would be a free parameter sitting
#: directly in the decision path, and the ridge-predicted matrices are already
#: smooth functions of three-to-six features and therefore well conditioned.
#: The `sample` context arm is the only one that would want it, and it is a
#: context arm precisely because it cannot decide anything.
SHRINK_TO_IDENTITY = 0.0

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
