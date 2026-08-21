# INSTR-PREDMARKET-MATCHING — V1 (frozen on commit, 2026-08-22)

The pairing procedure PREREG_PREDMARKET_2 gated behind its own commit. From
this commit forward, matched pairs may be graded; the procedure below may
not change. New contract families extend via V2+ of this instrument and
apply FORWARD only — re-matching history under a new spec is a new trial.

Committed BEFORE any prod snapshot pair existed (first possible pair:
2026-08-21 dev smoke — excluded from grading per the prereg; first prod
pair: 2026-08-21 17:55 ET snapshots, graded only from this spec's commit
date forward). The matcher implementation is
`backend/services/prediction_market_matching.py` (spec version string
`INSTR-PREDMARKET-MATCHING-V1` printed on every payload).

## V1 family: FED_DECISION

The target-rate action at one named FOMC meeting.

Match key = (family, meeting `YYYY-MM`, action_class), where action_class ∈
{maintain, hike_25, hike_50plus, cut_25, cut_50plus}.

- Kalshi side: ticker `KXFEDDECISION-{YY}{MON}-{ACT}` with ACT mapping
  H0→maintain, H25→hike_25, H26→hike_50plus, C25→cut_25, C26→cut_50plus.
- Polymarket side: title regexes
  `will the fed (increase|decrease) interest rates by (25|50)[+]? bps after
  the {Month} {YYYY} meeting` and
  `will there be no change in fed interest rates after the {Month} {YYYY}
  meeting`. "25 bps" (no plus) → *_25; "50+ bps" → *_50plus; any other
  strike wording is UNPARSED (no match), never approximated.

## Declared convention

The Fed moves the target range in 25bp multiples; therefore Kalshi's
">25bps" and Polymarket's "50+ bps" name the same event. If the Fed ever
moves off-multiple, every pair for that meeting is excluded under the
prereg's resolution-terms contamination clause.

## Refusals (all recorded, none silent)

- Ambiguous key (two contracts on one venue claim the same key): the key is
  refused entirely — listing quirks must not choose the price.
- One-sided book (no mid on either venue): pair recorded as REFUSED_NO_MID.
- Unpaired keys are counted and listed, never guessed into a pair.

## Price and metric

- Venue mids as defined in the preregs (Kalshi (yes_bid+yes_ask)/2 dollars;
  Polymarket (bestBid+bestAsk)/2).
- Same-day divergence = |mid_K − mid_P|; COST_BAR = 0.05 (frozen in
  PREREG_PREDMARKET_2).
- The trial's deciding metric additionally requires persistence: the same
  matched key above COST_BAR at the NEXT daily snapshot too.

## First live reading (context, not grading — dev smoke, excluded)

2026-08-21: 16 matched contracts across 4 FOMC meetings (Sep/Oct/Dec 2026,
Jan 2027); 0 above COST_BAR; max divergence 0.02 (maintain legs). Consistent
with the prereg's honest prior at daily observation frequency.
