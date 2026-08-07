# PRE-REGISTRATION — TRIAL-REPLAY-BOOK-1 (2026-08-08, pre-dawn)

**Written BEFORE the book is constructed or scanned.** Registered under
CANON §6. This is the money-leg adjudication the replay's 10 adoptions
earned (REPLAY_VERDICT_2026-08-08.md §Next-steps 1): the candidates are
ADOPTED on information evidence; this trial decides TRADABILITY. Per the
pre-fire addendum, no lane is seeded unless this trial passes.

## Design (frozen)

- **Book:** equal-weight composite of the 10 adopted signals' per-month
  cross-sectional pct-ranks (direction-applied, mirror rank 1−r for −1
  signs), SMALL segment, production book mechanics (top decile, 30% hold
  band), signals rebuilt by the Stage-B resolver (already reproduced each
  banked line exactly).
- **Windows:** explore 2004-2018 and confirm 2019-2024 both reported;
  **the confirm window is PRIMARY** (the explore window contributed to
  selection; stated, not hidden).
- **Cost arms:** flat-25, KO-half (INSTR-COST-MODEL spread frame), and
  stress-50 flat. Gross reported.
- **Placebo:** 5 seeded books, each the EW composite of 10 information-free
  persistent AR(1) signals (φ=0.99, seeds 1..5) through the identical book
  construction — controls book mechanics, universe drift, and small-segment
  cost structure.
- **Leg decomposition** (§28 methodology): long-leg share of the D10−D1
  spread, both windows.

## Decision rule (frozen)

- **PASS:** confirm-window net t ≥ 1.5 under BOTH flat-25 and KO-half, AND
  confirm net t exceeds every placebo book's confirm net t, AND long-leg
  share ≥ 50% in confirm.
- **WEAK-PASS:** confirm net t ≥ 1.5 under flat-25 only (KO-half in
  [0.8, 1.5)) — reported as cost-fragile; seeding decision goes to Murat
  with both numbers, no default.
- **FAIL:** anything else. The 10 adoptions KEEP their ADOPT ledger states
  (information is real); the book is recorded as not tradable at measured
  costs, and the forward path is closed until a cost-model change or new
  implementation layer is separately registered.

## Declared prior

Individual confirm net t's were 0.01-1.34; diversification across 10
imperfectly-correlated signals plus turnover netting should lift the
composite meaningfully — point guess: confirm net t 1.3-2.2 flat-25,
KO-half somewhat lower. P(PASS) ≈ 0.4. The σ-family members contribute IC
but little money; if the book fails, the first diagnostic (not a retry) is
that the money lives in the 6 generic-family signals — a 6-signal book is
a NEW registration, not a rerun.

## One shot

One run of this file's design. Output `runs/REPLAY-2/trial_replay_book_1.json`
is write-once. Any post-hoc variation (dropping signals, reweighting,
different windows) is a new trial ID.
