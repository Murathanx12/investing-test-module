# TRIAL-BRAIN-003-opportunistic-insider  (v2 — revised before any data)

**Registered:** 2026-07-21 (UTC). **Revised:** 2026-07-21, still BEFORE any SEC insider
datum has been fetched, parsed, or joined to a return (the collector is under construction;
no data observed). Revision is in response to *external methodological review* (five-AI
audit), NOT to any data — so pre-registration integrity holds. Changes from v1 are logged
in "Revision log" below.
**Registry row:** `TRIALS/registry.jsonl` (cumulative n = 18)
**Grade:** paper-grade backtest (CRSP returns) — a *prior-setting* run, not a deploy gate (see "Win condition").

## Win condition (reframed — read first)
The backtest gate (below) may be **structurally unclearable** for a single-digit-bps/month
net edge on ~18 years of data: a net Sharpe of 0.5 needs ~33yrs to reach t=3.4. So passing
the gate is **not** the definition of success and its likely failure is **not** a project
dead-end. The backtest does two honest jobs only: (a) kill an obviously-dead idea, (b) set a
defensible prior + effect-size estimate. **Conviction is earned forward**, by the calibration
ledger (`events/ledger.py`) scoring pre-registered insider-cluster calls. This trial FEEDS
that ledger; it does not gate deployment.

## Hypothesis
On survivorship-free CRSP 2006→2024, a long-only portfolio of stocks that had an
**opportunistic, non-10b5-1** insider **open-market purchase** in the trailing window
(entered at the FILING date, low-turnover long hold), earns positive net-of-cost abnormal
return vs a size/characteristic-matched benchmark. Mechanism (Cohen-Malloy-Pomorski 2012):
routine trades are uninformative; the residual opportunistic *purchases* signal private
conviction and predict future fundamentals.

## Literature prior & the cap-segment question (the key v2 fix)
CMP (JF 2012): opportunistic ≈ **82 bps/mo VALUE-WEIGHTED** (~180 bps EW), routine ≈ 0.
**Crucial nuance surfaced in review:** value-weighted ⇒ large-cap-tilted, and the
outsider-mimicking literature (Rozeff-Zaman; the Australian director-trades study) finds
tracking insider trades net of costs works in **large/mid caps** and can **lose** in
microcaps — insiders hide their trades in liquid flow. The low-turnover "not-sold"/long-hold
variants survive net (CAPM α ~47 bps/mo, 4-factor ~53 bps at the 1-year horizon).
**So we do NOT assume microcap.** We test cap segments as explicit arms and let the data say
where (if anywhere) the net edge lives. Honest prior: ~50/50 that *some* segment clears a
weak net-positive; large/mid more likely than micro.

## Expected effect size
Opportunistic arm: +20 to +60 bps/mo net abnormal in its best cap segment; routine ≈ 0.

## Signal & classification (frozen)
- **Source:** SEC **Insider Transactions Data Sets** (quarterly flat files, 2006→2024) —
  the tractable bulk source (millions of Form-4 XMLs are infeasible at 10 req/s).
- **Kept transactions:** non-derivative **open-market purchases only** — `TRANS_CODE='P'`
  and `TRANS_ACQUIRED_DISP_CD='A'`. Grants/exercises/tax/sells excluded.
- **10b5-1 exclusion (v2 add) — DATA LIMITATION, reported not hidden:** the SEC *bulk flat
  files* carry NO 10b5-1 column in any year (verified against SEC's schema readme); the
  checkbox lives only in the raw per-filing XML, and only from 2023-04-01. So the bulk-file
  study CANNOT apply a 10b5-1 filter historically. Mitigation: the CMP routine/opportunistic
  classifier already removes the bulk of scheduled/plan-like trades (routine = same-month
  repeat buyer); a future raw-XML pass can add the explicit 10b5-1 drop for the 2023+ tail.
  This gap is a pre-committed known limitation, not a silent one.
- **Routine vs opportunistic (CMP, point-in-time):** an insider (by reporting-owner CIK) is
  **routine** for a purchase if they bought in the **same calendar month in ≥3 consecutive
  prior years**; **opportunistic** otherwise. Insiders without a 3-year history are
  `is_classifiable=False` and DROPPED (not defaulted to opportunistic).
- **Clustering (reported):** #distinct opportunistic buyers per issuer-month — a conviction
  intensity used for the forward-ledger calls; primary backtest signal is the binary flag.
- **Timing:** signal fires on the **FILING date** (`observed_at`), never the transaction date.
- **Issuer→CRSP (PIT):** issuer CIK → ticker → CRSP `permno` via `msenames` ticker history as
  of the filing date; cross-check via `comp.company` cik↔gvkey + CCM link where possible.
  Ambiguous matches dropped; match-rate + drop-count reported.

## Arms
- **Arm A — routine buys (placebo / expected-loss).** CMP: routine ≈ 0. If Arm A ≈ Arm B, the
  classification isn't the alpha source → confound, void.
- **Arm B — opportunistic buys** (hypothesis).
- **Arm C — noise control** (random flag matched to Arm B's monthly count) — gross-t leak bar.
- **Cap segments (v2):** run Arm A & B in **two segments — large/mid (top 70% NYSE-cap)** and
  **micro (bottom 30%)** — pre-registered, reported side by side. No microcap assumption.

## Run spec (frozen)
- Panel: `data/crsp_panel_2002`, restricted 2006→2024. Long-only, equal-weight the flagged names.
- **Primary spec = LOW turnover / long hold:** 12-month hold with a hold-band; monthly entry.
  (The net-surviving insider variants are the low-turnover ones.) A 3-month-hold secondary is
  reported for decay shape only.
- **Cost model (v2): ADV/spread-conditional, not flat 25 bps.** Per-name one-way cost =
  max(25 bps, k · effective-spread proxy), with a microcap penalty scaling on inverse
  dollar-volume (a $50M name can carry ~150 bps). Implemented in `harness/costs.py`; the flat
  25 bps run is reported alongside as the optimistic bound.
- Benchmark: size/characteristic-matched EW within the same cap segment (not the whole universe).
- Metrics: net abnormal mean + t, gross t (leak bar), net Sharpe, **DSR vs cumulative n=18**,
  PBO where computable. ONE run per arm×segment. Results final.

## Kill conditions (pre-committed)
1. **Arm C (noise) GROSS |t| ≥ 3** → pipeline leak, all results void.
2. **Arm A (routine) net t ≥ 2 AND within 0.5t of Arm B (same segment)** → classification not
   the alpha source → confound, void/flag.
3. **Arm B (opportunistic) net t < 1 in BOTH cap segments** (full window) → backtest REJECT
   (published negative). NOTE: a backtest REJECT still permits forward-ledger calls — the
   win condition is forward, not the gate.
4. **Arm B best-segment post-2015 net t < 0.5** → flagged "decayed — forward-only, no
   backtest promotion."
- Deploy/promotion gate (separate, stricter): t > **3.4** (Chen-Zimmermann multiple-testing
  threshold) AND DSR ≥ 0.95 AND PBO < 0.5 — expected to be unmet on backtest; that's fine.

## Revision log (v1 → v2, pre-data, from five-AI review)
1. Cap segments as explicit arms; **dropped the microcap assumption** (insider net edge tilts
   large/mid). 2. Added **10b5-1 exclusion**. 3. Primary spec changed to **low-turnover 12-mo
   hold**. 4. **ADV/spread-conditional cost model** replaces flat 25 bps. 5. Benchmark is now
   **cap-segment characteristic-matched**. 6. Added the **forward-ledger win condition** and a
   separate stricter deploy gate at **t>3.4**. 7. Window 2004→**2006** (SEC bulk data starts 2006).

## Result (filled AFTER the run 2026-07-21 — never edited afterwards)
Data: 824,251 open-market purchases (76 SEC quarters 2006-2024), 150,401 classifiable,
103,163 opportunistic / 47,238 routine. Issuer→permno match **61.4%** (ticker-based;
ambiguous=0 dropped). 10b5-1 drop: N/A (no flag in bulk files — known limitation).
Audit fixes applied before the run: CRSP return-hygiene (H1), NaN-return renormalization
(M4), signal stamped at filing date (M7), real PBO + honest config count (M2/M3).

- **Arm C (noise leak check): PASS.** Gross excess t = **1.01** (large/mid), **0.27** (micro).
  Both |t| < 3 → no pipeline leak; the machine makes no gross edge from random flags.
- **Arm A (routine placebo):** net excess t = -2.26 (large/mid, only 48 mo — sparse) /
  -0.57 (micro). Negative, not near Arm B → no confound (kill cond 2 not triggered).
- **Arm B (opportunistic):**
  - **large/mid: +17.1 bps/mo vs cap-seg EW, net t=1.40** (gross t=1.78); **FF5+UMD alpha
    +102 bps/mo, t=1.89**; net Sharpe 0.52; **post-2015 t=1.30** (edge persists).
  - micro: **-3.2 bps/mo vs EW, net t=-0.20** — nothing net of costs; FF5+UMD alpha +76
    bps/mo (t=1.39). Null in microcap, exactly as the review/literature predicted.
- **Gate (deploy):** DSR **0.258** (<0.95), PBO **0.414** (<0.5, computed for real), vs
  cumulative n=24 (18 + 6 configs). Deploy verdict **NOT MET** — as expected.

### Verdict: **FIRST NON-REJECT (weak-positive prior, cap-segment-correct).**
By the pre-registered *kill conditions*: C1 no leak (PASS), C2 no confound, C3 NOT triggered
(opp net t=1.40>1 in large/mid — the signal is NOT killed), C4 NOT decayed (post-2015 t=1.30).
So this is the project's first signal to survive its own kill conditions. It does **NOT** clear
the stricter *deploy* gate (DSR 0.26 ≪ 0.95) — nor was it expected to (a ~17 bps/mo or even
102 bps/mo FF-alpha edge needs far more than 199 months to reach t>3.4). **This is a weak
POSITIVE PRIOR, not a discovery:** t=1.40 and FF-alpha t=1.89 are below conventional
significance; the 61% ticker match and the ADV-proxy cost model are limitations.

**The single most important finding:** the edge lives in **large/mid caps, NOT microcaps** —
vindicating the v2 cap-segment fix. Had I kept the original microcap assumption I'd have
recorded a false REJECT (micro net t=-0.20). Per the win condition, this graduates to
**forward-ledger opportunistic-insider-cluster calls** (needs live 2026 Form-4 data — the
immediate next build). Backtest sets the prior; the forward record earns conviction.
