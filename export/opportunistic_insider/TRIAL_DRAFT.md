# TRIAL-OPPORTUNISTIC_INSIDER-forward (draft from aegis-brain, 2026-07-21)

**Source:** aegis-brain `TRIALS/TRIAL-BRAIN-003-opportunistic-insider.md` · **Scorer:** `aegis_brain.signals.insider_scorer:opportunistic_insider_score`

## Hypothesis
Long large/mid-cap stocks with a non-routine (Cohen-Malloy-Pomorski) open-market insider PURCHASE filed recently; low-turnover ~12mo hold.

## Prior (deflated, from backtest — NOT a promise)
BRAIN-003 (2006-2024): large/mid +17 bps/mo vs EW (t=1.40), FF5+UMD alpha +102 bps/mo (t=1.89), post-2015 t=1.30; NULL in microcap. Leak-checked (noise gross|t|<3). Weak POSITIVE PRIOR — does not clear deploy gate (DSR 0.26).

## PIT inputs
- SEC Form 4 (filing-date stamped)
- CRSP/permno universe

## Kill conditions
net t<1 both cap segments = kill; noise gross|t|>=3 = leak void

## Forward scoring
Wire `aegis_brain.signals.insider_scorer:opportunistic_insider_score` into a pit_score_collector; score the forward clocks. Conviction is earned forward, not by the backtest.
