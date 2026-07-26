# SIGNAL TAXONOMY — the ranked map of families (v1, 2026-07-25)

Adopted at AI-panel round 4 (`aegis-finance docs/research/AI_PANEL_2026-07-25.md`).
**Standing rule (extends horizon-first):** every new registration declares 4
tags BEFORE any scan —

1. **Source** — where the information comes from (accounting, price/volume,
   filings/events, positioning, analyst, macro).
2. **Decay horizon** — how long the information should take to be priced.
3. **Turnover class** — LOW (<10%/mo one-way), MED (10–30%), HIGH (>30%).
   House law: only LOW survives honest costs (146-candidate receipt).
4. **Role** — PICKER (earns a book net of costs) | FILTER (screens/conditions
   a book or lane; IC or risk info without net excess) | ALLOCATOR (macro
   exposure timing, never stock selection).

A family is CLOSED when adjudicated both directions or killed at confirm;
closed families cannot re-enter under new clothing (re-litigation ban).

## The map (146 explore candidates, 2 survivors + 1 fusion, 2026-07-25)

| Family | Source | Horizon | Turnover | Role verdict | Status / receipts |
|---|---|---|---|---|---|
| Profitability/quality (gp, cash_prof, fscore, oper_prof) | accounting | annual+ | LOW | **PICKER (small seg) + combiner feature** | **BRAIN-008 survivor** (3 windows, 42yr); ICs pervasive everywhere; largemid net-dead. **INSTR-ANOMALY-TIME (2026-07-26): EAD/rdq availability ADOPTED** — confirm t 0.89→1.24 (book-level +2.7 bps/mo disclosed weak) |
| Opportunistic insider (single-buyer) | filings | 1–6mo | LOW-MED | **PICKER (weak-positive)** | **BRAIN-003 promoted**, forward clock 2027-07; clusters add nothing (BRAIN-009); role-weights = open stub |
| Fusion (insider + gp z) | composite | mixed | LOW | **PICKER candidate** | BRAIN-007 survives, beats best single, 3.6× names; SMQ lane live |
| Momentum (12-1, 6-1, consistency, sharpe) | price | 3–12mo | MED | none (net-dead largemid) | batch 1 closed; qual_mom interaction also failed (b5) |
| Momentum spillover (industry_mom, conn_mom; cust_mom b3) | price/links | 1–6mo | HIGH | none — conn_mom = starkest paper-vs-cost gap measured (lit 1.68%/mo t 9.67 → our net t −0.78, turnover 0.67); industry flat-since-2000 confirmed | b3/b9 closed |
| Reversal/dip (st_rev, dip_3m, dd_from_high, ltr) | price | 1–36mo | HIGH | none — Murat's dip theses rejected | batch 1 closed |
| Low-vol/defensive (vol_low, max_low, skew_low, defensive composite) | price | 6–12mo | LOW | **FILTER (lane risk design)** — maxDD −35% vs −52..−82%, IC t 7.1, zero net excess | batch 1+5; screen-class receipt |
| Value (btm, re_me) | accounting | annual+ | LOW | none in this era | btm flat; re_me STRONG prior FAILED (b7) — value's decade |
| Accruals/investment (accruals, asset_growth, dnoa, capx) | accounting | annual | LOW | none — INVERTED post-publication | batch 2/5 closed; 3× re-litigation refused |
| Issuance/payout (net_issuance, comp_issue_5y, payout_yield) | accounting | annual | LOW | combiner shelf — REINFORCED (1y: 1.10/2.18; 5y: 1.15/2.86 — two constructions, same IC-clears/net-doesn't shape) | b2/b7/b9 closed as pickers; strongest combiner case on the shelf |
| Earnings surprise (sue_streak, earn_accel, ea_shift, pead_agree) | events/analyst | 1–3mo FAST | HIGH | combiner shelf; pead_agree INVERTED (IC t −2.6 — 5th sign reversal, PEAD decay confirmed in-window) | b5+b8 closed at monthly cadence; daily event harness is the only admissible retry class |
| Short interest LEVEL / DTC | positioning | 1–6mo | MED | **FILTER candidate** — dtc book t 3.4 WITHOUT rank IC (b6, AND-rule held); small seg inverse | family closed as picker BOTH directions; squeeze/regime filter = taxonomy reclass |
| Short interest TREND (si_trend) | positioning | 1–6mo | HIGH | combiner shelf — IC t 2.12 largemid, net t −0.92 (turnover 0.33 ate it, as declared) | batch 8 closed; SI family fully mapped (level=filter, trend=shelf) |
| 13F positioning (inst_persist ±, own_dur, best_ideas) | positioning | quarters | LOW-MED | none — both tails lose to middle | b3/b5/b6 closed |
| Customer links (cust_mom, supplier baskets, cust_conc ±) | filings | monthly–annual | MED | **CLOSED** — comovement dead both arms; conc dead both directions incl. confirm KILL (BRAIN-010, DSR 0.0003) | NEG_RESULTS §12/§13 |
| Divergences (inv_div, rect_div) | accounting | annual | LOW | combiner shelf (small IC t 2.6–4.0, net-dead) | b7 closed |
| Gain overhang (cg_overhang) | price/holdings proxy | 3–12mo | MED | combiner shelf | b6 closed |
| Analyst revisions (rev_conf; dispersion pending) | analyst | 1–3mo | HIGH | rev_conf failed b5 | TP-dispersion design (PSZ 2025) → tgt rebuild registration |
| Target price (tgt_upside family) | analyst | 3–12mo | MED | VOID (split-adjust look-ahead) | rebuild unblocked by ibes_adj; dispersion-conditioned spec adopted |
| FDA approvals | events | days–weeks | HIGH | monthly resolution REJECT | daily-CAR successor queued (dsf on disk); attention arm = exploratory |
| R&D intangibles (rd_gp) | accounting | annual | LOW | none — book-without-rank in small (t 1.18, IC −0.07; AND-rule catch) | batch 8 closed as picker |
| Board networks (BoardEx) | filings/governance | quarters+ | LOW | **FILTER/layer prior** (Mgmt Sci: LSW alpha may be beta) | design queued; interlock event study = phase 2 |
| Macro regime (jump model, TSMOM-XA, GPR, SBCORR, DOD) | macro | weeks–months | LOW (asset-level) | **ALLOCATOR** — separate lane, never stock-picks | batch-4 instruments registered; daily harness = next build |
| Descriptive risk (LPPLS, fragility, crash composite) | macro | — | — | FILTER (descriptive, never-arm) | live lanes, no promotion path |

## The combiner shelf (IC-real / net-dead) — the map's core exhibit

Rank information with no standalone tradeable premium, held for the future
combiner registration: cash_prof, fscore_lite ICs; sue_streak; cg_overhang;
inv_div/rect_div (small); dtc small-seg IC; conc_low (post-confirm); payout
small IC; defensive (risk screen). Any combiner built from the shelf is a
NEW pre-registered trial deflated by the full cumulative count — the shelf
is inventory, not evidence.

## Reading the map

- Every surviving PICKER is LOW-turnover accounting/filings information at
  annual-ish horizons — the Novy-Marx recipe, rediscovered by our own scans.
- Fast-decay families (surprise, revisions, attention) consistently produce
  real IC and dead books at honest costs → their value, if any, is inside a
  low-turnover combiner or as event studies at DAILY resolution.
- Positioning data (SI, 13F) has produced books without rank and ranks
  without books, but never both — filter class, not picker class.
- The allocation layer (beat-SPY machinery, chunk 5) is a different game
  with different instruments; it must never leak into stock selection.
