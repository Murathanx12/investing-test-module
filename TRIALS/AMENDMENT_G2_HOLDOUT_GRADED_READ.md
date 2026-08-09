# AMENDMENT — G2, the one-shot holdout, becomes a GRADED read

**Registered** 2026-08-09, **before** G7 exists and **before** the holdout is
read. `allow_holdout=False` is still the default in `load_spine`, every factory
artifact still carries `holdout_read: false`, and the verification script still
exits non-zero on violation. This amendment changes what the read PRODUCES, not
when it happens, and Murat's sequencing decision (G7 first, attended, Murat
present) is untouched.

**Forward-only.** No banked verdict is relabelled.

---

## 1. Why

The registered G2 was a binary gate: read the 24 months of 2023-01..2024-12
once, pass or fail, failure final. External review showed the arithmetic makes
that indefensible, and the arithmetic checks out (`runs/PF4/GATE_POWER.json`):

* 24 monthly observations at the book's own tracking error give a standard error
  on the annualized excess of roughly 7 %/yr.
* The minimum effect the gate can detect at 80 % power is therefore several
  times the effect being tested.
* Run the other way: on a **true** +4.67 %/yr strategy a binary "excess > 0"
  read passes only about three times in four, and against a +3 % product bar
  barely better than a coin flip — and worse once the mega-cap headwind the
  dossier itself discloses is subtracted.

An irreversible binary decision, at that power, in a regime known in advance to
be adverse, is not rigour. It is a coin flip that the registry would then have
made permanent.

**What does not change:** the holdout is still one-shot, still attended, still
unrepeatable, and failure to clear the evidence threshold still BLOCKS
graduation. The change is that "the read produced no evidence" becomes a
distinguishable outcome from "the read produced evidence against" — which a
binary gate conflated, and which is the single most consequential distinction at
this sample size.

## 2. The graded read, specified now

On firing, compute over the 24 holdout months:

* `x` = annualized mean excess return of the book over the CRSP VW benchmark,
* `se` = the holdout's own realized tracking error / √2, estimated **from the
  holdout months themselves** so it is not a parameter anyone chooses later.

Compare three pre-stated point hypotheses, frozen here:

| label | true annual excess |
|---|---|
| `H_null` | 0.00 % |
| `H_product` | +3.00 % — the product bar |
| `H_claim` | +4.67 % — the backtest point estimate |

Report the Gaussian likelihood ratios `LR(H_product : H_null)` and
`LR(H_claim : H_null)`, and the posterior odds under an explicitly stated 50/50
prior. Report `x`, `se`, and the two-sided 95 % interval beside them, always.

## 3. Pre-stated verdict mapping (frozen)

| `LR(H_product : H_null)` | verdict |
|---|---|
| ≥ 3 | **HOLDOUT SUPPORTS** — the product-track candidacy survives this gate |
| between 1/3 and 3 | **HOLDOUT UNINFORMATIVE** — recorded as such, not as a pass and not as a failure. Graduation remains blocked; the forward ledger is the instrument that decides |
| ≤ 1/3 | **HOLDOUT EVIDENCE AGAINST** — graduation blocked and the candidate is marked FAILED |

An UNINFORMATIVE outcome may **not** be re-read, re-sliced, extended, or
supplemented with a second window. It is spent. The only remedy is forward time.

## 4. Bound to the same hard constraints as before

* One firing, attended, Murat present, on his instruction only.
* G7 (the sequential daily simulator) must exist and the candidate must have run
  through it first. Unchanged, and it is his decision, not mine.
* No metric substitution: `x` as defined above is the only input to the mapping.
* The prior is stated in the verdict, not chosen after seeing `x`.

## 5. Companion disclosure — G9

`runs/PF4/GATE_POWER.json` also prints, and every future verdict quoting G9 must
carry: the **false-negative rate of the 4-of-5 sub-sample rule at a range of
true effect sizes**, including +2.5 %/yr. G9 is calibrated to pass large
effects. That is a defensible design if it is stated and a misleading one if it
is not, and it was not.

The same file prints which gate actually **binds** for a given campaign and the
effect size each t-bar implies at the realized sample size. A gate that can
never bind is decoration and should be labelled as such rather than counted.

## 6. Recorded honestly

This amendment makes a gate **easier to survive** in one specific sense: a
strategy that would previously have been killed by an uninformative read is now
merely un-promoted. That is a real loosening and it is stated rather than
buried. The justification is that the previous rule discarded true strategies at
a rate the standard never acknowledged, and that a rule which cannot distinguish
"no evidence" from "evidence against" is measuring the sample size, not the
strategy.
