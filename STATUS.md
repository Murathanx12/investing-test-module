# STATUS — handoff after NIGHT-9 (2026-08-10)

**The project pivoted mid-session and the pivot is binding.** Read
`docs/HANDOFF_BUILD1.md` first — it says what is already built so BUILD-1 does
not rebuild it.

## Where the code is

* `factory/night-9` (Aegis module) — N1B, G8, typed stats, the N2 corrigendum.
* `aegis-finance` `main` `0c3f170` — **Optimus Portfolio Manager v1**, live.
  CANON §16 amended (it claimed G7 prices impact; it does not) and **§17 added**
  (an execution number carries the model that produced it).
* Holdout unread. No lane seeded, no flag flipped, no `paper_nav` touched, no
  keys changed. **LLM spend: $0.**
* Tests: **3,100 passed / 3 skipped** (aegis-finance, +26); module suite green
  (+22: 15 G8 invariants, 7 typed-stats invariants).

## The mandate changed

Three systems, none subordinate: **Research Lab** (~25%) asks what evidence we
possess; **Portfolio Manager** (~55%) compounds Murat's real $45k; **Opportunity
Engine** (~20%) finds where the payoff moved. Research sets reliability
*weights*; it does not block labelled OBSERVATIONAL information from reaching
the PM. The LLM never sizes. The engine never trades. Every wealth-target screen
prints the ruin probability beside the dream number.

## What NIGHT-9 found

Full detail: `docs/NIGHT9_VERDICT_2026-08-10.md`. Receipts in `runs/NIGHT9/`.

**1. N1B — every rank-based axis says the learned rankers are better, and the
book still earns less.** The re-fit reproduced the parent's published statistics
exactly (the first time this programme has verified that). Then: the advantage
is the **same size on the book's own rebalance months** (the clock hypothesis is
dead); it is **larger in the top decile than the bottom** (the §28 hypothesis is
dead); the learned top-K beats the control at **every** K from 25 to 300; and
the names they **add** beat the names they **drop** by 3.3–5.9 points. Overlap
between the two books is only **14–25%**. Four of five registered predictions
refuted.

**AMENDMENT 2 ran, and it is the finding of the night.** The label is a demeaned
**log** return; a long-only book is paid in **simple** returns. Under the simple
label the learned rankers' top-K is **worse than the composite's at every K and
in every arm — 15 of 15 negative**, agreeing in sign with the money result. And
**ΔIC is identical to five decimals under both labels**, because a rank
correlation is invariant to a monotone relabelling.

**So the ordering instrument is structurally blind to what determines the
money.** A portfolio earns the arithmetic mean of simple returns, which depends
on right-tail magnitudes; rank-IC discards magnitudes by construction. NIGHT-8
said "two instruments is what saved this from a vacuous null" — it did not. The
+0.068 at t 4.09 was never wrong and was never evidence about money.
**Standing consequence: rank-IC may describe ordering; it may not corroborate a
null money result, and "orders better" may not be said without a magnitude test
beside it.** No single top-K delta clears |t| 2 (0.98–1.70), so this is a
directional reconciliation across five cut points, three architectures and the
money instrument — not an independently significant effect.

**2. G8 — the impact term exists now.** Metaorder square-root law charged on the
whole order, so splitting an order over days no longer escapes it — G7's actual
loophole. Built beside G7, not inside it: `impact_coef = 0.0` skips the
arithmetic and reproduces G7 exactly. 15 invariants, two of which failed on the
first run for real reasons. **The capacity ladder was deliberately NOT run** —
institutional capacity does not help a $45k account.

**3. The N2 "15× better than chance" is withdrawn.** The random placebo was
count-matched to the union arm (288 names), not to distress (60). Correctly
normalised: distress **3.40×**, issuance 2.22×, union 1.49×, **accruals 1.05× —
chance**. Direction survives at a quarter of the size and only for two of three
families. Every return result in N2 stands.

**4. The units bug has a structural fix.** `aegis_brain/pf/stats.py` removes the
generic `paired()` entry point; four typed functions carry `unit`, `frequency`,
`annualization`, `estimator`, and the annualising arithmetic is unreachable from
the IC path.

**5. Portfolio Manager v1 ships and runs on live data.** One command, one
morning: state, the 12-month distribution with the downside beside the target,
per-holding BUY/ADD/HOLD/TRIM/SELL with dollars and kill conditions, threats, a
ranked radar, and which holding funds which buy. On the reconstructed book:
median ~$64,500, **P($100k) ≈ 20%**, **P(<$30k) ≈ 6%**, expected max drawdown
**−27%**. Two construction bugs found and fixed during the build, both of which
had produced confident nonsense.

## What is stubbed, wrong, or untrustworthy — read before quoting anything

* **The book is `confirmed: false`.** Reconstructed from the January 2026 PDF;
  no share counts, no cash. Every dollar figure carries a banner.
* **The analyst layer is Yahoo-only and has no target history.** ΔTarget over
  7/30/90 days — the mandate's central signal — **does not exist yet**; it is
  approximated by a 4-row rating-trend table. B1 is the real gate.
* **`TARGET_HAIRCUT = 0.35` is fitted to nothing** and every probability the PM
  prints depends on it.
* **No catalyst calendar at all.** For a book with three pre-revenue clinical
  names this is the largest gap in the product.
* **The N1B phase axis is not trustworthy** — twelve phases returned an
  identical excess CAGR, contradicting NIGHT-7's 2.45 pt/yr date-luck range. No
  phase claim may be made until it is resolved.
* **Every capacity number remains a delay-only lower bound** until G8 is pointed
  at the book (CANON §17).

## Queue

1. **B1 — the analyst data spine.** Call Finnhub / FMP / Polygon / EODHD /
   Alpha Vantage for target history and print status codes and payloads. Nothing
   in B4 is honest without it.
2. **The relabelling successor** — train on the arithmetic objective the book is
   actually paid in, rather than a demeaned log return. Registered by the N1B
   conclusion, not yet written.
3. **B5 catalyst calendar** — earnings, PDUFA, offerings, lockups.
4. **B7 reconstruction dataset** — the 25k→45k process as data, preserving the
   dated snapshots rather than refreshing them.
5. Fit the haircut once the journal has ~50 resolved instructions.
6. Resolve the phase axis.
7. **Background:** G8 capacity ladder, PF8 trigger confound, T4b coverage
   matrix, N3b. Displaced by the pivot, not by a finding.

## Decisions that are Murat's

Two inputs only he can give, and both gate real work: **actual holdings**
(tickers, shares, cost basis, cash) and the **trade history** behind the
25k→45k year. Both are private operational data — gitignored, per
`docs/BUILD1/PRIVATE_DATA_POLICY.md`. No lane, flag, capital or key decision is
outstanding.
