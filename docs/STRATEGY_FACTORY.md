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

**Standing:** BRAIN-008 = second survivor (weak). Next steps per protocol:
(1) forward paper-lane pre-registration in aegis-finance (attended seed —
Murat flips the flag; small-cap-quality book vs small-EW control);
(2) **BRAIN-007 fusion pre-registration RE-OPENS** (insider + gp-small,
weights frozen before any fusion backtest); (3) robustness on the 1963-2001
extension once harvested (one run, pre-registered). No skill claims — the
forward clocks are the only scorecard.
