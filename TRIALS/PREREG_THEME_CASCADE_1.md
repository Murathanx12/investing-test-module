# PREREG — THEME-CASCADE-1 (second-wave beneficiaries)

**Drafted:** 2026-08-12 (NIGHT-14), from the external review archived in
`aegis-finance/docs/NIGHT14_EXTERNAL_REVIEW.md` Part 3.
**Status: NOT REGISTERED. Held at the corpse gate. See §Verdict.**

## Provenance

The external reviewer's strongest new proposal. Observing that the Bloomberg
competition's aggregate leaders included second-order names (SK Hynix, SanDisk,
Western Digital, Kioxia, Vicor) alongside the obvious first-wave winners
(NVIDIA, AMD, Palantir, Micron, Broadcom), the review proposed:

> Once Optimus recognizes a major economic theme, can it construct the causal
> supply-chain graph and identify second- and third-order beneficiaries before
> the market fully prices them?

with the operational screen: *economic exposure accelerating + revisions
improving + momentum beginning + significantly less crowding/rerating than the
theme leader.*

## Hypothesis (as proposed)

Securities positioned downstream of an accelerating economic theme, which have
not yet re-rated to the degree the theme leader has, earn positive
net-of-cost excess returns over the following 1-12 months.

## Honest prior

Stated before the corpse check was run: ~40/60 against, on the general grounds
that supply-chain diffusion stories are popular, well-known, and therefore
likely arbitraged.

**That prior was wrong, and it was wrong in a way this programme has already
paid to learn.**

---

## Corpse check — the reason this is not registered

`TRIALS/TRIAL-THEME-SUPPLY-supplier-baskets.md` (registered 2026-07-24, run
once, result final) tested the same mechanism class and **REJECTED it with
adequate power**:

| Arm | Result |
|---|---|
| Noise leak check | **PASS** (gross t 0.35 / 0.83, both < 3) — the instrument was working |
| Arm B (top-decile suppliers), large/mid | −16.3 bps/mo net, t = −0.87 |
| Arm B, micro | **−80.8 bps/mo net, t = −4.27** — significantly NEGATIVE |
| **B − A spread (the direct test)** | **t = 0.10 (+3.2 bps/mo)** |
| Gate | DSR 0.043, PBO 0.36 → REJECT |

The B−A spread is the decisive number and it is the one that matters here. Top
and bottom customer-momentum deciles were **indistinguishable before costs and
both lost after**. That is not an underpowered null — the noise control passed,
so the instrument could see. Combined with batch 3b's earlier `cust_mom` REJECT
(monthly: information real but IC t only 1.6-1.8 against 70% one-way turnover),
the trial's own closing paragraph reads:

> "There is no holding period at which this signal pays retail-accessible costs
> on 2004-2018 CRSP. Any revival requires a genuinely different mechanism class
> (e.g. event-conditioned links on daily data), registered from scratch."

So the programme tested *fast* (monthly cust_mom → dies on turnover) and *slow*
(annual supplier baskets → information already diffused, spread ≈ 0). Both ends
are closed.

## Verdict: **BLOCKED — not run tonight**

Under CANON and the `pre-register-trial` procedure, a well-powered refutation
may only be resurrected by naming a genuinely new instrument, and "the reviewer
suggested it again" is not one. This draft does not have one, so it does not
run.

**This is itself the finding, and it is worth more than the trial would have
been:** the external review's most exciting original idea already has a
well-powered corpse in our own registry, with receipts. The reviewer could not
have known — the negative results are not published outside the repo — but that
is precisely why the corpse check is code and not a habit. NIGHT-10's census
found most of the graveyard is *not* refuted (31 POWER, 29 IMPL, 14 DATA rows
never produced a usable number, and re-running those is often exactly right).
This one is different: it produced a usable number, and the number said no.

There is a second reason to refuse tonight specifically. The SK Hynix / SanDisk
/ WDC / Kioxia / Vicor names come from a leaderboard we have already looked at.
Registering a hypothesis *after* seeing the names it would select is
retrofitting evidence, and the review itself flagged this risk ("we should
preregister it now rather than look backward and claim those names prove it").
Any legitimate version must be frozen before its selections are known.

## What a legitimate resurrection would require

Recorded now so a later session does not have to re-derive it. All four, not a
subset:

1. **A different link source.** The corpse used Compustat `seg_customer`
   disclosed customer-supplier links. An LLM-constructed thematic dependency
   graph is a *different object* — it spans relationships no filing declares
   (power, cooling, substrate, capital equipment) and it can be wrong in ways
   a disclosed link cannot. That difference must be characterised and its error
   rate measured, not assumed favourable.
2. **A different claim.** The corpse tested *customer momentum diffuses to
   suppliers*. The review's screen is not that: it is a **relative crowding /
   re-rating differential** — leader has re-rated, node has not, exposure is
   accelerating. That is a valuation-dispersion claim, and it needs its own
   hypothesis statement rather than inheriting this one.
3. **A different clock.** The corpse's own suggested revival route is
   event-conditioned links on **daily** data. Monthly and annual are both spent.
4. **Selections frozen before inspection**, on a window that does not include
   the period whose leaderboard suggested the idea.

Until those exist, this stays closed and counts as a corpse consulted, not a
trial run.

## Registry accounting

**No registry row is created.** Cumulative trial count is unchanged — a draft
stopped at the corpse gate never accrued data and must not inflate the
denominator that future promotions are deflated against.
