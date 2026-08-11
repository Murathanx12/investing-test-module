# PREREG — REVINFO-1: does the cross-section carry the revision information?

**Registered** 2026-08-11, NIGHT-11, before any statistic in §4 was computed.
**Family** analyst. **Data** `ibes.ptgsumu` + IBES EPS, already on disk from
ANALYST-IBES-1; CRSP panel 2002. **Parent** ANALYST-IBES-1
(`docs/ANALYST_IBES_1_VERDICT_2026-08-11.md`), re-audited by
`scripts/audit_power_hac.py`.

**Layer 1 only.** This trial asks whether information exists in the
cross-section. It may not conclude that money can be made and it may not size a
position. A positive result licenses a Layer-2 decision-boundary test, which is
a separate pre-registration.

**Denominator.** This accrues **zero** arms to the search denominator. It runs
no strategy, holds nothing, and produces no candidate. The Layer-2 test that a
positive result licenses *does* accrue, and is registered separately. Saying so
in advance is the point: a diagnostic that quietly becomes a strategy search is
how denominators get lost.

---

## 1. Why this is not re-litigation of ANALYST-IBES-1

ANALYST-IBES-1 measured whether an **EW top-50 long-only book formed on analyst
revisions beats the market**. Every arm came back below its own detection
threshold:

| arm | segment | reported gross | MDE (IID) | MDE (HAC) |
|---|---|---:|---:|---:|
| `tgt_rev_breadth` | small | **+6.05 %/yr** | 7.60 | **8.36** |
| `tgt_rev_breadth` | largemid | +2.57 | 6.48 | 4.67 |
| `tgt_rev_3m` | small | −0.73 | 12.31 | **15.27** |
| `tgt_rev_3m` | largemid | +5.94 | 12.48 | 11.78 |

The registered consequence stands: those are **UNRESOLVED**, not kills, and
this trial does not overturn them. It asks a **different and prior question** —
whether the ordering information exists at all — with an instrument that is not
a 50-name book. A Layer-1 answer cannot resurrect a Layer-3 corpse; it can only
say whether the corpse is worth a properly powered Layer-2 test.

## 2. Hypotheses, registered

**H1.** The cross-section carries information about forward returns from analyst
target-revision breadth, at horizon 1 month, in at least one segment.

**H2 (the half-life).** If H1 holds, the information decays with horizon. The
registered prediction is that the annualised spread at h=12 is **smaller** than
at h=1. This is a claim about the DIFFERENCE between two horizons and, under
CANON §18, it is tested on the paired difference with its own standard error —
never by comparing two point estimates and reading their order.

**H3 (the instrument).** The cross-sectional design resolves a smaller effect
than the incumbent top-50 book on the same signal over the same months.
Synthetic worlds put this gain at only **1.29x to 1.52x**
(`tests/test_information.py`, where an assertion of >2x failed at 1.31 and was
kept rather than tuned). **A measured gain near 1.0 refutes H3 and is a reported
result, not a failed run.** The graveyard rescue queue depends on H3; if H3
fails, the queue does not get its instrument from this direction and that is the
finding.

## 3. Control arm — the corpse this is not

`ibes:tgt_upside` is graded **PERVERSE/CLOSED** (−8 to −18 %/yr as a picker).
It runs as a control arm at every horizon and segment. **If it does not come
back negative at h=1, the pipeline is wrong and no other arm in this run may be
read.** A new mechanism carries the corpse it is not (ARENA-1).

## 4. Statistics, frozen before compute

* Estimator: Fama-MacBeth. Cross-sectional normal scores of the signal against
  the cross-sectionally demeaned forward return; one slope per month; the
  monthly series tested with Newey-West at `max(12, 2h)` lags.
* Effect reported in %/yr: the breadth-weighted dollar-neutral spread,
  annualised by 12/h, so a 12-month holding return is not counted twelve times.
* Every arm reports its own 80%-power MDE from `max(SE_hac, SE_iid)` (CANON §19,
  as corrected P0-A this session).
* Window 2002-01-31 to 2022-12-31. **The holdout is not read.**
* Segments: `small`, `largemid`, from the frozen eligibility masks.
* Horizons: 1, 3, 6, 12 months.

## 5. Decision rule, frozen before compute

For each arm:

| condition | verdict |
|---|---|
| \|spread\| >= own MDE | **INFORMATION_PRESENT** — licenses a Layer-2 test |
| \|spread\| < own MDE **and** MDE <= 5 %/yr | **NO_INFORMATION** — a real kill |
| \|spread\| < own MDE **and** MDE > 5 %/yr | **UNRESOLVED** — may not be recorded as a kill |

5 %/yr is the largest-credible-effect ceiling, frozen as a module constant in
`information.py` and deliberately **not** exposed as a parameter, so that no
caller can widen it to make its own null look decisive.

## 6. What this trial may NOT do

* It may not issue a money claim, a capacity number, or a position.
* It may not promote any signal to the registry. Registry grades change only
  through the adjudication path, on a Layer-3 result.
* It may not read the holdout.
* It may not report a power gain for the new instrument that was measured
  anywhere other than the real panel it is claimed for.

## 7. Instrument status at registration

`information.py` is calibrated against injected alpha before this trial is read
(`scripts/calibrate_information_instrument.py`): false-positive rate at a zero
effect, realised power at the instrument's own reported MDE, and magnitude bias.
The plant is verified present in every synthetic world as a paired difference
against the null world of the same seed — ARENA-1's generator cancelled its own
plant, and every known-answer test it ran was silently executed on a null world.
**If the calibration does not pass, this trial is not read.**
