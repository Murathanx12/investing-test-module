# The Layer-1 instrument's operating characteristics, measured

**2026-08-11, NIGHT-11.** Harness `scripts/calibrate_information_instrument.py`.
Receipt `runs/INSTRUMENT/information_calibration.json` (untracked — `runs/` is
gitignored, so the numbers are reproduced here in full).

**`INSTRUMENT_CALIBRATED = True`.** `aegis_brain/pf/information.py` is cleared to
issue verdicts. NEGATIVE_RESULTS #34 — a gate's kills are not trusted until the
gate is calibrated — is satisfied for this instrument.

---

## Why this run exists

An MDE is a promise: *at an effect of this size, this design finds it 80% of the
time.* Nothing in this programme had ever checked that promise against a world
where the answer was known. The MDE was an analytical formula, and that is
precisely how it went months being divided by the wrong standard error (P0-A,
this session) without anyone noticing — no measurement ever contradicted it.

## The world

1,200 names x 252 months. Monthly idiosyncratic vol 12% (roughly small-cap), a
market factor at 4.5%/month deliberately included because it is the term the
cross-sectional demeaning is supposed to remove and a world without it would
flatter the instrument. AR(1) signal persistence 0.85. 200 draws per cell,
common random numbers across cells.

## The results

| planted %/yr | detection (verdict rule) | significance rate | NO_INFORMATION | mean estimate | bias |
|---:|---:|---:|---:|---:|---:|
| 0.00 | **0.0%** | — | 93.5% | +0.05 | +0.000 |
| 1.00 | 10.0% | — | 58.0% | +1.05 | +0.000 |
| 1.82 *(its own MDE)* | **51.5%** | **81.0%** | 19.0% | +1.87 | +0.000 |
| 2.00 | 58.0% | — | 14.0% | +2.05 | +0.000 |
| 3.00 | 97.0% | — | 0.0% | +3.05 | +0.000 |
| 5.00 | 100.0% | — | 0.0% | +5.05 | +0.000 |
| 8.00 | 100.0% | — | 0.0% | +8.05 | +0.000 |

| check | value | verdict |
|---|---:|---|
| power at own MDE, **significance rule** | **81.0%** | target 80 — **the CANON §19 promise, verified** |
| detection at own MDE, **verdict rule** | **51.5%** | ~50 expected; stricter on purpose |
| false positives at a zero effect | **0.0%** | budget 2% |
| worst magnitude bias | **0.000 %/yr** | unbiased at every level |
| ever killed a real effect (>= 5 %/yr) | **never** | |

## Why two different rates at the same effect size

They are two different quantities and conflating them is what the external
reviews prescribed. An MDE is **defined** against a 5% significance test: at a
true effect of 2.8 SE, the rule "reject when |t| >= 1.96" fires 80% of the time.
Measured: **81.0%**. The label means what it says.

The **verdict** rule is stricter — `INFORMATION_PRESENT` requires
`|effect| >= MDE`, which is 2.8 SE rather than 1.96 — so at an effect of exactly
the MDE the estimate lands above it about half the time. Measured: **51.5%**.

That strictness is deliberate and is the winner's-curse guard. Among low-powered
studies, the results that clear mere significance systematically overstate their
effects, and NIGHT-10 found 21 of 21 configurations sitting in that region. An
instrument built to end that failure may not itself promote on it. Both rates
are reported on every run so the label cannot be misread.

## The plant is verified before it is used

ARENA-1's synthetic generator **cancelled its own plant**, so every known-answer
test it ran was silently executed on a null world and would have "passed" no
matter what the instrument did. This harness measures each world's realised
spread directly from the generated returns, independently of the estimator under
test, and **aborts** if the planted effect is absent.

The check is a **paired difference against the null world of the same seed.** The
first version compared each cell's realised level against its target and failed a
generator that was correct: it asked for 1.00 %/yr, measured 0.52, and the
missing 0.48 was the null world's own draw — present identically in every cell,
because the harness uses common random numbers so that a difference in detection
rate between two effect levels is the plant and not the draw. Differencing
against the paired null cancels it exactly.

That is **CANON §18** — a claim that two things agree is a claim about their
DIFFERENCE, tested with its own standard error — applied to the harness rather
than to a result.

## What this does not establish

The calibration says the estimator recovers what it is given, in a synthetic
world whose noise is well-behaved. It does not establish that the real panel's
noise is well-behaved, and it says nothing about whether an effect found on real
data is exploitable. **The instrument is cleared to issue Layer-1 verdicts. It is
not cleared to make money claims, and no Layer-1 result ever will be.**
