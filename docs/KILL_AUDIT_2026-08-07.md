# KILL AUDIT — what the recalibration does and does not overturn

Written 2026-08-07 evening, wave 3 still running. Prompted by Murat's
question after the run-2 design sweep: *"does this mean we falsely killed
theories? Many findings we claimed false might have been true."*

Method: classification of every recorded kill **by mechanism**, from the
ledger (NEGATIVE_RESULTS.md §1–§33, TRIALS/, CANON) and from the simulator
bank — **no real-candidate data was re-scored**. Re-scoring is the one-shot
replay, which stays unfired until the ladder question closes.

## 0. The short answer

**No — with one big exception and one new warning.**

- Kills that carried their own receipts (placebo gates that fired, sign
  reversals at confirm, zero-cost bounds, direct negative measurements)
  **stand**. Recalibrating thresholds does not un-fire a control.
- Kills whose *only* evidence was "failed the BRAIN-008 explore threshold"
  are now **uninformative** — the gate had ~0% power, so failing it never
  distinguished true from false. These are not "probably true" — they are
  *unmeasured*, and the one-shot replay adjudicates them.
- The exception: the **small segment was structurally ineligible** for the
  entire 179-candidate search (I3 result: a real small-cap edge adopts at
  exactly the null rate, 0.016). Nothing small was ever killed — it was
  never seen. §22 closed the small *cost* question; it did not open the
  graduation door. That is a genuine class of potentially-live candidates.
- The new warning (§3 below): the recalibrated IC-only ladder has a
  **~70% false-pass rate on σ/liquidity-family candidates**, measured on
  the certified nulls. Any naive replay would resurrect artifacts.

## 1. Classification of the recorded kills

### A. Killed by their own controls / receipts — STAND (recalibration cannot touch these)

| kill | receipt |
|---|---|
| Kirk / ABIO 164–166 (§26) | residualisation subtracted information; io_level t_ic 11.29 with gross t +0.02 — rank without money, measured on real data |
| option cohort 167–173 (§27) | all seven mechanism classes closed; third residualisation receipt |
| 13DG harvest (§30, §31) | killed twice by its own random-date placebo gate |
| COND-VT (§21) | confirm REJECT — 2020 crash outran the signal, direct measurement |
| conc_low (§13, TRIAL-BRAIN-010) | passed old explore *double-legged*, died at confirm on an IC sign flip (t −7.4). Not threshold starvation |
| 8-K filter (§20) | "drift" was selection — the control arm was the test |
| price targets (§17) | anti-signal, wrong sign — worse than dead |
| FDA drift (§11, §16) | dead at monthly AND daily resolution |
| supplier baskets (§12) | no holding period works, fully adjudicated |
| residual momentum (§23) | fitted leg carried the IC (t 2.80 of 2.84) |
| LLM alpha (§19), crash timing (§2, §33), LPPLS (§3) | direct negative measurements / external receipts |

### B. Killed only by the uncalibrated explore gate — UNINFORMATIVE, replay adjudicates

The bulk of the ~148 banked explore rejections that never reached a
dedicated instrument. Under BRAIN-008 the measured probability of adopting
even a true α=0.4 edge was **0.000** — so for these candidates, rejection
carries almost no information about truth. The preview (largemid only,
`scratchpad/inv179.py`): 2 pass old explore, 21 pass BRAIN-009 explore.
**"21 pass" does not mean "21 were real"** — see §3.

### C. Never seen at all — the small segment

I3 measurement: P(adopt | real small-only edge) = P(adopt | pure noise) =
0.016, at both α=0.4 and α=0.6. The factory's answer to every small-cap
candidate was decided by the segment filter, not the data. §22's five-member
small cohort (rec_mom, industry_mom, fscore_lite, cash_prof, re_me) is the
known shortlist; per §22 exactly one (rec_mom) is genuinely cost-killed by
its own 37%/mo turnover. The others were never adjudicated by a powered
gate. **This is the most credible pool of falsely-unexamined candidates in
the project** — pending the σ-family veto below, which bites hardest in
small.

### D. Underpowered-but-received: cost-killed shelf

INSTR-COST-REMEASURE-REJECTS (round 10) re-measured the largemid cost-killed
shelf under the corrected KO ruler and found it EMPTY — and the decisive
column was the **zero-cost bound**: the best rank-real reject reached gross
t 1.48 < 1.5, so nothing there could graduate *even if trading were free*.
That defense is a money-leg statement and survives the recalibration
unchanged. What the recalibration adds: candidates with high t_ic and dead
gross would now graduate on IC alone — and §32 + §3 below say that class is
exactly where the artifact lives. The cost-killed shelf conclusion stands.

## 2. So were we "falsely killing everything and adopting nothing"?

Precisely: the factory was **underpowered, not wrongly adjudicated**. The
0-for-179 adoption record is now explained by measurement (0% power even on
true α=0.6 constant edges) — the absence of adoptions was inevitable and
says nothing about the search pool. But the individual corpses in class A
died with receipts that hold regardless of thresholds. The candidates whose
status actually changes are class B (unmeasured, replay decides) and class
C (never examined).

Other projects' findings claimed false (crash timing §2/§33, LPPLS §3,
EODHD §8, momentum backtests §9/§10): all class A — direct measurements,
not gate verdicts. **None of them are reopened by this.**

## 3. NEW: the family-null veto — why the replay cannot be a naive re-threshold

Measured on the 250 certified v6 null panels (a0.0/base), per-signal explore
t_ic distributions (`runs/GATE-M1/family_null_tic_r1.json`):

| signal (largemid, NULL panels) | mean t_ic | P(t_ic ≥ 1.5) | p95 | small p95 |
|---|---|---|---|---|
| vol_6m_low | **1.91** | **0.72** | 2.96 | 4.21 |
| price_level | 1.85 | 0.70 | 3.01 | 4.54 |
| max_ret_low | 1.81 | 0.69 | 3.09 | 4.18 |
| high_52wk_prox | 1.79 | 0.66 | 2.99 | 4.28 |
| amihud_3m | −1.78 | (sign −) | | |
| … generic signals … | ~0 | 0.02–0.13 | 1.2–1.6 | |
| injected_edge (the FDR reference) | −0.08 | 0.036 | 1.33 | 1.42 |

Two consequences, stated plainly:

1. **The measured FDR (1.6%) is per generic candidate.** `evaluate()`
   follows the injected signal only; σ-family signals sit in the ranking
   pool. For a candidate whose construction is σ/liquidity-correlated, the
   explore gate false-passes **~70%** of pure noise, not 1.6%. This is §32
   (recorded 2026-08-04, *before* the freeze) re-derived quantitatively:
   IC-only graduation is structurally unsafe for that family; the old
   ladder was protected by the t_net AND-leg, which the frozen BRAIN-009
   dropped.
2. **The artifact is ~40% stronger in the small segment** (p95 ≈ 4.2–4.5
   vs ≈ 3.0), precisely where class C hopes live. A small-cap resurrection
   wave under an IC-only gate would be dominated by the artifact.

Note this cuts against my own earlier framing in-session: I pointed at
`inst_persist_low` (t_ic 3.35, t_net −3.49) as "the failure mode the
recalibration was built for." The ledger's competing explanation (§26 for
the ownership family, §28 for high-IC/negative-net generally) is that this
shape is **rank-without-money / short-leg information**, and the family-null
result makes the naive reading unsafe. The replay decides it; I should not
have presumed.

## 4. Pre-registered replay protocol amendment (binding before any replay)

The one-shot replay of the 179 under frozen BRAIN-009 gains one veto and
two receipts, all derived from evidence that predates the freeze (§32,
§28, §22) plus the bank:

1. **Family-null veto (binding):** each candidate maps to its nearest
   simulator family by construction (mechanical rule: what the signal is
   computed from — vol/downside → vol family; price/52wk → price_level
   family; liquidity → amihud; momentum-window → mom; else → generic
   `injected_edge`). Mapping is fixed by formula inspection BEFORE looking
   at the candidate's statistics. Explore pass requires
   **t_ic ≥ max(1.5, family null p95)** from
   `family_null_tic_r1.json`, segment-matched.
2. **Money-leg receipt (reported, not gating):** gross t and, where
   computable, the §28 short-leg share, printed next to every survivor.
3. **Small-segment candidates** (class C) are adjudicated with the small
   p95 column — the higher bar is the point.

The simulator cannot certify the veto's benefit (its injected edges couple
IC to alpha; its nulls lack an injected artifact *candidate*), so the
defense is the ledger receipts, disclosed as such.

## 5. What this does NOT license

- No re-running of closed families (class A stays closed; CANON §"closed
  rabbit holes" applies).
- No small-segment data examination before the replay fires (the small
  half of `data/factory/batch*_summary.csv` remains unread; checkable).
- No treating "passes BRAIN-009 explore" as "was true" — survivors of the
  replay enter confirm like any candidate, and the 24-month no-skill-claims
  clock (CANON §1) is untouched.

## 6. Amendment 2 (2026-08-07 evening, post external review — before any replay)

Adopted from the verified external-review panel (synthesis:
`aegis-finance/docs/AI_REVIEWS_SYNTHESIS_2026-08-07.md`), binding on the
one-shot replay in addition to §4:

1. **Resurrection status taxonomy.** Every one of the 179 gets exactly one:
   `DEAD` (receipt survives) · `UNMEASURED` (threshold-only kill) ·
   `UNDERPOWERED` (tested where simulator power is known low, e.g. small) ·
   `MIS-SPECIFIED` (test did not match the registered mechanism) ·
   `TEMPORALLY-MISMATCHED` (registered as a decaying/short-horizon effect
   but adjudicated on a confirm window past its half-life — "does the
   effect exist" was conflated with "does it still exist in 2019-24").
   The last category is new (GPT §14) and genuinely changes verdicts: a
   decay-registered candidate killed at confirm may be a real effect asked
   the wrong temporal question.
2. **Frozen family ontology file.** Before the replay reads any statistic,
   `TRIALS/family_ontology.json` is written mapping every candidate ->
   simulator family BY CONSTRUCTION (what the signal is computed from),
   deterministic, no per-candidate discretion afterward. Two null levels
   for now (generic + sigma-family, segment-matched); deeper hierarchies
   need more simulator signals and are future work.
3. **Resurrection tax.** First adjudication: normal bar. First
   resurrection of a previously-killed candidate: must clear the family
   bar AND carry a money-leg receipt. Any second resurrection: requires a
   new pre-registered trial with its own control. Repeated reopening is
   p-hacking with version control; the tax prices it.
4. **Independent recomputation.** The replay's gate verdicts are
   recomputed by a second, independently written implementation from the
   same frozen CSVs; verdicts ship only where both agree (disagreements
   are defects to resolve, not choices).
5. **Conditional language.** All FDR/power claims are stated as
   "under DGP-A v6 and the registered selection rule" — properties of
   simulator × pipeline × rule, not of markets. The sizing ladder is
   "evidence-conditioned sizing", not "posterior sizing".
