# Strategy Factory — explore/confirm protocol (pre-registered 2026-07-22)

## Why this exists

Murat's directive (2026-07-22): "test everything — hundreds of simple, stupid
strategies — find which ones actually win, then combine them into the brain.
Overfit if you must; I want to see the ceiling." Three independent AI reviews
(ChatGPT / Gemini / DeepSeek, saved in aegis-finance
`docs/research/AI_PANEL_2026-07-22.md`) converged on the same architecture:
a **library of simple hypothesis-driven signals, scanned at scale, with the
survivors promoted through the existing discipline gate** — and the LLM used
for perception/explanation, never allocation.

This document is the tamper-evident commitment for how that scan works,
written and committed BEFORE any scan result exists.

## The two tiers (the honest version of "overfit on purpose, then slay")

**EXPLORE tier (this doc's subject).** A fast decile scan of many signals on
the CRSP panel, restricted to the EXPLORE WINDOW. It is hypothesis GENERATION.
Its numbers are never evidence, never quoted as performance, never merged into
any track record. Running 40 scans here is deliberate multiple testing — that
is the point — and the cost is paid at confirm time (below).

**CONFIRM tier.** Each graduating signal gets ONE pre-registered trial
(registry + doc, normal BRAIN-nnn rules) evaluated on the CONFIRM WINDOW,
which the explore scan never touches. Deflated Sharpe at confirm uses
`n_trials >= total explore candidate count` (all scans count, including
failures — that is what makes the survivor's DSR honest).

## Windows (frozen)

- Panel: `data/crsp_panel_2002` — CRSP 2002-01..2024-12, 276 months,
  11,098 permnos, real delisting returns.
- **EXPLORE: test months 2004-01 .. 2018-12** (~180 months).
- **CONFIRM (held out): test months 2019-01 .. 2024-12** (72 months).
  The scan harness hard-stops at the boundary; confirm data is read only by
  the one pre-registered confirm run per graduate.

Contamination note, stated up front: TRIAL-BRAIN-001/002 already ran
mom_12_1 / st_reversal / vol_6m / illiq over the FULL sample (incl. the
confirm window) as a GBM combo and REJECTED it. Those four are included in
batch 1 as calibration references only, flagged `contaminated=True`; they
cannot graduate on confirm-window "freshness" grounds.

## Scan mechanics (identical economics to the walk-forward harness)

Per signal × segment: at formation month m, rank the declared-direction score
over eligible names in the segment; hold the top decile equal-weight for month
m+1; 30% hold-band incumbency (the TRIAL-BRAIN-001 turnover lesson); 25 bps
one-way costs on traded value. No model, no fitting — the signal IS the score,
so there is nothing to train and nothing to leak beyond PIT errors in the
signal itself (guarded by tests/test_factory.py alignment tests).

Segments (by formation-month dollar volume rank):
- `largemid` — top 1000. The primary segment: costs are real there.
- `small` — ranks 1001..3000. Reported, but 25 bps understates true small-cap
  costs; treat small-only results as directional.

Metrics per scan: mean net excess vs segment EW (bps/mo), t(net excess),
t(gross excess), monthly Spearman rank-IC vs next-month return (mean, t),
turnover, net CAGR, max drawdown.

## Batch 1 (price/volume family, 20 signals — frozen list)

Each signal is one economically-stated hypothesis (see
`aegis_brain/factory/batch1_price.py` for mechanisms + directions). Notable
pairs built to adjudicate Murat's theses directly against the literature:

- `dd_from_12m_high` (long DEEPEST drawdown — Murat's "buy the 50% dropper")
  vs `high_52wk_prox` (long CLOSEST to 52-wk high — George-Hwang). Mirror
  twins; the scan decides which side of this variable pays.
- `dip_3m` (long biggest 3-month losers — Murat's dip-buy at monthly horizon).
- `consistency_12m` (fraction of up-months — "steady winners", frog-in-the-pan).
- `max_ret_6m` LOW (avoid lottery spikes — the anti-"story stock" filter).

Candidate count for DSR at confirm: **20 signals × 2 segments = 40.**

## Graduation rule (frozen before results)

A fresh (non-contaminated) signal graduates to a pre-registered CONFIRM trial
iff, in the `largemid` segment: t(net excess) >= 1.5 AND t(IC) >= 2.0.
At most the top 5 by t(net excess) graduate from this batch. Everything else
is recorded and closed. Sign-flipping a failed signal is a NEW candidate in a
future batch, not a free retry.

## Pre-committed reading of results

- Explore numbers = candidate ranking only. The phrase "beats the market" is
  banned until a graduate survives its confirm trial AND its forward clock.
- Expected outcome, stated honestly: most of these 20 are known-marginal in
  the post-2000 US cross-section net of costs; 0–3 graduates would match the
  literature. A zero-graduate batch is a valid result and feeds PLAN_B.
- Factory excess is vs the EW universe (cross-sectional skill), NOT vs SPY.
  Beating SPY additionally requires the market-timing/allocation layer, which
  is a separate question (lanes, trend overlay) — do not conflate them.

## Roadmap position

Batch 2 (pre-registered before running): fundamentals/quality from the local
Compustat harvest (gross profitability, accruals, asset growth, F-score-lite,
net issuance) — the Novy-Marx net-of-cost survivor class. Batch 3: event/alt
(insider variants, PEAD interactions, congress, 13F best-ideas, FDA drift,
theme/supplier baskets = TRIAL-THEME-SUPPLY). Fusion (BRAIN-007) re-opens when
>= 2 confirmed survivors exist.

## Batch 2 (fundamentals/quality, 10 signals — frozen 2026-07-22 BEFORE running)

Annual Compustat via the PIT FundStore (`factory/fundamentals.py`: CCM link,
6-month reporting lag, 18-month staleness limit). The net-of-cost survivor
class — annual data turns over once a year, so the turnover drag that killed
batch 1 is structurally absent. Frozen list (directions declared in
`factory/batch2_fundamentals.py`): gross_prof(+), oper_prof(+),
asset_growth(−), accruals_cf(−), net_issuance(−), btm(+), roe(+),
cash_prof(+), capx_at(−), fscore_lite(+).

Same scan config, same segments, same graduation rule (largemid t_net ≥ 1.5
AND t_ic ≥ 2.0, top-5 cap). **Cumulative explore candidates: 40 + 20 = 60**
(confirm-stage DSR deflates by this number).

## Batch 3a (alt-data, 8 signals — frozen 2026-07-22 BEFORE running)

From the 2026-07-22 harvest (`factory/altstores.py`, PIT lags stated there).
Full-window (2004-2018): max_dret_low_D(−), ivol_low_D(−), amihud_D(+),
si_chg_low(−), breadth_chg(+), rec_mom(+). Short-window 2014-01..2018-12
(post-STOCK-Act congress coverage, stated a priori): congress_buys(+) =
INSTR-CONGRESS-HIST, gemini_score(+) = INSTR-GEMINI-SCORE (dip≥40% +5,
insider +10, congress +10; the narrative +5 is OMITTED — no PIT source — 
documented, not approximated). Same graduation rule; short-window signals
additionally flagged low-power (60 test months).
**Cumulative explore candidates: 61 + 16 = 77.**

Design note from the day's literature sweep: long-only + hold-band + low
turnover is exactly the Novy-Marx-Velikov net-of-cost survival recipe, and
Muravyev (JF 2025) shows short-leg anomaly returns die at borrow costs —
the factory's long-only constraint is now literature-backed, not just a
practical choice. The "disappearing index effect" (Greenwood) removes index
add/delete from the candidate queue; buyback/spinoff events remain queued
(need corporate-event data, future batch).


## Batch 5 (winner-picking interactions/streaks/13F — frozen 2026-07-24 BEFORE running)

15 signals from the 2026-07-24 research sweep (two web agents: replication
evidence vs McLean-Pontiff / Chen-Zimmermann / JKP / Chen-Velikov; novel
2019-2026 low-turnover ideas). Standing hurdle recorded: Chen-Velikov —
average anomaly nets ~4 bps/mo post-publication after costs. DEAD-prior
candidates are scanned anyway (cheap; the receipt is the product).
Stores: annual FundStore, NEW QuarterlyStore (rdq-anchored PIT, ffill<=6mo),
insider/SI/13F frames at filing-month availability (13F +2mo lag).
`factory/batch5.py`; directions declared in code. Cumulative explore
candidates: **90 + 30 = 120** (15 signals x 2 segments).

| signal | dir | prior (from replication sweep) |
|---|---|---|
| qual_mom | + | STRONG-ish: momentum among top-half GP/A (Novy-Marx interaction; both legs replicate; interaction itself unvalidated). CONTAMINATION NOTE: 12-1 momentum component ran full-sample in BRAIN-001/002 — graduation needs extra scrutiny |
| earn_stab | + | WEAK standalone (subsumed by low-vol; composite ingredient) |
| gp_mom | + | WEAK (annual fundamental momentum — only cost-viable variant) |
| roa_mom | + | DEAD (GHZ: quarterly fundamental predictors dead post-2003) |
| sue_streak | + | DEAD (PEAD-family; parent dead in liquid names post-2005) |
| insider_cluster | + | STRONG-ish (cluster buys ~2x single-buy returns; small-cap, 1-6mo horizon) |
| insider_si | + | WEAK (thin unreplicated literature; false-signaling counterevidence) |
| rev_conf | + | DEAD (revisions decayed post-Reg-FD; cost-fatal turnover). Same momentum contamination note as qual_mom |
| dtc_low | − | WEAK for long-only (alpha lives in the short leg; usable as screen) |
| defensive | + | STRONG as exclusion screen, WEAK as long-alpha; informative readout = Sharpe/DD not excess bps (noted, deciding metric unchanged) |
| earn_accel | + | MEDIUM-HIGH (He-Narayanamoorthy JAE 2020; post-pub attenuation noted) |
| ea_shift | + | MEDIUM-HIGH (Johnson-So JFQA 2018; rdq-only construction is noisier than WSH data — declared) |
| inst_persist_low | − | MEDIUM (Dasgupta-Prat-Verardo JF 2011; long persistently-SOLD; small/high-IO concentrated) |
| own_dur_t10 | + | MEDIUM (Cremers-Pareek JFE 2016 — TOP-10 PROXY, coarser than true duration; declared) |
| dnoa_low | − | MEDIUM (Hirshleifer NOA-bloat lineage; distinct from total accruals; Chen-Zimmermann-robust family) |

Blocked-on-columns (queued for WRDS batch 4, NOT scanned): RE/ME (Ball et al.
2020 B/M decomposition — needs `re`), inventory/receivables divergence (needs
`invt`/`rect`), payout/duration family (needs `dvc`/`prstkc`). q5 expected-
investment-growth deferred (needs cross-sectional fitting — not a sort).

## Results — batch 3a (run 2026-07-22, explore window only)

`data/factory/batch3a_summary.csv` + `batch3a_daily_rerun.csv` (the three
daily-agg scans re-ran after a tz-normalization bug produced zero months —
a broken pipe fixed, not a retry; the first pass never scanned).

**Graduates under the frozen largemid rule: ZERO.** Adjudications:

1. **si_chg_low (falling short interest), SMALL: +29.8 bps/mo net, t 2.16,
   IC t 6.09** — the batch's standout, same shape as gp-small (small-only).
   High turnover (0.46 one-way) makes costs decisive → pre-registered
   **CAND-SICHG-SMALL-HC** below.
2. **INSTR-CONGRESS-HIST ADJUDICATED: no post-disclosure edge.** t 0.26
   small / −0.34 largemid, IC ≈ 0 (60 months, low power, point estimate
   ~zero). Consistent with the post-STOCK-Act literature; DeepSeek's
   "5-10%/yr" not reproduced. Forward TRIAL-CONGRESS-IC keeps accruing.
3. **INSTR-GEMINI-SCORE ADJUDICATED: the composite LOSES.** Net negative in
   both segments; small-seg IC significantly NEGATIVE (t −2.83) — the
   dip-buy component poisons it, exactly as batch 1 predicted. The
   "will absolutely obliterate the S&P 500" claim is now a recorded
   refutation, not an opinion.
4. Daily-resolution upgrades: enormous ICs (max_dret small t 7.7, ivol small
   t 6.9) that long-only deciles cannot monetize — batch-1's lesson at
   higher resolution. Amihud premium is DEAD post-2002 (small t −3.6 net,
   IC t −9.5): illiquidity is a cost, not a premium, in this window.
5. rec_mom: small IC t 3.3 but 0.59 turnover kills it net (−3.26 largemid).
   Recommendations join estimates (BRAIN-005) as combiner-input-only.

## CAND-SICHG-SMALL-HC (pre-registered before running)

si_chg_low, small segment, cost sensitivity 25/50/75 bps, explore window,
identical mechanics — candidate #78. Survives → confirm run on 2019-2024
under the standard rule (t_net ≥ 1.5 AND t_ic ≥ 2.0 at 50 bps).

**RESULT (run 2026-07-22): FAILS honest costs — CLOSED, no confirm.**
25 bps: +29.8 (t 2.16) · 50 bps: +6.9 (t 0.50) · 75 bps: −15.9 (t −1.15).
The 46% monthly one-way turnover is fatal — the exact opposite of gp-small's
9%. The IC (t 6.09) is real; the tradeable premium is not, at realistic
small-cap costs. SI-change joins the combiner-input-only shelf. (A lower-
frequency variant — e.g. quarterly SI change with a hold-band — would be a
NEW candidate in a future batch, not a retry of this one.)

## Batch 3b (economic links, 3 signals — frozen 2026-07-22 BEFORE running)

`factory/altstores2.py`. Full explore window, standard mechanics/segments:
- **cust_mom(+)** — Cohen-Frazzini customer momentum on the 343k COMPANY
  segment-customer links (normalized-exact name matching; match rate logged;
  unmatched links drop, which UNDERSTATES the effect). This is the
  cross-sectional arm of Murat's suppliers thesis (TRIAL-THEME-SUPPLY's
  basket arm remains a separate future trial).
- **best_ideas(+)** — # managers holding the name top-3 (Cohen-Polk-Silli),
  45d filing lag.
- **tgt_upside(+)** — trailing-90d consensus 12m target / price − 1
  (Brav-Lehavy). The mirror read of Murat's "sell near the target" rule.
**Cumulative explore candidates: 78 + 6 = 84.**

## Results — batch 3b (run 2026-07-22, explore window only)

`batch3b_summary.csv` + `batch3b_tgt_rerun.csv` (tgt_upside re-ran after a
horizon-dtype bug — WRDS returns horizon as STRING '12'; the int comparison
silently emptied the frame; zero-month scan = broken pipe, fixed, not a retry).

**Graduates: ZERO.** Adjudications:

1. **cust_mom (Cohen-Frazzini customer momentum): does not survive as a
   monthly signal.** 70% one-way monthly turnover; net ≈ 0 largemid /
   −31 bps small; IC t only 1.6-1.8. Post-publication decay + the format's
   churn kill it. NOTE: Murat's suppliers THESIS is not dead — the
   TRIAL-THEME-SUPPLY basket arm (slow thematic supplier baskets, not
   monthly link-momentum) is a different, still-open question.
2. **best_ideas (top-3 manager positions): real information in small caps
   (IC t 2.70), net-negative book.** The crude count proxy ≠ CPS's
   weight-tilt construction; a tilt-based variant is a legitimate NEW
   future candidate.
3. ~~tgt_upside: REJECT with prejudice~~ **VOID — DATA ARTIFACT (see batch
   3c post-mortem below). Both directions of this variable are
   uninterpretable as constructed; no reading about targets survives.**

## Batch 3c (refinements from 3b's wrong-side findings — frozen BEFORE running)

Per the sign-flip rule these are NEW candidates, registered before any run:
- **tgt_upside_low(−)** — long LOW implied upside (names at/near their
  analyst targets). 3b showed the high side loses catastrophically; this
  registers the productive mirror as its own candidate.
- **best_ideas_frac(+)** — top-3-holder count NORMALIZED by total
  institutional breadth (fraction of holders with the name as a best idea) —
  closer to Cohen-Polk-Silli's conviction-tilt than the raw count.
**Cumulative explore candidates: 84 + 4 = 88.**

## Results — batch 3c (run 2026-07-22) — and the VOID that matters

`batch3c_summary.csv`. best_ideas_frac: negative both segments → CLOSED.

**tgt_upside_low posted the factory's best-ever explore line (+90.8 bps/mo
net, t 7.12, 8% turnover, 20.7% CAGR) — and it is VOID.** The pre-confirm
diagnostic caught it: the long book's top names show tgt/price ≈ 0.02-0.10
— consensus targets at 2-10% of the traded price, impossible for genuine
coverage. Cause: **IBES ptgdet `value` arrives adjusted for ALL subsequent
splits (through the download date), CRSP `prc` is nominal.** A stock that
splits in the FUTURE shows a tiny adjusted historical target vs its nominal
price → lands in the "near/above target" book → the signal covertly selects
future splitters, i.e. future winners. Textbook look-ahead via vendor
adjustment mismatch. The mirror artifact equally explains batch 3b's
−211 bps "reject" — **both tgt_upside runs are VOID, and the 3b reading
("sell-near-target is backwards") is RETRACTED as unadjudicated.**

Lessons pinned:
- The noise-arm leak bar cannot catch signal-DATA artifacts — only the
  book-composition diagnostic did. A "top-of-book sanity print" is now a
  MANDATORY pre-confirm step for any graduate (added to the process).
- Any IBES level variable (targets, actuals) must be adjustment-matched
  before use: pull `ibes.adj` (or CRSP cumfacpr) at the next WRDS session
  and reconstruct nominal-on-nominal. A properly-adjusted target-distance
  candidate is a legitimate FUTURE registration — after the fix, from
  scratch, both directions void until then.
- t = 7 in an explore scan is not a discovery signal — it is a bug alarm.
  (Recorded as the day's third silent-fragility catch: tz-shifted
  date_trunc, string horizon, split-adjustment mismatch.)

## Queued instruments (from the AI-panel pushbacks — test, don't trust opinion)

Murat's directive 2026-07-22: the pushbacks that were a-priori arguments must
become recorded experiments. Queued, each pre-registered before running:
- **INSTR-GEMINI-SCORE** (batch 3): Gemini's literal point-score composite
  (insider +10, dip +5, narrative-theme +5, mid/small only) as ONE explore
  candidate. Its dip component already failed alone; the composite gets its
  own honest shot.
- **INSTR-CONGRESS-HIST** (batch 3): historical congress-trade signal from the
  public disclosure archives (~2013+), PIT at disclosure date — adjudicates
  DeepSeek's "5-10%/yr" claim on data rather than my skepticism. (Forward arm
  already accruing: TRIAL-CONGRESS-IC.)
- **INSTR-OVERFIT-CEILING** (after batch 3): DeepSeek's "see the ceiling" —
  full-sample in-sample fit of the whole library, reported ONLY as
  (in-sample dream CAGR) vs (explore→confirm collapse), a fragility
  measurement, never a performance claim.
- **INSTR-RL-ALLOC** (after ≥2 confirmed survivors): small RL allocator over
  survivor sleeves, explore-tier; pre-registered expectation = fits explore,
  fails confirm; recorded either way.

## Results — batch 1 (run 2026-07-22, explore window only)

Full table: `data/factory/batch1_summary.csv` (40 scans, 180 test months).

**Graduates under the frozen rule (largemid, t_net >= 1.5 AND t_ic >= 2.0,
fresh only): ZERO.** Best fresh largemid candidates: vol_12m_low
(t_net 0.21, t_ic 1.89), price_level (t_net −0.15, t_ic 2.12) — nothing
close to the bar. Per the pre-commitment, a zero-graduate batch is a valid
result; batch 1 is CLOSED with no confirm trials.

What the scan actually taught (the reason to run it):

1. **Murat's dip-buy theses are now adjudicated, and they lose.**
   `dip_3m` (buy 3-month losers): t_net −1.48 largemid, −2.65 small.
   `dd_from_12m_high` (buy the 50%-dropper): t_net −0.67 largemid, −1.15
   small with significantly NEGATIVE IC (t −3.31) — deep-drawdown names
   keep underperforming, they do not mean-revert at this horizon. The
   information in that variable sits on the George-Hwang 52wk-high side
   (small-seg IC t +3.31), but even that side dies net (0.37 one-way
   monthly turnover eats it). Catching falling knives is not a system; if
   dip-buying ever works it needs a quality/solvency conditioner — that is
   batch 2's question, not a retry of this one.
2. **Rank information ≠ portfolio profit.** Many signals carry real
   cross-sectional information (small-seg IC t: price_level 6.6, ltr −5.7,
   max_ret_low 5.7, vol_12m_low 5.7, skew_low 5.0, consistency 4.3) while
   their long-only decile books still lose to the EW universe net of costs.
   The predictability is concentrated in the SHORT side (predictably-bad
   stocks) and in ranks a long book can't monetize — consistent with the
   anomalies literature and with price factors' demotion to
   combiner-input-only.
3. **The only family with positive net excess is defensive** (low-vol /
   high-price: +4 to +7 bps/mo, t ≈ 0.2-0.4 — indistinguishable from
   noise, but the sole survivor-shaped direction in price/volume space).
4. Seasonality, vol_calm, long-term reversal, and Amihud in a monthly
   decile format are strongly negative here — turnover-heavy formats of
   marginal effects. Dead as standalone lanes.

Conclusion: batch 1 replicates BRAIN-001/002's verdict signal-by-signal —
**long-only price/volume selection does not beat the EW universe net of
costs.** The factory moves to batch 2 (fundamentals/quality from Compustat:
gross profitability, accruals, asset growth, net issuance, F-score-lite —
the literature's net-of-cost survivor class) and batch 3 (events/alt-data),
where every remaining credible edge in this project's data lives.

## Results — batch 2 (run 2026-07-22, explore window only)

Full table: `data/factory/batch2_summary.csv` (20 scans, 180 test months;
FundStore coverage ~4,000 names/month).

**Graduates under the frozen rule (largemid, t_net >= 1.5 AND t_ic >= 2.0):
ZERO.** Best largemid: net_issuance_low (t_net 1.10, t_ic 2.18 — IC clears,
net doesn't), oper_prof (0.45 / 2.38). Batch 2 is CLOSED with no confirm
trials. But unlike batch 1, this batch found a real candidate one segment
over:

1. **The profitability family is the only thing in 60 scans with positive
   net excess everywhere it was tested.** Standout: `gross_prof` in SMALL —
   **+27.8 bps/mo net, t_net 2.35, IC t 6.03, one-way turnover 0.09** — the
   strongest result the factory has produced. Supporting cast, same segment:
   fscore_lite (+17.2, t 1.46, IC t 6.63), cash_prof (+12.9, t 1.26, IC t
   7.90), oper_prof (+10.1). Exactly the Novy-Marx / Ball et al. prediction.
   It does NOT graduate — the frozen rule requires largemid, and 25 bps
   understates small-cap costs. Handled by the book: pre-registered as a
   batch 3 candidate **CAND-GROSSPROF-SMALL-HC** = gross profitability,
   small segment, at 50 bps one-way + half-spread sensitivity table. If it
   survives honest costs there, it goes to confirm.
2. **Post-publication decay is visible in our own data**: accruals_low and
   asset_growth_low are strongly NEGATIVE in this window (small t_net −2.9 /
   −3.1) — the celebrated 1996/2008 anomalies inverted after publication
   (McLean-Pontiff). Value (btm) is flat. Our scan independently reproduces
   the known factor-decay landscape, which is evidence the harness measures
   what it claims to.
3. Quality ICs are large and pervasive (cash_prof IC t 7.9 in small, 2.3 in
   largemid) even where decile books don't pay — profitability belongs in
   the combiner feature set regardless of standalone graduation.

Running conclusion after 60 scans: cross-sectional edge net of costs, if it
exists in this data, lives in (a) small-cap quality — pending honest-cost
re-test, and (b) event/alt-data (batch 3). Large/mid long-only selection on
public characteristics is dead on arrival — consistent with the market
being hardest exactly where capacity is largest.

## CAND-GROSSPROF-SMALL-HC — honest-cost sensitivity (run 2026-07-22)

Explore window, small segment, identical book mechanics, cost sweep
(candidate #61; sensitivity levels are diagnostics of ONE candidate):

| one-way cost | net excess bps/mo | t_net | IC t | turnover 1-way |
|---|---|---|---|---|
| 25 bps | +27.8 | 2.35 | 6.03 | 0.092 |
| **50 bps (pre-registered level)** | **+23.2** | **1.96** | 6.03 | 0.092 |
| 75 bps | +18.7 | 1.57 | 6.03 | 0.092 |

**SURVIVES at 50 bps (and even 75). Graduates to confirm** per the batch-2
pre-commitment — the factory's first confirm-tier trial.

## CONFIRM pre-registration — TRIAL-BRAIN-008-grossprof-small (frozen BEFORE the run)

- **Hypothesis:** small-cap (formation dollar-vol ranks 1001-3000) gross
  profitability (Novy-Marx GP/AT, PIT FundStore) top decile, 30% hold-band,
  survives 50 bps one-way on the HELD-OUT confirm window 2019-01..2024-12 —
  data no factory scan has ever touched.
- **One run.** Frozen mechanics: top_frac 0.10, hold_band 0.30, cost 50 bps,
  min_names 100. No parameter changes after seeing results, ever.
- **Power note (honest):** at the explore effect size, expected t over 72
  months is only ~1.2 — the window cannot deliver 2+ even if the effect is
  fully real. Thresholds are set accordingly and committed here.
- **Decision rule:** KILL if mean net excess <= 0 OR mean IC <= 0.
  PASS (prior strengthened) if net excess > 0 AND t_net >= 0.8 AND
  t_ic >= 1.5. STRONG PASS if additionally t_net >= 1.5. A PASS's next step
  is a FORWARD paper clock (seed-a-lane, attended) — never direct arming,
  never a skill claim.
- **Deflation:** DSR reported with n_trials = 61 (all explore candidates);
  sr_variance estimated from the cross-section of batch 1+2 scan Sharpes.
  FF6 alpha (Newey-West) reported as a diagnostic.
- **Second-survivor clause:** a PASS makes this the candidate second survivor
  beside BRAIN-003 insider → BRAIN-007 fusion pre-registration re-opens.

### RESULT (one run, 2026-07-22): **PASS** — with both hands shown

`data/factory/confirm_gpsmall.json`. Held-out 2019-01..2024-12, 72 months:

- **Net excess +24.1 bps/mo** — the explore estimate was +23.2; the point
  estimate replicated almost exactly out of sample. t_net 0.89 (rule's
  statistic; ≥0.8) — Newey-West t is 0.77, disclosed: the PASS is by the
  letter of the frozen rule and is threshold-sensitive.
- **IC t 4.29 out of sample** — the rank information is unambiguous.
- **DSR 0.098** (n_trials=61): after honest deflation the Sharpe evidence is
  WEAK. Deploy gate emphatically NOT met. Weak-positive prior, same class as
  BRAIN-003.
- **FF6 alpha NEGATIVE** (−3.3%/yr, t −1.06; SMB beta 1.17): the book beats
  the small EW universe but NOT a factor-mimicking benchmark — the edge may
  be harvestable factor tilt rather than stock selection. A forward lane
  tests the investable claim (beats small-cap EW net), not an alpha claim.

### Robustness — TRIAL-BRAIN-008-EXT (1963-2001 extension; run 2026-07-22)

Frozen mechanics, one run, extension panel (live months 1982-11..2001-12 after
the thin-coverage guard): **SUPPORTIVE** — +18.8 bps/mo net at 50 bps
(NW t 1.39), IC t 3.06, despite 3x the turnover of the modern window. The
signal is now positive in three independent windows spanning 42 years:
1982-2001 (+18.8), 2004-2018 (+23.2), 2019-2024 (+24.1) — same spec
throughout. Still not deploy-gate evidence; it is the strongest forward-lane
prior this project has produced.

### Fusion — BRAIN-007 re-opened and run (see TRIALS/TRIAL-BRAIN-007-fusion.md)

Composite (insider + gp, frozen equal-weight z) **SURVIVES: +15.3 bps/mo net,
NW t 1.66, beats best single (1.61) with 3.6x the names** (312 vs 87). Noise
arm clean. The composite is the natural candidate book for the forward lane.

**Standing:** BRAIN-008 = second survivor (weak). Next steps per protocol:
(1) forward paper-lane pre-registration in aegis-finance (attended seed —
Murat flips the flag; small-cap-quality book vs small-EW control);
(2) **BRAIN-007 fusion pre-registration RE-OPENS** (insider + gp-small,
weights frozen before any fusion backtest); (3) robustness on the 1963-2001
extension once harvested (one run, pre-registered). No skill claims — the
forward clocks are the only scorecard.
