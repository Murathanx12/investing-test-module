# Product note v0.1 — core-satellite, with the numbers we can defend

**For Murat. One page. No marketing language — this is the sentence the app will
eventually stand on, so it has to be one that survives being attacked.**

Status: **draft for decision, not a claim to publish.** Every number below is
backtested on 1982-11 → 2022-12 (482 months), survivorship-free CRSP, net of a
measured cost model. Nothing here has forward evidence. The 24-month rule stands.

---

## The shape

**Core: a broad market index fund. Satellite: the annual small-cap
profitability book (150 names, rebalanced once a year).**

The core is not a placeholder — it is the answer to "why can't we buy the big
winners?" A cap-weighted index **already holds them, and already rides them**:
when a mega-cap wins, its weight rises and you hold more of it, with no
prediction required. That is exactly why the index is hard to beat, and it is
why every timing and winner-copying test this programme ran lost to simply
holding it. We are not missing the big stocks. The core owns them. Our job is
only the satellite.

## What each layer contributes

| Layer | What it is | Measured contribution |
|---|---|---|
| Core | market index | the market return, ~11.2 %/yr over this window |
| Satellite | 150 small-cap profitability names, annual | **+4.4 %/yr over the market**, t 2.69 |

**The satellite number is not ours, and the note must say so.** NIGHT-4's
spanning test showed a properly built small-cap profitability factor absorbs
almost all of it — incremental alpha falls from +4.23 %/yr (t 3.65) to
**+1.04 % (t 1.07)**. The return is real and it is **already paid by a known
factor**. This is a harvest, honestly named. It is not engine skill and must
never be sold as one.

## The number that decides whether this is a product

The honest comparison is not against the S&P. It is against **the buyable fund
that already does this** — a small-cap profitability/value ETF (AVUV, DFSV).
Using the Ken French SMALL HiOP portfolio as the closest proxy:

> **The book adds +2.03 %/yr over the buyable alternative, at t 1.13.**
> Post-2001: +2.88 %/yr at t 1.31. Terminal wealth 2.04× over 40 years,
> at a shallower max drawdown (−48.4 % vs −52.8 %).

**Read the t, not the headline. At t 1.13 this is not distinguishable from zero
even with forty years of data.** The comparison is also biased *in our favour on
one axis and against us on another*: the French portfolio is gross of trading
costs and of any expense ratio, while our number is net of a measured cost
model — but our number has also been selected by us, on this data, after 821
tests.

**This is the one thing blocked on you: a PIT-clean ETF price feed (Polygon or
FMP) for AVUV, DFSV, IJS, VBR from 2019-09.** Until that exists, the product
comparison rests on an academic proxy rather than the fund a person would
actually buy.

## What the blend implies at realistic weights

Blending is linear, and this was proved rather than assumed in NIGHT-2:
**excess of the blend = satellite weight × satellite excess.** There is no
diversification bonus to be had here.

| Satellite weight | vs holding the index alone | vs someone who already owns the ETF |
|---:|---:|---:|
| 20 % | +0.88 %/yr | +0.41 %/yr |
| 30 % | +1.32 %/yr | +0.61 %/yr |
| 40 % | +1.76 %/yr | +0.81 %/yr |

The right-hand column is the honest one for anyone who could just buy AVUV, and
**every entry in it sits inside the noise of the estimate that produced it.**

## What is NOT modelled, and matters

* **Tax.** The satellite turns over ~48 % of the book a year. In a taxable
  account that converts part of the excess into short- and long-term gains. Not
  modelled anywhere. On a small account this could plausibly consume the entire
  right-hand column above.
* **The trading a person actually does.** G7 — the daily simulator built
  tonight — replaces month-end fills with next-day opens, charges the spread
  actually quoted, caps orders at a share of daily volume and marks the book
  daily. Its results land with this note's next revision. **The daily maximum
  drawdown will be worse than the −48.4 % month-end figure above**, because a
  month-end mark is not what a holder lives through.
* **Capacity.** 150 small-cap names is not infinitely scalable. G7's capacity
  ladder is the first measurement this programme has of where it stops working.
* **Behaviour.** A −48 % drawdown lasting years is the actual product risk. Most
  people sell there. The strategy's returns assume they do not.

## The sentence, as I would write it today

> Hold a broad index as the core. If you want a tilt, the evidence supports a
> small-cap profitability satellite at 20–40 % — but that tilt is a **known
> factor you can also buy in one ticker**, and our version's advantage over that
> ticker is **+2 %/yr with a t of 1.1**, which is honestly indistinguishable
> from zero. Choose it because you want the tilt implemented cheaply and
> transparently, not because we have shown we beat the fund.

That is a smaller claim than the roadmap started with. It is the one the data
supports.
