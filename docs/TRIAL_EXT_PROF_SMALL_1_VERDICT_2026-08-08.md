# TRIAL-EXT-PROF-SMALL-1 — KILLED by clause (b), with a registration defect on record (2026-08-08)

Prereg: `TRIALS/PREREG_EXT_BANK_1.md` (frozen pre-M4). First run VOIDed by
the guard on a provenance mismatch (network-path vs local-parquet OSAP
values differ at ~0.07t — a finding in itself); guard re-anchored to the
trial's actual data source, PASSED exactly (7.24/2.40), then one shot.

## Results (small segment, explore only; confirm windows UNREAD)

| signal | t_ic | p vs floor | t_net flat25 | t_net KO | turnover | long-leg share | |ρ| vol12 |
|---|---|---|---|---|---|---|---|
| GP | 7.24 | 5e-05 | **2.40** | **2.46** | 0.092 | 0.289 | 0.13 |
| OperProfRD | 8.92 | 5e-05 | **2.81** | **3.00** | 0.095 | 0.222 | 0.26 |
| CBOperProf | 9.27 | 5e-05 | 0.80 | 0.95 | 0.098 | 0.170 | 0.24 |
| roaq | 7.39 | 5e-05 | 0.40 | 0.67 | 0.150 | 0.124 | 0.27 |
| cfp | 5.46 | 5e-05 | 0.81 | 0.83 | 0.105 | 0.193 | 0.27 |
| OperProf | 3.97 | 6e-04 | 0.20 | 0.43 | 0.100 | 0.138 | 0.21 |

- All 6 clear BH within the frozen m=226 denominator (kill (a) did not fire).
- **Kill (b) FIRED**: long-leg share < 0.50 for every member → by the
  frozen rule the family closes for long-only use as constructed.
- **Declared contrast FAILED**: CBOperProf (0.80) < GP (2.40) on t_net —
  Ball et al. (2016)'s cash-based superiority does not replicate in this
  window/segment/construction. Scored as a registered miss of the
  literature's claim, not ours.
- σ-family check: |ρ| vol12 0.13-0.27 — modest; these are not vol proxies.

## The registration defect, owned

Clause (b) was designed as the §28 discriminator ("is the long leg
worthless?") but it tests SHARE of the D10-D1 spread, not absolute
long-leg viability. GP and OperProfRD passed the money gate (G2) under
BOTH cost arms — long books at +39/+38 bps/mo net, t 2.4-3.0 — yet died
because their (huge) spreads are majority short-leg. A 29% share of a
135 bps spread is a viable long book; the gate could not represent that.
The kill STANDS as frozen (un-killing post-hoc is exactly what this
project refuses). The defect is recorded so the next registration tests
the right object.

## What is licensed next

GP and OperProfRD's **confirm windows are unread**. A future registration
(EXT-BANK-1 accounting, explore evidence now fully seen and disclosed) may
take exactly these two to confirm on their absolute long-book form. Note
GP externally re-validates the house survivor gp-small's money leg for the
second time (independent construction, direction fixed by Novy-Marx).
