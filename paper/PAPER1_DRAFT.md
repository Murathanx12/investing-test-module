# The Empty Shelf: A Pre-Registered, One-Shot Search for Retail-Accessible Equity Signals, and What Its 159 Failures Measure

**Working draft v0.1 — 2026-07-30.** Three-page skeleton per
`ROADMAP_2026-07-29_POST_FREEZE.md` (Priority B spec). Every number below was
verified against its primary repo artifact on 2026-07-30 (three independent
verification passes; receipts in the session transcript and
`docs/research/AI_PANEL_2026-07-29*.md`). Author: Murathan Abdullaev.

---

## 1. Introduction

Published cross-sectional equity anomalies decay after publication (McLean
and Pontiff 2016), and the decay is steeper for the most celebrated effects.
A solo researcher replicating this literature faces two additional hazards
the institutional literature rarely prices: retail-grade data that fails in
ways survivorship bias does not describe (wrong prices wearing the right
ticker, retroactively rewritten factor histories, look-ahead-contaminated
index files), and an unpriced multiple-testing bill — nothing stops a solo
project from quietly re-running a test until it passes.

This paper reports a research program built to make those failures visible
and expensive. Every hypothesis was **pre-registered before any data touch**
(hypothesis, primary metric, decision rule, and earliest decision date
committed to a git ledger whose timestamps are the tamper evidence), run
**once** against a frozen explore window (2004–2018), and promoted to a
held-out confirm window (2019–2024) only on a pre-declared bar — one shot,
results final, rejected trials published. Twelve research rounds
accumulated **158 cumulative candidates** (the multiple-testing denominator
used to deflate every Sharpe ratio) across 43 registered trials and
instruments, then froze; one post-freeze registration through the freeze's
own de-risking door (rejected) brings the count to **159**.

Three results are the paper:

1. **The cost-killed shelf is empty.** Under a rule frozen before it was
   applied, not one large/mid-cap candidate out of 155 had a
   gross-profitable, rank-informative book that transaction costs killed.
   Every large/mid rejection was informational — the signal was not there,
   at realistic (~3–4 bps half-spread) or any other cost.
2. **The held-out wall rejected every explore-passing allocation instrument
   with the same signature** — three regime/volatility overlays passed
   2004–2018 on the strength of one crisis (2008) and failed 2019–2024 on
   crises with different dynamics (2020's 23-day crash; 2022's dual
   stock-bond decline). The one survivor is a defensive diversifier that
   never claimed to beat the index.
3. **A belief engine that survives engineering review can still contain no
   information.** An analog-retrieval regime engine passed its architecture
   diagnostics, retrieved genuinely old analogs — and a constant forecast at
   the unconditional base rate strictly beat it on all four outcomes it
   scored.

The contribution is not a new anomaly. It is (a) a registered, one-shot,
deflated protocol demonstrated at retail scale, (b) the empty-cost-cohort
measurement, which locates the missing edge in information rather than
friction, and (c) a documented catalogue of retail data artifacts, each of
which produced a statistically compelling false result before a control arm
or a hash gate caught it.

## 2. Method

**Two ledgers.** The *registration ledger* (`TRIALS/registry.jsonl`, 43
rows; 21 further pre-registrations live in the product repo, of which
eight are forward-IC clocks and the rest lane trials and adjudicated
backtests) records each trial's frozen commitment. The *cumulative candidate count*
(159) counts every signal × segment arm ever scanned and is the deflation
denominator: Deflated Sharpe Ratios are computed against `n_trials` = the
cumulative count at run time, never against a per-batch count. The registry
carries no outcome field by design — verdicts live in the prose ledgers and
per-trial documents from which Table 1 is compiled.

**The gates, in order.** (i) `prior_check` — a retrieval gate over the
project's own graveyard; no registration without a prior-check transcript
(two candidates died at this gate before touching data; a third died at
the adjacent literature gate). (ii)
Pre-registration with kill conditions. (iii) One-shot explore 2004–2018.
(iv) Held-out confirm 2019–2024, opened only by explore graduates, bars
frozen at registration. (v) A re-litigation ban: closed families stay
closed. A late addition, earned twice in one round: **every pre-declared
fallback trigger must name its own control arm at registration** — a text
signal's fallback fired at t_NW = −9.74 (naive −15.03), and the same
filings scored against a random *different firm* fired it at t_NW = −8.39
(a placebo excess return 80% of the treatment's −3.06%). A fallback is a
hypothesis; it does not skip the design the primary had to pass.

**Costs.** A flat 25 bps one-way charge decided large/mid graduations
(50 bps for the small-cap segment); a Kyle–Obizhaeva (2016, eq. 33)
invariance spread model (ln s̄ = −3.07, exponent −1/3, half-spread primary)
re-measured them. Measured large/mid median half-spreads are 3.4–4.2 bps by
era — the flat 25 bps wall *over*-penalizes large/mid books, which
sharpens, not softens, the empty-cohort result.

**Ruler validation.** The panel harness was validated (2026-07-26) against
the Ken French vintage then on disk: equal-weight market vs Mkt-RF+RF
correlation 0.927 (bar 0.90), small-minus-large vs SMB 0.778 (bar 0.60),
momentum excess vs UMD 0.645 (bar 0.40). That vintage was hash-pinned two
days later (sha256 `54e3b8dd…`; vintage date ≤ 2026-07-21, download date
recorded honestly as unknown; the loader refuses a mismatch), and it is
the vintage this paper cites. Pinning is not pedantry: across one
~18-month vintage step,
92.8% of overlapping HML months, 91.5% of SMB, and 61.2% of Mkt-RF months
changed (measured over 1,182 overlapping months) — unpinned factor data
silently re-derives results on a different history.

**The self-deception ceiling.** Under the zero-skill null the expected
maximum |t| over this library is 3.59 (3.98 allowing sign flips). Mining
the full window with sign flips plus a single real rank-free book effect
manufactured t = 6.58. House rule since: on this data, t ≥ 7 is a bug, not
skill.

**Scoring probabilistic forecasters (the D3 protocol).** Any forecaster
that emits probabilities is scored against **persistence** (never
climatology — climatology flatters anything that hedges), by paired
Diebold–Mariano tests on Brier-score differences with Newey–West and
circular-block-bootstrap errors, effective sample size per Santer et al.,
and a Murphy decomposition (reliability − resolution + uncertainty).
Resolution is the payable part: a forecaster whose advantage is
reliability-only is a base-rate emitter wearing a model's clothes.

## 3. Results

### Table 1 — the graveyard (shell; full table from the prose ledgers)

| Bucket | Count | Note |
|---|---|---|
| Cumulative candidates | 159 | 158 at freeze + 1 post-freeze (conditional VT, rejected) |
| Died | 155 of 158 pre-freeze | only batches 2 and 7 ever graduated a candidate; every other batch closed at zero |
| Held-out confirm entries (hypothesis-level) | 6 | 4 rejected at confirm; 2 passed |
| Confirmed survivors | 2 | gp-small (weak, held honestly); TSMOM-XA (defensive) |
| Open, not survivors | insider CMP-IC clock; fusion composite (t 1.66, no confirm-grade claim) | see convention note |
| Sign reversals recorded | 5 | incl. monthly PEAD *inverted* (IC t −2.6) |

*(Counting conventions, stated because the ledgers do not force them.
Confirm entries: six hypothesis-level entries opened the held-out window;
in addition one pre-registered PIT-timing upgrade re-measured an existing
survivor there (adopted), and two diagnostic instruments read the window
under the freeze's contamination clause — none of the three is a new
hypothesis. Survivors: the freeze document's own survivor table lists four
rows while its "155 of 158 died" implies three; this draft counts gp-small,
TSMOM-XA, and the insider clock inside that arithmetic and carries fusion
as open-without-a-claim — the seam is the freeze doc's, flagged rather
than smoothed. The registry's 43 rows and the 159-candidate deflation
clock are different objects — §2.)*

**The lone cross-sectional survivor, stated at its honest size.** Gross
profitability in small caps: explore t_net 1.96 at flat 50 bps; held-out
confirm +24.1 bps/mo, t 0.89 (Newey–West 0.77), out-of-sample IC t 4.29,
DSR 0.098 at n_trials = 61; FF6 alpha *negative* (−3.3%/yr, t −1.06 — the
premium is size-loaded beta, not alpha). Under measured KO costs the
confirm t rises to 1.11. A separate pre-registered re-timing to
earnings-announcement availability (a pure PIT correction, 90.2% of
136,546 firm-years re-timed, median 4.0 months reclaimed) lifts the
flat-cost confirm t from 0.89 to 1.24, and 1.45 under KO costs — but the
paired book-level gain is +2.7 bps/mo (t 0.39), and +6.8 of the +9.4
headline improvement is benchmark composition. The upgrade was adopted on
PIT-correctness, not on the headline. This is what surviving looks like under this protocol:
below every conventional bar, and said so.

### Exhibit A — the empty cost-killed cohort (the lead result)

Rule frozen before application, large/mid segment, non-contaminated
candidates: *graduation-but-for-costs* ≡ IC t ≥ 2 **and** gross t ≥ 1.5
**and** net t < 1.5. **The cohort is empty across all 155 candidates.**
The gross-passed-net-failed set is literally empty; among rank-informative
rejects the best *gross* t is 1.48 — below the gross bar, so it could not
graduate at zero cost. With measured half-spreads of 3.4–4.2 bps, costs
were never the executioner in large/mid caps: every rejection was
informational. Consistent with the fame-decay ordering (Exhibit B), this
locates the post-publication decay mechanism in arbitrage of the
information, not in friction — the retail-accessible large/mid shelf is
not cost-gated, it is empty.

**The small-cap extension (INSTR-SMALL-SHELF, 2026-07-30) — and why the
claim is now a named exception rather than a blanket.** Large/mid is the
least retail-specific segment in a paper about retail accessibility, and
the small segment had been structurally barred from graduation by a design
premise ("25 bps *understates* small-cap costs") that our own later
measurement inverted: KO half-spreads in small are 11.6–13.1 bps, so the
flat wall *over*-penalized by 2–4×. Applying the identical frozen rule to
small returns a **non-empty cohort of five** (rec_mom, industry_mom,
fscore_lite, cash_prof, re_me) and **zero graduates** — two clear the
primary cost arm and both fail the pre-required stress arm. The deciding
column is again the zero-cost bound: in large/mid *nothing* could graduate
even for free, whereas in small exactly one candidate can (`rec_mom`, free
net t 2.64, IC t 3.32) and is destroyed by 36.8%/month turnover. So across
160 candidates there is **exactly one genuinely cost-killed signal in the
retail-accessible universe, and its executioner is turnover, which no cost
model repairs.** Two further facts belong in the same breath: the design
premise was wrong for the entire search, and correcting it moved **zero
verdicts**; and below dollar-volume rank 3000 the eligible universe is a
median of 35 names per month at the honest $1 / $200k floors, so there is
no smaller shelf left to appeal to.

### Exhibit B (supporting) — the published t-statistic as a contrarian ordering

Across 13 signals matched to the Chen–Zimmermann SignalDoc, the Spearman
correlation between published |t| and our in-window large/mid-cap |IC t|
is **−0.544**
(p 0.055, n = 13): the more celebrated the published effect, the deader it
runs in 2004–2018. Sign agreement is 0.923 — directions survive; magnitudes
invert (median level ratio 0.378). This is a variant of McLean–Pontiff's
Fig. 1.B (decay increasing in in-sample t) and is positioned as supporting
evidence only: n is small, p is above 0.05, and a same-construction
robustness arm — a stated precondition for any stronger claim — remains an
*unregistered* open door under the freeze; until it is registered and run,
this exhibit does not harden.

### Exhibit C — three allocation instruments, one failure signature

Every explore-passing regime/volatility overlay died at confirm the same
way: an explore pass carried by 2008, a confirm failure on crises 2008 does
not resemble.

- **Jump-model rotation:** explore 11.2% CAGR, maxDD −26.6% vs SPY −55.2%;
  confirm REJECT — 2022 cost −21.6% (risk-off into bonds during a dual
  crash), 2020 +4.8% vs SPY +18% (dodged the crash, missed the rebound).
- **Its inflation-gated repair (JM2):** made the year it was built for
  *worse* — 2022 −23.9% vs −21.6% — because the 2022 bond crash was
  real-rate-driven and the breakeven gate saw calm.
- **Conditional volatility targeting** (long-only, leverage ≤ 1.0,
  de-risking only above the causal 80th percentile of 63-day realized
  vol): explore PASS with ΔmaxDD +15.0pp vs SPY (−40.19% vs −55.19%);
  confirm REJECT with ΔmaxDD **0.00pp** — a maximum drawdown identical to
  SPY's to four decimal places, same trough date (2020-03-23) — at a cost
  of 2.6pp of CAGR. The mechanism is named and general: on 2020-02-28,
  trailing 63-day vol stood at 0.162 against a causal 80th-percentile
  threshold of 0.202 — a backward-looking window cannot resolve a 23-day
  crash launched from a calm base, and in the slow 2022 decline the same
  overlay bought only +2.3pp of return and +1.8pp of drawdown. An
  unconditional-VT contrast arm beat the conditional arm in both windows
  and still failed the confirm bar — the refinement subtracted value from
  a family that was already dead (four independent published refutations).

**The one pass:** a cross-asset time-series momentum overlay — crisis
alpha shown in-sample (2008 +4.9%) and replicated in the held-out window's
two unseen crises (2020 +9.2%, 2022 ≈flat at −0.9%), overlay maxDD −18.8%
vs SPY −33.7% — carried explicitly as a
defensive diversifier with a disclosed return drag (CAGR 10.2% vs 17.1%,
t −1.86). It is a sequence-risk instrument, not a beat-the-index claim.

### Exhibit D — the belief engine's honest null

An analog-retrieval regime engine (k-NN over 15 standardized macro
descriptors, 283 monthly belief states) was given three kill-first
diagnostics with pre-committed kill lines, then scored under the D3
protocol. Retrieval is genuinely historical (10.78% of analog mass within
12 months vs a 40% kill line; median analog age 4.9 years). The effective
dimension test fired (9 PCs at 90% variance vs a kill line of 5) — but the
prescribed low-dimension remedy is a no-op on the output: replacing 15-D
retrieval with 2–3 PCs changes 80–87% of retrieved analogs while moving
published probabilities by ≤ 0.05, because the outputs sit within
0.06–0.13 of the unconditional base rates regardless. The scoring verdict:
**a constant forecast at the base rate strictly beats the engine on all
four outcomes** (margins +0.031/+0.044/+0.095/+0.040 Brier). The engine's
single Diebold–Mariano win over persistence (6-month direction, t −2.31,
N_eff 54.9) is 87.6% reliability difference — hedging against a 0/1
baseline — and is fragile to bootstrap block length. Two earlier apparent
wins on crash outcomes were traced to an outcome-aggregation look-ahead
(analog forward windows overlapping the query's future) and vanished when
the aggregation was made causal. A disclosed engineering defect made the
null stronger, not weaker: the retrieval guard checked candidate counts,
not acceptances, so 59 of 239 causally-scored states — the entire GFC
block — silently used fewer than 50 analogs (minimum 3). The recorded
sensitivity (dropping states with fewer than 25 analogs) strengthens every
Diebold–Mariano statistic against persistence and would flip the two crash
outcomes to wins — disclosed as period selection, not adopted as a
correction; the shipped verdicts include the degenerate states. The confidence channel (D4) is
measurement-unresolved (rank and linear correlations disagree) and closed
by decision: no confidence output is surfaced until a successor validates
it under the same protocol. The engine ships as descriptive only; the
allocation layer that was to be built on it was cancelled by this result.

### Exhibit E — the data-artifact graveyard

Each artifact produced (or would have produced) a publishable-looking
number; each was caught by a control arm, a hash, or a canary — never by
inspection of the headline result.

1. **Selection wearing an event's clothes.** Distress 8-K filings showed
   −5.95% (t −7.06) 3-month drift — and a pseudo-event control dated 12
   months *before* each filing showed −6.79% (t −11.33). The "drift" was
   firm-level distress persistence plus eligibility attrition (the
   treatment arm silently kept 32% of events vs the control's 64%).
   Calendar-time confirms: −80 bps/mo (t −1.50) vs −229 (t −11.1).
2. **Rewritten factor history.** 92.8% of overlapping HML months changed
   across one Ken French vintage step (§2). Without a pinned,
   hash-verified vintage, an attribution re-run six months later is a
   different experiment.
3. **Look-ahead in the index file everyone uses.** SEC's full/quarterly
   EDGAR indexes are rebuilt weekly (vendor-documented: post-acceptance
   corrections are incorporated retroactively); the daily index is frozen
   at build time. Event studies built on the convenient index inherit
   look-ahead. A dateless quarterly aggregate (`master.idx`) nearly
   entered our pipeline through a loose glob; only SEC's 403 stopped it.
4. **Fabrication, not absence.** yfinance returns BBBY as a clean
   continuous series through 2026, `longName` "Bed Bath & Beyond, Inc." —
   with Overstock's prices ($18–20 in April 2023, when BBBY traded ~$0.25
   into Chapter 11). The retail failure mode is not missing data; it is
   wrong data wearing the right name.
5. **LLM look-ahead.** Backtesting an LLM on text predating its knowledge
   cutoff inflates apparent predictive power by ~37% of the standalone
   effect (Llama-3.3; Gao, Jiang & Yan 2025, arXiv 2512.23847), and the
   effect disappears genuinely out-of-sample (p = 0.033, Llama-2) — the
   "profit mirage" (Li et al. 2025, arXiv 2510.07920). All LLM signals in
   this program are therefore forward-only by construction.
6. **The silently dead collectors (two, different mechanisms).** A
   production SEC collector ran green under 12 passing tests while 403-ing
   on 100% of prod fetches — raw *unpaced* requests tripped SEC's 10/s
   threshold, which answers 403, not 429; the same User-Agent succeeded on
   the low-volume host, so the only difference was request count, a
   failure invisible from any dev machine. Six weeks later a second
   collector was found dead for a different reason (a pseudo-contact
   User-Agent SEC rejects) — on the first day a canary was pointed at it,
   having likely been dead since it shipped. "Ran without error" and
   "fetched data" are different claims; only the second one is evidence.

## 4. What remains open

A live forward program under the same registry: ten paper-trading lanes
(day 52 of a pre-committed 24-month no-claims window), a set of registered
forward-IC clocks (eight IC pre-registrations in the product repo;
earliest decisions begin 2027-01-11, the insider composite clock no
earlier than 2027-07-21), and a frozen candidate count that only attended,
pre-registered work may extend. The freeze at 159 is part of the result:
the protocol's value is that it stops.

---

### Notes to self (not part of the paper)

- Do-not-cite list respected (FABLE_HANDOFF §6): no Goyal-Welch-Zafirov
  "0 of 17", no "140 years"/Lorenz, no "17/40 years"/Lo, no Sharpe "74%",
  no unfetched secondary characterisations.
- Corrections applied to repo docs during this verification:
  AI_PANEL_2026-07-29's SPY explore maxDD (−45.2% → −55.19%, dated note);
  CANON.md §3's ~37% attribution split (dated note). Conventions held in
  this draft: +15.0pp is ΔmaxDD-vs-SPY, margin over bar is +10.0pp;
  TSMOM-XA 2022 = −0.9%; COND-VT 2022 = +2.3pp return / +1.8pp drawdown;
  guard defect on the causal ledger (59/239, min 3).
- UNRESOLVED before submission: the lookahead-inflation magnitude is
  recorded as ~37% (DEEP_RESEARCH_2026-06-14 §3.2, CANON §3) and ~32%
  (RESEARCH_SWEEP_2026-07-27:359, interaction 0.162 t 3.64) for the same
  arXiv ID (2512.23847). Fetch the paper and reconcile; until then the
  draft says "~37%" on the strength of the older verification but the
  conflict is on the record.
- Adversarial pass 2026-07-30: 8 substantive defects found and fixed
  (25-vs-50 bps wall, phantom robustness-arm registration, prior_check
  kill attribution, collector mechanisms/interval, zero-graduate batch
  list, confirm-entry convention, fusion counting seam, forward-clock
  dates). All magnitude claims confirmed exact.
- Candidate additions when full text is written: wall-decay curve (rank
  corr explore-t → confirm-t = 0.49); TEXT-LAZY as the measured
  Lazy-Prices post-publication decay (IC real at t 6.5–7.5 vs control,
  worth 11 bps/mo at t 0.87 long-only); FF vintage premium drift (HML
  4.143 → 4.062 %/yr).
