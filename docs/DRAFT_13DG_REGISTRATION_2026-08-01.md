# DRAFT — 13D/13G activist-stake event family (NOT REGISTERED, NOT FROZEN)

**Status: DRAFT FOR REVIEW. Nothing here is registered. No candidate is counted.
Cumulative candidates remain 166.** Murat and the next session freeze this (or
reject it) after review. Written 2026-08-01 by the Opus session that built the
daily event harness, per OPUS_SESSION_PROMPT task 2.

---

## Blocking dependency, found this session — read this first

`wrdssec` is **NOT SUBSCRIBED** on our WRDS account. From `manifest_p0c.json`:

```
"wrdssec_tables": {"error": "NotSubscribedError: You do not have permission
                             to access the wrdssec library"}
"wrdssec_13dg":   {"status": "NOT PULLED - no readable form-index table ...
                              13D/13G falls back to the free EDGAR full-text index path"}
```

So there is **no WRDS path to 13D/13G filings**. The event dates must come from
the free EDGAR full-text/company index, which means a collector we do not yet
have, with the failure modes the house already has receipts for: SEC rate
limiting returning **403 not 429** under volume (2026-06-17 postmortem,
NEG_RESULTS §5), and silent-fragility (green offline, dead in prod).

**Therefore this family cannot be registered until the event dates exist on
disk.** Registering a trial whose data source is unbuilt would be
pre-registration theatre. The honest ordering is:

1. Build + verify an EDGAR 13D/13G date collector routed through the existing
   `_sec_get` choke-point (shared limiter, env UA, 403 retry). Non-negotiable:
   it reuses that choke-point rather than making raw `requests.get` calls.
2. Audit coverage against a hand-checked sample of known activist campaigns.
3. **Then** freeze this registration against the landed dataset.

Estimated: one build session. No Duo tap needed (EDGAR is public).

---

## Hypothesis (draft)

A Schedule 13D filing discloses a >5% stake held with **intent to influence**
control; a 13G discloses the same threshold held **passively**. The literature
(Brav, Jiang, Partnoy & Thomas 2008; Klein & Zur 2009) reports large positive
announcement returns to 13D filings and continued drift. The testable claim
here is narrower and control-armed:

> Names with a **13D** filing earn positive abnormal returns over +1..+60
> trading days **relative to matched non-event names of the same segment,
> month and liquidity rank** — and 13G filings, which disclose the same
> ownership threshold without the control intent, do **not**.

The 13G arm is the point. It is a **near-perfect placebo**: same disclosure
threshold, same filer population, same regulatory trigger, same
"large-holder-just-appeared" salience — differing only in declared intent. If
13D and 13G produce the same drift, the effect is *stake-size disclosure* or
plain selection, not activism. If only 13D drifts, the intent is doing work.
This is the design NEG_RESULTS §20 says we should have had for 8-K.

## Declared prior: WEAK-NEGATIVE

1. **§20 is the direct receipt.** Distress-8-K "drift" was **selection, not
   information** — the harness's own placebo run this session reproduced the
   trap: 3,000 *randomly dated* events showed a **+170 bps** event-leg CAR over
   +1..+60 that collapsed to **-26 bps (t = -0.50)** once differenced against
   matched controls. Any uncontrolled 13D number will look impressive for
   exactly this reason.
2. **CZ-CALIB fame decay (rank corr -0.544):** the 13D announcement effect is a
   large, famous, heavily-published result, which in this programme is a
   predictor of decay, not of survival.
3. **The 13F family is now 8-for-8 dead** (NEG_RESULTS §26): every ownership-based
   construct we have tested carries rank information and no tradable book.
   13D/13G is ownership data at event resolution — related enough that the
   prior transfers, different enough (event-timed, intent-labelled) that it does
   not close the question.
4. **The announcement pop is not ours to have.** 13Ds are filed within 10 days
   of crossing 5%; the large return is concentrated at/before the filing. Our
   windows open at **+1**, deliberately. What is being tested is the *drift
   after* public disclosure, which is the only part a real book could hold.

**Honest prediction to be scored:** 13D +1..+5 differenced CAR positive but
under 100 bps with clustered t in 1.0-2.5; +1..+60 indistinguishable from zero;
13G indistinguishable from zero at all horizons; the 13D-minus-13G contrast
smaller than the raw 13D number. Net of costs, no arm graduates.

## Arms (draft — each would be a counted candidate)

| # | arm | construct |
|---|---|---|
| A | `13d_all` | every 13D filing, event date = filing date |
| B | `13g_all` | every 13G filing (the intent placebo) |
| C | `13d_first` | first 13D on a name in 24 months (excludes amendment churn) |

Three arms -> cumulative 169 if registered as drafted.

## Evaluation (draft)

- Harness: `aegis_brain/factory/daily_events.py`, built and tested this session.
- Windows: +1..+5, +1..+20, +1..+60 **trading** days; day 0 excluded.
- Control arm: same segment, same calendar month, nearest dollar-volume rank,
  **no event within +/-60 calendar days**. Mandatory — this is the test.
- Delisting-aware: `crsp.dsedelist` joined. Verified this session that
  `crsp.dsf.ret` does **NOT** contain delisting returns (permno 11713: dsf
  -0.096 on its delist date vs dlret **-0.697**). Without this join every
  distress-adjacent event study is biased upward.
- Inference: t clustered by **event month**; the iid t reported alongside so
  the inflation is visible.
- Explore 2004-2018 only. Confirm 2019-2024 is one-use and only a graduate
  earns it.
- Costs: the CAR is a return series, not a book. **A CAR result alone cannot
  graduate anything** — a graduating arm must then be built as a monthly
  portfolio and cleared through `scan_signal` under the standard deciding cost
  arms (largemid flat25, small KO-half, zero-cost bound reported). Stated now so
  the family cannot be declared a success on gross event-study numbers, which is
  how event studies usually flatter themselves.

## Kill condition (draft)

One shot per arm. If the **13D-minus-13G contrast** is not positive with
clustered t >= 2.0 in at least one window, the activist-intent mechanism is
recorded dead and the family closes — no re-cut by market cap, campaign type,
filer identity or window. If 13D and 13G drift **together**, the finding is
recorded as *"large-holder disclosure is a selection marker, not information"*
and both close.

## Open questions for review

1. Is the 13G placebo arm worth a counted candidate, or should it be a
   non-counted control? (Recommendation: **counted** — it can win on its own and
   a control that cannot lose is not a control.)
2. Amendment handling: 13D/A filings are frequent and mostly noise. Draft C
   handles this by first-in-24-months; is the alternative — dropping amendments
   entirely — cleaner?
3. Should the announcement window (-1..0) be *reported* as context even though
   it is untradable? (Recommendation: yes, reported, never deciding — it is the
   sanity check that the event dates are real.)
