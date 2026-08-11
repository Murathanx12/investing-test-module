# PREREG — HERESY-1: were the kills adequately powered?

**Registered** 2026-08-11, NIGHT-10, before any statistic in §4 was computed.
**Family** methodology. **Data** CRSP spine + IBES panel already on disk.
**Status** RESEARCH-ONLY, FOREVER. Nothing this trial produces may enter
production, seed a shadow book, or change any `allowed_in_pm` flag, whatever it
finds. That is a property of the lab, not a consequence of the result.

---

## 1. The gap this exists to close

ARENA-1 recorded its own honest limit: the genome pool is generated **from the
signal registry**, so a mechanism the registry has closed has no genome, and the
search can confirm what the lab believes but can never overturn it. The planted
+8 %/yr analyst effect was undetectable by construction.

The obvious response — re-run the dead strategies and see if any wins — is the
wrong one. It is re-litigation with extra steps, it mines the graveyard for a
lucky draw, and every corpse that "wins" would be a best-of-N with no
denominator.

So HERESY-1 asks the prior question, which is a **measurement** question and has
a determinate answer:

> **For each CLOSED mechanism, was the design that killed it capable of
> detecting the effect it was looking for?**

A kill from an adequately-powered test is evidence of absence. A kill from an
underpowered test is absence of evidence, and the two have been recorded
identically in this programme's graveyard for 195 experiments.

This is not a hypothesis about markets. It is an audit of instruments, and its
outcome cannot make any strategy tradeable.

## 2. Why this is not re-litigation

The re-litigation ban forbids a closed mechanism re-entering under a new name to
be traded. This trial:

* proposes no trade, no lane, no weight, and no registry change;
* computes **no** best-of-N winner and ranks nothing against anything;
* reports, per closed signal, a standard error and a detection threshold —
  quantities that are properties of the DESIGN, not of the mechanism.

The precedent is ANALYST-IDENT-1's power audit (2026-08-11), which found that
**0 of 10** ANALYST-IBES-1 arms reported an effect above their own 80%-power
MDE, and that the "sign disagreement" behind a published UNRESOLVED verdict
carried t = 1.03. That audit changed no grade and traded nothing. This one
generalises it to the graveyard.

## 3. Power check on the audit itself

The audit needs enough months to estimate a standard error at all. Any closed
signal whose panel implementation yields fewer than **60 priced months** or
fewer than **20 names/month** is reported as NOT_AUDITABLE and excluded — its
kill is left exactly as it stands, neither defended nor questioned.

## 4. Pre-registered predictions

For each CLOSED signal with a panel implementation, run the forbidden
configuration — that signal LEADING an EW top-50 book, the configuration the
registry forbids — through the same `pf.run.Factory` the kills were issued from.
Record effect, SE, t, and the 80%-power MDE.

* **H1 — the control reproduces its kill.** `analyst_target_upside_xs` must come
  back NEGATIVE. If a mechanism this programme has killed on three independent
  instruments comes back positive here, the harness is broken and **every other
  number in this trial is void**. This arm runs first.
* **H2 — most kills are underpowered.** Registered prediction: **more than half**
  of auditable closed signals show |effect| below their own 80%-power MDE.
* **H3 — the underpowered kills are not concentrated in one family.** If they
  are, the finding is about that family's data, not about the programme's
  method.

## 5. Decision rule, fixed now

| outcome | condition | consequence |
|---|---|---|
| **VOID** | H1 fails (the control comes back positive) | Nothing is reported. The harness is the finding. |
| **KILLS_UNDERPOWERED** | H1 holds and H2 holds | The graveyard is re-annotated: each affected corpse is marked `kill_power: INADEQUATE` with its MDE. **No corpse is reopened by this alone.** A reopening requires its own pre-registration, with the corpse as a control arm and an instrument whose MDE clears the effect being sought. |
| **KILLS_SOUND** | H1 holds and H2 fails | The graveyard stands as recorded and the closed list is better supported than before. A genuinely useful null. |

**In no branch does any signal become tradeable, permitted, or shadow-seeded.**

A heresy that unexpectedly clears its own false-discovery bar under a materially
different valid design is logged as an **INVESTIGATION**, never a promotion, and
carries its own corpse as a control arm if anyone later pre-registers it.

## 6. What would make this trial wrong

* **The MDE is design-relative.** A signal killed at top-50 EW monthly might be
  detectable at top-10 quarterly. This audit measures the design that ISSUED the
  kill, which is the right target for "was the kill safe", and says nothing
  about designs nobody ran.
* **An 80%-power MDE is a convention.** A signal below it is not proven absent
  and not proven present; that ambiguity is exactly the finding.
* **Some kills rested on more than one instrument.** `analyst_target_upside_xs`
  has three. A single underpowered arm does not overturn a mechanism killed
  three ways, and the report must show the count of independent instruments
  beside every power verdict rather than treating each corpse as one test.
* Costs are irrelevant here and are not quoted: an underpowered GROSS test
  cannot be rescued by a cost model, and CANON §16's denominator rule does not
  apply because nothing is being compared to a winner.
