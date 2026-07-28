# Round-12 bindings — the operative checklist for the rest of this round

Source of truth for dispositions is the aegis-finance panel docs; this file is the
**executable** restatement so nothing is lost across a long pull or a context
reset. Binding text wins over anything in a run script's comments.

- `docs/research/AI_PANEL_2026-07-27F.md` — sweep adjudication, both registrations
- `docs/research/AI_PANEL_2026-07-28.md` §3 — mid-round bindings (morning)
- `docs/research/AI_PANEL_2026-07-28B.md` §3 — mid-round bindings (evening)

## Open — must execute this round

| # | Binding | Source | Status |
|---|---|---|---|
| B1 | CIK-bridge coverage audit runs BEFORE the TEXT-LAZY explore result is read; banked next to it, never deciding | 28 §3.1 | **DONE** `64f86b4` → `docs/AUDIT_CIK_BRIDGE_2026-07-28.md` |
| B2 | The bridge-audit caveat attaches to a **PASS, not a REJECT** | 28B §3.1 | **PENDING** — applies at interpretation |
| B3 | Freeze at the converged count on the **existing** ceiling measurement; no re-registration below ~196; state it explicitly in the freeze note | 28 §3.2 / 28B | **PENDING** — applies at the freeze |
| B4 | R12-B SignalDoc robustness arm = **unified batch of all 13** matched signals under CZ's own construction, one shot; no decay-ranked subsetting | 28B §3.2 | **PENDING** — applies at registration |

### B2 — why the asymmetry (do not "balance" it)

The audit found the unbridged names tilt toward the **dead** (0.862 coverage vs
0.913 for survivors) and toward the **small** (0.847 D1 → 0.901 D10). Dropping
dead names can only *flatter* a long-only book. Therefore:

- **A marginal explore PASS carries the caveat verbatim** — it may be partly an
  artifact of not seeing the names that died.
- **A REJECT needs no discount.** The bias runs against the rejection, so a
  signal that fails despite a favourable coverage tilt has failed harder, not
  more ambiguously. Applying a symmetric "data quality" hedge to a null would be
  manufacturing doubt in the direction the evidence does not support.

### B3 — the freeze-note sentence (do not paraphrase away the reasoning)

The freeze note must state: the search **converged** at the round-12 cumulative
count, which is BELOW the ~196 threshold round 5 set as the next legitimate
ceiling re-check; the existing INSTR-OVERFIT-CEILING zero-skill envelope
(E[max t] ≈ 3.6–4.0) remains the operative alarm; stopping before the alarm
threshold requires no new registration — and **inventing filler hypotheses to
reach 196 would be the exact self-deception the ceiling exists to measure.**

### B4 — why unified, not decay-ranked

Subsetting the 13 by decay would condition the robustness test on the very
outcome it is testing (−0.544 *is* the decay ranking), i.e. post-hoc selection
inside the arm designed to detect construction artifacts. Per-signal construction
forensics are welcome **afterwards as reported diagnostics, never deciding.**
Note for the runner: the house harness is **monthly**, not daily.

## Standing — bind future registrations, no action this round

| # | Binding | Source |
|---|---|---|
| S1 | Any 8-K/event successor needs a **matched non-filer control** (nearest-neighbour on sector, size, prior-12m return) **plus** eligibility frozen at a pre-event date. One pre-registered hypothesis, never a sequence scan | 28 §3.3 (rows 2.1, 1.6) |
| S2 | Evidence-weight schema (forward 10 / confirm 8 / explore 3 / literature 2 / LLM 0.5) lands in the **REGIME-ANALOG phase-2 spec**, not as a trial. Reporting convention only — nothing allocates off it | 28 §3.4 (row 1.4) |
| S3 | Exits / SELL signals are a first-class family **inside the same registry and the same cumulative deflation count**. No parallel ledger — a separate registry would reset the multiple-testing clock that backs every claim in the paper | 28B §3.3 |
| S4 | **Capital-flows family** (ETF flows, passive share, dealer positioning, issuance, mechanical vol-target/CTA flows) qualifies for the freeze's "genuinely new information source" exemption. Hard gate: a **PIT-data feasibility audit per sub-hypothesis** before anything reaches `prior_check`. At most 1–2 deflated registrations, post-freeze. Known terrain: dealer gamma vendor-locked; CFTC COT free+PIT but futures-only; 13F follower play already closed; buybacks already on disk | 28B |
| S5 | TEXT-LAZY is **one-sided** — `text_cos`(+)/`text_jac`(+), long non-changers. Divergence-as-distress is not an arm; it exists only as the pre-declared bounded FILTER fallback (changer cohort t ≤ −2.0 in the same explore run → permits a NEW successor registration) | 28 §1 row 2.4 |

## Unchanged house law (restated because a long round erodes it)

`scripts/prior_check.py` before ANY new registration · pre-register before ANY
data touch · one-shot runs, results final · explore 2004-2018 / confirm 2019-2024
wall · re-litigation ban (cost-killed shelf, PEAD, Cop-vs-gp, tgt, conc,
LLM-alpha all closed) · house never shorts · module venv
`.venv\Scripts\python.exe` · `data/` gitignored · EXPLORE_END mutation for
confirm · **lane seeds are attended — sessions never set seed flags.**
