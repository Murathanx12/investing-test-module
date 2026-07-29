# TRIAL-COND-VT — results (2026-07-29)

Pre-registration: `TRIALS/TRIAL-COND-VT.md`, registry row
`TRIAL-COND-VT` @ `2026-07-29T06:30:48Z` — **both written before
`scripts/trial_cond_vt.py` existed.** Runner: `scripts/trial_cond_vt.py`
(deterministic; bootstrap seed 20260729). Artifacts:
`data/factory/trial_cond_vt_explore.json`, `data/factory/trial_cond_vt_confirm.json`.

**VERDICT: explore PASS (3/3 bars) → confirm REJECT (2 of 3 bars missed).
Conditional volatility targeting on SPY is CLOSED. Cumulative candidates 159.**

---

## 0. Spec actually executed (unchanged from registration)

SPY daily closes from `data/macro/etf_daily_close.parquet` (yfinance
`auto_adjust=True` → **total-return proxy**, correction disclosed at
registration §7; identical for every arm). Trailing 63-td realized vol,
√252-annualized. Expanding-window causal 80th-percentile breakpoint, 756-td
burn-in. Month-end rule, long-only, cap 1.0:
`w = min(1, q80_t / v_t) if v_t ≥ q80_t else 1.0`; cash earns 0. Weight decided
at month-end *t* applies to the **following** month. Costs 2 bps one-sided
(deciding) / 10 bps (stress, reported). rf = 0.

**Causality assertion (executed, both runs):** at probe date 2010-06-30 the
decided weight is 0.903792; multiplying every SPY close **strictly after**
2010-06-30 by U(0.3, 3.0) leaves it bit-identical at 0.903792. A mismatch
aborts the run. No look-ahead channel exists.

**Burn-in behaviour (disclosed):** vol observations begin ≈2002-04; 756 of them
accumulate by ≈2005-04, so the explore window's first ~15 months hold w = 1.0
and are byte-identical to SPY. First de-risked month in explore: **2007-08-31**.

---

## 1. EXPLORE — 2004-01-01 → 2018-12-31 (3,775 trading days), 2 bps

| arm | CAGR | ann vol | Sharpe | maxDD | Calmar | worst roll-12m | turnover/mo | turnover/yr | cost drag |
|---|---|---|---|---|---|---|---|---|---|
| **COND_VT** | **8.57%** | 15.28% | **0.615** | **−40.19%** | 0.21 | −36.79% | 3.4% | 0.41× | 0.8 bp/yr |
| SPY B&H (control) | 7.69% | 18.27% | 0.497 | −55.19% | 0.14 | −47.35% | 0.0% | — | 0 |
| 60/40 SPY/TLT (control) | 7.96% | 10.10% | 0.809 | −29.92% | 0.27 | −24.72% | 0.0%¹ | — | 0 |
| UNCOND_VT (descriptive) | 8.29% | 12.80% | 0.687 | −27.11% | 0.31 | −23.95% | 8.7% | 1.04× | 2.1 bp/yr |

¹ 60/40 drift-rebalance turnover is small enough to round to 0.0% at monthly
resolution on these two assets; it is not charged differently from any other arm.

### Bars (all three required)

| Bar | Value | Threshold | Verdict |
|---|---|---|---|
| (a) net Sharpe ≥ SPY − 0.05 | **0.615** | ≥ 0.447 | **PASS** (+0.168) |
| (b) maxDD shallower than SPY by ≥ 5pp | **−40.19%** | ≤ −50.19% | **PASS** (+15.0pp) |
| (c) avg one-sided turnover ≤ 50%/mo | **3.4%/mo** | ≤ 50% | **PASS** (0.41×/yr) |

**ALL_PASS = True → the confirm window was earned and opened.**

### 10 bps stress (reported, never deciding)
COND_VT Sharpe 0.612, maxDD −40.33%, CAGR 8.53% — bars still pass. Costs are
irrelevant at this turnover (4.1 bp/yr drag at 10 bps). Whatever kills this
strategy, it is not transaction costs.

### Block bootstrap (21-td circular, 2,000 draws), 90% CI on ΔSharpe vs SPY
| arm | point | 90% CI | P(Δ<0) |
|---|---|---|---|
| COND_VT | **+0.118** | [+0.005, +0.226] | 0.04 |
| 60/40 | +0.312 | [+0.095, +0.531] | 0.01 |
| UNCOND_VT (desc) | +0.190 | [+0.017, +0.358] | 0.03 |

### Exposure
180 month-ends; **26 de-risked (14.4%)**, min monthly weight 0.295, mean 0.961.
The rule does what "extremes-only" says: it is fully invested 85.6% of months.

### 2008 episode (explore-window crisis)
| arm | 2008 return | in-year maxDD | min weight | % days de-risked |
|---|---|---|---|---|
| COND_VT | −28.69% | −33.41% | 0.29 | 58% |
| SPY B&H | −36.80% | −47.12% | 1.00 | 0% |
| UNCOND_VT (desc) | −17.94% | −21.37% | 0.18 | 100% |

**This is the whole explore result.** 2008 is a slow-burn crisis: vol crossed
the causal 80th percentile in 2007-08 and stayed there, so a month-end
63-day-vol rule had time to react. Explore's 15pp drawdown improvement is
overwhelmingly this one event — the same single-crisis dependence that
INSTR-REGIME-JM carried into its own confirm rejection.

---

## 2. CONFIRM — 2019-01-01 → 2024-12-31 (1,510 trading days), 2 bps
### ONE SHOT. Data after 2024-12-31 never loaded (forward reserve).

| arm | CAGR | ann vol | Sharpe | maxDD | Calmar | worst roll-12m | turnover/mo | turnover/yr | cost drag |
|---|---|---|---|---|---|---|---|---|---|
| **COND_VT** | **14.55%** | 18.26% | **0.836** | **−33.72%** | 0.43 | −18.55% | 7.0% | 0.85× | 1.7 bp/yr |
| SPY B&H (control) | 17.12% | 19.83% | 0.897 | −33.72% | 0.51 | −19.73% | 0.0% | — | 0 |
| 60/40 SPY/TLT (control) | 9.69% | 12.67% | 0.794 | −27.24% | 0.36 | −25.31% | 0.0% | — | 0 |
| UNCOND_VT (descriptive) | 12.51% | 14.80% | 0.871 | −29.40% | 0.43 | −14.94% | 13.8% | 1.65× | 3.3 bp/yr |

### Bars (identical to explore)

| Bar | Value | Threshold | Verdict |
|---|---|---|---|
| (a) net Sharpe ≥ SPY − 0.05 | **0.836** | ≥ 0.847 | **FAIL** (−0.011) |
| (b) maxDD shallower than SPY by ≥ 5pp | **−33.72%** | ≤ −28.72% | **FAIL** (0.00pp — *identical to SPY*) |
| (c) avg one-sided turnover ≤ 50%/mo | 7.0%/mo | ≤ 50% | PASS |

**ALL_PASS = False → REJECT.** Bar (a) misses by 0.011 of Sharpe, which on its
own would be a hairline. Bar (b) does not miss narrowly: the drawdown benefit,
the entire point of a de-risking overlay, is **exactly zero**.

### Block bootstrap, 90% CI on ΔSharpe vs SPY
| arm | point | 90% CI | P(Δ<0) |
|---|---|---|---|
| COND_VT | **−0.061** | [−0.164, +0.055] | 0.78 |
| 60/40 | −0.103 | [−0.510, +0.239] | 0.69 |
| UNCOND_VT (desc) | −0.026 | [−0.207, +0.184] | 0.56 |

The CI straddles zero: out of sample this overlay is **statistically
indistinguishable from doing nothing** — while costing 2.6pp of CAGR. That is
the honest reading of the risk-adjusted leg; the drawdown leg has no such
ambiguity (it delivered nothing).

### Exposure
72 month-ends; **19 de-risked (26.4%)**, min monthly weight 0.345, mean 0.944.

---

## 3. Why it failed: the signal was late in 2020 and small in 2022

### 2020 — the drawdown was taken in full, then the rebound was missed

| arm | 2020 return | in-year maxDD | min weight | % days de-risked |
|---|---|---|---|---|
| **COND_VT** | **+3.28%** | **−33.72%** | 0.34 | 51% |
| SPY B&H | **+18.33%** | −33.72% | 1.00 | 0% |
| UNCOND_VT (desc) | −2.59% | −29.40% | 0.22 | 84% |

The decided-weight path settles it:

| month-end | 63-td vol | causal q80 | weight applied to next month |
|---|---|---|---|
| 2019-12-31 | 0.089 | ~0.202 | 1.00 |
| 2020-01-31 | 0.088 | 0.2022 | 1.00 |
| **2020-02-28** | **0.162** | **0.2018** | **1.00** ← the March crash is taken at full exposure |
| 2020-03-31 | 0.544 | — | 0.373 |
| 2020-04-30 | 0.592 | — | 0.345 ← the rebound is missed |
| 2020-05-29 | 0.588 | — | 0.350 |
| 2020-06-30 | 0.312 | — | 0.662 |
| 2020-07-31 | 0.214 | — | 0.970 |
| 2020-08-31 | 0.190 | — | 1.00 |

On 2020-02-28 — after SPY had already fallen ~12% from its high — trailing
63-day realized vol was still **0.162, below the 0.2018 breakpoint**, because
60 of those 63 days were the calmest market in years. The rule stayed fully
invested through the fastest crash in modern US equity history, then cut to
0.35 for exactly the two months of the sharpest rebound. **Both drawdown dates
are 2020-03-23 and both drawdowns are −33.72%: to four decimal places the
overlay did nothing on the way down and cost 15pp of return on the way up.**

This is a resolution failure, not a parameter failure. A 63-day backward
window cannot resolve a 23-day crash, and a month-end decision clock cannot
act inside one. No lookback or threshold setting fixes that — and per the
frozen kill clause, none was tried.

### 2022 — the mechanism worked; the payoff was small

| arm | 2022 return | in-year maxDD | min weight | % days de-risked |
|---|---|---|---|---|
| COND_VT | −15.92% | −22.75% | 0.73 | 75% |
| SPY B&H | −18.18% | −24.50% | 1.00 | 0% |
| UNCOND_VT (desc) | −11.83% | −16.67% | 0.46 | 100% |

The grind-down regime is the rule's home turf and it behaved exactly as
designed — a gradual de-risk from 1.00 (Feb) → 0.958 → 0.867 → 0.775 → 0.730
(Jun), recovering to 0.85 by year-end. It bought **+2.3pp of return and 1.8pp
of drawdown**. Real, correctly signed, and an order of magnitude too small to
carry the 5pp drawdown bar, because 2022's realized vol (0.21–0.28) barely
exceeds a breakpoint that 20 years of history has pushed to ~0.20.

**The structural point:** an expanding-window quantile of realized vol is a
*slow* threshold. It cannot fire before a fast crash and it barely fires during
a slow one. The two behaviours are the same defect seen from two sides.

---

## 4. The contrast exhibit — unconditional VT (descriptive, never deciding)

The arm that was registered as expected-to-fail per the dead list:

| window | arm | Sharpe | maxDD | CAGR | turnover/yr |
|---|---|---|---|---|---|
| explore | COND_VT | 0.615 | −40.19% | 8.57% | 0.41× |
| explore | **UNCOND_VT** | **0.687** | **−27.11%** | 8.29% | 1.04× |
| confirm | COND_VT | 0.836 | −33.72% | 14.55% | 0.85× |
| confirm | **UNCOND_VT** | **0.871** | **−29.40%** | 12.51% | 1.65× |

**The contrast exhibit came out backwards, and it is reported that way.** In
our data, over both windows, the *unconditional* median-vol arm — the one the
literature declares dead — dominated the *conditional* arm on both Sharpe and
max drawdown, at ~2× the turnover but still trivial cost. It would have passed
explore bar (b) with far more room (−27.1% vs SPY −55.2%) and it would still
have **failed** confirm bar (b) (−29.4% vs SPY −33.7% = 4.3pp, short of 5pp)
and confirm bar (a) is a 0.87 vs 0.90 miss inside tolerance — i.e. it fails the
same window on the same drawdown leg, for the same 2020 reason.

Two consequences, both binding:

1. This does **not** revive unconditional VT. It is a descriptive arm, it was
   never registered as a claim, it also fails the confirm drawdown bar, and the
   four published refutations (Liu-Tang-Zhou; Cederburg et al. Jobson-Korkie
   **p = 0.30**; DeMiguel et al. OOS-net **p = 0.979**; Angelidis-Tessaromatis)
   are not overturned by one instrument on one 21-year sample. **The dead list
   stands.**
2. It does mean the *specific* Bongaerts refinement — "adjust only in the
   extreme quintile" — bought us nothing relative to the plainer rule on SPY.
   The conditioning was the hypothesis, and the conditioning is what
   underperformed.

---

## 5. Verdict and disposition

**REJECT at confirm. The conditional-VT family is CLOSED** per the frozen kill
clause (§6 of the registration): no re-tuning, no VIX variant, no lookback
switch, no intra-month clock. Any successor is a **new registration against the
deflation count**, carrying this receipt as its prior — and would have to
address the resolution failure directly (an intra-month trigger with a faster
vol estimator is a different hypothesis, not a parameter of this one).

- **No paper lane.** The PASS branch (attended `seed-a-lane`, Murat's flag) is
  not reached. Nothing arms.
- Cumulative candidate count **159** (freeze base 158, +1 for this trial).
  Registered under freeze door **S3** (de-risking overlay), not S4.
- Mirrored to `aegis-finance/NEGATIVE_RESULTS.md` §21.

## 6. Publishable content (either direction, as registered)

The registered framing holds: this is the first long-only, no-leverage
conditional volatility target on SPY evaluated out-of-sample, net of costs,
with a post-2010 held-out window. **The result is the negative one, and it is
the more useful of the two:**

1. **A held-out, post-2010 refutation of the conditional variant** — the
   subsample split Bongaerts et al. never performed. Their US result
   (ΔSharpe +0.16, ΔMaxDD −8.3%, turnover 1.6×/yr, significant in **2 of 10**
   markets) does not survive translation to a long-only, capped, post-2010 SPY
   implementation.
2. **A named mechanism for the failure, not a shrug:** trailing-63d realized
   vol crossed with an expanding-window quantile is structurally blind to a
   crash faster than its own window (2020-02-28 vol 0.162 vs breakpoint 0.2018,
   with SPY already 12% off its high) and structurally weak in a slow one
   (2022: +2.3pp return, 1.8pp drawdown). Both windows of the same defect.
3. **The wall did its job for the third time on an allocation instrument**
   (after INSTR-REGIME-JM and INSTR-REGIME-JM2): an explore pass carried almost
   entirely by 2008 collapsed on 2020 + 2022. Explore ΔmaxDD +15.0pp → confirm
   ΔmaxDD **0.00pp**.
4. **Costs were never the executioner** (0.8–1.7 bp/yr drag at 2 bps; bars
   unchanged at 10 bps) — consistent with the freeze's finding that our
   rejections are informational, not cost-driven.
