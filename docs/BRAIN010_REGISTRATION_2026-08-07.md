# BRAIN-010 — pre-registered successor specification (2026-08-07)

**Registered while wave 3 is at rep ~420/1000 — no fresh-null results exist
or have been read.** The chain's automated aggregation will run regardless;
this registration predates any human or agent reading of wave-3 output.
Adopted from external review (GPT panel, 2026-08-07): a post-hoc discovery
must become a *named, frozen successor hypothesis*, not an "attended
decision" with unstated criteria.

## The specification (frozen, no free parameters)

BRAIN-010 = BRAIN-009 (frozen 2026-08-06, `runs/GATE-M1/brain009_frozen.json`)
with exactly two changes:

```
explore_segments: ("largemid",)  ->  ("largemid", "small")
explore_top_n:    5              ->  10
```

Everything else identical (explore t_ic >= 1.5 rank by t_ic; confirm
t_ic >= 0.5 + IC sign gate; prod book; DSR/PBO reported not gating).
`top_n = 10` is the first and only value tried; it is NOT to be swept or
tuned in this cycle. If BRAIN-010 is adopted, `top_n` becomes a registered
axis of the NEXT calibration family.

## Provenance and contamination, disclosed

- Discovered post-hoc on the same 250 panels that selected BRAIN-009
  (`RECAL1_RUN2_DESIGN_SWEEP_2026-08-07.md` §3). Measured there: largemid
  power 0.432 vs freeze 0.436, I3 0.424 vs 0.016, I4 0.544 vs 0.368,
  FDR 0.024; held-out odd half FDR 0.016 with largemid power 0.440.
- The 179-candidate preview that contaminated the explore *threshold* was
  largemid-only; no small-segment candidate statistics have been examined.
- The sigma-family artifact is ~40% stronger in small (null p95 4.2-4.5);
  the family-null veto (`KILL_AUDIT_2026-08-07.md` §4) therefore applies
  with the small-segment column to any BRAIN-010 replay verdict.

## Pre-registered decision rule (evidence rule; the swap itself stays attended)

On wave 3's 1000 fresh alpha=0 panels (reps 250-1249), evaluated once:

- **E1 (blind FDR):** BRAIN-010 point FDR <= 0.05 AND Wilson-95 upper
  <= 0.065. (n=1000 supports the tighter bound; run 1's 0.08 was set for
  n=125 halves.)
- **E2 (freeze comparison):** BRAIN-010 FDR minus BRAIN-009 FDR <= 0.02
  on the same 1000 reps (CRN-paired).
- **E3 (no power regression, already-measured):** held-out largemid power
  within Wilson overlap of the freeze (recorded PASS above; restated so
  the rule is complete in one place).

**If E1-E3 all pass:** BRAIN-010 is presented to Murat as the recommended
production ladder; the one-shot 179 replay runs under whichever ladder he
ratifies, with the family-null veto segment-matched either way.
**If any fails:** BRAIN-010 is recorded as refuted-on-nulls, BRAIN-009
stands, and the small segment remains closed until a properly powered
small design exists.

## Pre-registered prediction (same discipline as RECAL-1 §11)

BRAIN-010 fresh-null FDR lands in **[0.015, 0.035]** (the run-1/2 reads
straddle 0.016-0.024 and small adds ~one artifact-family's worth of
exposure that the top-10 cap partially absorbs). E1 and E2 both PASS.
If instead FDR > 0.05, the likely mechanism is sigma-family crowding of
the injected candidate's shelf — check the per-signal graduation mix
before concluding anything.

## What this registration does NOT do

- It does not fire the 179 replay.
- It does not reopen BRAIN-009's freeze record.
- It does not authorize any further ladder variants this cycle: BRAIN-010
  is the ONLY registered successor, and a failed E1-E3 does not license
  trying top_n = 8 next.
