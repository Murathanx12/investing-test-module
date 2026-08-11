# REVINFO-1 VERDICT — the revision information exists, in small caps, for about six months

**Trial** REVINFO-1 · **Registered** `TRIALS/PREREG_REVINFO_1.md` (before compute,
corpse-linted PASS against 306 priors) · **Receipt**
`runs/REVINFO/revision_information.json` · **Layer 1 only.**

**Accrues 0 to the search denominator.** This trial ran no strategy, held
nothing, and produced no candidate. The Layer-2 test it licenses *does* accrue
and is registered separately.

---

## 1. The result

Breadth-weighted dollar-neutral spread, %/yr, against each arm's own 80%-power
MDE. Window 2002-2022, holdout unread.

| signal | segment | h=1 | h=3 | h=6 | h=12 |
|---|---|---:|---:|---:|---:|
| `tgt_rev_breadth` | small | **+9.36** (4.87) | **+7.32** (4.31) | **+5.45** (3.31) | +2.95 (2.21) |
| `tgt_rev_breadth` | largemid | +3.48 (1.59) | +3.71 (2.05) | +2.83 (1.75) | +2.04 (1.81) |
| `tgt_rev_3m` | small | **+7.32** (3.01) | +5.78 (2.12) | +3.11 (0.98) | −0.86 (−0.32) |
| `tgt_rev_3m` | largemid | +4.44 (1.60) | +3.81 (1.37) | +1.99 (0.72) | −0.66 (−0.33) |
| `eps_rev_breadth` | small | **+6.64** (5.10) | **+5.54** (4.71) | **+4.66** (3.65) | +2.72 (2.72) |
| `eps_rev_breadth` | largemid | +2.34 (1.19) | +2.66 (1.63) | +2.61 (1.61) | +1.75 (1.61) |
| `tgt_upside` *(control)* | small | −0.16 (−0.03) | −2.89 (−0.66) | −2.54 (−0.59) | +0.46 (0.12) |
| `tgt_upside` *(control)* | largemid | −2.39 (−0.67) | −3.26 (−1.06) | −2.46 (−0.90) | −0.76 (−0.37) |

Bold = above its own MDE. Newey-West t in brackets.

**7 of 32 INFORMATION_PRESENT · 21 UNRESOLVED · 4 NO_INFORMATION.**

### What is licensed

**H1 SUPPORTED, in small caps only.** Three constructions of the revision idea —
target-revision breadth, target-level change, and EPS-revision breadth — all
carry information about forward returns in the small segment at h=1. Two of them
hold it out to six months.

**H2 (decay) SUPPORTED in shape, NOT YET TESTED as a claim.** Every arm declines
monotonically with horizon. Under CANON §18 that is a claim about a DIFFERENCE
and must be tested on the paired series with its own standard error before it is
asserted. **It has not been. No half-life number may be quoted from this
document.** That test is the first item of the Layer-2 registration.

**Large caps are empty.** Not one largemid arm clears its MDE at any horizon.

---

## 2. What this does NOT license

The spread is **dollar-neutral and unconstrained**. Round 16 measured 88 to
99.9% of a comparable spread living in the SHORT leg, which a long-only book
cannot hold. Nothing here says money can be made, and no position may be sized
from it. The licence is a Layer-2 decision-boundary test and nothing else.

It also does not overturn ANALYST-IBES-1. That trial asked whether an EW top-50
long-only book beats the market; this one asks whether the cross-section carries
information. Different questions, different instruments, and a Layer-1 answer
cannot resurrect a Layer-3 corpse.

---

## 3. The control arm passed on sign and FAILED on magnitude — read this before the rest

`tgt_upside` is graded PERVERSE/CLOSED and the incumbent measured it at
**−16.70 %/yr** gross in small caps. The registered gate was "must come back
negative at h=1", and it did: **−0.16 %/yr**. The gate passes.

**But −0.16 is not a reproduction of −16.70, and the difference is the most
important thing this trial found.** Its cause is visible in the decile spreads:

| h=1, small | breadth-weighted | top-minus-bottom decile | incumbent top-50 |
|---|---:|---:|---:|
| `tgt_rev_breadth` | +9.36 | **+13.21** (t 6.04) | +6.05 |
| `tgt_upside` | −0.16 | **+1.18** (t 0.19) | **−16.70** |

The top decile of ~1,658 small caps is ~166 names. The incumbent's top-50 is the
top **3%**. The revision signals get STRONGER as the instrument concentrates
(+9.36 breadth → +13.21 decile, same sign, rising t): their information is
**broad**, spread across the cross-section. `tgt_upside` does not: it is flat at
the decile level and only becomes catastrophic in the extreme top few percent,
where lottery-stock junk concentrates.

⇒ **A corpse killed by a concentrated top-50 book is not automatically
re-testable by a cross-sectional instrument, because the two can be measuring
different regions of the same ranking.** The graveyard rescue queue must carry a
tail-concentrated arm alongside the cross-sectional one, or it will quietly
exonerate tail-perverse signals by averaging their perversity away. Registered
here so the queue is not designed without it.

---

## 4. The instrument gain, measured — and it is not what the design was argued for

The cross-sectional design was justified on the claim that estimating over
~900,000 stock-months instead of 252 portfolio-months would collapse the standard
error. Written as a test assertion (`ratio > 2.0`) it **failed at 1.31**, and
synthetic worlds with beta dispersion, sector factors and correlated
within-basket residuals moved it only to 1.29–1.52.

On the real panel, same signals and same months:

| segment | measured gain (incumbent MDE ÷ cross-sectional MDE) |
|---|---|
| small | 1.45x, 1.87x, 1.95x, 2.11x |
| largemid | **0.98x, 0.99x**, 1.39x, 1.81x |

**Range 0.98x to 2.11x, median 1.63x.**

The gain is real, useful, and concentrated in **small caps**. In large/mid it is
**absent** — twice measured below 1.0. That is mechanically sensible: in large
caps a top-50 book already IS most of the investable cross-section, so there is
no breadth left to recover.

**Consequence for the roadmap.** The graveyard rescue queue was premised on a
large power upgrade. What is actually available is a ~1.6x finer ruler in small
caps and nothing in large caps. An 8 %/yr MDE becomes ~5 %/yr — enough to move
some UNRESOLVED corpses, not enough to make the standard design adequate. The
remaining power has to come from somewhere else: longer windows on the 1962-
spine, factor-neutralised test portfolios, or event-level rather than
monthly-panel estimation.

---

## 5. Two defects in this trial's own instrument, found and fixed before the verdict

**The MDE was IID while every t-stat was HAC** (P0-A, this session). Fixed
upstream; the re-audited incumbent MDEs move from 6.3–19.9 to 6.47–24.82 %/yr.

**`NO_INFORMATION` was not an equivalence claim.** The first rule issued a kill
whenever an effect missed its MDE and the MDE looked small. Run against this
data it labelled an arm with **t = 2.21** "evidence of absence", and another at
**t = 2.72**. An effect significantly different from zero cannot be evidence that
there is no effect. The rule is now a one-sided equivalence bound: the whole 95%
interval must lie inside the region already declared not worth having, and the
arm must not be significant.

Re-running the full grid under the corrected rule changed **7 of 32 verdicts**:

* **5 false kills prevented** (NO_INFORMATION → UNRESOLVED), including the t=2.72
  and t=2.21 arms;
* **2 kills correctly issued** (UNRESOLVED → NO_INFORMATION), where the interval
  genuinely sits inside the uninteresting region.

It moved in both directions, which is the evidence that it is more correct
rather than merely more permissive. The first-pass receipt is kept at
`runs/REVINFO/_firstpass_oldrule.json`.

---

## 6. Registered next steps

1. **The half-life, tested properly.** Paired difference between horizons with
   its own SE (CANON §18). No half-life claim until then.
2. **Layer 2 — the decision boundary.** Does the signal help at the cut a real
   book makes (rank 11 vs rank 13), and what is `E[r_entrant − r_incumbent]`?
   This accrues to the denominator.
3. **The short-leg decomposition.** How much of the +9.36 is in the leg a
   long-only book cannot hold? Round 16 says expect 88–99.9%. If it holds here,
   the whole family is a Layer-3 death regardless of Layer 1.
4. **A tail-concentrated arm** for the rescue queue, per §3.
