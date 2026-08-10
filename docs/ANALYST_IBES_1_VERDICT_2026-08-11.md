# ANALYST-IBES-1 — VERDICT

**Registered** `TRIALS/PREREG_ANALYST_IBES_1.md` (corpse-linted PASS, amended
before running after the linter surfaced three prior trials).
**Run** 2026-08-11, 32 books, 246 s. Receipts `runs/ARENA1/ANALYST_IBES_1/`.
**Window** 2002-01-31 .. 2022-12-31, 252 months. Holdout unread.

---

## The one-line answer

**Analyst target REVISIONS are real gross and dead net; analyst target LEVELS
lose money outright.** The distinction the PM was built on is correct. The
tradability of the good half is not established.

## Instrument checks passed, so the accruing arms are readable

Both replication arms reproduced their known kills on the new `ptgsumu`
instrument, which is the precondition the pre-registration set for reading
anything else.

| arm | must reproduce | got | verdict |
|---|---|---|---|
| A1 `tgt_upside` | NEGATIVE | **−8.6 to −17.6 %/yr net, all 8 cells** | ✅ |
| R1 `eps_rev_breadth` | net t < 1 | **max net t 0.88**, range −1.72..0.88 | ✅ |

A1 is negative on **gross** as well (−8.6 % to −16.7 %/yr), so this is not a
cost story: buying the names with the highest analyst-implied upside lost money
before a single basis point of trading cost. That is the third independent
confirmation of `analyst_target_upside_xs`, now on a data source the earlier
work did not have.

## The accruing arms

| arm | segment | clock | gross %/yr | net %/yr | t | turnover |
|---|---|---|---:|---:|---:|---:|
| A2 `tgt_rev_breadth` | small | 1m | **+6.05** | +0.38 | 0.54 | 10.2× |
| A2 | small | 3m | +3.53 | +1.70 | 1.06 | 3.3× |
| A2 | small | 3m (ko) | +3.53 | **+2.48** | 1.35 | 3.3× |
| A2 | largemid | 1m | +2.57 | −2.61 | −0.81 | 9.6× |
| A2 | largemid | 3m (ko) | +1.54 | +1.23 | 0.76 | 2.8× |
| A3 `tgt_rev_3m` | largemid | 1m (ko) | **+5.94** | **+5.29** | 1.66 | 4.3× |
| A3 | largemid | 3m (ko) | +3.05 | +2.68 | 1.13 | 2.8× |
| A3 | small | 1m | −0.73 | −3.46 | −0.02 | 5.2× |
| A3 | small | 3m | −0.50 | −2.26 | 0.21 | 3.3× |

### Against the registered predictions

1. **Instrument checks** — ✅ both.
2. **A2/A3 gross > 0** — ✅ for A2 in all 8 cells (+1.5 to +6.1). ✗ for A3 in
   small (−0.5, −0.7); ✅ in largemid (+3.1, +5.9).
3. **A2/A3 net ≈ 0** — ✅. Nothing reaches the registered bar of +3 %/yr at
   |t| ≥ 2. The best cell is A3 largemid monthly under KO costs at +5.29 %/yr,
   **t = 1.66**, which is below 2 and therefore not a result.
4. **Gross-to-net gap larger for revisions than levels** — ✅ and decisively.
   A2 small monthly gives up **5.67 points** to costs (turnover 10.2×); A1
   small monthly gives up 1.85 (turnover 3.7×). The mechanism predicted in
   advance is the mechanism observed.
5. **A2 and A3 agree in sign** — ✗ **REFUTED in the small segment.** A2 is
   +6.05 gross, A3 is −0.73 gross, on the same names in the same months.

## Verdict, by the registered rule

Prediction 5 was registered with a consequence attached: *"They are two
constructions of one idea. If they disagree, the idea is not identified and no
verdict may be issued for either."* They disagree in small. So:

* **SMALL SEGMENT — UNRESOLVED.** Breadth of target revisions and magnitude of
  target revisions point opposite ways. Until that is explained, neither is a
  finding. The most likely explanation is that `numup1m`/`numdown1m` count
  analyst *actions* while Δ-consensus mixes actions with coverage churn — a new
  analyst initiating at a high target moves the mean without anyone revising
  anything. That is a testable successor, not a result.
* **LARGEMID — NET-DEAD, DIRECTIONALLY POSITIVE.** Both constructions are
  positive gross and neither clears |t| 2 net. Registered prediction 3 stands.
* **LEVELS — CONFIRMED DEAD, third independent instrument.**

**No signal graduates.** `analyst_target_revision` stays HYPOTHESIS in the
registry, `allowed_in_pm` stays false.

## What this changes for the portfolio manager

The PM ranks revisions rather than levels. That choice is now **supported by
direct measurement** rather than by the literature: on 21 years of
point-in-time IBES, the level signal it declined to use loses 8–18 %/yr, and
the revision signal it prefers earns +1.5 to +6 %/yr gross.

It does **not** license the PM to claim an edge. Every positive cell here dies
on turnover, and the PM's own analyst layer is a Yahoo consensus with no
timestamp — a weaker instrument than the one tested.

The one genuinely encouraging structural point: **the thing that killed these
arms was turnover, and Murat's book does not turn over.** A 50-name book
rebalanced monthly pays 10× annual turnover; a 12-name book held for months
pays a small fraction of that. The Arena is where that question belongs, and it
is registered there rather than asserted here.

## What was NOT run, and why

* **The placebo band (C1).** Registered, and dropped for time: 100 draws per
  book at ~45 s each is ~40 hours for 32 books. This is a **declared scope
  reduction**, not a silent one. Nothing here claims to beat a random book at
  matched turnover, because that comparison was not made. It is only owed if
  something survives, and nothing did.
* **The holdout.** Locked and unread.
* **Per-analyst reliability.** `ptgdet` carries 17,364 analyst codes and is on
  disk, but its values are adjusted to the download-date share basis — the
  exact defect that voided the July run. Using it needs `ibes.adj` arithmetic
  that this trial deliberately avoided.

## Data receipt

`ibes.ptgsumu` 1,352,950 rows 1999-03..2026-05; `statsumu_epsus` 4,312,643;
IBES→CRSP link match rate **92.7 %** at link score ≤ 3; mean coverage 3,208
names/month over 276 panel months. Unadjusted files only. Split factors
recovered from CRSP as `price_{t-1}(1+ret_t)/price_t` and applied cumulatively
before differencing — without which a 10:1 split reads as a −90 % revision.

**Search denominator: 16 accruing books.** Replication arms accrue zero.
Programme cumulative count 179 + 16 = **195**.
