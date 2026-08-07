# TRIAL-REPLAY-BOOK-1 — VERDICT: FAIL (frozen rule, 2026-08-08)

Prereg: `TRIALS/PREREG_REPLAY_BOOK_1.md` (commit 8340298, before
construction). One shot, spent. Record: `runs/REPLAY-2/trial_replay_book_1.json`
(tracked copy in `docs/replay_record/`).

## Result

| window | t_ic | t_net flat25 | t_net KO-half | t_net stress50 | bps/mo | long-leg share |
|---|---|---|---|---|---|---|
| explore | 7.65 | 1.45 | 1.71 | 1.06 | +25.9 | 0.19 |
| confirm (PRIMARY) | 6.10 | **1.07** | 1.18 | 0.91 | +42.7 | **0.18** |

Placebo books (10 information-free persistent signals each, identical
construction), confirm net t: **+1.32**, +0.59, +0.78, −1.28, +0.02.
Placebo confirm ICs: −0.94 to +2.02.

## Frozen-rule adjudication

- Confirm net t 1.07 < 1.5 under flat-25 → not PASS, not WEAK-PASS.
- **Placebo 1 (1.32) beat the real book (1.07) on the money leg** — the
  book's net return is not distinguishable from what book mechanics on
  information-free signals produce in this window.
- Long-leg share 0.18 < 0.50 — the §28 short-leg pattern, now measured on
  the ADOPTED set: the composite's 290 bps/mo D10−D1 spread is ~82%
  short-leg, and the long-only book keeps ~52 bps of it before costs.

**FAIL.** Per the frozen rule: the 10 adoptions KEEP their ADOPT ledger
states — the information result stands untouched (book confirm IC t 6.10
vs placebo ICs ≤ 2.02 is a chasm; the IC was never the question here) —
but the equal-weight long-only book is NOT tradable at measured costs, no
lane is seeded, and the forward path is closed until a different
implementation layer is separately registered.

## Prediction scoring (house rule: score your own priors)

Declared prior: confirm net t 1.3-2.2 flat-25, P(PASS) ≈ 0.4. Realized
1.07 — **below my band; the prior was optimistic.** The miss has a
diagnosis the prereg itself anticipated: "the money lives in the 6
generic-family signals" was listed as the first post-FAIL diagnostic, and
the σ-family members (4 of 10 book slots) contributed IC and turnover but
~zero money (their individual confirm nets: +0.3, −4.5, +17.2, +38.8 bps
— mixed, with the two daily arms at ≈ 0).

## What is licensed next (registrations, not retries)

1. **A 6-generic-signal book** (cash_prof, conc_low, fscore_lite,
   oper_prof, roe, dtc_high) — NEW registration, declared in the prereg as
   the first diagnostic. Its honest prior must confront: those six's
   individual confirm nets averaged ≈ +24 bps/mo, t ≈ 0.9 — a 6-book may
   land near t 1.2-1.5, still marginal.
2. **The exclusion route** (TRIAL-EXT-EXCLUDE-1, already registered): 82%
   of the spread is short-leg — the long-only-legal use of that
   information is avoiding the bottom decile, not holding the top. The
   replay's own leg decomposition is now the strongest motivation on file.
3. **Cost-layer work**: KO-half beat flat-25 in both windows (turnover
   netting in the composite is real: 0.127 one-way vs 0.38 for the daily
   arms alone) — implementation engineering has headroom, but it must be
   registered as such, not tuned post-hoc.

## The through-line for the paper

One night, one pipeline: gates measured → replay under calibrated error
control → 10 information adoptions at held-out IC t 4.4-7.7 → money-leg
book FAILS its own placebo gate with long-leg share 0.18. The system now
distinguishes, on receipts, between *knowing something about small-cap
returns* and *being able to monetize it long-only after costs* — which is
exactly the distinction most published anomalies blur.
