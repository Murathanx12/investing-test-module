# Aegis Investor Brain — Status Snapshot

**As of:** 2026-07-21 (post-v1.0) · **Repo:** https://github.com/Murathanx12/investing-test-module
**Tests:** 61 green · **Cumulative trial count:** 21 (see TRIALS/registry.jsonl)

The one-screen picture of where the module is. Full architecture in ROADMAP.md;
per-session detail in docs/SESSION_*.md.

**2026-07-30 — PAPER-1 DRAFT v0.1 WRITTEN (Priority B executed):
`paper/PAPER1_DRAFT.md`** ("The Empty Shelf") — intro + methods + results
shell + all fixed exhibits (159 graveyard, empty cost cohort, −0.544
supporting, 3-dead-allocation-instruments signature, belief-engine null,
6-item data-artifact graveyard). Every number verified in its primary
artifact by 3 independent passes; adversarial 4th pass found 8 provenance
defects (25-vs-50bps wall, phantom robustness-arm registration, fused
collector mechanisms, fusion counting seam, clock dates) — all fixed and
logged in-draft. Two dated corrections pushed to aegis-finance
(AI_PANEL_2026-07-29 SPY maxDD −45.2→−55.19; CANON §3 ~37% attribution).
OPEN pre-submission: reconcile 32% vs 37% lookahead magnitude (same arXiv
ID, two repo docs); register-and-run the CZ-CALIB same-construction
robustness arm if −0.544 is to harden beyond supporting.

**2026-07-29 PM — Priority A EXECUTED (Fable sandbox): EVENT-INTEL LIVE +
FF product pin LIVE + 2 prod catches** (aegis-finance b4275c2/e9f0880/987ce03,
prod-verified). EVENT-INTEL per the 2B acceptance spec: typed events over
news/EDGAR/earnings, LLM classifies ENUMS only (playbook by construction),
per-feed canaries, measured-only context cards, stock page + brief + /dev;
shakedown 162 events, 100% valid structure. FF pin: research vintage is
monthly-only → product got its own frozen DAILY csv.gz (sha 17a97adc…,
pinned+live_append provenance on every decompose response). Catches: (1)
brief geopolitical event_score/label silently None for weeks (producer-key
mismatch, fixed, verified live); (2) **EDGAR 8-K feed silently dead in prod
since v13** — canary caught it on day 1; edgar_events' standalone github.io
UA is SEC-rejected; all its HTTP now routes through insider_form4._sec_get
(§5 convention, second dead SEC collector caught). GOOGL 8-K serves live.
Freeze holds at 159; nothing arms; fast suite 3,061 green.

**2026-07-29 — REGIME-ANALOG diagnostics D1-D4 RUN (Fable build session, kill lines pre-committed in FABLE_HANDOFF): the belief engine is a hedged base-rate emitter — phase 2 BLOCKED.** D1 NOT fired (10.78% of analogs ≤12mo vs 40% line; red-team distance-doubling didn't reproduce at real spec, 1.13x not 2.06x). D2 FIRED (D_A(90%)=9) but the 2-3-PC remedy fails on measurement: ~80-87% of analogs change, state_probs move ≤0.05 — retrieval is near-no-op on output (beliefs sit 0.06-0.13 from unconditional base rates). D3 at the leak-closed 504-td spec (causal standardization built + outcome aggregation causal; 63-td run's dd15/dd20 "wins" were the outcome leak): fwd6m BEATS persistence (DM t -2.31) but 87.6% of the win is hedging; other 3 INCONCLUSIVE; **REL>RES on all four — a constant at the base rate strictly beats the engine everywhere**. D4 unresolved (Pearson/Spearman disagree). Engine defect: retrieve_analogs guards candidates not acceptances — 59/239 causal states (whole GFC block) silently used <50 analogs (min 3). Everything independently re-verified by an adversarial pass (all deciding numbers exact; 3 report-prose defects corrected). Engine stays descriptive-only; successor = new walled registration, look at fwd12m first (RES/UNC 29.3%). Artifacts: causal_standardize.py + diag_d3_score.py (the persistence/DM/Murphy harness, reusable), diag_d1_d2.py, DIAG_* docs, belief_states_causal.jsonl. Sacred ledger untouched.

**2026-07-24 — TRIAL-BRAIN-006 FDA approval drift: REJECT** (pre-registered, one run): 671 in-panel NDA/BLA events 2002-2024; B large/mid -30.1 bps/mo net t=-0.89, B-PRI t=0.13, noise clean; micro segment untestable (2 live months) - daily-CAR revisit = NEW registration post crsp.dsf pull. Crosswalk data trap recorded: openFDA sponsor_name = CURRENT holder; roll-up events excluded as unattributable.

**2026-07-24 — TRIAL-THEME-SUPPLY basket arm: REJECT** (pre-registered, explore-only, one run): B-A spread t=0.10 (+3.2 bps) = NO cross-sectional info at annual cadence; micro B net t=-4.27; noise clean. Combined with 3b's cust_mom REJECT, the suppliers thesis is FULLY adjudicated - no holding period pays honest costs. Cumulative explore candidates 90.

**2026-07-24 — Factory batch 5: ZERO graduates (30 scans, priors 15/15 directional).** Sign reversals for batch 6: high-DTC (+, IC t 6.2), inst-persist (+, IC t 3.4). insider_cluster/insider_si VOID-DESIGN (need flag harness). defensive = screen-class (maxDD -35% vs -52..-82%). INSTR-HOLD-HORIZON: FLAT 14-17 bps/mo across 1-24mo bands - signal-band exits make long holds free. Cumulative candidates 120.

**2026-07-24 EOD — Batch 6 + BRAIN-009: ZERO graduates.** dtc arms post factory-best largemid net t (3.4/3.0) but FAIL the IC leg - rule held. inst-persist mirror refuted (both tails lose). cust_conc sign reversal book-inspected clean (IC t -7.4, Dhaliwal side). Insider clusters add nothing over single opportunistic buys (BRAIN-009 closed). Cumulative 130.

**2026-07-25 — WRDS batch 4 HARVESTED** (2 Duo taps, 311s+182s): ibes_adj 203k (tgt-price family un-voidable), funda ext cols 365k (re/invt/rect/dvc/prstkc/xrd ~78% coverage - RE/ME + divergence + payout unblocked), dsf_pharma daily 2.03M rows/750 permnos 2002-2024 VERIFIED superset of local universe (daily-CAR successor unblocked), BoardEx STARTERS 2.5M rows (catalogs: boardex 168 tables - entitlement confirmed), comp_pit pitnamesus 29k + pitqtrdataus 200k sample. Batch-5 batch4-guess tables comp_pit.r_company/co_ifndytd DO NOT EXIST - corrected names recorded.

**2026-07-25 — Batch 7 + TRIAL-BRAIN-010: conc_low graduated explore (t 2.28/IC 4.46, first since gp-small) then DIED at confirm (net -5.5 bps t -0.20, DSR 0.0003, FF6 alpha negative; IC t 2.6 persists - rank info real, premium gone). conc family CLOSED both directions. re_me (Ball 2020, STRONG prior) fails the bar in 2004-2018 - value's decade. Cumulative 140. The explore/confirm wall did its job on the first graduate it was handed.

**2026-07-25 PM — Panel round 4 + Batch 8 + taxonomy: ZERO graduates (6 scans, priors 3/3 borne out).** si_trend = IC-real/net-dead largemid (IC t 2.12, turnover 0.33 → net t −0.92; SI family fully mapped: level=filter, trend=shelf). rd_gp = book-without-rank in small (t 1.18, IC −0.07 — AND-rule catch; the novel GP conditioning does not rescue R&D/ME). **pead_agree INVERTED (IC t −2.6 both segments) = 5th sign reversal — strongest in-window receipt of post-2000s PEAD decay; no mirror (VERY-HIGH-turnover class).** Cumulative **146**. Panel round 4 adjudicated (aegis-finance `docs/research/AI_PANEL_2026-07-25.md`): taxonomy 4-tag rule ADOPTED (`docs/SIGNAL_TAXONOMY.md` = the ranked family map); tgt-rebuild inherits the PSZ-2025 dispersion-conditioned design; INSTR-REGIME-HMM amended to statistical jump model; INSTR-SBCORR registered to the macro family; payout/divergences/conc-conditioning/hold-horizon re-litigations REFUSED with receipts. INSTR-OVERFIT-CEILING run same day (see trial doc).

**2026-07-25 EOD — Batch-4 macro instruments: daily harness BUILT, explore + confirm BOTH run (pre-registered, one-shot each).** Jump model (λ=50, causal forward filter, 0.4-1.0 switches/yr — the persistence device WORKS mechanically) passed ALL explore bars (11.2% CAGR, −26.6% DD vs SPY −55.2%) then **REJECTED at confirm**: 2022 −21.6% (risk-off into TLT during the dual crash — safe asset wasn't) + 2020 missed rebound; both frozen bars missed; instrument CLOSED, successors need new registration. **INSTR-TSMOM-XA CONFIRMED PASS — first macro instrument to survive the wall:** crisis alpha in BOTH held-out crises (2020 +9.2%, 2022 flat), overlay maxDD −18.8% vs SPY −33.7%; disclosed: return drag t −1.86 → DEFENSIVE diversifier (Goal B), not beat-SPY; next = forward lane candidacy (attended seed). Descriptive receipts: SBCORR "disable dip-buying when corr flips positive" REFUTED in-window (dips bounce HARDER in corr+, +2.9% vs +0.6%, n=50 thin); GPR spikes NOT a sell signal (SPY CAR30 +0.61%, 64% hit; oil fades −2.5%, defense +0.9%). Panel round 5 adjudicated (aegis-finance `AI_PANEL_2026-07-25B.md`): 3-build order adopted (harness ✅ → FDA daily-CAR → tgt rebuild); hmmlearn/ceiling-rerun/USAspending/news-backtests refused; rate-cut-vuln = batch-9 stub, index-inclusion = data-blocked stub. Next ceiling re-registration legitimate at ~196 cumulative.

**2026-07-25 night — Build 2 + panel round 6.** **TRIAL-BRAIN-011 FDA daily-CAR: REJECT** (CAR(+1,+20) +2.1% t 1.45 vs bar 2.0; drift all in days 1-5, small-half, HIGH-attention +3.6% vs low +0.6% = the proposed attention gate refuted in its own arm; confirm gate never opened; FDA drift closed at BOTH resolutions, NEG_RESULTS §16). Crosswalk v2 SIGNED OFF (Murat + programmatic: 134 rows, 0 defects). **Brain review adjudicated** (`AI_PANEL_2026-07-25C.md`): panels' "no memory" premise wrong (Optimus MCP + registry + 10+ refused re-litigations); ADOPTED lightweight `scripts/prior_check.py` gate (procedural: no registration without a prior-check pass); vector DBs/Neo4j REFUSED at ~50-doc corpus (revisit ~500); meta-learning = taxonomy already. Queued w/ requirements: INSTR-REGIME-JM2 (inflation-gated; must declare post-hoc-repair provenance), zombie/rate-cut exclusion screen (long-side only; house doesn't short), capitulation long-leg (tgt-rebuild phase 2). Next: **Build 3 tgt rebuild**; TSMOM lane seed = attended (Murat).

**2026-07-26 — Self-directed research round (no AI panel): 2-agent sweep → Batch 9 + INSTR-VOC, ZERO graduates (cumulative 152).** Gates killed 3 candidates PRE-registration (prior-check: low-beta = closed low-vol family, NOA-level = closed accruals family; literature: ea_prem dead post-2004 per Heitz 8-K migration). **conn_mom (Ali-Hirshleifer, lit 1.68%/mo t 9.67) = starkest paper-vs-cost gap measured: net t −0.78, 67% monthly turnover, gross t <1.** industry_mom flat-since-2000 confirmed (largemid t 0.13). comp_issue_5y = IC-clears/net-doesn't (1.15/2.86, 6% turnover) — issuance shelf REINFORCED, strongest combiner case. **INSTR-VOC: virtue-of-complexity NOT SUPPORTED on our data** (all P lose to B&H both windows, non-monotone; corr w/ Nagel twin 0.13 — recipe produces noise here, not even the artifact; complexity class stays out; confirm sealed). Borrows banked: **OSAP SignalDoc snap** (331 signals w/ t-stats → `data/reference/`), queued instruments INSTR-ANOMALY-TIME (rdq-timing upgrade for gp-small — highest priority, it upgrades the one confirmed survivor), INSTR-CZ-CALIB, INSTR-HARNESS-VALID (Tidy Finance), Chen-Velikov cost-model port. Synthesis: aegis-finance `docs/research/RESEARCH_SWEEP_2026-07-26.md`.

**2026-07-26 PM — Panel round 7 + INSTR-ANOMALY-TIME: PASS + UPGRADE (first UPGRADE-class verdict; cumulative 153).** Re-timed gp-small availability from datadate+6mo to Q4 rdq month-end (90.2% of 136k firm-years re-timed, median 4.0 months reclaimed): explore 50bps t_net 1.96→2.19, held-out confirm +24.1→+33.5 bps/mo (t 0.89→1.24, IC t 4.35) — all frozen bars cleared. **Both hands:** paired book-level diff only +2.7–3.3 bps/mo (t 0.39–1.07); of the +9.4 confirm headline, +6.8 is benchmark-composition (EAD universe admits ~37 lower-return recent reporters/month). ADOPTED on PIT-correctness + weak-positive + costless (identical turnover), NOT on the headline. EAD availability now declarable at freeze for all fundamentals registrations; inv_div-EAD retry admissible. **prior_check hardened after near-miss** (whole-phrase search returned 0 hits on families IN the graveyard → word-split + stems). Round-7 reviewer hypotheses adjudicated: idio-skew = closed low-vol family (skew_low/max_low, FILTER already), CF-volatility = closed earn_stab family (b5 flat-negative), inventory-EAD = conditional queue (now unblocked). Panel doc: aegis-finance `AI_PANEL_2026-07-26.md`.

**2026-07-26 EOD — Round 8 (4 reviews) + Build 3 TRIAL-TGT-REBUILD: REJECT, family closed (cumulative 155).** Target-price family un-voided on nominal ptgdet + ibes_adj split-guard (drop straddling targets — NO adjustment arithmetic) and adjudicated: raw implied upside strongly PERVERSE (largemid −90 bps/mo t −3.62; small −199 t −7.21 — Da-Schaumburg optimism bias reproduced); PSZ low-dispersion conditioning moves the predicted DIRECTION (−90→−43.5) but never the sign (IC t −3.77). Confirm never opened. Analyst-source pickers now 0-for-3. Low-upside mirror admissible-not-queued (22-45% turnover → house law predicts net death). Round-8 adjudication (`AI_PANEL_2026-07-26B.md`): **GPT's Layer-2 argument + regime-analog retrieval engine ADOPTED as the post-freeze Brain direction** (INSTR-REGIME-ANALOG queued: deterministic k-NN over daily macro state vectors, LLM narrates only); DeepSeek hallucinated receipts corrected (no "INSTR-REVERSAL"; sentiment never tested — PIT-barred, not dead); NN-for-trading unanimously refused (matches VOC bar); Gemini's ordering Q answered: CZ-CALIB/HARNESS-VALID before Chen-Velikov (validate the ruler before re-measuring). Queue: calibration pair → cost model → JM2 + REGIME-ANALOG → ceiling ~196 → freeze.

**2026-07-26 night — Calibration pair run (instruments): HARNESS VALIDATED + the contrarian-t exhibit.** INSTR-HARNESS-VALID: all 3 proxy-factor bars met vs Ken French (EW mkt 0.927≥0.90; small−largemid vs SMB 0.778≥0.60; mom excess vs UMD 0.645≥0.40) — panel plumbing validated for the paper; Chen-Velikov re-measurement unblocked. INSTR-CZ-CALIB (13 matched signals vs OSAP SignalDoc): declared expectation rank corr>0 REFUTED — **rank corr = −0.544 (p 0.055): the more celebrated the published t, the deader the signal in 2004-2018** (accruals/asset-growth inversions drive it; GP-class moderates survive). Sign agreement 0.923 + harness pass = decay structure, not harness defect (frozen disambiguation). Median level ratio 0.378. Paper exhibit: "published t-stat is a contrarian indicator." **Murat's PIT question answered with receipts:** all forecast/event backtests use as-of dates (anndats/rdq/filing dates) — nothing from today; historical NEWS backtests deliberately don't exist (no survivorship-clean free PIT archive; GDELT unstable) — news runs forward-only; the PIT-safe route to his news thesis = **8-K event-flow family queued as batch-10 stub** (EDGAR, timestamped, free, survivorship-clean structured news).

**2026-07-26 late — INSTR-COST-MODEL (KO invariance spreads): gates pass, BRAIN-008 AFFIRMED + strengthened.** Corwin-Schultz/Roll infeasible on our pull (no daily high/low or return series) → Kyle-Obizhaeva ECTA-2016 eq.33 quoted spread (ln s̄=−3.07, exponent −1/3, W*=800k; formula verified from the paper PDF) from vol_d+dollar_vol. Sanity gate PASS (largemid median half-spread 4.2→3.4 bps, small>largemid; units confirmed); regression guard PASS (flat path byte-identical, 1.96/+23.2). Re-measures: gp_base confirm t 0.89→**1.11** (half) / 0.97 (full-spread stress); gp_ead confirm **t 1.45** / 1.31 — flat 50bps was OVER-penalizing the low-turnover small book. Honest counter-implication: largemid realistic spreads ~3-4 bps « flat 25 → cost-killed largemid rejects with real IC (si_trend +~14 bps/mo relief) were over-penalized → **INSTR-COST-REMEASURE-REJECTS now admissible** (one deflated registration, AND-rule intact; queued for decision, not run). Harness gains optional per-name cost_frame (flat path unchanged).

**2026-07-26 night2 — Round 10 + INSTR-COST-REMEASURE-REJECTS: COHORT EMPTY, shelf permanently closed.** Frozen mechanical rule (largemid, non-contaminated: t_ic≥2 AND t_gross≥1.5 AND t_net<1.5 = graduation-but-for-costs) committed BEFORE application → returned ZERO signals. Receipts: best gross among rank-real rejects = net_issuance_low **1.48** (0.02 below bar — cannot graduate even at zero cost); gross-passed-net-failed set literally empty across 155 candidates. **Paper finding: in large/mid caps, costs were never the sole executioner — every rejection was informational (arbitraged away), coherent w/ CZ-CALIB fame-decay + KO ~3-4bps realistic spreads.** No KO re-scan needed; no further cost-model appeals. Round-10 adjudication: both reviews aligned (YES-with-guardrails on remeasure — executed; guardrails held: rule frozen pre-application, empty = final). GPT's **belief-engine/state-estimation** proposal ADOPTED as the REGIME-ANALOG design spec (analog retrieval over macro descriptors + belief states w/ confidence trajectories + evidence lists; LLM narrates, deterministic engine allocates; descriptive phase first). Next: JM2 + REGIME-ANALOG build (the allocation program), then batch 10 (8-K), ceiling ~196, freeze.

**2026-07-28 round 12 RUN — TRIAL-EVENT-8K-FILTER: NO GRADUATION, killed by its
own control.** EDGAR acquisition clean and reusable: 4,860 daily indexes
2004-2024, **0 failed days**, 1,530,116 8-K originals, 30,558 filers; plus a
shared submissions pass over the 10,354 in-universe filers (13,444 fetches, 0
failures) that serves BOTH registrations (8-K item codes + 10-K document URLs).
New CIK bridge (CRSP historical names x EDGAR cik-lookup-data.txt, survivorship-
neutral, 88.5% of universe permnos) replaces the absent `cik` column.
**Result:** Arm B cleared its frozen bar (-5.95% 3m, t -7.06) and is NOT
claimable -- the -12mo pseudo-event control, registered as "expected ~0",
returned **-6.79%, t -11.33**. Attrition audit: Arm B keeps 32% of events vs Arm
A 64%, gap driven by ONE filter (65% vs 36% dropped as "not in segment" at
formation) -- distressed names fall out of the liquid universe before they file,
so Arm B silently excludes the worst cases. Calendar-time agrees (B -80 bps/mo t
-1.50 vs A -229 t -11.1). Reading: distress-8-K "drift" = firm-level distress
persistence + eligibility selection, not filing-date information; these names
were worse 12 months EARLIER. **Confirm window NOT opened** (uninterpretable
explore must not spend the held-out window); kill clause NOT invoked (needs a
non-negative cohort); family UNADJUDICATED, successors need a new registration
with eligibility frozen pre-event. NEG_RESULTS §20.
**Two departures declared BEFORE any data touch** (module 40047ba / 4ee7a40):
8-K deciding metric moved to 3-CALENDAR-MONTH from the first month-end after
filing (no daily CRSP for the general universe; bar unchanged), and TEXT-LAZY
coverage shrunk to 10-K only (fetch-time-bound at 8/s, not disk -- the pipeline
never persists raw filings). Acquisition hardening earned the hard way: the
first walk died on `master.idx`, the dateless QUARTERLY AGGREGATE that the
freeze BANS as an event source and that a loose glob had matched -- only SEC's
403 stopped it being ingested silently. Now regex-pinned to `master.YYYYMMDD.idx`,
per-year checkpointed, and >2% day-failure raises instead of yielding a thin
cohort.

**2026-07-28 round 12 RUN 2 — TRIAL-TEXT-LAZY: REJECT, family CLOSED, and its
fallback trigger was an artifact.** Text pull completed clean: 72,061 10-K
filings, **0 failed**, 12 retries, 358 min; 62,982 permno-month pairs / 7,392
permnos; per-filing link 86.9% (1,609 ambiguous dropped). **Picker fails
cleanly** — best cell `text_jac`/small **net t 0.87** vs bar 2.0 — and fails on
ALPHA, not costs (gross t 1.26 → net 0.87), so it does NOT belong on the closed
cost-killed shelf. Honest positive: treatment IC t 6.53/7.47 clearly exceeds
control 1.34/2.94, so the Lazy-Prices information IS present in our data and is
worth **11 bps/mo at t 0.87** long-only — the pre-registered decay measurement,
delivered. **The pre-declared FILTER fallback (changer cohort t ≤ −2.0) appeared
to fire at t −15.03 and DOES NOT COUNT:** Arm A — the same filings scored against
a RANDOM DIFFERENT FIRM — fires it too at t_NW −8.39, 80% of treatment
magnitude. Supporting: monthly obs of 3m returns overlap 2/3 (NW(3) cuts −15.03
to −9.74 — a correction, not the kill), and the cohort is **82–89% the same names
month over month**, a persistent characteristic (structurally odd filings), not
an event set. **Spec defect logged: the picker had a control arm, the fallback
trigger did not.** New house rule — *every pre-declared fallback trigger must
name its own control arm and overlap correction at registration time; a fallback
is a hypothesis and does not skip the design the primary had to pass.* This is
the **second consecutive trial invalidated by its control arm** (8-K was the
first): two for two in one round is the house discovering its treatment effects
were mostly design. Confirm window untouched by both. Cumulative candidates
unchanged at **158**.

**2026-07-27 round 12 open — SWEEP ADJUDICATED + BATCH 10 REGISTERED (reframed; cumulative candidates 158).**
External sweep (`aegis-finance docs/research/RESEARCH_SWEEP_2026-07-27.md`, 42
re-matched sources; all harness "refutations" VOID — killed agents tallied as
refutes) adjudicated in `AI_PANEL_2026-07-27F.md`. **Registered (freeze this
commit): TRIAL-EVENT-8K-FILTER** (batch 10 REFRAMED picker→distress exclusion
screen per Lerman-Livnat — drift lives on the short leg, good news reacts at
event date; items {1.03, 2.04, 5.01} frozen, daily-index PIT, 63td deciding,
Item-2.02 picker DECLINED: PEAD closed/inverted) **+ TRIAL-TEXT-LAZY** (CMN
Lazy Prices post-publication test, text_cos/text_jac, prior WEAK long-leg,
publishable either way; registered BEFORE any EDGAR text pull). **Declined
with receipts:** Cop/cash-profit re-spec of gp-small = RE-LITIGATION (batch 2
already ran the head-to-head: gp +27.8 t 2.35 vs cash_prof +12.9 t 1.26 small
— our data answered; HXZ external doesn't override); rebalance-date
randomization as live-lane change = FREEZE VIOLATION + paper lanes pay no
price impact (adopt as future-lane seed default + paper citation, NBER 33554);
vol-target refinements deferred post-freeze (2/10 markets significant;
TSMOM-XA spec frozen). **Paper repositioning adopted:** McLean-Pontiff Fig 1.B
is prior art for −0.544 → LEAD = method + empty cost-killed cohort; −0.544
demoted to supporting w/ SignalDoc-own-construction robustness arm queued.
Verified: "Reviving Anomalies" (SSRN 6468806) = NN-forecast overlay on anomaly
rules — the complexity class we refused, cite-and-position, NOT adverse to the
empty cohort; Berkin-Wang = long-only but GROSS, alpha in smallest quintile
(the regime Chen-Welch kills net). LLM/agent-alpha closure receipts → NEG_RESULTS
§19 (Kim-Muhn-Nikolaev WITHDRAWN; FINSABER 2004-2024 kills FinMem/FinAgent
net). 10b5-1 2023 break note added to TRIAL-CMP-INSIDER-IC (sales signal
destroyed post-amendment; our buys-side signal unaffected but pre/post-2023
pooling flagged for the Oct refresh audit). Runs (EDGAR pulls + scans) =
next research session (opus). Then: ceiling re-check at 158 → FREEZE → paper.

**2026-07-26 round 11 — THE ALLOCATION PROGRAM: JM2 REJECT + BELIEF ENGINE LIVE.**
**INSTR-REGIME-JM2** (inflation-gated rotation, post-hoc-repair provenance
declared at freeze 470ed0f): explore FLATTERED the repair (12.2% CAGR, 2008
+32.4%, better than JM1 everywhere) → confirm **REJECT, gate made 2022 WORSE
than JM1 (−23.9% vs −21.6%, t −1.18)** — 2022's bond crash was real-rate-driven
(T10YIE fell through the worst of it), so the breakeven-momentum gate routed
risk-off INTO TLT. Zero-weight declaration EARNED; single-trigger regime
rotation CLOSED w/ two receipts (NEG_RESULTS §18). **INSTR-REGIME-ANALOG phase
1 LIVE** (descriptive, never arms): macro_analog.py k-NN over 15-feature daily
descriptor (6,053 vectors 2002-07→2026-07; DBAA−DGS10 substitutes ICE-truncated
HY-OAS, GC=F substitutes removed LBMA fix — disclosed), episode clustering,
forward dists 3/6/12/24m, **283 BeliefStates in ledger/belief_states.jsonl**
w/ trajectories; face validity: 2020-03 retrieved GFC+2002, 2021-12 retrieved
Oct-2007 top, confidence sags in stress; 7 tests green. Round-11 adjudication
(`aegis-finance AI_PANEL_2026-07-26E.md`): Chen-Welch 2026 (7 bps/mo post-2005
non-micro) VERIFIED → paper reference; GPT's SSRN 6962678 unverifiable;
DeepSeek narrated the unbuilt belief engine as done (corrected); episodes +
agreement-confidence ADOPTED+built, Bayesian/failed-thesis = phase 2;
"close Phase I now" modified-refused (batch 10 + ceiling first). Batch-10
prep: 8-K prior-check clean; zombie/rate-cut **DATA-BLOCKED on xint** (not in
any pull — next WRDS tap). Next: batch 10 (8-K) → ceiling ~196 → FREEZE.

## 2026-07-22: STRATEGY FACTORY + BRAIN-008 (second survivor) + FULL WRDS HAUL

- **Strategy Factory** built (explore 2004-2018 / confirm 2019-2024 held out;
  docs/STRATEGY_FACTORY.md). Batch 1 (20 price/vol signals): ZERO graduates —
  Murat's dip-buy theses adjudicated and rejected. Batch 2 (10 fundamentals):
  zero largemid graduates, but small-cap gross_prof survived the pre-registered
  honest-cost re-test (50bps t 1.96; 75bps t 1.57).
- **TRIAL-BRAIN-008-grossprof-small: CONFIRM PASS** (one run, held-out 72mo):
  +24.1 bps/mo net (explore said +23.2 — replicated), IC t 4.29 OOS. Caveats:
  DSR 0.098 (n_trials=61), FF6 alpha negative (factor-tilt risk), NW t 0.77.
  **Second survivor → BRAIN-007 fusion pre-registration RE-OPENS.** Next:
  forward small-cap-quality paper lane (attended seed) + 1963-2001 robustness.
- **WRDS harvest #2+#3 (two Duo taps, zero failures, 629MB backed up):**
  seg_customer 667k links (Cohen-Frazzini → TRIAL-THEME-SUPPLY unblocked);
  13F mgr/breadth/top-10 best-ideas (3.6M rows) 1980→present; short interest
  5.2M; IBES recs 6.4M + price targets 2.5M; CRSP+funda+fundq+dsf-aggregate
  extensions back to 1963/1971; catalogs for comp_pit (12), optionm (578),
  ravenpack_trial, wrdsapps. Congress archives downloaded free (senate 8,350
  txns + kadoa 437 filers).
- Queued instruments: INSTR-GEMINI-SCORE, INSTR-CONGRESS-HIST,
  INSTR-OVERFIT-CEILING, INSTR-RL-ALLOC (see STRATEGY_FACTORY.md).

## 2026-07-21 (PM): PROMOTION EXECUTED — BRAIN-003 is live in aegis-finance

The INTEGRATION.md protocol ran end-to-end (human-authorized "adopt it"):
- Insider panel EXTENDED 2006→**2026Q1** (5 new SEC quarters + re-classify;
  852,512 purchases, 107,351 opportunistic; panel_end 2026-03-31).
- New `scripts/export_routine_history.py` → compact live-classification artifact
  (`cmp_routine_history.json.gz`, 25,020 insiders + 3,648 recent opportunistic
  buys, 0.22 MB) — closes the live false-zero gap the bundled scorer had.
- aegis-finance side: TRIAL-CMP-INSIDER-IC pre-registered (registry + doc),
  `insider_cmp:` forward collector wired beside the T9 clock. Forward IC clock
  runs from the next deploy. **Quarterly maintenance:** re-run download →
  build_insider_panel → export_routine_history, re-commit the artifact there.

## Pipeline status (L0 → L5)

| Layer | What | Status |
|---|---|---|
| L0 data | EODHD panel (direction-check) | ✅ built + cached (`data/panel_2017`, `_clean`) |
| L0 data | **CRSP panel (paper-grade)** | ✅ **BUILT** — 276 mo (2002→2024), 11,098 permnos, `data/crsp_panel_2002/` |
| L0 data | Compustat annual + quarterly, CCM link, IBES | ✅ harvested → `data/wrds_raw/` (fundamentals, rdq, revisions) |
| L1a events | openFDA approval feed | ✅ harvested 16,195 events 2002-2026 (2,742 NDA/BLA) |
| L1a events | sponsor→ticker PIT mapping | ⬜ next — CCM link + IBES cusip now available offline |
| L1b/c narrative + hypothesis | **LLM perception (DeepSeek)** | ✅ built — neutered situation→calibrated P, forward-only, never allocates |
| L2 signals | GKX price big-three | ✅ built (dead net of costs — see trials) |
| L2 signals | **insider collector (SEC bulk)** | ✅ built + 10 tests (CMP routine/opp classifier); BRAIN-003 run pending |
| L2 signals | PEAD / revisions / supplier | ⬜ next, each a new pre-registered trial |
| L3 combiner | shallow GBM + ≤2-layer MLP ranker | ✅ built |
| L4 gate | DSR vs cumulative n, PBO, survivorship bound | ✅ built |
| L4 harness | walk-forward + costs + **hold-band turnover control** | ✅ built |
| L5 forward | **event ledger — FORWARD CLOCK RUNNING** | ✅ 7 real pre-registered PDUFA calls (Jul-Sep 2026); Brier-scored via yfinance at maturity |
| L5 forward | promotion to main-repo forward clocks | ⬜ manual, when a candidate survives |

## Trials run (all pre-registered, results final)

- **BRAIN-000** (EODHD) — REJECT. Surfaced OTC adjusted-close corruption (→ clean universe).
- **BRAIN-001** (EODHD clean) — REJECT on merits. GKX price factors don't beat universe
  net of 25 bps; **turnover drag (~45 bps/mo) is the killer** → hold-band added.
- **BRAIN-002** (CRSP, hold-band) — **REJECT (2026-07-21).** First paper-grade backtest.
  Price big-three GBM-ranked don't beat the EW CRSP universe net of 25 bps (net excess
  t=-2.80); leak check PASSED. Price factors permanently demoted to combiner-input-only.
- **BRAIN-003** (opportunistic insider, CRSP) — **FIRST NON-REJECT (2026-07-21).**
  Survives kill conditions in **large/mid caps** (+17 bps/mo vs EW t=1.40; FF5+UMD alpha
  +102 bps/mo t=1.89; post-2015 t=1.30), **null in microcap** — vindicating the cap fix.
  Leak PASSED; PBO 0.41; deploy gate NOT met (DSR 0.26). Weak-positive prior. **PROMOTABLE**
  (`export/opportunistic_insider/`, scorer `signals/insider_scorer.py`).
- **BRAIN-004** (PEAD/SUE) — **REJECT.** Strong gross surprise-drift in microcap (gross t=3.0)
  dead net of costs (B net t<1 both segs; B-A spread t=0.54). Leak-checked clean.
- **BRAIN-005** (revisions) — **REJECT.** Leak bar caught a benchmark-mismatch bias (noise gross
  t 4.0/5.9 → void); fixed (coverage-universe benchmark), re-run → the "edge" was the bias, not
  signal (B net t<1). A clean false-positive save.
- **BRAIN-007** (fusion) — **NOT RUN.** Only 1 signal survived; fusion needs ≥2. Re-opens later.

## The one blocker — CLEARED (2026-07-21)

WRDS account re-enabled by support; the whole harvest is done. Two Duo taps pulled
CRSP + Compustat (annual/quarterly) + CCM link + IBES (~7.4M rows) in one session, and
the CRSP paper-grade panel is built. **We now read local parquet — no more WRDS pulls.**
TRIAL-BRAIN-002 is unblocked and runs fully offline.

## Next: run the pre-registered trial (offline, no WRDS)

```
.venv\Scripts\python -m scripts.run_trial_002    # ONE run on data/crsp_panel_2002 -> record in trial doc
```

## Backups (OneDrive\AegisBackups)

- `eodhd_archive_2026-07-19.tar` (1.07 GB, 50,471 entries)
- `fda_approvals_2026-07-20.parquet` (16,195 events)
- `wrds_2026-07-21/` (184 MB) — raw tables + built CRSP panel + `WRDS_DATA_PREVIEW.xlsx`

## Buildable now without WRDS (candidate next chunks)

1. Insider Form-4 collector (SEC EDGAR is public) → opportunistic-vs-routine signal,
   new pre-registered trial. Strongest documented edge in the roadmap.
2. FDA event-drift study design doc (needs price+ticker link to run — partial until WRDS).
3. LLM narrative-extraction spike on the FDA/EDGAR text (L1b), scored into the event ledger.
