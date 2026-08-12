# PREREG — WINNER-GENOME-1: does a tournament-winner strategy family shift the whole distribution, or only fatten its right tail?

**Registered** 2026-08-12, NIGHT-14, **before any simulation is run.**
**Family** portfolio-construction behaviour under a tournament objective
(selection-vs-sizing decomposition). **Grade** simulated-null direction check on
CRSP daily 2002-2024. **ACCRUES ZERO ARMS** — nothing here can seed, arm, size
or default anything on any lane, shadow or live. It is a measurement
instrument whose output is a distribution, not a policy.

**Provenance.** Murat entered the Bloomberg Global Trading Challenge and asked
how the enormous 5-week leaderboard returns were produced: *"it doesnt seem
real even looks luck but i dont think so."* The scientifically answerable form
of that question is `NIGHT14_BRIEFING.md` §4 and the external review's own
restatement: **which observable portfolio-construction behaviours occur
disproportionately among winning portfolios, survive controls for volatility
and winner-selection, and continue to work in periods not used to discover
them?**

**What we do NOT have, stated before any number is produced:** the winning
teams' actual holdings. The Bloomberg tables in Murat's screenshots are
**aggregate across all ~2,600 competitors**, so no team's portfolio can be
reconstructed from them, and this trial does not pretend to. What is
reconstructible is the **strategy family** each winning captain publicly
described. Those descriptions are the input; the holdings are not available at
any price and their absence is a permanent limit on what this trial can say.

---

## 0. Corpse check

Run before writing §1 and re-run before commit:
`python scripts/lint_prereg.py TRIALS/PREREG_WINNER_GENOME_1.md`.

**Deliberate non-collision with TRIAL-THEME-SUPPLY / THEME-CASCADE-1.** Both of
those test *second-order supply-chain beneficiaries*, and that mechanism class
is CLOSED (supplier baskets REJECT at annual cadence, `cust_mom` REJECT at
monthly). **Nothing in this trial touches it.** No family here is defined by a
customer-supplier link, an input-output table, a theme graph, or a second-wave
node. The five families are defined only by trailing price, volume, volatility,
accounting quality, sector membership and size/price level. If a reader
recognises "the SK Hynix / SanDisk / WDC pattern" anywhere in this document,
they have misread it — that idea is dead and stays dead.

Resurrects: TRIAL-COND-VT and the exposure/sizing family (EXPOSURE-CONTROL-1,
`sell_to_cash`) — new instrument: those trials asked whether a **timing rule**
improves ONE realised path (n=1 book, n=1 war). This asks a different question
with a different unit of observation: whether a **selection rule's whole return
distribution** sits above its own volatility-matched random control, measured
across **231 non-overlapping 5-week windows × 2,600 simulated teams per arm**,
where the window is the sampling unit and the MDE is computed from the measured
between-window dispersion rather than from one episode. A timing verdict on one
path cannot answer a distributional question about selection, and the reverse
is also true — no result here reopens the conditional-vol-target family.

---

## 1. Hypothesis

**H1 (the deciding one).** At least one of the five publicly-described
tournament-winner strategy families produces a 5-week return distribution whose
**median** sits above the median of a **random portfolio matched on the same
constituent-volatility distribution, same position count, same weighting rule
and same window** — by at least that difference's own measured 80%-power MDE,
with the same sign in ≥5 of 8 pre-declared regime blocks and in both halves of
the sample.

**H2 (the mirror, equally publishable).** The families beat the *unmatched*
market-volatility random control (C4) on the maximum-over-2,600 and on p95
while being indistinguishable from the *volatility-matched* control (C3) on the
median. That is **dispersion, not selection**: the family bought a lottery
ticket with a bigger variance, not a better expectation.

**H3 (the transfer question).** If a family's selection carries information,
that information survives removing the leaderboard gamble: re-sized at 10% /
5% / inverse-vol / ERC risk-parity / half-Kelly, the same name sets still beat
their matched control on return-per-unit-volatility. If the advantage exists
only at the 20% tournament cap, the family was a bet, not a signal.

**Honest prior: LOW for H1, HIGH for H2.** Stated plainly so it cannot be
revised afterwards. Three separate reasons: (a) our own registry has killed
cross-sectional momentum, small-cap tilts and volatility timing repeatedly and
at better power than this design has; (b) the 2024 RIT captain said outright
that the objective was maximum dispersion and that they could have finished
last; (c) the maximum of 2,600 draws from *any* high-variance distribution is
enormous, which is a fact about order statistics and not about skill. The
prior that some family clears its MDE on the **median** is roughly **20%**. The
prior that at least one clears it on **p95 or the max** while failing on the
median is high, ~70% — and that outcome is H2, which is a finding, not a
failure.

**"It is all luck" is not the registered expectation either.** It is a
hypothesis with its own control (C3) and it can lose. The null here is
*simulated*, never asserted.

---

## 2. Data, frozen

- **Spine:** CRSP daily stock file, `data/wrds_raw/dsf_full/dsf_{2002..2024}.parquet`
  (daily `ret`, `prc`, `vol`, `shrout`). Survivorship-free.
- **Delisting:** `data/wrds_raw/crsp_dsedelist.parquet`, spliced at
  `dlstcd >= 200` (code 100 = still active, per `daily_sim.py`); performance
  delists (400-591) with missing `dlret` get Shumway −0.30. A team holding a
  name that dies mid-window eats the delisting return. **This is the single
  most important survivorship control in the design** and it is the reason
  CRSP was chosen over a yfinance fetch of current index members.
- **Universe classification:** `data/wrds_raw/crsp_stocknames.parquet`
  (`shrcd`, `exchcd`, `siccd`), evaluated at each window's formation date.
- **Quality (F3 only):** `data/wrds_raw/comp_funda.parquet` +
  `ccm_link.parquet`, annual fundamentals lagged **6 months** after
  `datadate` before they may be used. Coverage share is reported per window;
  a window with <40% F3 coverage is reported as such and F3's own MDE absorbs
  the smaller n.
- **Benchmark:** `data/wrds_raw/crsp_dsi.parquet` `vwretd` (CRSP value-weighted
  total return) — the honest market yardstick, reported beside C2.
- **Sample:** 2002-01-01 → 2024-12-31. Everything before 2002 is excluded
  because `dsf_full` starts there; 2025-26 is excluded because the daily file
  ends in 2024. **No window is chosen by hand.**

### Eligible universe at formation date T0 (frozen filters, in order)
1. `shrcd ∈ {10, 11}`, `exchcd ∈ {1, 2, 3}` on the name row valid at T0.
2. Price at T0 `abs(prc) ≥ $5`.
3. ≥252 trading days of price history strictly before T0.
4. 63-day median dollar volume ≥ $1,000,000 as of T0.
5. Rank the survivors by 63-day median dollar volume, keep the **top 1,500**.

That is a deliberate "S&P-1500-like liquidity screen off the CRSP names" and it
is frozen. It is NOT the tournament's 10,000+ WLS global universe — see §8.

---

## 3. Windows, frozen and mechanical

A tournament round is **25 trading days** (5 weeks). The window set is
**every non-overlapping consecutive 25-trading-day block** tiling the CRSP
trading calendar from the first trading day of 2002 to the last of 2024, with
any final partial block dropped. That is ≈231 windows and **it is a tiling, not
a selection** — there is no seasonal, regime or event choice available to the
analyst, which is the point.

**Pre-declared regime blocks (8), for the coverage condition:**
2002-2003 · 2004-2006 · 2007-2009 (GFC) · 2010-2012 · 2013-2015 · 2016-2018 ·
2019-2021 (COVID) · 2022-2024 (rate shock). At least two are drawdown regimes
by construction.

**Sample halves for the out-of-period check:** DISCOVERY-half = windows starting
before 2014-01-01; VALIDATION-half = the rest. Note the families were *not*
discovered in this data at all — they come from public interviews about
2021-2025 competitions — so the whole record is out-of-sample with respect to
their origin. The halves are a stability check, not a discovery/holdout split,
and will be described that way.

---

## 4. The arms

Every arm obeys the 2025 handbook rules exactly: **long only, no leverage
(weights sum to ≤1, remainder in cash at `rf`), no single position above 20%,
ranked on total return over the window.**

**Team construction, common to every stochastic arm:**
- position count `k ~ DiscreteUniform{5, …, 25}` (5 is the minimum compatible
  with the 20% cap);
- names drawn **uniformly without replacement from that arm's selection pool**;
- weights `~ Dirichlet(1)` over the k names, then water-filled to satisfy the
  20% cap;
- rebalance policy `~ Bernoulli(0.5)`: buy-and-hold, or reset to target weights
  every 5 trading days;
- `N = 2,600` teams per arm per window, matching the real field size.

**Families (selection pools, computed only from data strictly before T0):**

| id | family | public source | pool definition (frozen) |
|---|---|---|---|
| F1 | momentum + volume + clean price action | CUHK 2025 captain | top quintile of the equal-weighted average of three within-window ranks: 126d total return; 21d-over-252d median dollar-volume ratio (volume acceleration); trend quality = 63d return ÷ 63d realised daily vol |
| F2 | bet on volatility | RIT 2024 captain | top quintile of 126d realised daily volatility |
| F3 | quality momentum | Imperial 2025 | top tercile of 126d return **∩** ROE > 0 **∩** above-median ROE **∩** below-median (dlc+dltt)/ceq, among names with lagged Compustat coverage |
| F4 | concentrated sector bet | Drexel 2025 (biotech) | each team draws ONE Fama-French-12 industry at random, then k names within it; the biotech/pharma sub-arm (SIC 2833-2836, 8731) is reported separately |
| F5 | speculative underdogs | UConn 2021 | bottom quartile of market cap **∩** bottom quartile of price, within the eligible universe |

**Controls (these are the trial, not decoration):**

| id | control | definition |
|---|---|---|
| C1 | equal-weight whole universe | deterministic: EW all ~1,500 eligible names, one entry per window |
| C2 | large-cap benchmark | deterministic: EW top-100 by market cap; CRSP `vwretd` reported beside it |
| C3 | **random at matched volatility — per family** | for each family F: same k, same weight rule, same rebalance draw; names drawn uniformly from the universe conditional on reproducing **F's own realised distribution of constituent 126d-volatility percentile buckets** (5-percentile buckets, sampled from F's pooled empirical bucket distribution for that window). Selection information is destroyed; the volatility profile is preserved by construction. |
| C4 | random at market volatility | same k / weights / rebalance, names drawn uniformly from the whole eligible universe |

**Costs:** 10 bps one-way on traded value **decides**; 0 bps and 25 bps are
reported. Turnover comes from the initial build and any 5-day rebalances.

---

## 5. THE primary metric — one number

> **Δmedian(F) = mean over windows of [ median 5-week net return of family F's
> 2,600 teams − median 5-week net return of C3(F)'s 2,600 teams ]**, in
> percentage points per 5-week window, at 10 bps.

The **sampling unit is the window**, not the team. Teams inside one window share
a market factor and are not independent; treating 600,000 team-draws as n would
manufacture significance out of a common shock. n = 231.

**MDE (CANON §19):** `MDE_80 = 2.80 × SE`, with
`SE = max(SE_HAC(NW, lag 1), SE_IID)` computed from the 231 per-window Δ values
(the NIGHT-11 rule: MDE and t share a Newey-West SE, and MDE takes the max of
HAC and IID). Every reported number in the writeup prints its own MDE beside
it. **A difference below its MDE is NOT DETECTABLE and is never reported as a
kill or as a win.**

Everything else — the max over 2,600, P(arm produces the winner), p5, p95, the
worst case, skew, realised portfolio volatility, the sizing table — is
**reported, never deciding.**

---

## 6. Decision rule, frozen

| condition (all at 10 bps, on the primary) | verdict for that family |
|---|---|
| Δmedian ≥ its MDE **AND** same sign in ≥5/8 regime blocks **AND** same sign in both sample halves | `SELECTION_DETECTED` — direction check only; licenses a successor trial, nothing else |
| Δmedian ≥ its MDE but coverage or half-consistency fails | `UNRESOLVED_UNSTABLE` |
| \|Δmedian\| < MDE **AND** Δp95(F vs C3) ≥ the p95 difference's own MDE | `DISPERSION_ONLY` — the family fattens the right tail without moving the centre. This is a positive finding about the leaderboard, not a null. |
| \|Δmedian\| < MDE **AND** \|Δp95\| < its MDE | `UNRESOLVED` — the instrument cannot see it |
| Δmedian ≤ −MDE | `SELECTION_HARMFUL` |

**Trial-level verdict** = the set of five family verdicts. There is no
"the trial passed". A family verdict does not transfer to another family.

**Contamination clause.** If the delisting splice, the Compustat lag, or the
C3 volatility matcher fails its own assertion (§7), every affected arm is
**VOID and investigated**, not reported with a caveat. A vol-matcher that
silently fails to match makes C3 equal to C4 and would turn dispersion into
"selection" — this is the exact NIGHT-10/12 silent-defect shape and it gets an
explicit runtime check.

**No crash-event override applies** — the window tiling already contains every
drawdown in the sample and none of them can be dropped.

---

## 7. Runtime assertions that must pass or the arm is void

1. **Vol-match check:** for each family, the mean absolute difference between
   F's and C3(F)'s constituent-volatility bucket histograms must be ≤2
   percentage points per window; the realised portfolio-volatility ratio
   F : C3 is printed for every family and window.
2. **Delisting reach:** the count of window-positions terminated by a delisting
   return must be > 0 over the full sample. Zero means the splice never fired
   and the survivorship control is decorative (NIGHT-10 insider-collector
   defect class).
3. **No-lookahead:** every pool statistic uses data with date < T0 strictly.
   A perturbation proof runs on one named window — perturbing all returns
   after T0 must leave the selection pools bit-identical.
4. **Cap legality:** no simulated weight exceeds 0.2000001; no arm's weights
   sum above 1.0.
5. **C4 sanity:** C4's median 5-week return must sit within a few bps of C1's
   universe return in expectation; a large gap means the sampler is biased.
6. **Search denominator logged:** every arm × parameter combination executed,
   including failed and voided ones, is counted in the receipt.

---

## 8. Frozen parameters (not tunable mid-trial)

`window = 25 trading days` · `N teams = 2,600` · `k ~ U{5..25}` ·
`weights ~ Dirichlet(1) capped 20%` · `rebalance ∈ {none, 5d} p=0.5` ·
`pool quantiles: quintile (F1,F2), tercile (F3), quartile (F5)` ·
`lookbacks: 126d momentum & vol, 63d trend quality, 21d/252d volume ratio,
63d dollar-volume screen` · `costs 10 bps decides` ·
`vol buckets = 5 percentiles` · `Compustat lag 6 months` ·
`universe top 1,500 by dollar volume, price ≥ $5` ·
`seeds: np.random.default_rng(20260812 + window_index*1000 + arm_index)` —
never `np.random.seed`.

## 9. What this trial may NOT conclude

- **Not alpha evidence.** Simulated portfolios on historical data are a
  DIRECTION CHECK. Nothing here is a Sharpe claim, a money claim, or a skill
  claim, and no result licenses a change to any live or paper lane, any
  position size, any product default, or any buy/sell language.
- **Not a statement about any actual team.** We do not have the winners'
  holdings. A family verdict is a verdict about the *described strategy class*
  simulated in a US CRSP universe, not about CUHK, RIT, Imperial, Drexel or
  UConn.
- **Not the real tournament.** Ours is US-only, ~1,500 liquid names, 25 trading
  days, no intraday execution, no news reaction, no discretionary exits. The
  real event is global, >10,000 names, and its winners describe *active*
  entry/exit as the core of what they did. **This design can measure the
  selection and the sizing; it structurally cannot measure execution**, and
  the execution component is exactly what the CUHK captain claims mattered
  most. That is a known, stated, uncorrectable-tonight gap.
- **Not "it was all luck".** If every family lands `DISPERSION_ONLY`, the
  correct statement is that these families' *selection* component was below
  this instrument's resolution while their *dispersion* component was measured
  — not that skill was absent from an event we cannot observe.
- **No skill claims before 24 months of forward record**, per canon, and this
  trial produces zero forward record.

## 10. Result

Filled after the run, never edited. Receipts:
`data/factory/winner_genome_1_*.json` (untracked, as `/data/` is gitignored);
writeup `aegis-finance/docs/NIGHT14_WINNER_GENOME.md`;
runner `scripts/run_winner_genome_1.py`.
