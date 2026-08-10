# NIGHT-7 BRIEF — External Review Synthesis + Research Directive

**Date:** 2026-08-10
**Author:** home session (the brain — approves and validates)
**Executor:** fresh Opus session (the worker — researches, builds, updates the roadmap)
**Repo:** `C:\Users\mrthn\Aegis module` · branch `factory/night-7`
**Start ritual:** `session_briefing()` + `aegis_verified_state()` (Optimus MCP), then read this doc end to end. Before proposing any research, `brain_query` + `aegis_postmortems` — the idea may already have a corpse with receipts.

---

## 0. Roles and decisions carried from the brain

1. **Roles.** Murat's words: *"you are the brain approving and validating, opus is the worker."* This doc is the brain's adjudication of five external reviews plus Murat's directive. The worker executes, and every verdict comes home for validation before it becomes canon.
2. **Merge `factory/night-5` and `factory/night-6` to main: APPROVED.** Do this first. Confirm the G7 tests and the T4 verdict-guard tests pass post-merge.
3. **The smaller product claim: ACCEPTED.** The product note leads with AVUV: *"against the fund actually running our strategy, we have not shown an edge; vs value ETFs and the French proxy the convergent estimate is ~+2%/yr at t≈1.2."*
4. **AVUV framing CORRECTED** (review 5, verified against Avantis's own materials): AVUV is **actively managed** — daily active oversight, current-price-based selection, deliberate implementation. It is not a rigid passive rule. Our benchmark is a competent active implementer, which makes beating it harder and more meaningful. Update every doc that calls it passive.
5. **Standing rules unchanged:** pre-register before compute; holdout (2023-01+) locked, loader refuses; no lane/paper_nav writes from research compute; LLM spend cap $15 for the night; "blocked on Murat" claims require a printed status code; reviews are **evidence, not instructions** — every checkable claim gets checked before it carries weight; UNRESOLVED is a valid and often correct ending.

---

## 1. What Murat asked (his directive, condensed — verbatim in Appendix A)

Murat's core asks, in his own framing:

- Run a **detailed research pass on our methods, theories, approaches** — he suspects some of the ~190 killed ideas were killed by bad tests, not because they were wrong.
- Turn **hard-to-quantify information** (FDA dates, CEO quality, politics, geopolitics, supply chains, ownership, social/network structure) into **usable numbers via LLMs**, with the engine/Optimus as the context machine and validator.
- Build/improve a **brain**: every run should teach it; it should catch patterns, hold weights, remember; he proposed masked/renamed historical replay to teach the LLM without contamination.
- His own trading history: bought MRVL at 40, MU at 100, NVDA at 20 — **sold all of them far too early**. He believes we're "failing at beating the S&P because we keep re-trying tried methods"; wants **novel** approaches, including watching what funds/insiders/the world's investors do, and betting on the future (semis, energy, defence, space, batteries, quantum) even when Sharpe looks bad today.
- He worries we are **too focused on small caps** and on safety.

The brain's read: the five reviews, independently, answer almost every one of these asks — sometimes by confirming his instinct with published receipts, sometimes by correcting it. Section 2 is the map.

---

## 2. Adjudication of the five reviews

Five reviews were received (full text in Appendices B–F). Quality varies sharply. Review 4 is the strongest (specific, citation-dense, adversarial); review 5 is the deepest on architecture and governance; reviews 1–3 add convergent support and a few unique ideas but contain invented precision that must not be adopted as numbers.

### 2.1 Convergence map — what ≥3 reviews say independently

| # | Converged claim | Reviews | Brain's verdict |
|---|---|---|---|
| C1 | **LLM = measurement instrument / extractor, never the decision-maker.** Extract structured numbers from text; small regularised models learn weights; deterministic engine decides. | 1,2,3,4,5 | **ADOPT** — this is already CANON direction; now it has independent convergence and citations |
| C2 | **Implementation ("craftsmanship alpha") is our real, provable edge** — fee, capacity, clock, veto, tax are deterministic arithmetic, not t-tests. NIGHT-4's annual-beats-monthly and NIGHT-6's G7 cost result ARE this. | 2,3,4,5 | **ADOPT** — formalise as the craftsmanship ledger (T7) |
| C3 | **Rebalance-clock ensemble**: split capital into staggered annual cohorts (one per month). Removes date-luck by construction; deterministic variance-reduction claim, not alpha. | 2,3,4,5 | **ADOPT** — cheap, aligns with NIGHT-5's frontier nulls (T3) |
| C4 | **EDGAR text signals are the best novel × free × LLM campaign** — Lazy Prices–style year-over-year diff of 10-K risk factors / MD&A, upgraded from cosine similarity to LLM semantic diff. | 2,3,4 | **ADOPT AS REGISTRATION** — power check before compute; effect-size prior must come from the verified paper, halved for post-publication decay (T6) |
| C5 | **The self-improving memory loop as Murat described it is a trap.** An LLM writing prose "lessons" after seeing results is an unregularised prior fit to the test set — unfalsifiable and persuasive. Needs a one-way firewall. | 4,5 (1 implicitly) | **ADOPT** — the firewall is the correct version of Murat's brain, not a rejection of it (T5) |
| C6 | **Score the extractor, not the strategy.** Validate LLM features against ground truth that arrives later (earnings direction, PRisk, restatements) — thousands of observations, no market noise — before any money test. | 4,5 | **ADOPT** (T5) |

### 2.2 Unique high-value findings (single review, strong evidence)

- **THE EXIT LAYER (review 4 — the night's headline).** We ran ~179 tests on *entry/selection* and **zero on exit**. Akepanidtaworn, Di Mascio, Imas & Schmidt, *Selling Fast and Buying Slow* (JF 2023): institutional PMs show skill buying, and their selling underperforms even **random** selling; forced attention (earnings season) fixes it. Compose with Bessembinder (JFE 2018): ~4% of stocks account for all net wealth creation — exiting winners early structurally misses the entire right tail. Murat's own record (MRVL 40→80, MU 100→200, NVDA 20→100) is a textbook instance. **An exit-rule campaign has higher expected value than anything left in the selection graveyard. Run it first** (T2).
- **Tax-loss harvesting is real but not ours (review 4).** Chaudhuri, Burnham & Lo (FAJ 2020): ~1.08%/yr gross, 0.82%/yr with wash-sale. **Hong Kong has no capital-gains tax** → TLH is worth ~zero to Murat's personal account. It is a **product feature for US-taxable Aegis users** and a publishable claim — never part of our own performance target.
- **Trial-count accounting (review 4).** Harvey-Liu-Zhu: new-factor claims need t>3 given the mining history. Bailey & López de Prado: Deflated Sharpe scales the bar with trials. Our survivor at raw t 2.85 after a 179-candidate search must be run through this **and the number published even if it kills the claim** (T4).
- **The substrate exists (review 4).** ChronoBERT/ChronoGPT (point-in-time-trained LLMs) for honest historical text work; **FINSABER** (KDD 2026) is essentially our harness published as a peer-reviewed benchmark — stop rebuilding, benchmark against it. Its diagnosis matches ours: LLM advantages evaporate over long horizons/broad cross-sections.
- **Event-object architecture (review 5).** The PIT "causal event graph": LLM reads primary sources (8-K, FDA, government releases) → emits a structured Event object (surprise vs prior expectation, channel, exposure, horizon, provenance, decay) → deterministic validators → small models test for **incremental** information after factors/revisions. This is the correct form of Murat's "turn the world into numbers" ask. The data-side companion already exists: `aegis-finance/docs/RESEARCH_PROMPT_SOCIAL_DATA.md` (lobbying, FEC, USAspending, Form 4 acceptance timestamps, 13F lags, 8-K 5.02) — fold its answers into the event-store plan (T7).
- **Two scoreboards (review 5).** Research scoreboard (factor-residual alpha, MDE, placebos, forward evidence) vs product scoreboard (terminal wealth, drawdown, costs, taxes, usability). A portfolio can be a **good product** without novel alpha — AVUV itself is proof. Keep them permanently separate (T7).
- **Regulatory guardrail (review 5).** SEC has brought AI-washing enforcement actions; marketing language like "AI brain that beats the market" must never appear unless literally true. Our publish-negative-results habit is legally protective, not just scientifically admirable.
- **The strategic fork (review 4, addressed to Murat, folded into the roadmap).** Path A (fund): needs capital, t>3, years of forward track record — moves at one month per month. Path B (research/infrastructure): the graveyard, the firewalled PIT pipeline, and a semantic-diff paper are **citable assets worth more at 18 than 1%/yr on a small account**, and they open Path A later. The roadmap update must present both honestly.

### 2.3 VERIFY-FIRST — checkable claims that must be confirmed before they carry any weight

The proof-of-reading gate applies. Each item below gets read at the source and a one-line VERIFIED/FAILED note in `runs/NIGHT7/VERIFIED_CITATIONS.md` before anything is built on it:

1. **Lazy Prices effect size.** Review 2 claims "Sharpe >1.5 from 10-Q distance features"; review 4 claims "up to 188bps/month". These disagree with each other and smell inflated (the brain's recollection of Cohen-Malloy-Nguyen JF 2020 is a long-short alpha in the 30–60bps/**month** range in the original sample, small-cap concentrated). Get the real number; that number, halved for decay, is T6's prior.
2. **"3S-Trader 131.83% on DJIA" (review 2)** — unverified, likely a cherry-picked window; do not cite until read.
3. **Review 2's bps tables (120–310bps total edge vs AVUV) and review 3's per-idea bps estimates** — invented precision. Treat every one as a *hypothesis label*, never as an estimate. Our own numbers come only from our own registered runs.
4. **FINSABER, StockBench, KTD-FIN, FinCAD, NoLBERT, Lookahead Propensity, ChronoBERT/ChronoGPT, RD-Agent(Q)** — confirm each paper exists as described and skim the abstract+method before citing in any Aegis doc.
5. **Maeso & Martellini "rebalancing premium >100bps" (review 1)** — verify what population/assumptions; the rebalancing-premium literature is contested and often conflates volatility harvesting with alpha.
6. **Selling Fast and Buying Slow, Bessembinder, Craftsmanship Alpha, Harvey-Liu-Zhu, Deflated Sharpe, Glasserman-Lin, Kim-Muhn-Nikolaev, Ben-David thematic-ETF, Chaudhuri TLH, Hassan PRisk (firmlevelrisk.com)** — the brain believes these are real and correctly characterised, but the gate applies to everything: read, then note.

### 2.4 REJECTED / CORRECTED (encode these so they don't return)

1. **"BlackRock/Vanguard hold it → the system won't let it fail."** Index ownership is mechanical cap-weight tracking — approximately zero information, no backstop. The informative version is **concentrated active ownership** (13F of high-active-share managers), used with its real timestamp: filings arrive up to **45 days** after quarter-end. Never treat 13F as real-time.
2. **"NVDA >1% of the S&P → it has peaked."** Not supported. Cap weight is an output of value, not a ceiling on future returns; the size premium does not run in reverse at the mega-cap end. Review 4's diagnosis is exact: this belief **is** the sell heuristic that cost Murat NVDA at $100 — the thing T2 exists to measure.
3. **Ethnicity / inferred demographics as features: EXCLUDED, hard rule.** Murat's directive mentions ethnic background and political-group support. The mechanisms he's pointing at are real but must be measured through **observable economic variables**: board networks (BoardEx), prior employment, political appointments, lobbying spend, campaign contributions, government contracts, disclosed ownership, geographic revenue. Inferred ethnicity or any protected characteristic is a poor proxy, ethically unacceptable, and adds nothing the observable variables don't. This rule goes in CANON.
4. **LLM directly picking stocks** — already REJECTED by NIGHT-3 (t 0.04 / 0.93 over 204 months, 16,320 graded decisions). All five reviews independently agree. Closed.
5. **"Every backtest makes the brain better" (naive form)** — rejected per C5. The correct version: the memory hierarchy. Procedural memory (bugs, leakage patterns, bad controls) and mechanism memory (economic hypotheses, tagged retrospective) update freely from historical work; **calibration memory** updates from scored extractions; **P&L never writes beliefs** (already CANON, now with the reviews' independent endorsement).
6. **Thematic bets at narrative peak** — Ben-David et al. (RFS 2023): specialised ETFs lose ~30% risk-adjusted in their first five years, and it's overvaluation at launch, not fees. Murat's themes (semis, energy, defence, space, batteries, quantum) are not rejected — the **entry timing** is inverted: exposure is only interesting entered in the *bottom* of narrative salience, which is a testable signal on the GDELT feed we already ingest. Registered idea, queued.

---

## 3. NIGHT-7 tasks, in priority order

**T0 — Housekeeping (mandatory, first).** Merge `factory/night-5` and `factory/night-6` to main. Run the fast test suite; confirm G7 tests and verdict-guard tests green. Update MEMORY/state pointers.

**T1 — Citation verification pass (mandatory, gates everything).** Work §2.3 top to bottom. Deliverable: `runs/NIGHT7/VERIFIED_CITATIONS.md` — one line per claim: source read, number as published, VERIFIED or FAILED-AS-QUOTED. Anything failing is quarantined and the dependent task's prior is re-derived.

**T2 — THE EXIT-LAYER SWEEP (the registered campaign of the night).**
- Entry held fixed: PROF-COMPOSITE-150, annual clock, small segment — the banked book.
- Pre-registered arms (exits only): (a) annual rebalance baseline; (b) trailing stop −20%; (c) momentum-conditional hold (hold while 12-1 momentum positive); (d) fundamental-break exit only (exit when the profitability signal that selected the name breaks); (e) earnings-anchored scheduled review.
- Power comes from **paired differences** (entry noise shared across arms). Print MDE before running. Any arm that materially changes turnover must pass through **G7** before its net number is quoted (NIGHT-6 rule: the monthly panel understates churn costs ~2.7×).
- Register predictions before compute (the brain's own predictions are in §5 — write yours independently first, then compare).
- Verdict vocabulary: taxonomy v2. UNRESOLVED is a valid outcome.

**T3 — Rebalance-clock ensemble (cheap, deterministic).** 12 staggered annual cohorts, 1/12 capital each. Claim to measure: mean return ≈ single-clock mean; cross-clock dispersion collapses. No alpha language anywhere — this is diversification of implementation risk. Product-relevant regardless of outcome.

**T4 — Trial-count accounting (cheap, mandatory honesty).** Deflated Sharpe over the closed search with an explicit estimate of effective independent trials (the constraint ledger already prints denominator 821 and Bonferroni 4.01 — extend it to a DSR read on the survivor). **Publish the number even if it kills the survivor.** This immunises every future claim.

**T5 — The firewall spec (architecture, no money).** Write the three-layer design as code interfaces in `aegis_brain/`:
- **Layer 1 extraction** (LLM): anonymised+standardised inputs, fixed JSON schema, per-field confidence, stamped (value, as_of_ts, source_doc_id, model_ver, prompt_hash). Sees no prices, no returns, no outcomes, ever.
- **Layer 2 learning** (no LLM): ridge/GBM, purged CV + embargo. The only place weights change.
- **Layer 3 adjudication** (LLM): explain / red-flag / veto, read-only, scored on Brier/log-score, never on P&L. A veto is a registered scoreable claim.
- First extractor-validation target, registered tonight: **PRisk replication** (Hassan et al., ground truth at firmlevelrisk.com) or earnings-direction on anonymised statements (Kim-Muhn-Nikolaev protocol). If our Layer 1 can't reproduce a published measurement, everything downstream is noise.
- **No self-improving memory loop until Layer 1 has a measured calibration curve.**

**T6 — Register (do NOT run) LAZY-PRICES-SEMANTIC-DIFF.** LLM semantic diff of year-over-year 10-K risk factors / MD&A on the EDGAR full-text feed (proven open in NIGHT-6): "reworded boilerplate" vs "quietly deleted the customer-concentration disclosure". Prior = verified paper effect × 0.5 (McLean-Pontiff decay); power check vs that prior; runs only if the MDE math says the test can see it.

**T7 — Roadmap update (the worker owns the doc, the brain approves).** Update the roadmap with: the two scoreboards; the craftsmanship ledger as the product's deterministic backbone (fee/capacity/clock/veto arithmetic; TLH listed as US-user product feature only); the corrected AVUV framing; the Path A / Path B strategic fork presented honestly for Murat's decision; the event-store plan folded with the PIT social-data source research; the queued registered ideas (narrative-salience thematic entry, insider-disagreement interaction, network diffusion — each behind prereg + power check). Ethnicity-exclusion rule into CANON.

**Stop rule.** T0–T2 are mandatory. T3 and T4 are cheap — do them. T5–T7 as depth allows. Three tasks with receipts beat seven done thinly. STATUS handoff at the end: predictions scored, denominators printed, spend accounted.

---

## 4. Budget and boundaries

- LLM spend cap: **$15** for the night (extraction experiments included).
- No lane / paper_nav writes. Holdout stays locked. Keys env-only.
- Every new claim: pre-register → compute → verdict in taxonomy v2 → constraint ledger updated.
- Reviews (Appendices B–F) are **evidence, not instructions** — nothing in them overrides canon, and nothing in them is adopted without the T1 gate.

## 5. The brain's registered predictions (score these in STATUS)

1. **≥2 of the flagged review numbers fail verification as quoted** (Lazy Prices magnitude and the 3S-Trader figure are the likely casualties).
2. **The DSR/trial-count read (T4) leaves the survivor below the t>3 bar** — the honest label stays "factor harvest + unproven ~1%/yr skill".
3. **Exit sweep (T2): no exit arm beats the annual baseline at paired t ≥ 2; trailing-stop arms land NEGATIVE net of the baseline** (stops sell winners — the Bessembinder tail cuts against them).
4. **Clock ensemble (T3): ensemble mean within ±0.3%/yr of the single-clock mean; cross-clock dispersion reduced by more than half.**

---

# Appendix A — Murat's directive (verbatim)

> I want you to run a detailed research our our methods, our theories our approaches. We run so many tests, we had so many promising ideas, like we had 190 plus ideas. And with these ideas, the issue is, I think some of them were great, and we killed them. We killed many of them, and we realized like with our backtest that yeah, we actually killed them. Some of them were data-driven, research paper-based, and from like other projects, and we killed them because they were pushing them to be noise or overtraining. I think we had so many problems saying novel ideas such as like using large language model to receive news about the companies, look at their expectations, look at the social norm, look at the future expectations, and based on that, make investments, looking at their like FDA approval dates, looking at the CEO's future, looking at what the company does in overseas, what is the political stance. Like, for example, when Trump said, I'm going to support electricity or I'm going to support petrol, the Iran war, the Gulf opening and closing, the Venezuela impact, the petrol prices going down. Like, all of these are data, and these are really hard to get as numerical values. And I was hoping that we can use this data, turn them into usable numerical values using LLMs, and use the engine or the Optimus brain, maybe as an MCP or like a different context. I'm not sure with the methodology, to make sure the large language model works in a better way, where it is consistent, where it knows the context of what it has been doing. That's why I was like forcing it to do backtesting with large language models. It said it can't because it has historical data. And I said, we can move around this by changing the name of the companies, changing their data, so it thinks it's a different one, and it's trying to learn from the instances. That's why I also said, give it historical events and ask it to review what will happen versus what happened, so it will learn, and it will log the things it learned, and it will look for patterns. This kind of backtesting where we are changing the values, names, events, to teach the LLM to create a brain was essential, where I wanted to switch this into a neural network, a supervised learning algorithm even. I'm not sure the methodology we should do for creating a brain, but I know we need to create or improve our brain. Obviously, we are not creating our own large language model, but we are creating a brain that uses a large language model API, and it is constantly having a conversation between the brain and the model to make investment decisions such as fund. Like, I want it to think like an investor. I think we are failing really bad at beating S&P 500 because we are constantly trying already tried methods where we should be doing novel things with the new data, with the new tools, new access. Like, we need to think novel. So that's why I was like, so much forcing past few days to try new things with the methodologies. There is a lot of social biases, social things that goes between these things, like people's network, social backgrounds, CEOs' backgrounds, how competent they are, the company's ethnic background, because the ethnic backgrounds also get like certain support from political groups, their own ethnic like environment groups, how diverse the company is really good for them so they can be more productive overseas. Like, I think neurodiversity or neuroscience can be used in that sense to also, like, work on these companies' internal environment. How, like, what are the companies that are holding these stocks are also really important. If BlackRock, Vanguard, JP Morgan, Goldman Sachs, is holding these companies with a good percentage, these companies cannot fail because the system will not allow them to fail. The point is, we know, we need to know when to buy these companies and when to sell. I knew when to buy. I bought these companies in my conviction name really early, but I sold them at very terrible times. I bought Marvel when it was $40, I sold at $80. I bought Micron, $100, sold at $200. I bought Nvidia, $20, and I sold at $100. These companies now become like one of the biggest companies and they are holding a great chunk on S&P 500. But the thing is, they already increased so much, I don't see a point where, like, we should still hold them. I think they already reached to a peak, and from now on, just like Nvidia in the past year, it will just either be standing there or continue to fall because their market percentage is too long, too much. If they are making more than 1% of the S&P 500, they are a big company and how much they increase or decrease is really dependent on the market. So I was trying to say, choose winning S&P 500 stocks where I'm saying like, don't go mainstream or don't go too small stocks like penny stocks. I'm saying buy like Marvel or Micron when they are cheap. Try to find them. Like, for example, now, I'm looking where I'm seeing that semiconductor companies are the backbone of the future. They will always increase. Oil companies, because oil is a big problem right now in the world, and kind of recycle energy, military, future like space, telecommunication, like battery especially, quantum computers in the next years. Like, these are the future, where they might be unprofitable right now. The sharp is not good. Like, we are so focused on sharp, we are like, we have to be safe, safe, safe. I get it, we have to be safe, but sometimes we have to bet on the future with an educated guess. That's why I'm saying like, we need to use other firms' findings or other hedge funds, like what they are doing, keep track of them, check what they invest, like public is investing at, check the new sentiment, like what people think about the market, certain stocks, check what, like, not only on US, check what international investors are thinking, like China thinking, Europe is thinking, because, like, the world is not gonna fight the US, there is a big role investing in the US market, Arab people investing, like, we need to check the whole world for what they are doing and how they are investing it. Plus, I just think we need to come up with more novel ideas to see how we can improve our approaches to these problems, how we can utilize the large language models better. I think our way of using large language models with the paper accounts, etc., is something novel with the backtest. So with every backtest, I want the large language model to learn more, log the brain better. Like, every run should make the brain better. Every instance of what happens should log into the brain, and the brain should catch on patterns, make weights, make sklearns, like, Markov chains, like, the data science algorithms we need to use. I'm not familiar with the methodology so much, so that's why I'm asking, like, think about the methodology. Use new methods, like, join two existing ideas to create a new one, or just create a new idea by itself. So think about this, tinker about this. I think there's so many public data. We already have the wart background like the CRSP and I already applied like a lot of APIs. I think we already have the data, we just have to figure out a way of approach, like how to synthesize this data for our usage, and how to use the current upcoming data and make up guesses for that, like. That's why I want to utilize the large language model and the engine. I understand we can't do a lot of backtesting because it's like getting picked up on the noise, making too much overtraining, but I think when the other findings are showing different results with ours, where they are publicly renowned, it's making me inclined to think that our approach and methodology is wrong. I feel like we are too focused with the small cap stocks. Our approach is like we are just trying the same thing over and over again, where we should not reinvent the wheel, but find a new approach, like find a way around the problems.

---

# Appendix B — Review 1 (Consensus.app literature pass)

_Reproduced verbatim from Murat's paste._

## Research on **Aegis Methods** and **LLM Investing**

Your methods, theories, and approaches break into three questions: **what your current edge really is**, **how LLMs should be used**, and **how to redesign the research loop**. The literature supports your own internal finding that **rebalancing and implementation** often matter more than clever stock-picking tweaks, while also showing that LLMs are most promising as structured signal extractors and agent components rather than as a standalone "brain" (Maeso & Martellini, 2020; Arnott et al., 2024; Jadhav & Mirza, 2025).

### Current Edge

Your strongest validated result appears closest to a **known small-cap profitability recipe** plus better implementation, not a wholly novel alpha source. Small-cap portfolios can produce positive abnormal returns, but trading costs matter materially, and recent work suggests some volatility-managed and small-cap effects have weakened as markets became easier to arbitrage (Gorman, 2003; Angelidis & Tessaromatis, 2023).

- **Rebalancing premium** is real and can exceed 100 bps annually after factor controls (Maeso & Martellini, 2020).
- Small-cap and **high-volatility baskets** tend to generate larger rebalancing gains than random portfolios (Maeso & Martellini, 2020).
- Smart rebalancing can **retain factor premia** while cutting turnover and implementation shortfall (Arnott et al., 2024).

### LLM Role

The evidence supports using LLMs to transform messy qualitative information into usable signals, especially from news and multi-source text, but not treating the model alone as a reliable end-to-end investor. Advanced LLM sentiment models outperform dictionary methods on stock forecasting, and hybrid systems that combine LLM reasoning with quantitative modules, RL, or modular agents consistently outperform standalone NLP baselines (Kirtac & Germano, 2024; Siddique et al., 2025; Hajaghaie & Thulasiram, 2025).

- LLM news signals show **predictive relevance** for next-day returns, with OPT outperforming traditional sentiment methods (Kirtac & Germano, 2024).
- Multi-source architectures work better when the LLM is a **manager or analyst layer**, not the only decision engine (Yu et al., 2024; Fatouros et al., 2024).
- Layered memory and **continuous feedback loops** improve adaptation, interpretability, and resistance to model drift (Yu et al., 2023; Menda, 2025).

### Research Redesign

The literature points away from brute-force idea killing and toward a narrower research factory: use LLMs to extract structured event signals, pass those into a supervised or RL allocation layer, and evaluate with low-turnover, regime-aware rebalancing. Several papers report that combining external text signals with RL or portfolio reallocation improves returns and Sharpe ratios, while reviews of the field emphasize scalability, interpretability, and real-world validation as the main gaps (Gu et al., 2024; Unnikrishnan, 2024; Jadhav & Mirza, 2025).

- Use LLMs for **event extraction and reasoning**, then let ML or RL assign weights and trades (Gu et al., 2024; Siddique et al., 2025).
- Favor **gradual or selective rebalancing** over constant full turnover, especially after costs (Lim et al., 2021; Arnott et al., 2024).
- Track short-horizon signals first, because news-based forecasting degrades at longer horizons and high-volatility regimes remain harder (Chuang et al., 2025).

Aegis should likely stop treating novelty itself as the edge. The research base supports a redesign where **LLMs structure alternative data**, **quant models size the bets**, and **rebalancing discipline** delivers more of the live edge than raw stock-picking novelty.

References (as supplied): Angelidis & Tessaromatis (2023) JFM; Arnott, Li & Linnainmaa (2024) FAJ "Smart Rebalancing"; Chuang, He & Hu (2025) BDCC; Fatouros et al. (2024) MarketSenseAI, Neural Comput & Applic; Gorman (2003) RFE; Gu, Ye, Wang & Yin (2024) ICAIF; Hajaghaie & Thulasiram (2025) FLLM; Jadhav & Mirza (2025) Frontiers in AI; Kirtac & Germano (2024) FRL; Lim, Cao & Quek (2021) Neural Comput & Applic; Maeso & Martellini (2020) JPM; Menda (2025); Siddique et al. (2025) TAJET; Unnikrishnan (2024) arXiv:2411.11059; Yu et al. (2024) FinCon arXiv:2407.06567; Yu et al. (2023) FinMem IEEE TBD.

---

# Appendix C — Review 2 ("Aegis-Finance Research Audit — NIGHT-7")

_Reproduced verbatim from Murat's paste. **Brain's warning:** this review's bps tables and several headline numbers (e.g., "Sharpe >1.5 from 10-Q features", "3S-Trader 131.83%", "Total plausible edge 120-310bps") are invented precision — see §2.3. Use its STRUCTURE (the dimension enumeration), never its numbers._

### 1. "We can't beat AVUV — find a way around."

| Dimension | Plausible Edge (UNVERIFIED) | Cheapest Honest Test |
|-----------|---------------|---------------------|
| Rank-shape selection (inverted-U) | 30-50bps | Rank-weighted selection vs AVUV factor exposures |
| 10-K red-flag veto | 20-40bps | FinBERT/Loughran-McDonald scan on 10-Ks; "Lazy Prices" cited |
| Rebalance-date choice | 10-30bps | Test different annual dates |
| Exclusion rules (sector/REIT/utility) | 10-20bps | Run with and without sector constraints |
| Capacity | 20-50bps | Go below AVUV's size floor |
| Tax-aware execution | 30-100bps | TLH overlay on annual rebalance |

Claimed total: 120-310bps/yr (UNVERIFIED — hypothesis labels only).

### 2. Graveyard/mid-large caps
Argues the funnel was right (profitability premium stronger in small caps; Dimensional uses exclusions-only in small caps); suggests a PEAD test on mid-caps via EDGAR: "If the Sharpe is <0.5 after costs, the triage was correct."

### 3. Engine-LLM loop registered design
Engine-only vs LLM-only vs Loop over the same universe; adopt if Loop Sharpe > max(halves) by ≥0.1 over 12 months. Cites "3S-Trader (2025), 131.83% on DJIA" (UNVERIFIED).

### 4. Landscape
Claims nobody combines simulate-first factories + pre-registration + LLM adjudication; says we're ahead on pre-registration/honest naming/LLM-as-adjudicator, behind on AQR's full QMJ quality score (4 dimensions), Dimensional's multi-premium integration, and systematic EDGAR NLP.

### 5. Five campaigns
(1) EDGAR sentiment veto; (2) Form 4 insider clusters; (3) rebalance-date ensemble; (4) QMJ score integration; (5) LLM forward prediction log scored after 12 months. Prioritises (3) then (1).

### 6. Logic-brain gaps
Memory (vector store of postmortems), pattern recognition (sklearn/Markov on the ledger — out-of-sample only), signal weighting (Bayesian updates with a weight floor), MCP context integration, forward-testing feedback with pre-registered predictions.

---

# Appendix D — Review 3 ("NIGHT-7 RESEARCH REPORT: THE WAY AROUND")

_Reproduced from Murat's paste, condensed only where it repeats Appendix C. **Brain's warning:** same invented-precision caveat._

- **Beating AVUV structurally:** 10-K red-flag veto via LLM on EDGAR ("dropping the worst 10% of a value bucket is often worth more than picking the top 10%"); point-in-time lobbying × Form 4 cross-reference; inverted-U "shoulder" selection (avoid hyper-crowded top profitability); tax-aware execution.
- **Mid/large caps:** price-based signals are dead there (HFT-arbitraged); the honest edge is unstructured text — LLM parsing transcripts for capex/strategic pivots before the narrative is priced.
- **Engine-LLM loop, scorable claim:** "The Engine + LLM verification loop reduces false-positive entry signals by ≥20% vs Engine-only, measured over a 3-month forward paper window, without reducing total return." Flow: engine flags anomaly → LLM finds catalyst → engine backtests the micro-thesis → ledger.
- **Landscape:** behind DFA/AQR on microstructure and cost models (G7's $935k finding shows it); ahead on unconstrained LLM adjudication + pre-registration ("the LLM as an automated, skeptical risk officer").
- **Five candidates:** (1) Lobbyist-Insider Nexus (PIT lobbying × Form 4); (2) 10-K Risk-Factor Delta (LLM diff YoY); (3) Rebalance Clock Ensemble (12 staggered annual cohorts — "low alpha, massive timing-risk reduction, very low cost"); (4) GDELT second-order proxies (trade the secondary beneficiaries of geopolitical shocks); (5) engineering-retention as profitability lead (LinkedIn/Glassdoor — high complexity).
- **Logic brain gaps:** plain-English "why" translation with hard-coded risk limits the LLM cannot override; vectorised postmortem cards forced into context before approving a same-sector thesis; the ledger auto-rejects ideas that failed recently.

---

# Appendix E — Review 4 (the citation-dense adversarial review)

_Reproduced verbatim from Murat's paste. The brain's assessment: strongest of the five._

Six things that matter most:

**1. Three of your "novel" ideas are published, validated, and you should stop re-deriving them.**
Anonymising company names before LLM sentiment extraction is Glasserman & Lin (2023) — and their result is better than you expected: anonymized headlines actually outperformed originals in-sample, because the "distraction effect" (the model's general knowledge of the firm polluting the measurement) costs more than look-ahead bias gains, especially for large companies the model knows well. Standardised+anonymised financial statements → GPT-4 is Kim/Muhn/Nikolaev: 60.35% directional accuracy on one-year-ahead earnings vs 52.71% for analysts, on par with a purpose-trained neural net. And the honest backtest substrate you actually need now exists — ChronoBERT/ChronoGPT, LLMs trained only on text available at each point in time.

**2. Your harness has been published as a peer-reviewed benchmark. Stop rebuilding it.**
FINSABER (KDD 2026) is your night-factory: 20 years of multi-source data including news and filings, unbiased symbol expansion, explicit survivorship/look-ahead/data-snooping mitigation, code on GitHub. Its headline finding is your finding: previously reported LLM advantages deteriorate significantly under broader cross-section and longer evaluation; LLM strategies are overly conservative in bull markets and overly aggressive in bear markets. Free diagnosis.

**3. The engine↔LLM conversation is crowded and the leakage-controlled results are bad.** Under masked, leakage-controlled evaluation, LLM agent cumulative returns are largely explained by passive market and style exposure, with limited evidence of persistent stock-selection alpha. On StockBench most agents fail to beat buy-and-hold. Register the loop as a claim, but don't build the fund on it.

**4. "Every backtest makes the brain better" will destroy you.** An LLM writing lessons into memory after seeing a result isn't learning — no weights update. It's an unregularised prior fit to your test set, expressed in prose, therefore unfalsifiable and persuasive. The correct architecture is a one-way firewall: LLM extracts numbers from anonymised text and never sees outcomes → a small regularised model learns weights → LLM adjudicates read-only, scored on Brier not P&L.

**5. You spent 179 tests on entry and zero on exit — and your own history says exit is the problem.** MRVL 40→80, MU 100→200, NVDA 20→100 is textbook: institutional PMs with $573M books show clear skill in buying while selling decisions underperform even random selling strategies, and the tell — during earnings season, when firm information is widely available, selling decisions outperformed the control by 90–120bps per day. Compose with Bessembinder: ~4% of CRSP firms account for all net wealth creation since 1926. Exiting winners at 2x is structurally guaranteed to miss the tail. **Run the exit sweep before any new selection campaign.**

**6. The AVUV target is wrong, and "semis are the future" is a trade you'd lose.** Your NIGHT-4 result (annual > monthly beats all stock-picking) *is* AQR's craftsmanship alpha — you found it and discounted it for not being novel. That plus capacity and concentration is your real delta. On themes: specialized ETFs lose about 30% risk-adjusted over their first five years, ~-6%/yr for recent launches, and it isn't fees — it's overvaluation of the underlying at launch. By the time a theme is articulable, the price contains it. The fix isn't abandoning the thesis, it's inverting entry timing against narrative salience — testable with the GDELT feed you already have.

One thing to resolve before you build on it: tax-loss harvesting is the biggest clean edge over any ETF (1.08%/yr gross, 0.82%/yr with the wash-sale rule) — but it's worth nothing to a HK-resident account with no capital gains tax. It's a product feature for US users, not a personal edge. Don't put it in your own target.

### The full review body (as pasted)

**0. Verdict in four sentences:** (1) the research machine is honest and unusually well-built; the **objective function is wrong**, which is why it keeps producing nulls. (2) ~179 tests on **selection**, ~0 on **exit**, which is where the literature and Murat's own history say the money is. (3) The LLM instincts (anonymisation, qualitative→numeric, learning loop) independently rediscovered three real research programmes — two published and validated, one a trap. (4) "Beat AVUV on gross alpha" is the worst possible target; four axes exist where a small private book is structurally advantaged.

**1.1 The AVUV axes table:** fee (0.25%, deterministic); capacity (AUM forces up-cap; size premium concentrates in the tail they cannot reach); concentration (cuts both ways); veto (rules-based fund cannot decline a name for qualitative cause; EDGAR full text is open); rebalance date (free to tranche; small but deterministic variance reduction); tax (82–108bps/yr per Chaudhuri, Burnham & Lo FAJ 2020 — **worthless in HK**, product feature for US users). Named: Israel, Jiang & Ross, *Craftsmanship Alpha* (JPM 2018) — "Your NIGHT-4 finding is craftsmanship alpha. You discovered it independently and then discounted it because it didn't feel novel. That was the mistake."

**1.2 Exit layer:** Akepanidtaworn, Di Mascio, Imas & Schmidt, *Selling Fast and Buying Slow* (JF 2023), 783 institutional portfolios averaging $573M, 2000–2016: skill in buying; selling underperforms a random-selling benchmark; mechanism is attention; earnings-season selling outperformed control by 90–120bps/day. Bessembinder (JFE 2018): ~4% of CRSP stocks account for all net wealth creation; half fail to beat T-bills. "An exit-rule campaign has higher expected value than anything left in your selection graveyard."

**1.3 The statistics were unwinnable from test ~40 onward:** Harvey-Liu-Zhu (RFS 2016) t>3.0 for new factors; Bailey & López de Prado Deflated Sharpe (JPM 2014). "Your t≈1.8 after 179 trials is the expected maximum of 179 draws from a null distribution." Three legitimate exits: forward out-of-sample (the lanes ARE the product); claims that need no t-stat (cost/tax arithmetic — G7 is stronger than any alpha claim we have); borrowed priors (test implementation of published results, inherit the prior, defend only the delta).

**1.4 The memory-loop trap** (as summarised in point 4 above), with the three-layer firewall diagram: Layer 1 extraction (LLM, anonymised inputs, fixed schema, stamped provenance, never sees outcomes) → one-way data firewall → Layer 2 learning (ridge/GBM, purged CV, the only place learning happens) → Layer 3 adjudication (LLM, read-only, scored on calibration). "What 'the brain learns' then means: the calibration map — (feature_type × regime × model_version) → realised skill. It needs hundreds of scored predictions, not hundreds of backtests — another reason the forward paper lanes are the asset."

**Score the extractor, not the strategy:** 10-K risk section → P(going-concern/restatement/guidance cut within 4 quarters); earnings call → P(next-quarter revenue beat) vs PRisk ground truth; Form 4 cluster → P(material 8-K within 90 days). "Cheap, high-n, labelable, and they tell you whether the instrument works before you attach money to it."

**2. Where the instincts are right:** anonymisation (Glasserman-Lin — a performance improvement, not just hygiene; but partial: the model still recognises eras — ChronoBERT/ChronoGPT is the proper fix); qualitative→numeric (Kim/Muhn/Nikolaev — the two operative words are *standardised* and *anonymised*); political/FDA/geopolitical features (Hassan et al. *Firm-Level Political Risk* QJE 2019, data at firmlevelrisk.com — "use it as a validation target, not a competitor"); thematic futures (Ben-David et al. RFS 2023 — entry must be anti-correlated with narrative salience); institutional ownership (index ownership is mechanical, zero information; concentrated active 13F ownership is the real signal); **NVDA >1% ⇒ peaked is NOT supported** — "this belief is the mechanism that cost you NVDA at $100."

**4. Five campaigns ranked by EV/compute:** (4.1) Craftsmanship ledger — deterministic arithmetic, "already ~90% proven by NIGHT-4 and G7, the highest-certainty thing you own"; (4.2) **Exit-layer sweep — run first** — fixed entry, sweep exits, paired-difference power, pre-registered ranking hypothesis: earnings-anchored review ≥ annual rebalance > any trailing stop; (4.3) Lazy Prices upgraded with LLM semantic diff (Cohen, Malloy & Nguyen JF 2020; "assume ~half the original effect post-publication"); (4.4) PRisk replication as extractor validation ("if it fails, everything downstream was noise"); (4.5) inverted narrative-salience thematic entry on the GDELT feed. Plus: clock ensemble — "deterministic argument, not a mined one."

**5. Landscape table:** FINSABER (KDD 2026, arXiv:2505.07078) — "your harness, published; benchmark against it"; StockBench (2025, arXiv:2510.02209) — most agents fail to beat buy-and-hold; KTD-FIN (2026, arXiv:2605.28359) — under masking, LLM agent returns decompose into market+style beta; BlackRock AlphaAgents (2025, arXiv:2508.11152); ChronoBERT/ChronoGPT (arXiv:2502.21206). "Where you are behind: no chronologically-consistent model; no deflated-Sharpe accounting on the 179; harness rebuilt rather than benchmarked; extraction and decision not firewalled. Where you are genuinely ahead and undervaluing it: pre-registration with an external hash anchor, a published graveyard, and a forward-only paper record that cannot be backdated. That is a real contribution. You keep treating it as process overhead. It is the differentiated asset."

**6. The strategic question:** Path A (fund) vs Path B (research-and-infrastructure). "At 18, a first-authored finance-ML paper plus an open dataset is worth vastly more than 1%/yr on a small account — and it is what actually opens the door to (A) later." The commercial angle: the honest failure log is a positioning asset nobody else has.

**7. Next three actions:** (1) trial-count accounting on the registry — publish even if it kills the survivor; (2) exit-layer sweep before any new selection campaign; (3) firewall the LLM in code, then PRisk replication as first extractor validation; no self-improving memory loop until Layer 1 has a measured calibration curve.

**Sources listed:** Israel/Jiang/Ross 2018 JPM; Chaudhuri/Burnham/Lo 2020 FAJ; Akepanidtaworn et al. 2023 JF; Bessembinder 2018 JFE; Harvey/Liu/Zhu 2016 RFS; Bailey/López de Prado 2014 JPM; Kim/Muhn/Nikolaev arXiv:2407.17866; Glasserman/Lin arXiv:2309.17322; He/Lv/Manela/Wu arXiv:2502.21206; Hassan et al. 2019 QJE; Cohen/Malloy/Nguyen 2020 JF; Ben-David et al. 2023 RFS; FINSABER arXiv:2505.07078; StockBench arXiv:2510.02209; KTD-FIN arXiv:2605.28359; BlackRock AlphaAgents arXiv:2508.11152.

---

# Appendix F — Review 5 (the deep methodology review)

_Reproduced from Murat's paste, condensed only where it restates other appendices; every load-bearing claim retained._

**Central conclusion:** Aegis does not mainly have an "idea shortage" — it has an inference-design problem it is unusually close to solving. Separate the system into three jobs: (1) understand events/narratives/context — LLM + retrieval + structured event extraction (LLM never directly emits "buy Nvidia"); (2) estimate whether extracted information has incremental predictive content — small, strongly regularised statistical models, hierarchical Bayes, trees/GAMs (not a huge neural net learning historical P&L); (3) construct and execute — deterministic engine, cost/liquidity model, risk budget (LLM never changes weights on vibes). Consistent with Microsoft's RD-Agent(Q) (NeurIPS 2025), which converts LLM-generated hypotheses into explicit mechanically-testable factors and warns against unconstrained natural-language trading signals.

**On the graveyard:** the 9-Aug amendment found 66% of the closed 179-signal search could not detect the project's own +3%/yr target (median MDE 3.74%/yr) — many kills are evidence the *experiment* was underpowered, not that the *idea* was false. The machine-enforced taxonomy (POWER_FAILED / DATA_FAILED / IMPLEMENTATION_FAILED / FACTOR_EXPLAINED / PLACEBO_FAILED / LEAKAGE_FAILED / UNRESOLVED / REJECTED / CONFIRMED) with per-class resurrection policy is exactly right; the brain should reason over failure causes, not treat all fails as negative rewards.

**On historical learning:** historical experiments may safely improve **procedural knowledge** (which datasets leak, which signals collapse after costs, which controls catch fakes, which prompts distort). Letting historical P&L update live stock-selection beliefs recreates the selection bias months were spent removing. Masking is a good contamination diagnostic (the 1,080-call experiment: instructions do nothing, masking produced 0/240 identifications, synthetic ≈ masked), but 2025-26 work (FinCAD, Lookahead Propensity, NoLBERT) shows parametric look-ahead can survive prompting — so masked replay is a **reasoning laboratory, not an alpha-certification laboratory**.

**On neural nets:** Gu, Kelly & Xiu found shallow nets beat deep ones in finance (sparse data, low signal-to-noise). With Aegis's current count of independent event resolutions, hierarchical Bayes / regularised GLM-GAM / boosted trees / conformal layers are more defensible than an end-to-end neural brain. Use neural representations for text/graph embeddings first.

**On small caps:** the concentration is informative, not necessarily a bug — size/value/profitability are established return dimensions and AVUV itself targets exactly this. But it could partly reflect search bias (most of the 190 ideas were cross-sectional characteristics whose dispersion is naturally largest in small caps). **Stratify before testing:** give small, mid, large-cap families fixed hypothesis budgets.

**On mega-caps:** ">1% of the S&P" imposes no ceiling; weight is an output of value. The right conclusion is "large-cap generic factor spreads may be harder", not "large companies can't deliver exceptional returns."

**On HMM/regimes:** use regime probabilities as continuous exposure conditioners, never as an oracle choosing which strategy wins next (crash-timing already failed every test).

**The Event object** (the core proposed innovation): observed_at, source_type, source_quality, actors, event_class, prior_expectation, outcome, surprise_direction, surprise_magnitude, fundamental_channel, firm_exposure, horizon, counterevidence, calibrated extraction confidence, provenance, decay_rule. LLM reads the 8-K/FDA release/transcript and emits the object; deterministic code attaches market data and exposures; small models test for **incremental** information after PEAD/revision baselines. SEC EDGAR's unauthenticated JSON APIs (data.sec.gov) make this reproducible. Beliefs update over **mechanism claims** ("conditional on event class × context × horizon, X carries incremental information"), never over ticker P&L. This strengthens the existing ABN design rather than replacing it.

**Memory hierarchy:** procedural (yes, updates from history, influences live); mechanism (updates with retrospective tags, influences with shrinkage); episodic (masked historical in quarantine; forward/PIT preferred); calibration (updates from scored extraction; forward-only for return predictions); portfolio/P&L (stored forever, **cannot write beliefs**); forward evidence (primary promotion source).

**Six campaign families:** EVENT-SURPRISE (textual surprise beyond earnings/revision baselines, mid+large); NETWORK-DIFFUSION (news propagating through customer/supplier/board networks — Cohen/Frazzini/Malloy found education-network effects that Regulation FD later destroyed, a lesson in regime-change-aware beliefs); POLICY-EXPOSURE (event × measured exposure, not ideology); INSIDER-DISAGREEMENT (non-routine insider buys × analyst-revision disagreement — interaction, not standalone); BIO-EVENT (FDA/clinical surprise vs market-implied expectation, natural event clocks); CAPACITY-EDGE (can a small private book implement factor exposure better than AVUV at the marginal names — ADV participation and price-impact curve).

**Explicitly excluded:** ethnicity / inferred protected demographics. Observable economic variables (board connections, prior employment, political appointments, supplier relationships, disclosed ownership, geographic revenue, government contracts) cover every legitimate mechanism.

**13F reality:** filings arrive up to 45 days after quarter-end; "BlackRock owns it" is neither real-time nor a floor. Model ownership as slow state: concentration, passive-flow sensitivity, changes, crowding.

**AVUV programme:** AVUV is **actively managed** (Avantis: daily active oversight, current-price-based selection, $25B+). Realistic Aegis advantages: capacity (high plausibility, ADV/price-impact test), fewer names (raises idiosyncratic risk — wealth/DD bootstrap), exclusion of marginal names (rank-shape frontier), TLH (US-taxable product), staggered clocks (ensemble); "AVUV cannot actively decide" is FALSE; superior alpha not yet demonstrated.

**Clock ensemble:** six clock variants correlated 0.958-0.993, no significant pairwise difference ⇒ do not pick the best historical date; tranche across 12 staggered annual cohorts — converts an unmeasurable timing choice into diversification of implementation risk without pretending it's alpha.

**Two scoreboards:** research (factor-residual alpha, incremental IC, MDE, placebo, era stability, forward evidence) vs product (terminal wealth, drawdown, taxes, costs, capacity, usability, simplicity). Report gross edge, cost model, turnover, capacity-at-half-edge, net — "a result that works at $100k and disappears at $5M is capacity-limited, not false."

**Regulatory:** SEC AI-washing enforcement (misrepresenting how AI is used); ASIC pursuing unlicensed finfluencer advice; the 2023 SEC predictive-analytics proposal was withdrawn June 2025 — existing adviser/fiduciary/anti-fraud frameworks are what matter. Never claim "AI brain that beats the market" unless literally true and evidenced.

**Phased budget:** mechanism census + graveyard reclassification (1-2wk, minimal spend) → event-store infrastructure (2-4wk, SEC/FDA free) → LLM extraction benchmark vs human labels, no return data (1-2wk, hard LLM budget) → EVENT/NETWORK/INSIDER pilots (3-6wk) → synthetic-power calibration (parallel — manufacture worlds where the truth is known: no effect, weak effect, stratum-only effect, disguised size/value factor, one-day timestamp leak, cost-killed, LLM memorisation, format-vs-content placebo) → locked historical confirm (one firing per family) → forward trial (6-24mo) → product/capacity evaluation.

**The one-sentence methodology:** *Let the LLM discover and structure economic context; let transparent quantitative models decide whether that context contains incremental information; let a deterministic portfolio engine convert only validated information into risk; and let forward evidence — not historical P&L — change the system's beliefs about what works.*
