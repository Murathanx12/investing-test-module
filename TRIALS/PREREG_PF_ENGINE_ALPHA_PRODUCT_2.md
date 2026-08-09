# PRE-REGISTRATION — PF-ENGINE-ALPHA-PRODUCT-2 (product track)

**Registered:** 2026-08-09, by the commit that adds this file.
**Track:** PRODUCT (per `aegis-finance/docs/EXECUTION_STANDARD_2026-08-08.md`,
second amendment of 2026-08-09).
**Class:** **RETROSPECTIVE.** See §2 — this is the honest label, stated in the
registration rather than discovered later.
**Authorized by:** Murat, 2026-08-09, answering the PF-2 open question on the
regime-breadth gate. His instruction, binding: *do not retro-label
ENGINE-ALPHA; register the product track fresh.*
**Holdout:** 2023-01-01 .. 2024-12-31 stays unread. The loader refuses it.

---

## 1. The claim, stated in one sentence

*The five-sleeve ENGINE-ALPHA construction is a better long-only holding than
any investable alternative a retail investor could reasonably have chosen
instead, net of realistic costs, over the full survivorship-free window.*

It is **not** a claim that the engine found anything the standard factors do not
already span. That claim was tested as `PF-ENGINE-ALPHA-2` and **FAILED** (G4a
FF5+UMD α +0.89 %/yr at t 0.71; regime breadth 3/5). That verdict stands and is
not reopened by this registration.

## 2. Disclosure — why this registration is RETROSPECTIVE-class

**Every number this registration's product bar will be judged on already exists
on disk**, computed during PF-2 and recorded in `runs/PF2/CAMPAIGN_PF2_FINAL.json`
under `product_bar`:

| book | × benchmark terminal wealth |
|---|---|
| candidate (ENGINE-ALPHA construction) | **15.58** |
| ALT-MULTIFACTOR (naive multifactor mix) | 8.94 |
| ALT-VALUE-PROF (simple value+profitability screen) | 6.82 |
| ALT-EW-UNIVERSE (equal-weight universe) | 1.13 |
| BENCHMARK (CRSP VW total return) | 1.00 |

with ruin P(maxDD > 60 %) = 0.0054.

So the product bar **passes at registration time**, and that is precisely why
this registration cannot be treated as a blind test. Recording it as PASS would
be re-badging a known number as a new result. The registration therefore
declares:

> **The product-bar outcome is INFORMATIONAL, not evidential.** The only
> untouched evidence available to this candidate is **G2 (the 2023-24 holdout)**
> and **G7 (the daily sequential simulator, not yet built)**. Nothing else in
> this registration can move the verdict, because nothing else in it is unread.

This is the same discipline applied to `PF-PROF-COMPOSITE-150` on 2026-08-09 and
is applied here without being asked for.

## 3. Frozen alternative set (the comparison, fixed before any further compute)

`BENCHMARK` (CRSP VW total return, FF `mktrf + rf`, pinned vintage) ·
`ALT-EW-UNIVERSE` · `ALT-VALUE-PROF` · `ALT-MULTIFACTOR`. All net of the same
cost model (flat 25 bps unless the spec says KO), same window, same universe
construction, same rebalance calendar. No alternative may be added, dropped, or
re-parameterized after this commit.

## 4. Decision rule (frozen)

**PASS (product track)** requires all of:

1. **Product bar** — beats every frozen alternative on excess terminal wealth.
   *(Informational: already true, see §2.)*
2. **G8 ruin** — P(maxDD > 60 %) ≤ 0.20. *(Informational: 0.0054.)*
3. **G3 placebo** — turnover-matched random selection band passed.
   *(Informational: passed in PF-1/PF-2.)*
4. **G7 daily simulator** — the book survives sequential daily simulation with
   production timing and idempotency, net excess remaining positive.
   **NOT YET RUN. Gating.**
5. **G2 holdout** — a single attended read of 2023-01..2024-12 printing
   positive net excess over the benchmark. **NOT YET RUN. Gating. Failure is
   final** — no re-windowing, no "regime was hostile" appeal.

**Mandatory disclosure at any publication** (amendment §c): the two negative
regime blocks named explicitly, worst calendar year, time underwater, and the
FF5+UMD decomposition identifying the harvested premia.

**Prohibited language, permanently:** engine alpha, model skill, discovery,
edge, "our engine found". Permitted: factor-harvest product, implementation,
premia capture.

## 5. Registered prediction (mine, before G7/G2 run)

> **P-A:** The book survives G7 with net excess degraded by less than 1.0 %/yr
> versus the monthly harness. *Rationale: monthly rebalance at 25 bps is already
> conservative; daily sequencing mostly adds timing slippage, not turnover.*
>
> **P-B:** The book **FAILS** G2 on the 2023-24 holdout. *Rationale: 2023-24 is
> a mega-cap-led regime, exactly the weather in which this book's two negative
> regime blocks occurred. I expect the holdout to print negative net excess.*

P-B is registered deliberately as a prediction against my own candidate. If it
fails as predicted, the product track has cost nothing and taught something. If
it passes, that passage is worth more than any number in §2 — because it is the
only one that was unread when the bar was set.

## 6. What this registration may NOT do

- May not seed a paper lane. Nothing seeds a lane except through G1-G9.
- May not be cited to rehabilitate `PF-ENGINE-ALPHA-2`'s failed engine-skill
  verdict, in any document.
- May not have its alternative set, ruin tolerance, or holdout window amended.
  An amendment invalidates the trial; record it abandoned and register a
  successor.
- May not fire the holdout unattended. G2 is an attended one-shot with Murat
  present, after G7 exists.
