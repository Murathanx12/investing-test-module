# HANDOFF — external anchor work, 2026-08-07 (review-round session)

**For the main session.** Everything below is on disk and re-runnable. Nothing
graduated, nothing was seeded, no lane was touched, and **the cumulative
candidate count is unchanged at 179**. Two pre-registrations were written
before any statistic existed; one arm was killed by its own clause.

---

## 0. TL;DR — what changed

1. **The circularity leg that NEGATIVE_RESULTS §34 left open is now half-closed.**
   The candidate population and the null were both ours. An external, licensed,
   peer-reviewed candidate population is now cached locally and runs through the
   existing harness unmodified.
2. **A real-data null for the explore gate exists and is measured.** It says the
   simulator's generic null is ~2.3x too narrow.
3. **A structural finding about the frozen ladder** that needs an attended
   decision before the one-shot replay runs (§4).
4. **The placebo half of the external anchor is not available** and is recorded
   as a data-availability negative result with two live paths.

---

## 1. Data landed

| Path | What | Size | License |
|---|---|---|---|
| `data/osap/firm_char.parquet` | OSAP firm-level panel, **5,416,424 rows x 211 cols** (permno, yyyymm + **209 signals**), yyyymm 197112-202611 | 1.95 GB | data openly distributed; cite Chen & Zimmermann (2022) |
| `data/osap/signed_predictors_dl_wide.zip` | the source download, kept for provenance | 2.36 GB | as above |
| `data/osap/_cat_availability.json` | category reconciliation | — | — |
| `C:\Users\mrthn\reference-codes\harvest\sp500/` | fja05680/sp500 | 13 MB | **MIT** |
| `C:\Users\mrthn\reference-codes\harvest\entropy-pooling/` | fortitudo-tech/entropy-pooling | small | **BSD-3-Clause** |

**Licence discipline, binding.** The OSAP *code* repo (`OpenSourceAP/CrossSection`)
is **GPL-2.0** and the `openassetpricing` pip package's licence was **not
verified**. Nothing from either is vendored. `scripts/fetch_osap.py` and the
`import openassetpricing` calls inside `aegis_brain/factory/osap.py` are **lazy,
inside functions**, so no shipped module imports it at runtime — the package is
used as an offline ETL tool only, and the cached parquet is the artefact. Keep
it that way (CANON §10).

---

## 2. Code written

| File | Purpose |
|---|---|
| `aegis_brain/factory/osap.py` | Adapter turning OSAP signals into `FactorySignal`s the existing `explore.scan_signal` scans unmodified. Direction read from the OSAP doc's `Sign` (i.e. from the source paper) **before** any scan — CANON §6 intact. Raises rather than scanning a network-truncated set. |
| `scripts/fetch_osap.py` | One-shot fetch + availability reconciliation. |
| `scripts/_osap_to_parquet.py` | Extract + streaming CSV->parquet. |
| `scripts/run_ext_null_1.py` | The EXT-NULL-1 / EXT-POWER-1 runner. Guard-gated, resumable, incremental CSV writes. |
| `TRIALS/PREREG_EXT_NULL_1.md` | Pre-registration for both arms. |
| `runs/EXT-NULL-1/VERDICT_placebo_arm.md` | The killed arm. |
| scratchpad `PREREG_REAL_NULL_1.md`, `real_null_1.py`, `real_null_1_result.json` | REAL-NULL-1 (§3). |

**Reproduction guard, used everywhere.** Per the NEGATIVE_RESULTS §28
discipline, every harness in this session had to reproduce banked batch-1
numbers **exactly** before any new number was read:

```
vol_12m_low / largemid  t_ic = 1.89   (banked 1.89)  PASS
price_level / largemid  t_ic = 2.12   (banked 2.12)  PASS
```

Both passed in REAL-NULL-1 and again at the head of the predictor run.

---

## 3. REAL-NULL-1 — the real-data null (COMPLETE, pre-registered)

Provably information-free AR(1) signals (RNG independent of every panel input),
scanned on the real CRSP panel, largemid, 2004-2018, K=1000 per persistence
level.

| phi | top-decile churn/mo | sd(t_ic) | **P(t_ic >= 1.5)** | end-to-end P(adopt) |
|---|---|---|---|---|
| 0.00 (iid control) | 0.908 | 0.936 | 0.054 | 0.017 |
| 0.90 | 0.365 | 1.001 | 0.066 | 0.026 |
| 0.97 | 0.236 | 1.072 | 0.083 | 0.028 |
| 0.99 | 0.171 | 1.172 | **0.094** | 0.038 |
| 0.995 | 0.144 | 1.121 | 0.073 | 0.022 |
| 0.999 | 0.113 | 1.067 | 0.078 | 0.030 |

Pooled phi >= 0.97 (K=4000): **P(t_ic >= 1.5) = 0.082 [0.0735, 0.0905]** vs the
DGP-A v6 generic null **0.036 [0.013, 0.059]** (`docs/family_null_tic_r1_frozen.json`,
`injected_edge`/largemid, n=250). Non-overlapping -> the pre-registered
"OPTIMISTIC" branch fires. Confirm-pass-given-graduation: **118/328 = 0.360**
(vs the simulator's 2-of-4 = 0.5).

**The declared mechanism was WRONG and is recorded as a miss.** I predicted
IC-series autocorrelation; measured lag-1 autocorrelation is -0.004 to -0.011
at every phi. The inflation is heteroskedasticity/fat tails in the monthly IC
cross-section, not serial dependence. The headline survives; the mechanism leg
does not.

Real candidates are *more* persistent than the most persistent arm tested
(`price_level` hold-band turnover 0.028 vs my churn 0.113), so 0.082 is a
**lower bound**.

---

## 4. The structural finding that needs an attended decision BEFORE the replay

Read `runs/GATE-M1/brain009_frozen.json` and `held_out_tables` alongside this.

1. **`FDR` as defined in `select.py:12` and `RECAL1_SPEC` line 110 is
   `P(adopt | alpha = 0)` — a per-candidate false-positive rate, not a false
   discovery rate.** It is invariant to the number of tests, which is the exact
   property a multiple-testing control must not have. At 179 candidates:
   `E[false adoptions] = 179 x 0.016 = 2.86`, `P(>=1) = 0.944`.
2. **It rests on 2 events.** `table2_stage_attribution`, cell `a0.0/base`,
   n=125: `adopt = 2`, `confirm_fail = 2`, `no_graduate = 121`.
3. **The FDR budget was not binding**: `family_size 1800, n_feasible 1798`.
4. **The cap was never measured in the geometry that will run.** Summing
   `p_ge_1.5` over the 21 largemid signals in `family_null_tic_r1_frozen.json`
   gives **E[qualifiers] = 4.54 against a cap of 5** — hence
   `p_cap_crowded_out = 0.0`. The replay runs 179.
5. **In the actual bank the cap binds ~4:1 and the family-null veto removes
   none of the graduates.** Across `data/factory/batch*_summary.csv`: **67
   distinct largemid candidates, 22 (32.8%) clear `t_ic >= 1.5`.** Top five by
   `t_ic`: `conc_low` 4.46, `tgt_upside_low` 3.67, `inst_persist_low` 3.35,
   `si_chg_low` 3.11, `comp_issue_5y` 2.86. The sigma-family members sit at
   ranks **10, 11, 14, 18** (`price_level`, `vol_6m_low`, `vol_12m_low`,
   `max_ret_low`) — all below the cap.
6. **BRAIN-009 deletes the leg NEGATIVE_RESULTS §32 says makes the rule safe**
   (`explore_t_net: null`, `confirm_t_net: null`, `dsr_threshold 0.0`,
   `pbo_threshold 1.0`). §32: *"safe only because of the AND — the money leg
   vetoes the rank artifact."* Note `inst_persist_low` graduates on IC with
   `t_excess_net = -3.49`.

Combining (5) with REAL-NULL-1's measured confirm rate:
`E[false adoptions] = 5 x 0.360 = 1.80`, `P(>=1) = 1 - 0.640^5 = 0.892`.

**This is not a recommendation to change the freeze.** It is the input to an
attended decision, which is Murat's call. The cheapest fix, if one is wanted,
is a calibrated absolute floor: REAL-NULL-1's real-data p95 for persistent
signals is ~1.75-1.88, not 1.5.

---

## 5. RUNNING NOW — EXT-POWER-1 (pick this up)

```
cd "C:\Users\mrthn\Aegis module"
PYTHONIOENCODING=utf-8 python scripts/run_ext_null_1.py --arm predictor --chunk 12
```

- Scans all **209 OSAP predictors**, both segments, **explore window only**.
- Output: `runs/EXT-NULL-1/scan_predictor.csv` (written incrementally — safe to
  inspect mid-run), `meta_predictor.json`, log at `predictor_run.log`.
- **Resumable**: re-running skips acronyms already in the CSV.
- **Pre-registered metric M4**: fraction clearing `t_ic >= 1.5` in largemid.
  Declared prior was **30-50%**; score it honestly either way.

**The confirm window is deliberately NOT read for predictors.** Reading it
would burn the held-out window on 209 potential candidates. Keep that rule
unless a new registration opens it.

### First two scans, as a sanity anchor (already run)

```
osap_GP (Novy-Marx 2013)         largemid t_ic 1.42  t_net -0.63
                                 small    t_ic 7.31  t_net +2.42  t_gross +2.76  turn 0.092
osap_AbnormalAccruals (Xie 2001) largemid t_ic -0.11 t_net -1.78
                                 small    t_ic -0.97 t_net -3.38
```

`osap_GP` clears **both** legs of the original BRAIN-008 rule in small. Read it
as a **cross-validation receipt, not a discovery**: it is an independent
reproduction of the project's own `gp-small`, with the direction set by
Novy-Marx rather than by us.

---

## 6. Killed, with receipts — EXT-NULL-1 placebo arm

`runs/EXT-NULL-1/VERDICT_placebo_arm.md`. **0 of 114 OSAP placebos are
published at firm level** (209 of 212 predictors are). Confirmed by two
independent routes. The pre-registered kill clause (n < 40) fired. Two live
paths documented there; note the GPL-2.0 constraint on route 2.

---

## 7. Merging with the G2 results

The G2 / wave-3 fresh-null work and this work measure **different halves of the
same question** and should be reported side by side, not merged:

| | source of the null | provably null? | realistic candidate? |
|---|---|---|---|
| G2 / wave-3 (1000 fresh panels) | DGP-A v6, ours | yes, by construction | no — our 21 signals |
| REAL-NULL-1 | real CRSP + RNG | **yes**, by construction | no — artificial |
| EXT-POWER-1 | OSAP, external | n/a (power arm) | **yes** — 209 published |

Concretely, when G2 lands:
1. Put G2's tightened `P(adopt | alpha=0)` next to REAL-NULL-1's **0.082 /
   0.0295**. If G2 tightens the Wilson interval around 0.016 while the real-data
   number sits at 0.0295, **that is the finding** — the simulator is precise and
   biased, which is worse than imprecise.
2. Re-run §4's arithmetic with G2's confirm-pass rate in place of the 2-of-4
   estimate. REAL-NULL-1's 118/328 = 0.360 is the better-powered comparator.
3. BRAIN-010's pre-registered prediction (FDR in [0.015, 0.035]) should be
   scored against **both** nulls, and the disagreement reported.

---

## 8. Validation checklist for the main session

```bash
cd "C:\Users\mrthn\Aegis module"

# 1. guards reproduce banked numbers (must print 1.89 / 2.12, else everything is VOID)
PYTHONIOENCODING=utf-8 python scripts/run_ext_null_1.py --arm predictor --limit 1

# 2. category availability (must be Predictor 209/212, Placebo 0/114)
python -c "import json;print(json.load(open('data/osap/_cat_availability.json')))"

# 3. the 22-of-67 bank count behind §4.5
python -c "
import pandas as pd,glob
a=pd.concat([pd.read_csv(f).assign(src=f) for f in glob.glob('data/factory/batch*_summary.csv') if 't_ic' in pd.read_csv(f,nrows=1).columns],ignore_index=True)
lm=a[(a.segment=='largemid')&a.t_ic.notna()].drop_duplicates('signal')
print(len(lm),'candidates |',(lm.t_ic>=1.5).sum(),'clear 1.5')
print(lm.nlargest(5,'t_ic')[['signal','t_ic','t_excess_net']].to_string(index=False))"

# 4. REAL-NULL-1 (~10 min, K=1000 x 4 phis; guard aborts on mismatch)
python "<scratchpad>/real_null_1.py" 1000
```

---

## 9. Open items, ranked

1. **Attended decision on §4** before the one-shot replay is run. Highest value,
   lowest cost, and it is a decision, not more compute.
2. **Score EXT-POWER-1's M4** against the declared 30-50% prior when the run
   lands.
3. **Decide whether 209 external predictors become candidates.** They are
   confirm-clean today. If they enter, they enter under the resurrection/
   deflation rules like anything else, and the count moves off 179.
4. **`fja05680/sp500`**: 2,718 rows, 1996-01-02..2026-06-30, **1,206 distinct
   tickers, 503 current, 703 ex-members**, 28/33 famous delisted names present.
   This fixes the **universe** half of NEGATIVE_RESULTS §4, not the price half.
   Worth a §4 amendment: survivorship becomes *measurable* on free data rather
   than merely uncorrectable.
5. **`entropy-pooling` (BSD-3)** is vendorable and is the one portfolio-side
   adoption. Gate it explicitly: priors and views must come from data external
   to the strategy under evaluation, or it becomes a backdoor fit on own P&L
   (CANON §4). `fortitudo.tech` and `pcrm-book` are **GPL — reference only**.
