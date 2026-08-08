# PRE-REGISTRATION — INSTR-ERA-BACKTEST-1 (2026-08-08)

**Written BEFORE any era statistic exists.** Registered under CANON §6.
INSTRUMENT: no candidate may be adopted or killed by this run — its outputs
are (a) era-robustness receipts for the replay's adopted candidates,
(b) measured decay priors for future accounting, (c) the long-window power
Murat asked for ("if 6 months not enough run longer backtests").

## Panel and windows (frozen)

`data/crsp_panel_1962_2001` (certified pipeline, real delisting returns,
20,902 permnos) — DISJOINT from both one-shot windows (2004-2018 explore,
2019-2024 confirm). Production eligibility rules unchanged (nominal floors);
measured consequence, stated: the $200k dollar-volume floor empties the
small segment before ~1982. Windows therefore:

- **W-A: 1985-01..2001-12, both segments** (204 months; small ≈ 850-2000
  eligible names/mo).
- **W-B: 1972-01..1984-12, largemid only** (156 months).
- Stability sub-splits of W-A: 1985-1993 / 1994-2001.

## Signals (frozen list, constructions fixed before any scan)

OSAP externals (directions from source papers, local parquet provenance):
`GP`, `OperProfRD`, `CBOperProf`, `OperProf`, `cfp`, `roaq`, `RoE` (+1
each); `MaxRet`, `IdioVol3F` (−1) — the profitability family plus the
monthly analogs of the adopted daily σ-arms. Panel-native batch-1
constructions of adopted members: `price_level` (log price, +1),
`vol_12m_low` (−rolling 12m std), `max_ret_low` (monthly MAX, −1).
NOT runnable pre-2002 and excluded, stated: conc_low (customer data),
dtc_high (short interest), fscore_lite (multi-item Compustat wiring),
daily arms (no daily pull).

## Metrics

Per signal × segment × window: t_ic, ic_mean, t_gross, t_net_flat25,
turnover, months. **Gross is PRIMARY** — no cost model is registered
pre-2004 (flat-25 printed as reference only, labeled). Book mechanics =
production ScanConfig (top decile, 30% hold band).

## Declared predictions (scored afterwards, hit or miss)

1. Profitability core (GP, CBOperProf, OperProfRD) small W-A:
   **gross t ≥ 2.0 for all three** (Novy-Marx 2013 evidence spans
   1963-2010).
2. Profitability family small: IC t ≥ 3.0 in BOTH W-A sub-splits (era
   stability of the information).
3. Decay direction: era W-A gross t > the matched 2004-2018 explore gross
   t for GP-class signals (pre-publication eras stronger).
4. σ-arms (MaxRet, IdioVol3F, vol_12m_low, price_level): era IC t ≥ 3 in
   small W-A (the structural rank-IC channel is not a 2004+ artifact).

## One shot

Frozen list, frozen windows, one run, write-once output
`runs/ERA/instr_era_backtest_1.json`. Guard: the harness must reproduce
one banked 2004-2018 number on the MODERN panel before touching the era
panel (osap_GP small t_ic 7.24, local-parquet provenance) — proving the
identical code path, then pointed at 1962-2001.
