# PREREG — TRIAL-PF6-PRODUCT-REAL-1

**Registered** 2026-08-10, NIGHT-6, **before any book-vs-ETF number is computed**.
The ETF price spine was fetched first (`data/etf/etf_FETCH_STAMP.json`) so the
data vintage is fixed and auditable, but no comparison has been run.

## 0. Correcting the record before using the data

NIGHT-4 and NIGHT-5 both recorded "a PIT-clean ETF feed is the one thing Murat
must supply" as the blocking dependency on the product question. **That was
wrong, and it was my error, not a missing key.** Tested tonight:

* `POLYGON_API_KEY` — valid, but the plan does not cover the timeframe
  (403 `NOT_AUTHORIZED`).
* `FMP_API_KEY` — valid, but the legacy endpoint is retired (403) and the
  replacement is premium-gated for this symbol (402).
* **`EODHD_API_TOKEN` — works, and has since July.** All four target ETFs plus
  three references, with `adjusted_close`, from inception.

Two nights were spent waiting on a key we already had because I asserted the
blocker instead of testing it. Recorded here rather than quietly fixed.

## 1. The question

Not "does the book beat the market" — NIGHT-4 answered that (+4.4 %/yr, t 2.69)
and NIGHT-4's own spanning test then showed the return is a **known factor**.
The product question is the one a person actually faces:

> **Does the annual small-cap profitability book beat the ETF they could have
> bought instead — net of that ETF's real fees, using its real traded prices?**

Until tonight this was answered against a Ken French academic portfolio, which
is gross of fees and not buyable. This replaces the proxy with the funds.

## 2. Frozen alternative set

Per the execution standard's product bar, the alternative set is frozen **here**,
before compute, and every entry is a fund a person could have bought:

| Ticker | What | Overlap with the book (to 2022-12) |
|---|---|---|
| **IJS** | iShares S&P Small-Cap 600 Value | **2004-08 → 2022-12, ~221 months** |
| **VBR** | Vanguard Small-Cap Value | 2004-03 → 2022-12, ~226 months |
| **AVUV** | Avantis US Small Cap Value (profitability-tilted) | 2019-10 → 2022-12, ~39 months |
| **DFSV** | Dimensional US Small Cap Value | 2022-03 → 2022-12, ~10 months |
| SPY | the market, reference | full |
| IWM | small-cap beta, reference | full |

**IJS and VBR carry the trial.** AVUV and DFSV are the *right* comparison
conceptually — they are the profitability-tilted funds — and they are far too
short to decide anything. That asymmetry is registered now so that a favourable
short-window AVUV number cannot later be promoted to the headline.

## 3. Primary metric and decision rule (frozen)

**Primary: the paired monthly difference between the book's net return and each
ETF's total return, annualized, with a Newey-West(12) t.** The book is net of
its measured era-appropriate cost model; the ETF is net of its expense ratio by
construction (adjusted close). No further adjustment either way.

* **PRODUCT EDGE SHOWN** — requires beating **both IJS and VBR** at
  **t ≥ 2.0** on the paired difference, over their full overlap, **and** the
  ruin constraint P(maxDD > 60 %) ≤ 0.20.
* **NO PRODUCT EDGE SHOWN** — the paired difference against either fund is
  negative at t ≤ −2.0.
* **UNRESOLVED** — anything else. Given ~221 months I expect this outcome, and
  the **MDE must be printed with it**; per the NIGHT-5 amendment a null without
  its detectable effect size may not be published.

**Mandatory disclosure, per standard §(c):** per-regime-block excess including
every negative block by name, worst calendar year, time underwater, and the
FF5+UMD decomposition naming which premia are being harvested. A product number
without its negative blocks violates the standard.

## 4. What this trial may NOT do

* It may not quote AVUV or DFSV as the headline. They are registered as
  underpowered before the numbers exist.
* It may not switch to gross-of-fee French portfolios if the funds are less
  flattering. The proxy's job is over.
* It may not re-open the strategy definition, the clock, or the cost model.
* It may not extend the window past 2022-12; the CRSP panel ends there and
  splicing a different price source onto the book's own returns to reach 2026
  would be a new instrument, not a longer window.
* Survivorship is recorded and **cuts against us**: AVUV, DFSV, IJS and VBR all
  survived. Comparing to survivors makes the alternative look better than the
  average fund a person might have picked, which is the conservative direction.

## 5. House prediction, registered before compute

* **R1** — the book beats IJS and VBR on point estimate but **UNRESOLVED on t**
  (|t| < 2.0). Confidence 0.6.
* **R2** — the margin against IJS/VBR is **smaller** than the +2.03 %/yr the
  French SMALL HiOP proxy gave, because the proxy is gross of fees while these
  funds actually charge them and still track well. Confidence 0.45 — this one
  cuts against the intuition that fees should help us.
* **R3** — against **AVUV** specifically the book **loses** on point estimate
  over the 39-month overlap. AVUV is the same trade run by professionals with
  better execution. Confidence 0.55.
* **R4** — the FF5+UMD decomposition against these funds leaves an alpha whose
  t is **below 2**, i.e. the funds already span the book. Confidence 0.7.
