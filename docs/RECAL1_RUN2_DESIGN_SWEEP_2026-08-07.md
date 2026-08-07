# RECAL-1 run 2 — design sweep (wave 2) + a post-hoc capacity finding

Written 2026-08-07 18:4x, **while wave 3 is still running**, so that the
post-hoc status of §3 is on the record before the fresh nulls that will test
it exist. Bank: 250 reps × 11 cells, tag `r1`, ρ_sig 0.5.

## 0. Wave 2 ran; the chain's own assertion crashed

Wave 2 completed all 250 reps (6.79h, every rep `+7 cells (11 total)`), then
the chain exited 3 on `NameError: name 'tag' is not defined` — inside the
coverage assertion added in response to run 1's silent no-op. The guard I
wrote to catch invisible failure had never been executed by anything until a
6.8-hour grid ran it.

Fixed twice over: the block is now a callable `bank.assert_coverage()`, and
`tests/test_recal_ruleset.py::test_coverage_assertion_passes_and_fails`
exercises both branches. Coverage independently verified before the rerun —
250/250 rep files, 11/11 cells, nothing missing. **No compute was lost.**

Lesson worth keeping: run 1's failure was a guard that did not exist; run 2's
was a guard that could not be called. An assertion with no callable entry
point has no test, and code with no test is a hypothesis.

## 1. The design sweep (frozen BRAIN-009, largemid / top-5)

| cell | graduate | adopt |
|---|---|---|
| a0.0/base (null) | 0.032 | **0.016** |
| a0.2/I1 | 0.252 | 0.164 |
| a0.4/I1 | 0.596 | 0.436 |
| a0.6/I1 | 0.872 | 0.796 |
| a0.2/I2 | 0.232 | 0.112 |
| **a0.4/I2** | **0.564** | 0.232 |
| a0.6/I2 | 0.812 | 0.340 |
| a0.4/I3 | **0.032** | **0.016** |
| a0.6/I3 | **0.032** | **0.016** |
| a0.4/I4 | 0.516 | 0.368 |
| a0.6/I4 | 0.776 | 0.664 |

**A4 PASS** — P(graduate | α=0.4, I2) = **56.4%** against a ≥30% target. This
is the target that mattered: M1's headline failure was that the explore gate
killed 93–99% of decaying edges. It now kills 43.6%. End-to-end I2 adoption
(23.2%) stays low, and per spec §1(a) that is *correct* — an I2 edge is at
9.2% strength inside the confirm window, so confirm is right to be sceptical.

**I3 is the finding.** A small-cap-only edge scores **0.032 / 0.016 at both
α=0.4 and α=0.6 — identical to the null cell, to three decimals.** The
factory is not merely weak on small-cap edges; it is *exactly as likely to
adopt a real one as to adopt noise*. Injected strength does not move the
number at all, because the ladder never looks at the segment. This is total
structural blindness, and it is now measured rather than suspected.

**I4** (size-correlated, ρ=0.5) at 0.368 vs I1's 0.436 — a real but modest
degradation, ~85% of constant-edge power.

## 2. A5, as pre-registered

A5 asked for P(graduate | α=0.4, I3) ≥ 30% under the both-segments variant.
Measured: **28.0%. NARROW MISS** (Wilson [0.229, 0.338] covers 30%, but the
rule is the point estimate).

And the variant is not free — the same change costs largemid power:

| ladder | FDR | a0.4/I1 | a0.4/I3 | a0.4/I4 |
|---|---|---|---|---|
| largemid, top-5 (FROZEN) | 0.016 | 0.436 | 0.016 | 0.368 |
| both-seg, top-5 | 0.000 | **0.212** | 0.204 | 0.288 |

Doubling the universe while holding the shortlist at 5 halves the power on
the segment that was working. On the pre-registered family, breadth traded
against depth and A5 missed.

## 3. POST-HOC: the trade was an artifact of the cap

`explore_top_n` was **not** an axis of the pre-registered 1800-member family;
it was fixed at 5 throughout. Having seen §2, the obvious question is whether
the shortlist is a *capacity* parameter — if the universe doubles, 5 slots is
half the shelf space it was. Raising it to 10 (one free bank re-aggregation,
zero grid cost):

| ladder | FDR | a0.2/I1 | a0.4/I1 | a0.4/I2 | a0.4/I3 | a0.6/I3 | a0.4/I4 |
|---|---|---|---|---|---|---|---|
| largemid, top-5 (FROZEN) | 0.016 | 0.164 | 0.436 | 0.232 | 0.016 | 0.016 | 0.368 |
| both-seg, top-5 | 0.000 | 0.044 | 0.212 | 0.124 | 0.204 | 0.560 | 0.288 |
| **both-seg, top-10** | 0.024 | 0.160 | 0.432 | 0.224 | **0.424** | **0.784** | **0.544** |

Both-seg/top-10 **weakly dominates the frozen ladder on every cell measured**:
largemid power is unchanged (0.432 vs 0.436, well inside noise), I2 unchanged,
I4 improves 0.368 → 0.544, and I3 goes from the null rate to 0.424 — a 26×
change on the blindness cell. The cost is FDR 0.016 → 0.024, still inside the
5% budget with Wilson upper ≈ 0.068 < 0.08.

Pre-registered even/odd validation, run before this was written up:

| ladder | half | FDR | a0.4/I1 | a0.4/I3 | a0.4/I4 |
|---|---|---|---|---|---|
| FROZEN | selection (even) | 0.016 | 0.432 | 0.016 | 0.344 |
| FROZEN | **held-out (odd)** | 0.016 | 0.440 | 0.016 | 0.392 |
| both-seg/top-10 | selection (even) | 0.032 | 0.424 | 0.424 | 0.560 |
| both-seg/top-10 | **held-out (odd)** | **0.016** | **0.440** | **0.424** | **0.528** |

On the held-out half the two ladders have *the same* FDR (0.016) and *the
same* largemid power (0.440), and the candidate additionally sees small-cap
and size-correlated edges. It does not look like an overfit.

### What this is not

It is **one post-hoc hypothesis with an a priori direction**, tested on the
same 250 panels that chose the frozen ladder. It is not a pre-registered
selection and must not be reported as one. Three things are required before
it could replace the freeze:

1. **An independent null.** Wave 3's 1000 fresh α=0 reps are running now and
   were not used to find this. That is the clean FDR test, and it is the
   reason this document is dated before they land.
2. **A cap sweep, pre-registered.** top-10 is the first value tried. If it
   ships, top_n belongs in the family with its own grid, or the choice is
   again a single point picked by eye.
3. **Murat's attended call**, under the contamination caveat below.

### Contamination status — narrower than it looks

I previewed the 179 real candidates under the frozen ladder's explore
threshold (t_ic ≥ 1.5) **filtered to `segment == "largemid"`**. So:

- changing the **threshold** post-hoc is contaminated — I have seen how real
  candidates fall around 1.5;
- changing the **cap** and **adding the small segment** is not — the frozen
  threshold is untouched, and I have never looked at a small-segment row.

This distinction is checkable: the preview script is
`scratchpad/inv179.py`, and its filter is `d.segment == "largemid"`.
The small segment of `data/factory/batch*_summary.csv` remains unexamined
and should stay that way until the ladder question is closed.

## 4. Status of the acceptance targets

| | target | run 2 |
|---|---|---|
| A1 FDR ≤5%, Wilson ≤8% | | PASS (0.016) — wave 3 will tighten |
| A2 P(adopt \| α=0.4,I1) ≥30% | | PASS (0.436) |
| A3 P(adopt \| α=0.2,I1) ≥10% | | PASS (0.164) |
| A4 P(grad \| α=0.4,I2) ≥30% | | **PASS (0.564)** |
| A5 P(grad \| α=0.4,I3) ≥30% both-seg | | **MISS (0.280)** — but see §3 |
| A6 posterior monotone | | pending wave 3 |
| A7 held-out within Wilson overlap | | PASS |
