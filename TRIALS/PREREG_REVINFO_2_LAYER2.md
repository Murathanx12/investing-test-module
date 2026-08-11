# PREREG — REVINFO-2: the decision boundary for a long-only revision book

**Registered** 2026-08-11, NIGHT-12, **before any Layer-2 statistic was
computed.** **Family** analyst. **Parent** REVINFO-1
(`docs/REVINFO_1_VERDICT_2026-08-11.md`) and its leg decomposition
(`docs/REVINFO_1_SHORT_LEG_2026-08-11.md`). **Data** IBES + the CRSP spine
already on disk; frozen window 2002-01-31 to 2022-12-31; **holdout unread.**

**This trial ACCRUES ONE ARM to the search denominator.** REVINFO-1 and the leg
decomposition both accrued zero because neither could promote anything. This one
can, so it counts. Saying so before it runs is the point.

---

## 1. Why this trial is now licensed, and by what exactly

Three results in sequence, none of which alone would justify it:

1. **REVINFO-1 (Layer 1)** — the cross-section carries revision information in
   small caps out to about six months. `eps_rev_breadth` is the most persistent
   arm and had never been tested at Layer 1 before.
2. **The leg decomposition (NIGHT-12)** — the information is **not** trapped in
   the short leg. The long leg alone clears its own MDE in 6 of 7 licensed arms;
   `eps_rev_breadth` small reads **+3.24 / +3.08 / +2.72 %/yr** at h=1/3/6
   against MDEs of 2.57 / 2.26 / 2.19, at t 3.53 / 3.82 / 3.47.
3. **The instrument is calibrated** — 81.0% power at its own MDE against planted
   effects, 0.0% false positives (`docs/INSTRUMENT_INFORMATION_CALIBRATION`).

What is still completely unknown is the only thing that decides a product:
**whether a book that must actually TRADE this signal keeps any of it.**

## 2. The one thing that is most likely to kill this

**ANALYST-IBES-1 measured the revision family dying at 10× turnover.** That
result was later re-graded UNRESOLVED by the power audits, so it is not a kill —
but it is the single most informative prior available, and it points one way.

A signal whose information decays over six months but whose ranking churns
monthly is the classic shape of an edge that exists and cannot be collected. So
**this trial does not test the signal and the costs separately.** Both arms run
in the same trial, and the headline number is the net one.

## 3. Hypotheses, registered

**H1 (the decision boundary).** For a long-only book of small-cap names formed
on `eps_rev_breadth`, the expected return of the marginal ENTRANT exceeds that
of the marginal INCUMBENT it replaces: `E[r_entrant − r_incumbent] > 0`,
estimated on the paired monthly difference with its own Newey-West SE (CANON
§18 — this is a claim about a difference and is never read off two levels).

**H2 (net of costs, through G7).** The same book, simulated daily through
`aegis_brain/pf/daily_sim.py` at `impact_coef = 0` (that is G7, not G8), earns
net excess CAGR above zero versus the CRSP value-weighted benchmark.

**H3 (the rebalance frequency that survives).** Because the information decays
over about six months while a monthly ranking churns, the net result is expected
to IMPROVE as the holding period lengthens from 1 to 3 to 6 months. Registered
as a claim about DIFFERENCES between adjacent frequencies, each with its own SE.
NIGHT-6 measured annual beating monthly by +2.43 %/yr on a different family; a
result in the same direction here is corroboration, not a new discovery.

## 4. The decision rule, frozen

| outcome | verdict |
|---|---|
| H2 net excess ≥ its own 80%-power MDE **and** ≥ 4/6 regime blocks | `CANDIDATE` — eligible for a forward shadow lane, attended decision only |
| H2 net excess > 0 but below its own MDE | `UNRESOLVED` — absence of evidence, NOT a kill (§19). No lane. |
| H2 net excess ≤ 0 with the whole interval below the economic threshold | `NET_DEAD` — the information is real and cannot be collected long-only at this turnover |
| H1 fails while H2 passes | **the run is VOID and investigated**, not reported — a book cannot earn from a boundary that does not exist |

**Every arm reports its own 80%-power MDE beside its estimate (§19), and the MDE
uses `max(HAC, IID)` because an MDE licenses a null.**

**The expected outcome is `UNRESOLVED` or `NET_DEAD`.** Registering that in
advance is deliberate: the Layer-1 result is genuinely good and that is exactly
the condition under which a programme talks itself into a product.

## 5. What may NOT be concluded

- That REVINFO-1 is confirmed. A Layer-2 result cannot re-grade a Layer-1 one.
- That ANALYST-IBES-1 is overturned. Different construction, different question.
- Any money claim, any Sharpe, any skill claim. **No skill claims before 24
  months of forward record**, and this trial produces no forward record at all.
- That a `CANDIDATE` verdict seeds anything. Seeding a lane is Murat's decision
  and his alone.

## 6. Pre-specified controls

- **The corpse as control:** `tgt_upside` must reproduce its negative sign
  through the same pipeline, and — per the NIGHT-11 standing rule — it carries
  **both a cross-sectional and a tail-concentrated arm**, because a corpse killed
  by a concentrated top-50 book is not automatically re-testable
  cross-sectionally.
- **A no-information control:** the same book construction on a signal that is
  pure noise, to confirm the pipeline earns nothing when there is nothing.
- **Turnover is reported, never assumed.** If realised turnover comes in below
  what ANALYST-IBES-1 measured, that discrepancy is investigated before any
  number is reported — a cheaper book than the prior expects is more likely a
  bug than a discovery.

## 7. Power, stated before the run

The parent's long-leg MDEs are 2.19–2.57 %/yr *gross at Layer 1*. A long-only
book of 50–100 names will have a materially larger MDE than the full
cross-section — NIGHT-11 measured the instrument gain at only **1.63× median,
and 0.98× in large caps**, so the loss going the other way is real and must be
computed rather than assumed. **If the book's own MDE exceeds its point
estimate, the correct verdict is `UNRESOLVED` and the trial has answered
"this design cannot see it" — which is a result, not a failed run.**
