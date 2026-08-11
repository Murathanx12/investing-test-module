# The revision family survived the leg a long-only book cannot hold

**2026-08-11, NIGHT-12.** `scripts/decompose_revision_legs.py`, receipt
`runs/REVINFO/leg_decomposition.json` (untracked — `runs/` is gitignored, so
every headline number is reproduced here).

**Accrues ZERO to the search denominator.** This re-partitions an
already-registered result using the same weights over the same months. No
outcome here can promote anything; it can only subtract.

---

## Why this ran first

NIGHT-11 found revision information in small caps and immediately registered
the reason it might mean nothing: the spread is **dollar-neutral and
unconstrained**, and Round 16 measured **88 to 99.9%** of a comparable spread
living in the short leg. If that held here, the Layer-1 pass would be real and
the product still dead — and it is far cheaper to learn that before an exposure
controller, a belief state and a lane are built on top of it.

It does not hold here.

## The decomposition

`y` is cross-sectionally demeaned before the legs are taken, so **the long leg
already IS an excess return over the equal-weighted eligible universe** — the
object a long-only book can actually hold. The short leg is what it cannot.

| arm (small caps) | spread | **long leg** | its MDE | t | short-leg share |
|---|---:|---:|---:|---:|---:|
| `tgt_rev_breadth` h1 | +9.36 | **+4.48** | 3.21 | +3.91 | 52.1% |
| `tgt_rev_breadth` h3 | +7.32 | **+3.95** | 2.79 | +3.96 | 46.1% |
| `tgt_rev_breadth` h6 | +5.45 | +2.78 | 2.82 | +2.76 | 48.9% |
| `tgt_rev_3m` h1 | +7.32 | +3.86 | 4.26 | +2.16 | 47.2% |
| `eps_rev_breadth` h1 | +6.64 | **+3.24** | 2.57 | +3.53 | 51.2% |
| `eps_rev_breadth` h3 | +5.54 | **+3.08** | 2.26 | +3.82 | 44.5% |
| `eps_rev_breadth` h6 | +4.66 | **+2.72** | 2.19 | +3.47 | 41.8% |

**6 of the 7 licensed arms clear their own long-leg MDE.** The top decile alone
earns **+3.44 to +6.48 %/yr at t 2.88 to 5.45**.

## The share is descriptive; the claim is about the difference

Under **CANON §18**, "one leg carries more than the other" is a claim about
their DIFFERENCE and must be tested with its own standard error. It is estimated
from the **paired monthly series**, so the legs' common exposure cancels rather
than being carried into the comparison.

**It is not detectable in any of the seven arms** — |t| ≤ 1.04 against MDEs of
2.1 to 4.3 %/yr. The honest reading is that the split is **even**, and the
41.8–52.1% share is descriptive only. No number here supports "most of it is in
the short leg" *or* "most of it is in the long leg."

## Round 16 does not replicate, and that is a finding about scope

Round 16's 88–99.9% was measured on a different signal family with a different
construction. Its non-replication here does not overturn it; it bounds it. The
standing lesson survives in its correct form: **a dollar-neutral spread is not
evidence that a long-only book earns anything, and must be decomposed rather
than assumed.** What changes is that this particular family passes the test
rather than fails it.

## The partition is asserted, not trusted

The legs must sum to the spread they decompose, exactly. The runner **aborts**
if they ever do not — a partition that fails to reconstitute its parent would
make every share above wrong by an unknown amount, silently. Five tests in
`tests/test_information.py` pin the identity, the even split of a symmetric
planted effect, the refusal to inherit a long-only verdict from the
dollar-neutral spread, and that the difference is never read off the share.

## What this does NOT license

* **Still Layer 1 and still gross of every cost.** ANALYST-IBES-1 measured this
  family dying at **10× turnover**. Surviving the short leg says nothing
  whatever about surviving costs, and the turnover question is untouched.
* No money claim, no position, no capital, no lane.
* It licenses one thing: a **Layer-2 decision-boundary test for a long-only
  book**, which is a separate pre-registration and which **does** accrue.

## The registered next test

`eps_rev_breadth` small is now the highest-value open question in the registry:
it is the most persistent arm, its long leg clears its MDE at h=1, 3 and 6, and
it had never been tested at Layer 1 before NIGHT-11. Its Layer-2 test should
carry the turnover question through **G7** in the same trial, because a long leg
that survives its short leg and then dies on costs is the most expensive way
this family can still fail.
