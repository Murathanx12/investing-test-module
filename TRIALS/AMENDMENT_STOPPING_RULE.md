# AMENDMENT — a stopping rule, because the programme did not have one

**Registered** 2026-08-09. **Forward-only.** No banked verdict is relabelled.

External review, section E: *"83 trials, 35 dead ends, 1 survivor ≈ 1.2 % hit
rate. That is consistent with pure noise mining at a high effective number of
independent tests. There's no declared point at which the programme concludes
there is nothing there."*

The hit-rate arithmetic in that sentence is worth correcting before adopting the
rest of it, because the correction cuts the other way: at the programme-wide
denominator of **821 tests**, an unadjusted 5 % screen applied to pure noise
would have produced about **41** apparent discoveries. We have declared **one**.
A 1.2 % declaration rate against a 5 % noise rate is evidence of a conservative
screen, not of noise mining. It does not prove the one survivor is real; it does
refute the specific charge.

The underlying point stands anyway. A search with no declared end is a search
that will eventually declare something, and the honest time to write the
stopping rule is while the answer is still unknown.

---

## The rule

**Definitions.** A *campaign* is a pre-registered trial with a primary metric
and a frozen decision rule. A campaign *clears* if its primary metric beats the
**Bonferroni-deflated bar** implied by the programme-wide denominator at the
time it runs (`aegis_brain/pf/ledger.py`), not the unadjusted t ≥ 2.

**Family exhaustion.** A signal family is declared **DEAD** once **20 registered
variants** have run without one clearing. A dead family may not be re-entered on
the same data. It may be re-entered only with a genuinely new input — a new data
source, not a new construction of the same source — and the re-entry is
registered as a new family with the counter reset to zero and the prior 20
counted in the denominator forever.

**Programme exhaustion.** The search is declared **EXHAUSTED** when **three
consecutive campaigns** produce no candidate clearing the deflated bar. On
exhaustion:

* no further search campaigns run on the existing data spine;
* the deliverables become the methodology paper, the negative-result paper and
  the measurement tool;
* re-opening requires a new data spine, registered before it is touched.

**The counter is public.** `ledger.programme_health()` prints the current run of
non-clearing campaigns beside the denominator, and every verdict carries it.

## Where the counter stands tonight

`TRIAL-PF4-DECOMPOSITION-1` **cleared**: the annual configuration's incremental
alpha t of 4.50 beats the Bonferroni bar of 4.01 at a denominator of 821. The
consecutive-failure counter is therefore **reset to 0**.

Recorded so it cannot be quoted as a triumph: that clearance is on a
**reported-never-deciding** configuration of an already-selected strategy, and
the same strategy's *headline* statistic clears nothing. The rule is satisfied
by the letter and the honest reading is that the programme has one candidate
whose best statistic survives deflation and whose economic claim is
"+2.0 %/yr over a buyable alternative, at t 1.13".

## Why asymmetric loss is not in this rule

Review also argued the ladder should be asymmetric — a false positive costs a
19-year-old years of capital, a false negative costs him time. That is right,
and it is deliberately **not** implemented as a tilt inside the statistics,
because tilting a bar is indistinguishable from moving it. It is implemented
where it belongs: in the standard's existing requirement that nothing reaches
capital without forward evidence, and in the product-track rule that regime
breadth is mandatory disclosure. If Murat wants the asymmetry made explicit in
sizing, that is a separate registration and his decision, not mine.
