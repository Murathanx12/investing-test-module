# PREREG — TRIAL-TEXT-SEMDIFF-1 (REGISTERED, **NOT RUN**)

**Registered:** 2026-08-10 · **Family:** TEXT · **Stage:** design + power check only
**Status: DOES NOT RUN.** The power check below says the money version of this test
cannot see its own prior. Registering it and stopping is the point of the gate.

---

## 1. The idea

Cohen, Malloy & Nguyen, *Lazy Prices* (JF 75(3) 2020): year-over-year **changes**
to 10-K/10-Q language predict returns; a portfolio short "changers" and long
"nonchangers" earns **up to 188 bps/month** in alpha over 1995–2014. The proposed
upgrade: replace their cosine-similarity distance with an **LLM semantic diff** —
distinguishing "reworded boilerplate" from "quietly deleted the customer-
concentration disclosure." The EDGAR full-text feed was confirmed open and
unauthenticated in NIGHT-6, so the data is free and already reachable.

## 2. The prior, derived in the open

The verified headline (`runs/NIGHT7/VERIFIED_CITATIONS.md` item 1) is **188 bps/
month**. Three haircuts are mandatory before it can be our prior, and each is
stated so the arithmetic can be attacked:

| step | factor | running estimate |
|---|---|---|
| published headline (long **short**, 1995–2014) | — | 188 bps/mo |
| it is the **"up to"** figure, not a central estimate | (kept, as a ceiling) | 188 bps/mo |
| **long-leg only** — a long-only book cannot hold the short leg | ×0.30 (generous: our own §28 measurement found 88–99.9% of a comparable spread lived in the **short** leg, which implies ×0.01–0.12) | 56 bps/mo ≈ **6.8%/yr** |
| **McLean-Pontiff post-publication decay** | ×0.5 | **≈ 3.4%/yr** |

**Registered prior: +3.4%/yr, and that is the optimistic end.** Under our own
short-leg measurement rather than the generous 30%, the prior falls to
**0.1–1.4%/yr**.

## 3. The power check (run before compute, 2026-08-10)

EDGAR full-text search covers **2001+**, so the usable window is 2001-01 … 2022-12
= **264 months**. Monthly excess-return volatility of a 150-name long-only book in
this harness, measured on that exact window: **σ = 3.06%/month** (from
`runs/NIGHT7/T2_exit_arms_monthly.csv`, A0 vs CRSP VW).

| bar | MDE |
|---|---|
| t = 2.0 (our standing bar) | **4.52%/yr** |
| t = 3.0 (Harvey-Liu-Zhu new-factor bar) | **6.78%/yr** |

**MDE (4.52%/yr) exceeds the optimistic prior (3.4%/yr).** At the Harvey-Liu-Zhu
bar it exceeds it by 2×. Under the short-leg-realistic prior it exceeds it by
3–45×.

> **Verdict: POWER_FAILED before compute. The money version does not run.**
> Running it would produce a null that says nothing about the idea — which is
> precisely the failure mode the graveyard census found in 66% of the closed
> search (median MDE 3.74%/yr against a 3%/yr target). We are not adding row 149.

## 4. What *is* licensed to run

The design's problem is that a **150-name monthly portfolio** throws away almost
all the information in the data. Our own graveyard shows the pattern exactly:
rows with **rank-IC t 6.63** and **net t 0.37** on the same signal. Information
was there; the money construction could not carry it.

So the version that survives the gate is **not a strategy test at all** — it is a
**Layer-1 extractor validation** under the firewall (`aegis_brain/firewall/`):

- **Unit of observation:** filing-pair (firm × year), thousands per year, not 264
  months.
- **Primary metric:** cross-sectional **rank IC** of the semantic-diff score
  against a *labelled, non-price* outcome — going-concern language, restatement,
  guidance cut, or realised earnings direction — following the Kim-Muhn-Nikolaev
  protocol (verified: GPT-4 60.35% vs analysts 52.71% on **standardised and
  anonymised** statements).
- **Why this is the right first test:** if the extractor cannot reproduce a
  measurement that has *ground truth independent of returns*, no downstream money
  test is worth running. And if it can, the effect size it measures becomes the
  prior for a properly-powered money test later.
- **Firewall constraints:** requests must be built through `ExtractionRequest`,
  which refuses outcome-shaped context. Entity masking alone marks the run
  **not alpha-certifiable** (`alpha_certifiable == False`) — the NIGHT-7 finding
  that date-keyed memory survives entity anonymisation (LAP arXiv:2512.23847;
  FinCAD arXiv:2605.24564).

## 5. What would license the money version later

Any **one** of the following, registered as an amendment before compute:

1. A measured extractor IC that implies a long-leg effect **> 6.8%/yr** (i.e. the
   MDE at t=3), from §4's validation.
2. A construction with materially lower σ — e.g. a **paired/hedged** book
   (changers vs matched nonchangers) whose difference series has σ well below
   3%/month. Paired differences are what gave the exit sweep its power; the same
   trick applies here.
3. A longer window from a text source with pre-2001 coverage.

Absent one of these, this trial stays registered and unrun. **UNRESOLVED, not
rejected** — the idea is untested, and this document says so with its arithmetic
attached.

## 6. Ledger

Branches consumed: **0 money tests.** One design registration and one power
check. Counted in the constraint ledger as a registered trial that did not fire.
