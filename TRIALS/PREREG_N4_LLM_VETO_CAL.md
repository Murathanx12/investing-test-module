# PREREG — TRIAL-N4-LLM-VETO-CAL-1 (REGISTERED, NOT RUN — DATA NOT PRESENT)

**Registered:** 2026-08-10 · **Family:** N (extension) · **Stage:** Layer-3
calibration · **Status:** blocked on a build, not on a decision

## 1. The question

NIGHT-3 measured that the LLM does not earn a role in **stock selection** (M1
t 0.04, M2 t 0.93, 16,320 graded decisions). It did not test the role the
firewall was actually designed around: the LLM as a **scoreable risk officer**
that reads a filing and votes veto/keep, scored on Brier against outcomes that
arrived later.

That is the one LLM role never tested here, and it is the cheap, high-n one —
because the target is an *observable corporate event*, not a return.

## 2. Why this is not runnable tonight, stated plainly

The extension list called this cheap. It is not, and the reason is data:

| input | present? |
|---|---|
| CRSP performance delisting within 4 quarters | **yes** — `data/wrds_raw/crsp_dsedelist.parquet`, already used by G7, codes 400–591 |
| 10-K text, point-in-time, maskable | **no** — no local corpus; EDGAR full-text answers unauthenticated (NIGHT-6) but the retrieval is unbuilt |
| guidance cuts | **no** |
| restatements | **no** |

One of four. Building EDGAR retrieval, entity+date masking (CANON §13: masking
the name is not masking the date) and the outcome joins is a night's work, and
the extension list's own stop rule put N1, N2 and N5 ahead of it.

**A half-built calibration would produce a Brier score nobody could trust**,
which is precisely the failure this programme spent NIGHT-8 documenting.

## 3. Design, frozen now so the build has a target

- **Sample:** firm-years with a 10-K on file, drawn from the small segment the
  book actually trades, balanced across eras.
- **Masking:** entity **and** date. CANON §13 — NIGHT-1's 0/240 identification
  result measured company recall; LAP measures memory keyed on the date, and it
  survives entity masking (`FINCAD-LAP-NOLBERT`). An unmasked date makes this a
  memory test, not a reading test.
- **The ask, in the frozen firewall schema:** a `VetoProposal` with a
  `reason_code` from the closed vocabulary, a probability, and a `resolves_at`.
  Never prose, never a direction, never a weight — `apply_to_book()` raises.
- **Ground truth (start with the one we have):** a **CRSP performance delisting
  (codes 400–591) within four quarters** of the filing date. Guidance cuts and
  restatements are added only when their feeds exist.
- **Scoring:** Brier against that outcome, versus two baselines that must both
  be beaten — **climatology** (the base rate) and **a logistic model on the
  accounting variables already in the shelf**. Beating climatology alone proves
  only that the LLM knows the base rate.
- **Probabilities elicited in basis points**, per NIGHT-3's adopted finding that
  basis-point elicitation gave 5/5 coherence against 3/5 in prose.

## 4. Decision rule (frozen)

| outcome | consequence |
|---|---|
| Brier beats **both** baselines, and calibration is monotone across the probability range | Layer 3 has a measured calibration curve. It still earns **no** portfolio action — a scored veto proposal is a measurement, not a trade. |
| beats climatology but not the accounting logit | the LLM is reproducing what the numbers already say; **no new information**, and the extraction layer is where the effort should go |
| beats neither | REJECTED as a risk officer on this target, and the LLM programme narrows to extraction only |

**No result here may move a weight**, on any branch. That is the firewall, and
it is code (`aegis_brain/firewall/`, 32 tests).

## 5. Registered predictions

1. **It beats climatology.** Delisting risk is legible in a 10-K's going-concern
   and liquidity language.
2. **It does not beat the accounting logit.** Ohlson's OScore was built for
   exactly this target out of exactly these numbers, and N2 separately found the
   composite already avoids distressed names at ~15× better than chance.
3. **Calibration will be poor at the extremes** even if discrimination is decent
   — LLM probabilities cluster.

## 6. Ledger

Adds **0 branches** until it runs. Blocked on the EDGAR retrieval build, which
is a queue item and not a decision for Murat.
