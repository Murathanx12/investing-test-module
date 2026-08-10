# Graveyard census — what actually happened to the ideas

**T4c, NIGHT-5.** Re-classification of banked numbers under verdict taxonomy v2
(`aegis_brain/verdicts.py`, 23 unit tests). **No book was re-run. Nothing is
promoted. No new evidence was created.** Artifact:
`runs/PF5/T4_GRAVEYARD_TRIAGE.json`, rows in `T4_graveyard_rows.csv`.

## The denominator, stated rather than rounded

The programme has quoted **"179 candidates"**. The batch summaries on disk carry
**148 signal × segment rows over 74 unique signals**; the larger figure includes
reruns and variants never banked as summary rows. Both numbers are printed here
rather than reconciled silently. The census below is over the 148.

## The census

| State | Rows | Share |
|---|---:|---:|
| **REJECTED** — adequately powered, bar excluded | **69** | 47 % |
| **POWER_FAILED** — could not have seen the bar | 31 | 21 % |
| **IMPLEMENTATION_FAILED** — information present, money absent | 29 | 20 % |
| **DATA_FAILED** — never produced a usable number | 14 | 9 % |
| **UNRESOLVED** — powered, interval straddles the bar | 5 | 3 % |

**Killed by the idea: 69. Killed by the experiment: 74.** The split is almost
exactly even, and the old ledger recorded all 143 of them the same way.

## The three numbers that carry the finding

* **Median MDE = 3.74 %/yr.** The execution standard's bar is **+3 %/yr** net
  excess. **66 % of the scans could not have detected the effect size the
  standard requires**, whatever the signal did. RECAL-1 reached the same
  conclusion from the other direction in 2026-08-07: the graduation rule had a
  *measured 0 % probability* of adopting even a true α = 0.6 edge. The 0-for-179
  record was substantially a property of the screen.
* **Median point estimate = −1.40 %/yr.** This is the half of the answer that
  does *not* flatter us. The mass of the distribution is genuinely negative, so
  most of these ideas really are bad; a true +3 %/yr signal would have to sit
  4.4 SD above the median row. "The experiment was broken" does not rescue the
  central tendency.
* **14 rows never ran at all** — `max_dret_low_D`, `ivol_low_D`, `amihud_D`,
  `tgt_upside`, `insider_si`, `defensive`, `insider_cluster` (largemid) at
  0 months, `insider_cluster` (small) at 4. They were carried in the
  "0-for-179" record as though they had been tested. **They are not evidence of
  anything** and the taxonomy now refuses to let them be counted as tests of
  their ideas.

## Two premises checked before use — one of them fails

The night's brief expected the two known systematic biases to have penalised
every small/illiquid candidate that ever entered the harness. Checked, because a
triage built on an unchecked premise repeats the error it exists to find:

* **The never-indexed $200k dollar-volume floor did NOT touch this search.** The
  scan ran on the 2002-2024 panel, where the small segment carries ~1,950
  eligible names throughout. The floor is a *63-year-panel* problem: there it
  deletes 1963-1982 entirely (median eligible small names — 1960s: **0**,
  1970s: **0**, 1980s: 763, 1990s onward: ~1,950). The bias is real, severe, and
  irrelevant here.
* **Era-appropriate costs apply only weakly.** The scan window is entirely
  post-decimalisation, so the mechanical tick floor is ~1 ¢. The live warning is
  the scan document's own: flat 25 bps *understates* small-cap costs, so the
  small-segment rows are flattered, not penalised.

Net: of the two biases nominated at home, one does not apply to the graveyard
and the other cuts the opposite way. What killed the search was **power and
construction**, not those two biases.

## Resurrection shortlist (capped at 5)

Eligibility: killed by the experiment rather than the idea, not contaminated,
and carrying positive cross-sectional information (rank-IC t ≥ 3.0) — the
statistic the replay night established is the adequately powered one.

| Signal | Segment | State | IC t | net t | turnover | Reading |
|---|---|---|---:|---:|---:|---|
| `cash_prof` | small | IMPLEMENTATION_FAILED | 7.90 | 1.26 | 0.095 | profitability family |
| `conc_low` | small | POWER_FAILED | 7.41 | 2.31 | 0.082 | **the only genuinely distinct hypothesis** |
| `fscore_lite` | small | IMPLEMENTATION_FAILED | 6.63 | 1.46 | 0.129 | quality family |
| `price_level` | small | IMPLEMENTATION_FAILED | 6.63 | 0.37 | 0.090 | size/junk proxy |
| `oper_prof` | small | IMPLEMENTATION_FAILED | 6.62 | 0.77 | 0.091 | profitability family |

**The shortlist mostly re-discovers what we already ship.** `cash_prof`,
`oper_prof` and `fscore_lite` are the profitability/quality family — the same
family as `PF-PROF-COMPOSITE-150`, whose constituents are GP, OperProfRD and
CBOperProf. `price_level` is a size/junk proxy that the small segment already
tilts toward. That is not a disappointment, it is a corroboration from an
independent direction: the one thing this programme has found survives being
re-derived by a rule that was written to look for something else.

**Only `conc_low` (low customer concentration, the Dhaliwal relationship-risk
side) is a genuinely distinct hypothesis**, and it is the one entry whose money
leg actually showed up (net t 2.31) while still failing the screen. It is
therefore the single highest-value resurrection.

**Each resurrection is a NEW pre-registered trial with its own decision rule,
never a rescue of the old number, and the old test stays in the denominator
forever.** None is registered tonight; registering five trials at the end of a
night is how a shortlist becomes a fishing licence.

## What this changes about how the factory reports

The old ledger's `FAILED` was doing five jobs. Under v2 the states are
distinguishable *and machine-enforced*: a report whose statistics say
`UNRESOLVED` can no longer print `REJECT`, and a `FACTOR_EXPLAINED` result can no
longer be written as "no edge". That guard is 23 unit tests, several of which are
sentences this project actually wrote and should not have.
