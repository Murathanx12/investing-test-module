# PREREG — TRIAL-N3-SEASONING-1

**Registered:** 2026-08-10 · **Family:** N (extension) · **Stage:** diagnostic
**Data grade:** `crsp`

## 1. The question

The book holds names for as long as they stay inside a 3× incumbency band, so a
name can sit in it for years. Nobody has asked where in that tenure the return
actually accrues.

> **Does the edge live in fresh entrants and decay in stale incumbents?**

The decision it settles is narrow and worth settling: if the profile is **flat**,
the incumbency band is not a lever and band tuning closes permanently — one fewer
family for a future night to re-explore. If it **decays**, the band becomes a
registered improvement candidate.

## 2. Design

Run the banked annual book, record holdings, and profile realised returns by
**months of continuous membership**.

Two instruments, because the existing one is the weaker of the two:

- **A — the existing `decomp.event_time_profile`.** Buckets 1–6, 7–12, 13–24,
  25+ months, compared against the benchmark. Reported for continuity with prior
  nights.
- **B — the within-month comparison, which is the powered one.** For each month,
  the mean return of names in a tenure bucket **minus the mean return of the
  other names held that same month**. Market direction, regime and the book's own
  factor tilt all cancel, exactly as in the NIGHT-7B trigger study. Paired series,
  Newey-West(12).

Also reported: the monthly exit hazard by bucket, and the tenure distribution —
because a bucket holding 4% of name-months cannot support a conclusion however
its t-statistic reads.

## 3. The confound, stated before compute

**Tenure is endogenous and this design cannot make it otherwise.** A name is
still in the book because its composite score stayed high, and score persistence
correlates with realised returns. A "fresh entrant" is by construction a name
whose score just rose. So a tenure profile is *descriptive of where returns sat*,
never causal.

What that permits and forbids:

- **Permitted:** the decision question. If returns do not vary with tenure, then
  changing the band cannot move returns through this channel, and the family
  closes.
- **Forbidden:** any claim that entering fresh *causes* higher returns, or any
  mechanism story built on the profile alone. A decaying profile would license a
  registered band-tuning trial, not an adoption.

## 4. Decision rule (frozen)

| outcome | consequence |
|---|---|
| no bucket differs within-month at abs t ≥ 2.0, **and** the MDE is below 2.0%/yr | **band tuning CLOSED** — recorded in the closed-families list |
| a monotone decay across buckets at abs t ≥ 2.0 | register a band-tuning trial; do not adopt from this diagnostic |
| any bucket differs but not monotonically | `UNRESOLVED` — a non-monotone tenure effect is more likely a composition artifact than a seasoning one |
| MDE above 2.0%/yr | `POWER_FAILED`; the family stays open and this diagnostic is not evidence it is dead |

This is a **diagnostic**, so it may register a successor trial and close a
family. It may not adopt anything.

## 5. Registered predictions

1. **The profile is flat within-month** — no bucket reaches abs t 2.0.
2. **Instrument A will look like it has structure that B removes**, because A
   compares against the benchmark and inherits every market-direction wobble the
   within-month comparison cancels.
3. **The 25+ bucket carries most of the name-months** on an annual clock with a
   3× band, so the "fresh entrant" buckets will be the thin ones.

## 6. Ledger

Adds **1 branch** (one diagnostic, two instruments on the same book, no
parameter swept).
