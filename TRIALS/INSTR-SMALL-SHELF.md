# INSTR-SMALL-SHELF — the small-cap graduation door was closed on a cost premise measured backwards

**Registered 2026-07-30, FROZEN BEFORE ANY RE-SCAN CODE IS WRITTEN.**
Instrument, one shot. Cumulative candidate **160**.
Authority: Murat delegated the session ("do whatever you see fit"); registered
under the same S3 de-risking door used for TRIAL-COND-VT — same registry, same
cumulative deflation count, no exemption claimed. Murat's to overrule.

---

## The defect this trial exists to test

`docs/STRATEGY_FACTORY.md`, frozen 2026-07-22, defines the two segments and
then makes one load-bearing assumption:

> `small` — ranks 1001..3000. Reported, but **25 bps understates true small-cap
> costs**; treat small-only results as directional.

and, in the same frozen document, the graduation rule:

> A fresh signal graduates to a pre-registered CONFIRM trial iff, **in the
> `largemid` segment**: t(net excess) >= 1.5 AND t(IC) >= 2.0.

So for the entire 159-candidate search, **the small segment was structurally
ineligible to graduate**, on the stated ground that 25 bps was too generous
there. Later registrations hardened this into "small documented 50 bps"
(TRIAL-TEXT-LAZY registry row).

**INSTR-COST-MODEL then measured it, and the assumption is backwards.** Kyle-
Obizhaeva invariance half-spreads on our own panel (`data/factory/
instr_cost_model.json`, sanity gate PASS):

| segment | 2004-2010 | 2011-2018 | 2019-2024 |
|---|---|---|---|
| largemid | 4.2 bps | 3.4 bps | 3.4 bps |
| **small** | **13.1 bps** | **12.1 bps** | **11.6 bps** |

Small-cap realistic one-way cost is **~12 bps, not 25 and not 50.** The flat
wall *over*-penalizes small books by roughly 2× (against the 25 bps scans) to
4× (against the 50 bps documentation standard) — the same direction as the
already-recorded largemid over-penalty, which INSTR-COST-MODEL disclosed as a
"honest counter-implication" and propagated to largemid only
(INSTR-COST-REMEASURE-REJECTS, cohort EMPTY, shelf closed).

**The small segment never received that propagation.** This trial performs it,
once, under the identical frozen rule.

Why it matters beyond bookkeeping: the paper's lead exhibit ("the cost-killed
shelf is empty") is a **large/mid** statement, in a paper titled *retail-
accessible equity signals*. Large/mid is the least retail-specific segment, and
the program's one confirmed survivor (gp-small) lives in small. If the small
shelf is also empty, the lead exhibit generalises and the paper gets stronger.
If it is not empty, the paper has a second, more interesting result and the
factory has a real design defect on the record.

---

## Frozen cohort rule (verbatim from INSTR-COST-REMEASURE-REJECTS; only the segment changes)

From the banked explore summaries (`data/factory/batch*_summary.csv`), segment
**small**, take every non-contaminated signal row with:

    t_ic            >= 2.0    (rank leg PASSED)
    t_excess_gross  >= 1.5    (gross leg PASSED)
    t_excess_net    <  1.5    (net leg FAILED — died of the flat wall alone)

Mechanical, no discretion. An EMPTY cohort is a valid and final result.

### ⚠️ Disclosure — partial cohort visibility before registration

The audit that motivated this trial displayed `batch1_summary.csv` and
`batch2_summary.csv` on screen, so **two cohort members (`fscore_lite`,
`cash_prof`) were visible before this document was written.** Recorded rather
than smoothed over. What bounds the damage:

- the rule is **verbatim** from a trial frozen 2026-07-26 and applied to a
  segment named in the same frozen document — there is no free parameter,
  threshold, or filter chosen after seeing the data;
- batches 3-9 were **not** inspected, so cohort membership is not known;
- the **deciding metric is the KO re-scan and the confirm run**, neither of
  which has been computed. Seeing that a cohort is non-empty tells you nothing
  about whether any member clears a bar.

A reader who discounts this trial for the disclosure is reasoning correctly;
the disclosure is why it is here.

---

## Frozen procedure (one shot)

1. Apply the cohort rule; print the cohort in full, including near-misses.
2. Rebuild each cohort signal **byte-identically** from its original batch
   builder (same spec, direction, hold-band, window). Builder wiring is
   mechanical plumbing, disclosed, not tuning.
3. Re-scan **explore 2004-01..2018-12, small** under three cost arms:
   - **KO half-spread — PRIMARY** (per-name `cost_frame`; names missing from
     the frame fall back to flat 25).
   - **KO full-spread — STRESS.**
   - **zero cost — BOUND** (descriptive only; answers "could this graduate even
     for free?", the check that terminated the largemid instrument).
4. **Graduation re-check (house rule, unchanged, applied to small):**
   `t_excess_net >= 1.5 AND t_ic >= 2.0`. A graduate must clear the bar under
   **BOTH** the primary and the stress arm. Clearing only under KO-half is
   recorded as a near-miss and does **not** graduate.
5. Any graduate → **ONE** confirm run, 2019-01..2024-12, small, KO half-spread.
   **PASS iff** mean net excess > 0 **AND** t_excess_net >= 0.8 **AND**
   t_ic >= 1.5 (the standard confirm mirror; 72-month power note applies).
6. Report, always, whether or not anything graduates:
   - **mechanical-relief decomposition** per signal: expected relief =
     `mean_traded × Δbps / 1e4` where `Δbps = 25 − KO_half`. If a graduate's
     entire improvement is mechanical relief, **say so** — that is the
     hypothesis, not an embarrassment, and hiding it would be the defect.
   - DSR at `n_trials = 160`, FF6 alpha where computable, turnover.
   - old (flat-25) and new (KO) numbers side by side, permanently.

One shot. Crashes before results are readable are repairable (disclosed).

---

## Kill condition (frozen)

Cohort empty **OR** no member clears the graduation bar under **both** cost arms
→ the small-cap cost-killed shelf is **CLOSED permanently**, matching largemid,
and **no further cost-model appeals exist for either segment.** No re-tuning of
the bar, the segment bounds, the cost arm, or the window. A different cost model
is a new registration against the deflation count, not a retune.

Confirm-window rule is identical: any bar missed → REJECT, no re-reading.

## Honest prior (declared before the run)

**MIXED, leaning toward at least one cohort member but no confirm survivor.**
The largemid instrument returned empty because *nothing had a gross-passing
book* there — the rank information was gone. Small is different: gross books
are demonstrably stronger (gp_base survived to a confirm run from this
segment), so a non-empty cohort is likely. But the confirm wall has killed
every graduate it has been handed except gp-small, the relief is only ~13 bps
one-way, and CZ-CALIB's fame-decay applies to whatever is in the cohort. The
honest expectation is: **non-empty cohort, 0-1 explore graduates, and the
confirm window decides — probably against.**

If this trial produces a confirm survivor it is the second in the program's
history and it will be the first one the factory's own design assumption had
been suppressing.

---

## RESULT (one run, 2026-07-30): **cohort NON-EMPTY (5), ZERO graduates. Small-cap cost shelf CLOSED.**

Artifact: `data/factory/instr_small_shelf.json`. Runner:
`scripts/run_instr_small_shelf.py` (written after the freeze).

### Cohort (frozen rule applied mechanically)

| signal | source | t_ic | t_gross | t_net (flat-25) | turnover 1-way |
|---|---|---|---|---|---|
| rec_mom | batch3a | 3.32 | **2.64** | 0.48 | 0.368 |
| industry_mom | batch9 | 2.06 | 2.03 | 1.39 | 0.244 |
| fscore_lite | batch2 | 6.63 | 2.01 | 1.46 | 0.129 |
| cash_prof | batch2 | 7.90 | 1.73 | 1.26 | 0.095 |
| re_me | batch7 | 5.30 | 1.56 | 1.37 | 0.074 |

The pre-registration disclosed that `fscore_lite` and `cash_prof` were visible
before the doc was written; the three that were not (`rec_mom`, `industry_mom`,
`re_me`) came from uninspected batches, and `rec_mom` — the strongest member —
was found only by the rule.

**Builder gap, caught and closed:** the first execution reported `rec_mom` as
having no builder (batch-3a constructs its signals inline in the runner script
rather than in a `build_*` function). Rather than report a cohort with its
strongest member missing, the loader was rebuilt from the same
`altstores.load_rec_momentum` with the same declared direction, and the run
repeated. Mechanical plumbing, disclosed; no spec, direction, window or bar
changed.

### Re-scan, explore 2004-2018, small

| signal | KO-half (primary) | KO-full (stress) | zero-cost bound | flat-25 guard | banked flat-25 |
|---|---|---|---|---|---|
| rec_mom | 1.42 | **0.20** | 2.64 | 0.48 | 0.48 ✓ |
| industry_mom | 1.63 | 1.22 | 2.03 | 1.39 | 1.39 ✓ |
| fscore_lite | **1.72** | 1.44 | 2.01 | 1.46 | 1.46 ✓ |
| cash_prof | 1.45 | 1.17 | 1.73 | 1.26 | 1.26 ✓ |
| re_me | 1.39 | 1.23 | 1.56 | 1.37 | 1.37 ✓ |

**The flat-25 regression guard reproduces every banked number exactly** — the
rebuilds are byte-identical and the re-measure is a pure cost substitution.

**GRADUATES: NONE.** `fscore_lite` (1.72) and `industry_mom` (1.63) clear the
1.5 bar under the primary arm and both fail the stress arm, which the
registration required them to clear as well. The both-arms rule was frozen
before the run and is what decides this trial. Confirm window NOT opened.

### The finding

The **zero-cost bound** is the deciding column and it equals `t_gross` by
construction — "could this graduate if trading were free?"

- **large/mid (round 10):** best rank-real reject reached 1.48 gross — *nothing
  could graduate even at zero cost*, which is why that cohort was empty.
- **small (here):** exactly one candidate, `rec_mom`, clears both legs for free
  (2.64 net / 3.32 IC). It is **the only signal in 160 candidates genuinely
  killed by trading costs alone** — and its executioner is 36.8%/month turnover,
  which no cost-model correction repairs.

So the paper's lead exhibit extends to the retail-accessible segment with a
named exception rather than a blanket claim: the shelf is not empty everywhere;
it contains one signal, and that signal trades itself to death.

**Bookkeeping:** the factory's small-segment cost premise was backwards for the
entire 159-candidate search, and correcting it moved **zero verdicts.** The
design defect was real and immaterial — both halves belong on the record.

Per the frozen kill clause: **small-cap cost-killed shelf CLOSED permanently;
no further cost-model appeals exist for either segment.** NEGATIVE_RESULTS §22.
