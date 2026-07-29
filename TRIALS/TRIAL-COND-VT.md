# TRIAL-COND-VT — conditional (extremes-only) volatility targeting on SPY

**Registered:** 2026-07-29 UTC — **BEFORE any return is computed.** No
conditional-VT backtest has ever been run in this program; `scripts/trial_cond_vt.py`
does not exist at the moment this doc is frozen and is written only after the
registry row is appended.
**Registry row:** `TRIALS/registry.jsonl` via `register_trial()`.
**Counts:** +1 candidate → **cumulative 159** (freeze base 158).
**Class:** de-risking overlay (allocation layer), explore-then-confirm, ONE run
per window, results final.

---

## 0. Standing ruling (recorded verbatim, Murat 2026-07-29)

> "Conditional volatility targeting is a DE-RISKING OVERLAY and falls under the
> freeze's S3 open door (exits/de-risking are first-class inside the same
> registry and the same cumulative deflation count) — not a new cross-sectional
> family, no exemption needed. Registration is mandatory; the 'admissible
> without pre-registration' suggestion from an external review is REFUSED
> (house canon: if it isn't pre-registered, it didn't happen). Approved by
> Murat 2026-07-29 (ruling delegated to the build session). Conditioning
> variable is BACKWARD-LOOKING REALIZED VOL, not VIX — matches the Bongaerts
> realized-vol conditioning, is trivially PIT-clean, and a VIX-conditioned
> variant would be a second hypothesis against the deflation budget (refused
> for now)."

Consequences taken here without further interpretation: one registration, one
cumulative increment (158 → 159), realized-vol conditioning only, no VIX arm.

## 1. Prior-check transcript (run 2026-07-29, before this doc)

`python -m scripts.prior_check "volatility targeting" "vol-managed" "vol target"
"de-risking overlay"` → **173 hits** across the ledger corpus. Every family-level
hit reconciled:

| Hit | Where | Reconciliation |
|---|---|---|
| "vol-managed momentum printed a false PASS" | `aegis-finance/NEGATIVE_RESULTS.md` §4 | That is the **survivorship** receipt: a *cross-sectional* vol-managed momentum book on a survivor-only yfinance universe. Same doc, same paragraph, states the exemption this trial relies on: *"Risk overlays (vol-management, ATR exits) are universe-independent and unaffected."* This trial is single-instrument SPY — no universe, no survivorship channel. |
| `vol-managed` (Moreira-Muir) as a **benchmark** in INSTR-VOC | `TRIALS/INSTR-VOC.md` | Used there as a comparison arm inside a complexity falsification on CRSP monthly, never registered as a claim. No overlap with this hypothesis. |
| "do-NOT list: vol-target the profitability book" | `AI_PANEL_2026-07-27F` | Refers to applying VT to the **gp-small cross-sectional book**. This trial does not touch any stock book. |
| "state-conditional / downside-vol TSMOM refinements DEFERRED post-freeze" | `AI_PANEL_2026-07-27F` row 9 / `STATUS.md:110` | That defers **refinements to the seeded TSMOM-XA lane** (no mid-trial respec, ever). This is a separate, self-contained overlay on SPY; it does not modify TSMOM-XA's frozen spec and does not touch its lane. |
| "Allocation Factory (~50 policies: cash, sector rotation, **vol targeting**, DD response) ADOPTED as the post-freeze Phase II framing; each policy = a pre-registered walled trial" | `AI_PANEL_2026-07-26E` | This trial **is** the first such walled policy trial, executed exactly as that adjudication requires. |
| S4 capital-flows mentions "mechanical vol-target/CTA flows" | `ROUND12_BINDINGS.md`, `FREEZE_2026-07-28.md` §5.1 | Different object: that is a *flow signal* derived from other people's VT programmes. Not claimed here, and this trial does **not** consume the S4 budget — it enters under **S3**. |
| INSTR-MACRO-BATCH4 §2 note: "per-asset 10%-vol sizing leaves portfolio vol at 6% — under-deployed vs portfolio-level vol targeting; a v2 sizing variant would be a NEW registration, not a retune" | `TRIALS/INSTR-MACRO-BATCH4.md` | Explicitly anticipated this as a *new registration*. This is it (and it is not a TSMOM sizing variant — it is standalone SPY). |

**No prior registration of any volatility-target rule exists.** Nothing in the
graveyard is re-entering under new clothing.

## 2. How this differs from the DEAD family (stated explicitly)

CONTINUOUS / unconditional volatility targeting — w ∝ target/σ every period,
scaled at all vol levels, typically levered — is on the project's **DEAD list**,
on four peer-reviewed refutations (`aegis-finance/docs/research/
ALLOCATION_EVIDENCE_2026-07-29.md` §A):

- **Liu, Tang & Zhou (2019)** *JPM* 46(1): after correcting look-ahead, max
  drawdown **68–93%**; *"One cannot easily beat the market via volatility-timing
  the market alone."*
- **Cederburg, O'Doherty, Wang & Yan (2020)** *JFE* 138(1): MKT Sharpe
  0.42→0.51 but **Jobson-Korkie p = 0.30**; real-time OOS **0.42 vs 0.46
  unmanaged**; lower CER in **72 of 103** strategies; 99th-pct implied weight
  **6.47×** (unreachable long-only).
- **DeMiguel, Martín-Utrera & Uppal (2024)** *JF*: MKT OOS net of costs
  0.519→0.325, **p = 0.979**.
- **Angelidis & Tessaromatis (2023)** *JFM* 65: profitability *"disappeared when
  changes in the trading and information environment in the U.S. in the early
  2000s made arbitrage less costly."*
- Moreira & Muir (2017) itself fits its scaling constant on the full sample
  (*"we choose c so that the managed portfolio has the same unconditional
  standard deviation as the buy-and-hold portfolio"*) — a look-ahead constant.

**Four concrete differences from that dead family, each a design constraint:**

1. **Extremes-only conditioning.** Exposure is adjusted **only** in the extreme
   high-volatility state (vol ≥ causal 80th-percentile breakpoint). In the other
   four quintiles the position is **unscaled at w = 1.0**. Continuous VT scales
   in every state; that is precisely the behaviour the four refutations kill.
2. **Leverage hard-capped at 1.0.** No arm of this trial can ever hold more than
   100% SPY. Cederburg's 6.47× implied weight is structurally unreachable here.
   The house also never shorts, so w ∈ [0, 1] by construction.
3. **No ex-post scaling constant.** The breakpoint is an **expanding-window
   causal quantile** of the instrument's own realized-vol history — nothing is
   fitted to the full sample. Moreira-Muir's `c` has no counterpart in this spec.
4. **Costs and a held-out window are binding, not reported.** Net-of-cost bars,
   a post-2010 confirm window containing 2020 and 2022, one shot.

**The surviving evidence this trial tests.** Bongaerts, Kang & van Dijk (2020)
*FAJ* 76(4), open access, 10 index-futures markets 1982–2019, costs 2–5 bps, no
ex-post scaling. Their own words on the dead family: conventional VT *"fails to
consistently improve performance… and can lead to markedly greater drawdowns"*;
it *"actually increases the maximum drawdown in the UK, Canadian, Australian,
and Hong Kong markets, by 4.0%–34.4%… increases expected shortfall in 8 out of
10 markets, including the US."* Their **conditional** variant, US market
(base SR 0.59, MDD −52.8%, ES −14.9%):

| | ΔSharpe | ΔMaxDD | ΔES | realized/target vol | turnover/yr |
|---|---|---|---|---|---|
| Conventional VT | +0.15 | −7.0% | +1.2% (worse) | 1.16 (overshoots) | 2.4× |
| **Conditional VT (US)** | **+0.16** | **−8.3%** | **−1.7%** | **0.97** | **1.6×** |
| 10-mkt avg conditional | +0.07 | −6.6% | −1.3% | 0.98 | 1.4× |

Those are the **only** numbers quoted from that paper here. The house does not
say "doubles Sharpe" — nobody credible reports that. Their own caveat, carried:
significant in **2 of 10 markets** only, and **no post-2010 subsample split**.

## 3. Hypothesis

De-risking SPY **only** in the extreme high-realized-volatility state — cutting
exposure toward the level that would hold the extreme state's risk at the
80th-percentile vol, never levering, never adjusting in normal or calm states —
improves the risk profile (materially shallower max drawdown) without paying for
it in risk-adjusted return, net of costs, out of sample.

**Mechanism, not pattern.** Volatility is strongly autocorrelated at daily/monthly
horizons while the equity risk premium is not proportionally higher in high-vol
states; the ratio of expected return to variance therefore deteriorates in the
extreme-vol tail. The reason it is not arbitraged away: this is not an arbitrage.
It is a *utility* trade — a leverage-constrained long-only investor trading a
small amount of expected return for a large reduction in path risk. Anyone with
access to leverage (Citadel) is on the other side of exactly nothing; there is
no mispricing to take. That framing is also why the honest prior on the *return*
side is neutral-to-negative.

**Honest prior: MEDIUM-LOW.** The single supporting paper is significant in 2 of
10 markets, and its US ΔSharpe of +0.16 is measured on futures with leverage
available and over a window (1982–2019) dominated by 1987, 2000–02 and 2008.
Our design is long-only, capped at 1.0, and half of the confirm window is
post-2019. The drawdown leg is the more plausible half of the claim.

## 4. Expected effect size

- **Sharpe:** flat to slightly better than SPY. The registered bar is
  deliberately a **non-inferiority** bar (≥ SPY − 0.05), not a superiority bar,
  because the claim is de-risking, not alpha.
- **Max drawdown:** ≥ 5 percentage points shallower than SPY. Bongaerts's US
  conditional row is −8.3%; 5pp is the bar.
- **Turnover:** order 1–2 round trips per year (Bongaerts US: 1.6×/yr).
- **Cost drag:** at 2 bps one-sided and ~1–2×/yr, of order 0.5–1 bps/yr — i.e.
  costs cannot be the executioner here, which is itself worth recording.

## 5. Expected decay / capacity

No decay mechanism through arbitrage (there is no arbitrage to crowd). The real
decay risk is **regime**: the rule is a levered bet on volatility clustering
plus a negative vol/return relation, and Angelidis-Tessaromatis's finding that
the phenomenon weakened post-2000 is the specific reason the confirm window is
post-2010. Capacity for a long-only SPY sleeve is effectively unbounded.

## 6. Kill condition (pre-committed, binding)

Explore window 2004-01-01 → 2018-12-31, ONE run. **If any of the three explore
bars fails: the confirm window DOES NOT OPEN, the result is recorded as a
NEGATIVE result** (`aegis-finance/NEGATIVE_RESULTS.md`), and the conditional-VT
family is **CLOSED**. No parameter tweaking, no reruns, no lookback switching,
no quintile→decile switching, no "try 70th percentile", no monthly→weekly
rebalance retry. A different specification is a **new registration** against the
deflation count, not a retune of this one.

## 7. Frozen run spec (verbatim — no tuning channel)

**Instrument.** SPY daily closes from `data/macro/etf_daily_close.parquet`
(coverage 2002-01-02 → 2026-07-24).

> **Data departure, disclosed and CORRECTED at registration.** The trial brief
> specified "price series, DIVIDENDS EXCLUDED". That is factually wrong about
> this file and the correction is recorded here rather than silently inherited:
> the parquet was written by `scripts/fetch_macro_analog_data.py` with
> `yf.download(..., auto_adjust=True)`, i.e. it is **dividend-adjusted — a
> total-return proxy**, exactly as `aegis_brain/macro/daily_harness.py` already
> discloses ("auto-adjusted, i.e. total-return proxy — disclosed assumption").
> Arithmetic check: SPY 74.09 (2002-01-02) → 738.79 (2026-07-24) = 9.97× ≈ 10.0%
> CAGR, which is a total-return, not a price-only, path. The departure is
> disclosed as such: it affects the strategy arm, the SPY control, the 60/40
> control and the descriptive arm **identically**, so it cannot flatter the
> treatment. `rf = 0` Sharpe convention (house standard) is retained and is the
> one genuinely conservative-in-the-wrong-direction choice here: with a
> total-return series and rf = 0, **all** arms' Sharpes are overstated in
> absolute level, while the strategy's cash sleeve earns 0 — i.e. the
> convention is biased **against** the treatment. No adjustment is made.

**Vol signal.** Trailing **63-trading-day** realized volatility of SPY daily
simple returns, annualized by √252. Computed on every trading day.

**Conditioning.** **Expanding-window** quantile breakpoints of that realized-vol
series, causal: the breakpoint used at month-end *t* is computed from vol
observations **≤ t only**. **Burn-in: 756 trading days** of realized-vol
observations before the first tradable signal; before that the weight is the
unscaled default w = 1.0 (identical to SPY, no trading).

**Rule (long-only, leverage capped at 1.0).** At each month-end *t*, with
`v_t` = current realized vol and `q80_t` = causal expanding 80th-percentile
breakpoint:

```
if v_t >= q80_t:   w = min(1.0, q80_t / v_t)
else:              w = 1.0
```

Cash remainder `(1 − w)` earns **0**.

**Rebalance.** Month-end only. The weight set at month-end *t* applies to the
**following month's** returns (signal at close *t* → exposure over
*t+1 … next month-end*). No intra-month adjustment.

**Costs.** One-sided **2 bps** on traded value (base, decides the bars);
**10 bps** stress reported alongside, never deciding.

**Windows.** Explore **2004-01-01 → 2018-12-31**. Confirm **2019-01-01 →
2024-12-31**, HELD OUT, opened by one shot only on an explore pass (satisfies
the post-2010 requirement Bongaerts lacks; contains the 2020 and 2022 stress
events). **Data after 2024-12-31 is NOT touched** — forward reserve, even though
the parquet extends to 2026-07-24.

**Causality assertion (executable, not asserted in prose).** The runner must
demonstrate for at least one named month-end date that perturbing all data
strictly after *t* leaves the weight at *t* bit-identical. A failure of this
assertion aborts the run.

## 8. Bars

**Explore pass bars — ALL three must hold** (else negative result, stop):

| Bar | Threshold |
|---|---|
| (a) Net Sharpe | ≥ SPY buy-and-hold net Sharpe **− 0.05** |
| (b) Max drawdown | shallower than SPY's by **≥ 5 percentage points** |
| (c) Avg one-sided turnover | **≤ 50%/month** (expectation: order 1–2×/yr) |

**Confirm bars: identical**, on 2019-01-01 → 2024-12-31.

- **PASS (both windows)** → the trial becomes a **PROPOSAL** for an attended
  forward paper lane. Murat seeds it (`seed-a-lane`, env-gated). **Nothing arms
  automatically. Sessions never set seed flags.**
- **FAIL (either window)** → `NEGATIVE_RESULTS.md`, family CLOSED.

## 9. Controls (binding, R5)

- **SPY buy-and-hold** — the economic yardstick, and the arm the bars are
  measured against.
- **Static 60/40 SPY/TLT, monthly-rebalanced.** TLT coverage in the parquet
  begins **2002-07-30**, i.e. fully available from 2004-01-01 — verified, no
  truncation or disclosure needed.
- **Descriptive reference arm — UNCONDITIONAL vol targeting** (reported, NEVER
  deciding): `w = min(1.0, causal-median-vol / current vol)` every month-end,
  same burn-in, same costs, same cap. Expected to fail per the dead list; it is
  present as the **contrast exhibit** that makes the conditional/continuous
  distinction empirical rather than rhetorical in our own data.

## 10. Reported-not-deciding

CAGR, annualized vol, Calmar, worst rolling 12-month return, average one-sided
turnover, cost drag (2 bps vs 10 bps), **block bootstrap (21-trading-day
circular) 90% CI on the Sharpe difference vs SPY**, per-window equity curves,
% of months in the de-risked state, and **2020 and 2022 episode behaviour
specifically** (calendar-year return, in-episode drawdown, weight path).

## 11. Paper framing

To our knowledge — per the 2026-07-29 evidence review — this is the **first
long-only, no-leverage conditional volatility target on SPY evaluated
out-of-sample, net of costs, with a post-2010 held-out window.** Bongaerts et al.
use 10 futures markets 1982–2019 with leverage available and **no recency
split**; the four refutations target the continuous variant. **The result is
publishable in either direction:** a pass extends the one surviving VT result to
the constrained long-only case and to the post-2010 regime; a failure is the
first held-out, post-2010 refutation of the *conditional* variant, which is
currently an open question in the literature.

---

## 12. Result (filled AFTER the runs, 2026-07-29 — never edited)

Runner `scripts/trial_cond_vt.py` (written after this doc and the registry row
were frozen). Artifacts `data/factory/trial_cond_vt_{explore,confirm}.json`.
Full tables: `docs/TRIAL_COND_VT_RESULTS_2026-07-29.md`.

**Causality assertion PASS on both runs** — weight decided at 2010-06-30 is
0.903792 and is bit-identical after every post-*t* close is multiplied by
U(0.3, 3.0).

### EXPLORE 2004-01-01..2018-12-31 (3,775 d, 2 bps) — **ALL 3 BARS PASS**

| | CAGR | vol | Sharpe | maxDD | turnover/mo |
|---|---|---|---|---|---|
| **COND_VT** | 8.57% | 15.28% | **0.615** | **−40.19%** | 3.4% |
| SPY B&H | 7.69% | 18.27% | 0.497 | −55.19% | — |
| 60/40 | 7.96% | 10.10% | 0.809 | −29.92% | — |
| UNCOND_VT (desc) | 8.29% | 12.80% | 0.687 | −27.11% | 8.7% |

(a) 0.615 ≥ 0.447 ✓ · (b) −40.19% ≤ −50.19% ✓ (+15.0pp) · (c) 3.4% ≤ 50% ✓.
ΔSharpe vs SPY +0.118, 90% CI [+0.005, +0.226]. Bars unchanged at 10 bps.
De-risked in 26 of 180 months (14.4%). **2008: −28.69% vs SPY −36.80%,
in-year DD −33.41% vs −47.12%** — and that single crisis is essentially the
whole explore result. Confirm window earned and opened same day.

### CONFIRM 2019-01-01..2024-12-31 (1,510 d, 2 bps) — **REJECT (2 of 3 bars missed)**

| | CAGR | vol | Sharpe | maxDD | turnover/mo |
|---|---|---|---|---|---|
| **COND_VT** | 14.55% | 18.26% | **0.836** | **−33.72%** | 7.0% |
| SPY B&H | 17.12% | 19.83% | 0.897 | −33.72% | — |
| 60/40 | 9.69% | 12.67% | 0.794 | −27.24% | — |
| UNCOND_VT (desc) | 12.51% | 14.80% | 0.871 | −29.40% | 13.8% |

(a) 0.836 ≥ 0.847 ✗ (−0.011) · (b) −33.72% ≤ −28.72% ✗ (**0.00pp — identical to
SPY, same trough date 2020-03-23**) · (c) 7.0% ≤ 50% ✓.
ΔSharpe vs SPY −0.061, 90% CI [−0.164, +0.055] — indistinguishable from doing
nothing, at a cost of 2.6pp of CAGR.

**2020: +3.28% vs SPY +18.33%, in-year DD −33.72% vs −33.72%.** Cause, from the
frozen weight path: at 2020-02-28 the trailing 63-td vol was **0.162 against a
causal q80 breakpoint of 0.2018**, so the rule entered March at w = 1.00 with
SPY already ~12% off its high; it then cut to 0.373 / 0.345 / 0.350 for
Mar/Apr/May — the rebound. A 63-day backward window cannot resolve a 23-day
crash and a month-end clock cannot act inside one.
**2022: −15.92% vs SPY −18.18%, DD −22.75% vs −24.50%** — the mechanism worked
as designed (gradual de-risk 1.00→0.73 by June) and bought +2.3pp return /
1.8pp drawdown: correctly signed, an order of magnitude short of the bar.

**Contrast exhibit came out backwards, reported as such:** the descriptive
UNCONDITIONAL arm beat the conditional arm on Sharpe AND max drawdown in BOTH
windows. It does not revive the dead family (it also fails confirm bar (b) at
−29.40% vs −33.72% = 4.3pp, short of 5pp, and four published refutations are
not overturned by one instrument) — but the Bongaerts extremes-only refinement,
which was the hypothesis, bought nothing on SPY.

### VERDICT

**REJECT. Conditional-VT family CLOSED** per §6: no re-tuning, no VIX variant,
no lookback/clock switch; any successor is a NEW registration carrying this
receipt. **No paper lane — the attended seed branch is not reached, nothing
arms.** Costs were never the executioner (0.8–1.7 bp/yr drag; bars unchanged at
10 bps). Mirrored to `aegis-finance/NEGATIVE_RESULTS.md` §21. Cumulative
candidates **159**.
