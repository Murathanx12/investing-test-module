# PREREG — TRIAL-PF7-EXIT-SWEEP-1

**Registered:** 2026-08-10, before any exit-arm compute.
**Family:** PF-7 · **Stage:** backtest (historical panel, holdout untouched)
**Brief:** `docs/NIGHT7_BRIEF_2026-08-10.md` §3 T2 · **Citation gate:** `runs/NIGHT7/VERIFIED_CITATIONS.md`

---

## 1. Why this trial exists

The closed search ran ~179 candidates on **what to buy** and **zero** on **when to
sell**. Two verified results say that is the wrong allocation of attention:

- **Akepanidtaworn, Di Mascio, Imas & Schmidt (JF 78(6) 2023)** — 783 institutional
  portfolios, avg $573M, 4.4M trades, 16 years: clear skill in *buying*; *selling*
  underperforms **even a random-selling counterfactual**. Mechanism: asymmetric
  attention. (Verified; the "90–120bps/day earnings-season" magnitude is **not**
  verified and is **not** used here — only the direction.)
- **Bessembinder (JFE 129(3) 2018)** — **4.3%** of 25,967 CRSP stocks account for
  all net wealth creation over T-bills; only 42.6% of stocks beat T-bills over their
  lifetime. Wealth lives in a thin right tail, so any rule that systematically
  truncates winners forfeits the prize.

Murat's own record (MRVL 40→80, MU 100→200, NVDA 20→100) is the same pattern.

## 2. Hypothesis

**H0 (null):** conditional on a fixed entry rule, the choice of exit rule does not
change net excess CAGR — all arms are statistically indistinguishable from the
annual-rebalance baseline on paired differences.

**H1:** at least one exit arm differs from the baseline at paired NW |t| ≥ 2.0.

## 3. Design — entry held fixed, exits swept

**Fixed across every arm** (the banked book, `PF-PROF-COMPOSITE-150`, spec hash
`a1265dc617fb`, moved to the annual clock per NIGHT-4/6):

| element | value |
|---|---|
| signals | `osap:GP` + `osap:OperProfRD` + `osap:CBOperProf`, equal weight |
| segment | small (dollar-volume rank 1000–3000) |
| top_n | 150, equal-weighted, `hold_band_mult` 3.0 |
| window | 1963-07-31 … 2022-12-31 (holdout 2023-01+ **not read**) |
| costs | **era-appropriate** (`era_cost_frame`: KO half-spread + mechanical tick floor) — never flat25 |
| benchmark | CRSP VW total return (Ken French `mktrf+rf`, pinned) |
| invested | **always fully invested at 150 names** — every interim sale is replaced immediately by the best-scoring eligible non-held name |

The full-investment rule is deliberate: it removes cash drag as a confound so the
comparison is purely *which names are held*, not *how much is in the market*.
Cash-drag versions of a stop are a different (worse) question.

**Arms (exits only):**

| arm | rule |
|---|---|
| **A0 BASELINE** | annual (12m) rank rebalance with the incumbency band. Nothing else. This is the shippable config. |
| **A1 TRAILING-STOP-20** | A0, plus: each month, any held name whose cumulative return has fallen ≥20% from its since-entry peak is sold and replaced. |
| **A2 MOMENTUM-HOLD** | A0, but at the annual rebalance an incumbent with positive 12-1 momentum is **force-retained** regardless of rank. ("Let winners run.") |
| **A3 FUNDAMENTAL-BREAK** | Never sell on rank. A name is sold only when the signal that selected it **breaks** — its composite percentile falls below the universe median (0.50) — checked monthly, replaced on sale. Annual clock refills empty slots only. |
| **A4 EARNINGS-ANCHORED** | No annual rank rebalance. Held names are reviewed only in **Feb/May/Aug/Nov**; at review, a name outside the incumbency band is sold and replaced. |

**Disclosed proxy (A4).** The CRSP spine carries no per-firm report dates, so
Feb/May/Aug/Nov is a **calendar proxy** for earnings season (correct for
December-fiscal-year firms, the majority, wrong for the rest). A4 therefore tests
*scheduled staggered review* and only approximates the attention mechanism. It is
also the only arm whose **review frequency** differs from A0, so A4 vs A0
confounds anchoring with frequency; turnover is reported for every arm so the
reader can see it.

## 4. Primary metric and decision rule (frozen)

- **Primary:** paired monthly difference `arm_net − A0_net`, annualised, with a
  **Newey-West(12) t** on the paired difference. Pairing is what buys the power:
  entry noise is common to all arms and cancels.
- **Decision:** an arm is **CONFIRMED** different only at paired **NW |t| ≥ 2.0**
  *and* a same-signed point estimate ≥ +1.0%/yr. Below that it is **UNRESOLVED**
  (never "no effect") and the **MDE is reported next to it**.
- **Turnover gate (NIGHT-6 rule):** any arm whose 1-way annual turnover differs
  from A0 by more than **0.10** may not have its net number quoted as final until
  it has been through **G7** (the daily simulator). The monthly panel understates
  churn cost by ~2.7×, so a turnover-increasing arm's monthly-panel net is an
  **upper bound**, and a turnover-*decreasing* arm's is a **lower bound**.
- **MDE is printed before the verdict is read.**

## 5. Registered predictions (worker session, written before compute)

Scored in STATUS. Written independently of the brain's §5 predictions.

1. **No arm reaches paired |t| ≥ 2.0.** The frontier nulls of NIGHT-5 (six clocks,
   ρ 0.958–0.993, no significant pairwise difference) say arms sharing 150 names
   and one entry rule are too correlated to separate on 59 years.
2. **A1 (trailing stop) is the most negative arm in both gross and net**, and is
   negative gross-of-costs — i.e. it loses by selling the right-tail names, not
   merely by trading. This is the Bessembinder mechanism and it is the prediction
   most likely to be falsified cleanly.
3. **A2 (momentum-hold) has the lowest turnover of all five arms** and a net point
   estimate above A0, driven mostly by cost saving rather than selection.
4. **A3 (fundamental-break) drifts furthest from the small segment** — its mean
   held-name dollar-volume rank rises the most, because unsold winners grow out of
   the segment. Whatever its return, it is the least faithful to the product.
5. **Spread between the best and worst arm exceeds 1.5%/yr** — exits matter
   *mechanically* even if no single arm is statistically separable. If this fails
   too, the honest headline is "the exit layer is not where our money is either."

## 6. What would make this trial worthless (declared in advance)

- If the baseline A0 reproduced here does not match the banked annual-clock
  numbers from NIGHT-6's G7 clock compare, the harness is mis-wired and **every
  arm is void**. This reconciliation runs first and is reported.
- If any arm's book size drifts off 150 names, the full-investment invariant
  broke and that arm is void.
- Verdicts use taxonomy v2 (`aegis_brain/verdicts.py`). UNRESOLVED is expected and
  is a valid ending.

## 7. Constraint-ledger accounting

Branches added by this trial: **5 arms + 1 reconciliation = 6**. These are added to
the programme denominator before any t is interpreted, per the standing amendment.
