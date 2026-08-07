# PRE-REGISTRATION — EXT-NULL-1 / EXT-POWER-1

**Written 2026-08-07, BEFORE any OSAP signal was scanned through the ladder.**
Registered under CANON §6. No ladder statistic existed at write time.

Companion to `scratchpad/PREREG_REAL_NULL_1.md` (REAL-NULL-1). The two are
complements and neither is sufficient alone — see §6.

---

## 1. What is being measured, and why it is not another candidate hunt

The recalibrated ladder BRAIN-009 (`runs/GATE-M1/brain009_frozen.json`) has its
operating characteristics measured **entirely on panels and candidate
constructions authored by this project's own agents**. NEGATIVE_RESULTS §34's
meta-lesson — "the instrument that adjudicates everything else must itself be
adjudicated" — therefore still has one unmeasured leg: the *candidate
population* is ours too, as is the null.

Open Source Asset Pricing (Chen & Zimmermann 2022, *Critical Finance Review*
11(2), 207-264) supplies an independent population: 331 documented signals
built by an outside team from the published literature, of which

- **212 are `Predictor`** — the source paper found predictability;
- **114 are `Placebo`** — the literature considered the construction and found
  it NOT predictive;
- 5 are `Drop`.

Directions come from the OSAP documentation's `Sign` field, i.e. from the
original papers. **No direction is chosen by us**, before or after any scan.

## 2. The two arms

### EXT-NULL-1 (the FDR arm) — Placebos, explore AND confirm

Every OSAP `Placebo` available at firm level is scanned on
`data/crsp_panel_2002`, largemid, and put through the frozen BRAIN-009 ladder:

```
explore  2004-01-31..2018-12-31, t_ic >= 1.5, rank by t_ic, top_n = 5
confirm  2019-01-31..2024-12-31, t_ic >= 0.5 AND mean IC > 0
DSR/PBO  inert (threshold 0.0 / 1.0 as frozen)
```

Scan settings are `ScanConfig()` defaults, unmodified: top decile, 30% hold
band, 25 bps flat one-way, 100-name monthly floor.

### EXT-POWER-1 (the power arm) — Predictors, EXPLORE ONLY

Every OSAP `Predictor` available at firm level is scanned on the **explore
window only**. The confirm window is NOT read for predictors.

**Reason, stated in advance:** reading confirm on 212 external signals would
burn the held-out window on 212 potential future candidates. Placebos are
calibration instruments and are expendable; predictors are candidate stock and
are not.

## 3. Contamination bookkeeping (binding)

- Every OSAP **Placebo** scanned here is **permanently marked confirm-
  contaminated**. None may ever be adopted as an Aegis candidate on this
  evidence. A future adoption requires a new registration against a window this
  run did not read (2025+ forward).
- OSAP **Predictors** remain candidate-eligible: their confirm window is
  untouched by this run and must stay untouched until a separate registration
  opens it.
- Nothing in this trial graduates, seeds a lane, or increments the Aegis
  candidate count. The cumulative candidate count remains **179**.

## 4. Primary metrics and decision rules

**M1 — per-candidate explore false-pass rate.** `P(t_ic >= 1.5)` among
placebos. Compared against two existing estimates of the same quantity:
- DGP-A v6 generic null, `injected_edge`/largemid: **0.036** (n=250,
  `docs/family_null_tic_r1_frozen.json`)
- REAL-NULL-1, real panel, persistent random signals: **0.082**
  [0.0735, 0.0905] (K=4000)

*Decision rule:* if M1 exceeds 0.036 with non-overlapping binomial 95%
intervals, the simulator's generic null is declared **optimistic against an
external candidate population**, independently of REAL-NULL-1.

**M2 — per-candidate end-to-end adoption rate.** Fraction of placebos reaching
terminal state `adopt` with the cap disabled. Compared against the brief §3(a)
headline **FDR 1.6% [Wilson 0.4-5.7%]**, which `select.py:12` defines as
`P(adopt | alpha = 0)`.

*Decision rule:* if M2's 95% interval excludes 0.016, the published figure does
not transfer to an external candidate population and must be restated with that
scope.

**M3 — the replay geometry (the one that has never been measured).** Apply the
top-5 cap ONCE across the whole placebo batch, exactly as `ruleset.evaluate()`
does, and count adoptions. The calibration measured a 42-candidate batch in
which expected qualifiers were 4.54 against a cap of 5, so the cap never bound
(`held_out_tables`, `p_cap_crowded_out = 0.0`). The replay runs 179. This arm
measures what the cap does when it actually binds.

*Decision rule:* report the realised count of false adoptions and
`P(>=1 false adoption)` implied by the measured confirm-pass rate. No threshold
— this is an estimation arm, not a test.

**M4 — external power.** Fraction of OSAP Predictors clearing the explore bar,
by segment. This is a lower bound on power against real published effects,
uncontaminated by our injection-design choices.

## 5. Kill conditions

- **EXT-NULL-1 dies** if fewer than 40 placebos are available at firm level
  with >= 100 names/month of largemid coverage — below that the binomial
  interval is too wide to adjudicate anything, and the arm is reported as
  UNDERPOWERED rather than squeezed for a number.
- **The whole trial is VOID** if the guard in §7 fails.
- **M1's interpretation dies** if placebo explore t_ic is systematically
  *negative* rather than centred near zero: that would mean OSAP placebos are
  sign-flipped anti-signals rather than nulls, and they cannot serve as a null
  population.

## 6. The limitation that bounds every claim here — stated first, not last

**OSAP placebos are not provably null.** They are constructions the original
literature found non-predictive *in the original sample, specification and
universe*. Some may genuinely predict in our window, our segment, or our
construction class. So EXT-NULL-1 does **not** measure a false-positive rate in
the strict sense.

The two arms bracket the truth from opposite sides and that is the point:

| | provably zero-information? | realistic candidate? |
|---|---|---|
| REAL-NULL-1 (synthetic AR(1) signals) | **yes**, by construction | no — artificial |
| EXT-NULL-1 (OSAP placebos) | no | **yes** — real published constructions |

If both land materially above 0.036, the conclusion is robust to the weakness
of either. If they disagree, the disagreement is the finding and is reported as
such.

## 7. Guard — must pass before any ladder statistic is read

The scan harness must reproduce two banked real-panel numbers exactly, per the
NEGATIVE_RESULTS §28 discipline:

```
vol_12m_low / largemid : t_ic = 1.89   (data/factory/batch1_summary.csv)
price_level / largemid : t_ic = 2.12   (data/factory/batch1_summary.csv)
```

Both already reproduced exactly during REAL-NULL-1. The runner re-asserts them
and **aborts the whole run** on any mismatch. Additionally, `osap.download_long`
raises rather than scanning a network-truncated signal set.

## 8. Declared honest prior (scored afterwards, wrong or right)

1. M1 lands in **0.10-0.25** — above both 0.036 and REAL-NULL-1's 0.082,
   because placebos are economically motivated constructions correlated with
   size/volatility, not white noise.
2. M2 lands in **0.03-0.10**, i.e. 2-6x the published 1.6%.
3. M3 fills all 5 cap slots and adopts 1-3 placebos.
4. M4: **30-50%** of Predictors clear the explore bar in largemid — published
   effects should pass an explore gate more often than placebos, and if they do
   not, the ladder has no external discriminating power at all.
5. The single most likely way I am wrong: placebo firm-level availability is
   poor (the `BetaSquared` probe already failed), and the arm ends UNDERPOWERED
   at n < 40.
