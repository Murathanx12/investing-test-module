# ANALYST-IDENT-1 — POWER_FAILED, and what the power audit found instead

**Trial** `TRIALS/PREREG_ANALYST_IDENT_1.md`, registered 2026-08-11 (NIGHT-10),
corpse linter PASS vs 304 prior experiments.
**Receipts** `runs/ARENA1/ANALYST_IDENT_1/results.json`,
`power_audit_factory.json`.
**Accrues to the search denominator: 0.** Diagnostic of an UNRESOLVED verdict,
declared non-accruing before it ran.

---

## The verdict: POWER_FAILED

The trial asked whether the small-cap sign disagreement between A2
(`tgt_rev_breadth`) and A3 (`tgt_rev_3m`) is caused by **coverage churn** — an
analyst initiating at a high target moving the consensus mean with nobody
having revised anything, a contamination that scales as 1/`numest` and so bites
hardest where coverage is thin.

Two gates ran first, as registered. The first passed, the second did not.

| gate | result | number |
|---|---|---|
| DATA_QUALITY | **PASS** | `numest` is a clean integer count (non-integer share 0.000), and its 3-month change has real mass at zero (52.2%), so "same count" can be read as "same analysts" |
| POWER | **FAIL** | churn-free subsample retains **52.2%** of name-months over **250** months — both floors cleared — but the realised MDE is **10.8 %/yr** against a registered target of 4.0 and a disputed gap of **6.8** |

Per the registered decision rule, **no arm was run and no number is quoted.**
The small segment stays UNRESOLVED.

The first implementation of the POWER gate used an *assumed* monthly dispersion
of 6% rather than the realised dispersion the pre-registration specified. It
also returned FAIL, at 12.8 %/yr. It was replaced with the registered method
before the verdict was taken, because a gate that is stricter than its own
registration manufactures the verdict it reports.

---

## The power audit — the finding this trial actually produced

POWER_FAILED raised a question about the **parent**, not the successor: if a
top-50 EW small-cap book over 250 months cannot resolve 6.8 points, could
ANALYST-IBES-1 resolve any of the effects it published?

`scripts/audit_analyst_power2.py` rebuilds each of the parent's ten arms through
`pf.run.Factory` with the parent's own specs, then reads the standard error of
each arm's monthly excess series.

**Instrument fidelity first.** Eight of ten arms reproduce their published gross
excess to **0.00 points**. The two `tgt_upside` arms do not (gaps 8.13 and 2.12),
so they are marked unfaithful and **their power readings are withheld** rather
than quoted. An earlier hand-rolled version of this audit reproduced only some
arms and was **withdrawn entirely**; it is kept in the repo
(`scripts/audit_analyst_power.py`) as the receipt for why the Factory version
exists. Its headline number — a paired t of 0.03 — was computed on a different
pair of books than the parent's and must not be cited.

### Was the parent powered to see its own numbers?

| | count |
|---|---:|
| arms measured | 10 |
| arms reproducing their published number (gap ≤ 1.5 pts) | 8 |
| arms **significant at 5%** | **1** |
| arms **above their own 80%-power MDE** | **0** |

Not one arm in ANALYST-IBES-1 reported an effect large enough for that design to
have found it reliably. This does not make the parent's numbers wrong. It means
the trial was operating in the region where significant findings systematically
overstate their effects, and where a null and a real effect look alike.

### The disagreement, tested directly

The parent moved the small segment to UNRESOLVED because registered prediction 5
("A2 and A3 agree in sign") was **REFUTED**: A2 printed +6.05 %/yr gross and A3
printed −0.73 %/yr, on the same names in the same months.

That adjudication compared two point estimates. It never tested the difference.
Tested on the **paired monthly excess series** — which handles the correlation
between the two books exactly, rather than assuming it away — with both arms
reproducing at gap 0.00:

| quantity | value |
|---|---:|
| paired months | 249 |
| correlation of the two monthly series | **0.578** |
| mean difference (A2 − A3) | **+3.70 %/yr** |
| standard error | **3.60 %/yr** |
| **t** | **1.03** |
| significant at 5% | **no** |

**Two estimates whose difference is one standard error apart are not in
contradiction.** They are what two noisy draws of one quantity look like. The
"disagreement" that produced the UNRESOLVED verdict is not distinguishable from
zero, and the churn hypothesis this trial was built to test may have had nothing
to explain.

---

## What changes

1. **The small segment stays UNRESOLVED — for a different, better-supported
   reason.** Not "two constructions contradict each other", but "the trial could
   not resolve effects of the size it was looking for". The distinction matters:
   the first invites a search for a mechanism, and the second says the
   instrument needs more power before any mechanism question is worth asking.
2. **`analyst_target_revision` stays HYPOTHESIS.** `allowed_in_pm` stays false.
   Nothing here graduates anything; the pre-registration forbade it in advance
   regardless of outcome.
3. **The churn hypothesis is neither confirmed nor rejected.** It was never
   tested, because the gate stopped the trial. It remains open, and it is not
   worth reopening on this instrument at this power.

## Standing amendment proposed (for CANON)

> **A registered prediction that two constructions AGREE is a claim about their
> DIFFERENCE, and must be adjudicated by testing that difference with its own
> standard error — never by comparing two point estimates and reading their
> signs.**

ANALYST-IBES-1 is the type specimen: prediction 5 was recorded as REFUTED on a
sign comparison, and the difference it was really about carries t = 1.03. Two
underpowered estimates will disagree in sign routinely, and a decision rule that
treats that as refutation will manufacture "unidentified object" verdicts out of
noise for as long as it is left in place.

A second, narrower amendment follows from the audit table:

> **Every trial reports, beside each arm, the arm's own 80%-power MDE.** An
> effect below it is reported as "not reliably detectable by this design", never
> as evidence for or against a mechanism.

## What would overturn this

* The paired test uses **gross arithmetic** monthly excess; the parent's
  headline is a **geometric** CAGR difference. The two are not the same
  functional and a large enough skew could separate them. The t on the paired
  series is nonetheless the correct significance test for the difference.
* The two unfaithful `tgt_upside` arms mean the levels result — the programme's
  third independent confirmation that raw implied upside is negative — was **not
  re-measured here** and is untouched by this document. Its registry grade
  (PERVERSE/CLOSED) rests on the earlier instruments and is unaffected.
* 249 months is one sample. A different window would give a different t. That is
  the point of the finding, not an objection to it.
