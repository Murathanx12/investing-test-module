"""Vendored anti-overfitting discipline from aegis-finance (engine/validation).

Vendored verbatim on 2026-07-19 from commit 790a0cb so this module has zero
import-time dependency on the main repo. If the originals change, re-vendor —
do not fork the math.
"""

from .overfitting import (  # noqa: F401
    CombinatorialPurgedCV,
    deflated_sharpe_from_returns,
    deflated_sharpe_ratio,
    effective_number_of_trials,
    expected_max_sharpe,
    min_track_record_length,
    passes_multiple_testing_hurdle,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)
from .purged_cv import PurgedKFold, purged_train_test_split  # noqa: F401
