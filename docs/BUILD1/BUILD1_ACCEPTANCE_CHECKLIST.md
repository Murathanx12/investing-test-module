# BUILD-1 Acceptance Checklist

## Mandatory product gate
- [ ] B1 source coverage report exists and is based on real endpoint/tool probes.
- [ ] B2 private portfolio schema/persistence exists and is gitignored.
- [ ] B3 runs end-to-end from one command on dummy or real book.
- [ ] B3 writes machine JSON and human report with the same `as_of` timestamp.
- [ ] Every holding receives BUY/ADD/HOLD/TRIM/SELL.
- [ ] Every non-HOLD action includes recommended dollars, target weight, reason codes and evidence label.
- [ ] Replacement/funding source is explicit for adds where applicable.
- [ ] Wealth-target probability and severe-downside probabilities print together.
- [ ] LLM cannot set weights/dollar changes.
- [ ] Engine cannot auto-trade.

## Data integrity
- [ ] Analyst target/rating observations preserve published/first-seen/retrieved timestamps.
- [ ] Source provenance + raw hash stored.
- [ ] No invented analyst history.
- [ ] Stale observations are marked and downweighted/blocked.
- [ ] Conflicting sources remain visible.
- [ ] Historical PDF/Bloomberg snapshots preserve original as-of dates.

## Portfolio logic
- [ ] ReplacementEdge compares against the current portfolio, not standalone stock score only.
- [ ] Missing covariance is not treated as zero correlation.
- [ ] Position/sector/theme concentration checks exist.
- [ ] Microcap spread/liquidity warning exists.
- [ ] Growth/High Growth/Moonshot change sizing constraints only.
- [ ] Evidence scores are invariant to target mode.

## Auditability
- [ ] Numerical report claims bind to JSON/receipt fields where possible.
- [ ] Referee checks qualitative framing/qualifiers rather than substituting for deterministic checks.
- [ ] Recommendation snapshot is persisted for later scoring.
- [ ] Recommended trade and executed trade are separate states.
- [ ] Private holdings are blocked from Git staging/commit.

## End-of-session handoff
- [ ] Morning-report command documented.
- [ ] Live/stubbed/missing fields documented.
- [ ] B1 coverage matrix linked.
- [ ] VALIDATED/OBSERVATIONAL inventory printed.
- [ ] Tests pass.
- [ ] Repos pushed; manifests regenerated.
- [ ] Highest-value next item stated.
