# PREREG — TRIAL-N2-NEGATIVE-SELECTION-1

**Registered:** 2026-08-10 · **Family:** N (extension) · **Stage:** backtest
**Data grade:** `crsp`

## 1. The question

Across 179 candidates, this factory has only ever tested one thing: **picking the
best**. Every signal was used to rank names up and buy the top. Not one trial
asked the opposite question:

> **Is refusing the worst worth more than picking the best?**

The asymmetry has a plausible mechanism, which is why it is worth a night rather
than a shrug. Bessembinder (2018, `BESSEMBINDER-4PCT`) measured that 4.3% of
CRSP stocks account for all net wealth creation and 57.4% fail to beat T-bills
over their lifetime, so a long-only book's realised return is dominated by
avoiding the left tail. Accruals, net share issuance and distress are three of
the most replicated anomalies in the literature and are conventionally traded as
*avoidance* signals in practice, not as selection signals.

## 2. Design

Veto operates on the **eligible set at the annual rebalance, before selection**.
The book still holds 150 names — it simply draws deeper into the composite
ranking to replace what the veto removed. That is deliberate: it isolates
"refusing the worst" from "holding fewer names", which would otherwise be
confounded.

| arm | veto |
|---|---|
| **V0** | none — the banked book (**control**) |
| **V1** | bottom decile of `osap:Accruals` |
| **V2** | bottom decile of `osap:ShareIss1Y` (net share issuance) |
| **V3** | bottom decile of `osap:OScore` (Ohlson distress) |
| **V4** | union — vetoed by **any** of V1–V3 |
| **V5** | **PLACEBO** — a random veto of the same size each month, seeded |

The OSAP wide file is pre-signed (higher = higher predicted return), so the
bottom decile is the *unattractive* end in every case. Decile is fixed at 10% and
is not swept.

**V5 is not optional.** Any veto forces replacements and changes turnover, and a
book that holds different names for no reason at all will still post a different
return. Without a size- and turnover-matched random veto, an effect here cannot
be attributed to the anomalies rather than to the act of vetoing. The standing
rule is that every control-armed design carries a placebo gate.

## 3. Metrics and decision rule (frozen)

- **Primary:** paired monthly net excess vs V0, annualised, Newey-West(12).
- **Bar: ±1.5%/yr.** This is an increment to an existing book, not a standalone
  strategy, so the +3%/yr adoption bar is the wrong one. The bar is only
  meaningful if the design can see it — see the power condition below.
- **Placebo gate, read FIRST:** if V5 reaches |t| ≥ 2.0, the instrument is
  measuring the act of vetoing and every other arm is `PLACEBO_FAILED`.
- **Attribution:** an effect in V4 that is not present in any of V1–V3 is
  reported as unattributed and does not support a mechanism.
- **Turnover (CANON §15):** every arm's one-way annual turnover is reported. All
  trades occur on the scheduled annual rebalance and reconcile exactly, so the
  monthly panel is admissible — but any arm differing from V0 by more than
  **0.10** goes through G7 before its net number is quoted.
- **Power condition:** if the realised MDE exceeds the 1.5%/yr bar, the verdict
  is `POWER_FAILED` and the point estimate is not interpreted.

## 4. Registered predictions

1. **The placebo will be small but not zero** (|t| < 1.5). Vetoing 10% of a
   150-name book from a deep eligible set should barely move it.
2. **V3 (distress) is the most likely to show something**, because OScore is the
   most direct proxy for the left tail Bessembinder describes.
3. **No arm reaches +1.5%/yr at |t| ≥ 2.0.** The composite already tilts to
   profitability, which is correlated with all three veto signals, so the veto
   should mostly remove names the composite was not going to buy anyway.
4. **The overlap is the real finding.** I expect to report that the vetoed names
   were largely already outside the top 150 — in which case the honest answer is
   that this book *already* refuses the worst implicitly, and the question is
   answered by a diagnostic rather than by a return.

## 5. Ledger

Adds **5 branches** (V1–V5 against V0). Counted before any result is
interpreted.
