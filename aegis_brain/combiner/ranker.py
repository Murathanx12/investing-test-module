"""L3 shallow combiner — a RANKER, not a learner.

GKX: predictive slopes deteriorate quickly with depth at this signal-to-noise;
shallow beats deep. Two implementations behind one interface:

  - GBMRanker: LightGBM (deliberately small trees), falls back to sklearn
    HistGradientBoosting when lightgbm is unavailable.
  - ShallowNNRanker: 1–2 hidden-layer MLP. If it ever needs more depth to win,
    that is evidence of overfitting, not a reason to add layers.

Both consume a stacked design matrix (rows = (month, symbol) observations,
columns = signal values, target = NEXT month's return) and emit scores whose
only meaning is cross-sectional ORDER within a month.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class GBMRanker:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self._model = None

    def _make(self):
        try:
            from lightgbm import LGBMRegressor

            return LGBMRegressor(
                n_estimators=200,
                num_leaves=15,          # shallow trees
                max_depth=4,
                learning_rate=0.05,
                min_child_samples=100,  # cross-sectional data is noisy — big leaves
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=self.random_state,
                verbose=-1,
            )
        except ImportError:
            from sklearn.ensemble import HistGradientBoostingRegressor

            return HistGradientBoostingRegressor(
                max_iter=200, max_depth=4, learning_rate=0.05,
                min_samples_leaf=100, random_state=self.random_state,
            )

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "GBMRanker":
        self._model = self._make()
        self._model.fit(X.values, y.values)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self._model.predict(X.values)


class ShallowNNRanker:
    """1–2 hidden-layer MLP over rank-standardized features."""

    def __init__(self, hidden: tuple[int, ...] = (32,), random_state: int = 42):
        if len(hidden) > 2:
            raise ValueError("Shallow means shallow: at most 2 hidden layers (GKX).")
        self.hidden = hidden
        self.random_state = random_state
        self._model = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "ShallowNNRanker":
        from sklearn.neural_network import MLPRegressor

        self._model = MLPRegressor(
            hidden_layer_sizes=self.hidden,
            alpha=1e-3,               # L2 — regularize hard
            early_stopping=True,
            n_iter_no_change=10,
            max_iter=500,
            random_state=self.random_state,
        )
        self._model.fit(X.values, y.values)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self._model.predict(X.values)


def make_ranker(kind: str = "gbm", **kw):
    if kind == "gbm":
        return GBMRanker(**kw)
    if kind == "nn":
        return ShallowNNRanker(**kw)
    raise ValueError(f"unknown ranker kind: {kind}")
