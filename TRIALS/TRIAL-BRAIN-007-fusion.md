# TRIAL-BRAIN-007-fusion

**Registered:** 2026-07-21 (UTC) — the fusion METHOD is frozen here BEFORE the combined
portfolio is ever formed, and (deliberately) the equal-weight scheme uses NO weights fit
to returns, so the fusion cannot be a second hidden layer of selection (audit warning).
**Registry row:** `TRIALS/registry.jsonl` (cumulative n → 21)

## Hypothesis
Weakly-positive, weakly-correlated signals can clear net-of-cost where each alone cannot
(diversification of alpha; JKP: the theme cluster survives, not the lone factor). A fixed
EQUAL-WEIGHT composite of the signals that survived their OWN kill conditions, long-only
top-quintile in the large/mid segment, earns positive net excess vs a cap-seg EW benchmark.

## Method (frozen — no tuning on returns)
- **Membership rule:** include a signal iff it SURVIVED its own pre-registered kill
  conditions (decided by that trial, not by fusion performance). Candidate pool:
  `opportunistic_insider` (BRAIN-003, survived), SUE (BRAIN-004), revisions (BRAIN-005).
  Whatever the membership turns out to be, the weighting below is fixed in advance.
- **Segment:** large/mid (fixed a priori — the segment where BRAIN-003's edge lived; NOT
  re-chosen on fusion results).
- **Combine:** each member signal → cross-sectional z-score per month (winsorized ±3);
  composite = simple MEAN of the member z-scores. **Equal weight. No return-fit weights,
  no ranker trained on the composite** (that would re-introduce selection).
- **Portfolio:** long-only top-quintile of the composite, 3-month hold-band, ADV cost,
  benchmark = large/mid EW. Arm C noise = random matched flag (gross-t leak bar).

## Kill conditions
1. Arm C noise GROSS |t| ≥ 3 → leak, void.
2. Composite net excess t < 1 → backtest REJECT (forward-only still allowed).
3. Composite does not beat the best single member's net t → fusion adds nothing (flagged).
4. Deploy gate: t > 3.4 AND DSR ≥ 0.95 AND PBO < 0.5 (expected unmet on this history).

## Result (2026-07-21 — never edited)
**Members qualifying (survived their OWN kill conditions): 1 — `opportunistic_insider` only.**
BRAIN-004 (PEAD) REJECT and BRAIN-005 (revisions) REJECT, so per the frozen membership rule
they are excluded (including them would be selecting weak/negative-net signals into the fusion —
exactly the hidden selection this pre-registration forbids).

### Verdict: **NOT RUN — insufficient surviving members.**
A fusion needs ≥2 survivors to test diversification-of-alpha; with a single survivor the
equal-weight composite is identical to BRAIN-003 and would only reproduce it. Recorded as
not-run (honest) rather than forcing rejected signals in to manufacture a "fusion." The trial
re-opens automatically when a second signal survives its kill conditions (e.g. a future FDA or
LLM-narrative signal). The pre-registration and its trial-count (n=21) stand.
