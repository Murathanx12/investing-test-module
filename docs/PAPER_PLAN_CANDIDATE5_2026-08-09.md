# Paper plan — the controlled negative result (Candidate 5)

**Decision, 2026-08-09:** this is the paper. The novelty ranking in the external
review dossier was inverted; the candidate ranked last is the only one still
standing, and it is on a clock.

## What the literature check changed

Reviewer 4 ran citation searches. The load-bearing ones were verified before
being written down here, and they are real:

| our claim | status |
|---|---|
| masked decision replay as a leakage instrument | **preempted.** Glasserman & Lin (arXiv 2309.17322, 2023) already compare trading performance on original vs identifier-removed headlines and propose anonymization for de-biased backtesting. We did not cite it. That is the first thing a referee finds. |
| leakage-controlled replay + "cumulative return is a noisy proxy for selection skill" | **preempted, and recently.** KTD-Fin (arXiv 2605.28359, May 2026) makes our §5.4 paired-difference argument roughly three months before our dossier. |
| "instruction-based forgetting does nothing" | **preempted in substance** by the unlearning literature. One piece survives: memory is *sparse and self-selecting*, so aggregate contamination metrics mislead and canaries must gate PER CASE. That is a methods note, not a paper. |
| membership vs ordering | **preempted conceptually** — Grinold's Fundamental Law (1989), IR ≈ IC·√breadth, with Clarke-de Silva-Thorley's transfer coefficient the sharper frame. And per the retraction of 2026-08-09 our evidence never supported it anyway. |
| CRL/PDUFA "no literature exists" | **withdrawn.** Absence of papers on a strategy that funds run commercially is evidence of unpublishability, not of un-arbitraged edge — and it contradicts our own premise that a known edge is an arbitraged edge. The forward ledger continues as a ledger; the novelty claim is dropped. |
| **the controlled negative result with a memory-content placebo** | **standing.** FinMem (Yu et al. 2023), FinAgent (Zhang et al. 2024), TradingAgents, FinCon and others claim memory-augmented LLM agents trade profitably. A well-instrumented negative with a content placebo, paired-difference isolation and a stated MDE contradicts that literature directly. |

**And the finding is simultaneously more credible and less novel than we
thought.** Min et al. (EMNLP 2022, arXiv 2202.12837) showed that randomly
replacing labels in in-context demonstrations barely hurts performance — the
label space, input distribution and sequence format are the active ingredients.
That is our +5.07 % scrambled arm, four years early, on a different task. It
*explains* our result rather than competing with it, and it must be cited. You
et al. (2022) revisit Min et al. and argue input-label correspondence matters
more than originally concluded; that tension is precisely what makes a
finance-domain replication worth reporting.

## The paper

**Working title:** *Memory-augmented LLM agents do not select stocks: a
leakage-controlled replay with a memory-content placebo.*

**Claim:** on 204 months of survivorship-free, identity-masked, outcome-embargoed
decisions, (i) an LLM decider is not distinguishable from the engine it was
meant to improve, (ii) episodic memory's apparent benefit survives destroying
the situation→outcome mapping, and (iii) the effect sizes these designs can
detect are large enough that most published positive results are not excluded by
their own power.

**The distinguishing component — lead with it.** The 2026 leakage-control
literature (Look-Ahead-Bench, CLQT, KTD-Fin, Profit Mirage) does temporal gates,
integrity ledgers, memory ablations and repeated-run noise floors. What it does
not appear to run is a **memory-content placebo**: memory of identical shape,
volume and marginal distribution with only the mapping destroyed. An ablation
asks "does memory help"; the placebo asks "does its CONTENT help", and those give
different answers.

**Sections**
1. Why cumulative return cannot grade a selector (paired difference, MDE).
2. The apparatus: masking, per-case canaries, outcome embargo, immutable cache.
3. Results: M1, M2, both REJECT with intervals.
4. The placebo, and the four-arm upgrade (no-memory / situations-only /
   scrambled / real) with a permutation distribution rather than one seed.
5. Elicitation: basis points vs decimals, 3/5 → 5/5 coherence, 0 wrong
   directions in 500 pairs. Small, practical, reproducible.
6. Honest limits: one model family, one asset class, one horizon, and the two
   harness defects we found in ourselves.

**Cite, non-negotiable:** Min et al. 2022; You et al. 2022; Glasserman & Lin
2023; KTD-Fin 2026; CLQT 2026; FinMem; FinAgent; Li et al. 2025 (FinMem's
post-cutoff collapse).

**Timeline:** weeks, not months. Roughly one quarter of runway before the 2026
benchmark papers close the gap.

## What does not go in

* Any claim that the apparatus is novel in aggregate. Components are; the
  assembly is not.
* Membership-vs-ordering as a finding — it is a 35-year-old identity and our
  measurement of it was retracted on 2026-08-09.
* PDUFA/CRL novelty.
* Anything about PF-PROF-COMPOSITE-150 until `TRIAL-PF4-DECOMPOSITION-1` has
  settled what it is made of. The strategy paper and this paper are separate,
  and this one does not depend on that one.
