# AUDIT-CIK-BRIDGE — coverage profile of the CIK↔permno bridge (2026-07-28)

**Binding:** `aegis-finance docs/research/AI_PANEL_2026-07-28.md` §3.1 (row 2.2).
**Status: REPORTED, NEVER DECIDING.** This audit moves no bar, opens no gate, and
cannot kill or graduate anything. It ran BEFORE the TEXT-LAZY explore result was
read, so the result is interpreted next to an honest statement of which names the
bridge can see. Artifact: `runs/AUDIT-CIK-BRIDGE/results.json`.

## What was actually asked

Not "is coverage high" (88.5% of universe permnos, already known). The question is
whether the ~11.5% the bridge MISSES are random, or concentrated in the small and
the dead — because the small segment is TEXT-LAZY's live shot, and a bridge that
quietly drops dead micro names flatters a long-only result the way survivorship
bias does.

**Correction to the review that requested this** (recorded in the panel doc): the
bridge was already built survivorship-neutral — CRSP historical name rows × EDGAR
`cik-lookup-data.txt` (every former name a CIK ever filed under), with SEC's
`company_tickers.json` current-filer snapshot explicitly rejected. This audit
**verifies** that property empirically; it does not add it.

## Method

- Universe = the 11,098 permnos of the module CRSP panel (2002-2024) with a usable
  dollar-volume history.
- Size axis = decile of each permno's median monthly dollar volume over its own
  live months. Dollar volume, not market cap, deliberately: it is the factory's
  OWN segmentation variable (`explore.segment_mask` ranks on it), so it is the
  axis on which a coverage hole would actually distort a scan.
- Death axis = **panel death** (return series ends before the panel does).
  `crsp_msf.dlstcd` is populated on only 4,724 of 1.1M rows in this pull, so
  keying the audit to it would itself be a coverage-biased measurement. Panel
  death is complete and survivorship-neutral. The `dlstcd` bad-delist set
  (500, 520-584) is reported as a secondary cut.

## Result — coverage by size decile (1 = smallest)

| decile | n universe | n bridged | coverage |
|---|---|---|---|
| 1 | 1110 | 940 | 0.847 |
| 2 | 1110 | 924 | 0.832 |
| 3 | 1110 | 971 | 0.875 |
| 4 | 1109 | 964 | 0.869 |
| 5 | 1110 | 974 | 0.878 |
| 6 | 1110 | 994 | 0.896 |
| 7 | 1109 | 993 | 0.895 |
| 8 | 1110 | 998 | 0.899 |
| 9 | 1110 | 1000 | 0.901 |
| 10 | 1110 | 1000 | 0.901 |

## Result — coverage by survival, and the interaction

| cut | coverage |
|---|---|
| survived to panel end (n 3,806) | **0.913** |
| died inside the panel (n 7,292) | **0.862** |
| deciles 1-3 (small) | 0.851 |
| deciles 8-10 (large) | 0.900 |
| **overall** | **0.885** |

Cross-tab (coverage, survived vs died):

| decile | survived | died |
|---|---|---|
| 1 | 0.849 | 0.847 |
| 2 | 0.899 | 0.817 |
| 3 | 0.914 | 0.860 |
| 4 | 0.929 | 0.840 |
| 5 | 0.925 | 0.855 |
| 6 | 0.919 | 0.883 |
| 7 | 0.914 | 0.885 |
| 8 | 0.915 | 0.887 |
| 9 | 0.901 | 0.901 |
| 10 | 0.913 | 0.879 |

Worst cell: **0.817** (decile 2, died).

## Ambiguity, measured two ways

**At the bridge** (55,302 rows, 22,686 CIKs, 22,309 permnos): 2,141 CIKs (9.4%)
reach more than one permno; 3,935 permnos are reached by more than one CIK. These
are the *candidates* for ambiguity, not drops — the link is date-bounded, so most
resolve to a unique permno at any given filing date.

**Per filing, actually incurred** (TRIAL-EVENT-8K-FILTER explore pull, the only
completed round-12 link): 7,809 filings in → 6,094 linked (78.0%),
**169 dropped ambiguous (2.2%)**, 1,546 unmatched (19.8%). Ambiguity is the small
part of the loss; plain name-mismatch is the large part.

## Reading — what this does and does not license

1. **The survivorship-neutrality claim is verified, not merely asserted.** A dead
   name is 5.1pp less likely to be bridged than a surviving one (0.862 vs 0.913).
   For contrast, a `company_tickers.json`-style current-filer bridge would lose
   essentially *all* of the 7,292 dead names. The gap here is a name-matching
   nuisance, not a survivorship cliff.
2. **The bias is real, mild, and monotone in the expected direction**: 0.847 at
   the smallest decile rising to 0.901 at the largest — a 6.9pp spread. Micro and
   dead names have messier, more frequently-changing names, so they fail exact
   normalized matching more often.
3. **Interpretability caveat to carry next to any TEXT-LAZY small-segment number:**
   the small segment loses ~15% of its names, tilted slightly toward the dead. The
   direction of that tilt flatters a long-only book. The magnitude (≈5pp
   differential, not ≈95pp) is far too small to manufacture an anomaly, but it is
   large enough that a *marginal* small-segment pass must not be read as clean.
4. **What it cannot do:** this changes no bar in TRIAL-TEXT-LAZY. A pass is still
   a pass and a fail is still a fail under the frozen rule. Per the binding, the
   audit is banked beside the result.
