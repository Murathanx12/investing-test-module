"""LLM perception layer — extraction ONLY, never allocation.

The LLM is a sensory organ: it turns unstructured event text into a falsifiable,
timestamped probability. A separate rules layer maps calibrated probabilities to
positions. Two hard rules (from the methodology + five-AI review):

  1. NEVER backtest an LLM call on historical text with a current-vintage model —
     the model has memorised how history turned out (look-ahead by training).
     Valid evaluation is FORWARD ONLY, via the calibration ledger's Brier score.
  2. Entity-neuter inputs (strip names/tickers/dates) so the model cannot recall
     the specific outcome, per Gao-Jiang-Yan (2025).
"""
