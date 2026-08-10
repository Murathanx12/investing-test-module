# BUILD-1 — Optimus Portfolio Manager

You are the worker for **BUILD-1**, a product build session, not a research night, in `C:\Users\mrthn\Aegis module` on branch `factory/build-1` (with product-side changes on a dedicated branch in `aegis-finance`). The home session is the brain; Murat is the user.

Start with `session_briefing()` + `aegis_verified_state()`. Read `STATUS.md`, `ROADMAP.md`, the NIGHT-8 verdict, current firewall contracts, the analyst-ledger preregistration, Event object implementation, and the existing Aegis-Finance services for earnings revisions, Monte Carlo, risk number and screener before writing replacements.

## Binding mandate

Write this into the top of `ROADMAP.md` verbatim:

> **Aegis Research determines what evidence can be trusted. Optimus Portfolio Manager exists to compound Murat's real capital ($45k reference account; stretch target $100k/12m shown as a probability, never a promise). Neither is subordinate. Three systems: Research Lab (~25% effort, all discipline intact), Portfolio Manager (~55%), Opportunity/Intelligence Engine (~20%). Research gates set reliability weights on signals; they do not block clearly-labelled OBSERVATIONAL information from reaching the PM. The LLM never sizes; the engine never auto-trades; every real-money action is Murat's, attended. Wealth-target screens always print severe-downside probabilities beside the upside with equal prominence. The referee and claim-checker audit PM outputs like research verdicts.**

The product question is now:

> **Given Murat's actual portfolio and cash today, what should he buy, add, hold, trim or sell; how many dollars; what changed; what alternative is better; and what is the resulting wealth/downside distribution?**

Do not allow research backlog to crowd this product question out.

## Binding product rules

1. The LLM may read, extract, reconcile, identify contradictions and explain. Deterministic code owns target weights and dollar changes. A direct LLM weight is a firewall violation.
2. The engine never auto-trades. Recommendations are attended; execution remains Murat's action.
3. Every recommendation carries evidence state: `VALIDATED`, `OBSERVATIONAL`, `STALE`, `MISSING`, or `CONFLICTED`. Observational signals may be used immediately with explicit reliability and provenance.
4. Stretch targets are goals, never forecasts. Any display of `P(W >= target)` must display severe downside probabilities beside it, including at minimum `P(W < $30k)`, `P(W < $20k)`, expected max drawdown and `P(50% drawdown)`.
5. Growth / High Growth / Moonshot may alter sizing and risk constraints only. They must not alter evidence scores or confidence to force the desired outcome.
6. No missing-data hallucinations. Missing/stale analyst data reduces confidence or blocks the affected calculation.
7. Every position competes against its replacement. A candidate is not actionable merely because its standalone score is high.
8. Do not assign credibility because a recommendation comes from JPMorgan, Goldman Sachs, or another prestigious firm. Reliability is empirical when history exists; otherwise it is unavailable.
9. Personal account execution scope is roughly $500-$10,000 orders. Institutional $50m-$500m capacity is BACKGROUND until relevant. For the live PM, model spread, slippage, liquidity/ADV participation and microcap risk.
10. Never commit Murat's real holdings, cost basis or trade history to Git. Private input files are gitignored and tested by pre-commit/CI leakage checks.

## Stop rule

**B1-B3 are mandatory.** An end-to-end morning report must run on a realistic dummy book or the real book before secondary subsystems are polished. If B3 is not running, do not spend the session polishing B4-B7.

## B0 — Roadmap + scoping

- Put the mandate at the top of `ROADMAP.md`.
- Update `STATUS.md` so Portfolio Manager is the current primary product.
- Mark institutional-capacity work BACKGROUND for the personal account. Keep personal execution checks.
- Preserve the Research Lab unchanged as the PM's immune system.

## B1 — Analyst + market data spine (gates B2/B3)

Inventory every source already configured or realistically reachable for:

- current prices and basic fundamentals;
- analyst targets;
- rating actions/upgrades/downgrades;
- target changes;
- EPS/revenue estimate revisions;
- analyst/firm identity and coverage;
- earnings dates;
- EDGAR offerings/13D/13G/material filings;
- FDA/PDUFA/clinical events using the existing harvest where possible.

Probe every endpoint. For every source record:

- actual HTTP/tool status;
- sample payload shape;
- universe coverage;
- history depth;
- freshness;
- analyst identity availability;
- target-history availability;
- rate limits/cost;
- licensing/product-use restriction;
- source timestamp semantics.

No `blocked`, `unavailable` or `not supported` conclusion without a probe receipt.

Normalize analyst observations to the supplied schema. Critical timestamps: `published_at`, `first_seen_at`, `retrieved_at`. Store source ID/locator and raw payload hash.

**Hard constraint:** target history is the likely bottleneck. If historical analyst-level target revisions cannot be reconstructed honestly, v0 must run without analyst-level historical reliability and state `UNAVAILABLE`. Do not invent it.

Deliver `analyst_source_coverage.json/csv` plus a human summary of what can actually be built now.

## B2 — Position objects + private real book

Implement the supplied schemas for `PortfolioState`, `PositionState`, `TradeMemory`, `Recommendation` and `CatalystEvent`.

Private persistence:

- local JSON file for the desktop/module reference implementation;
- gitignored by default;
- public web product keeps holdings client-local unless the user explicitly opts into persistence;
- recommendations and executed trades are separate states.

Minimum position state:

- ticker, shares, cost basis, price, market value, weight;
- original thesis, current thesis, kill conditions;
- consensus target, target upside, revisions 7/30/90d when available;
- analyst breadth/dispersion/freshness;
- next catalyst/date;
- bear/base/bull scenarios;
- evidence labels and reliability;
- current recommended action + dollar change.

Use the supplied dummy book until Murat supplies current holdings and cash. The real book must be ingestible without code changes.

## B3 — Optimus Daily Portfolio v1 (mandatory milestone)

One documented command produces both:

1. a machine-readable JSON report; and
2. a human-readable Markdown/HTML morning report.

Both must share the same `as_of` timestamp and reconcile numerically.

### Header

Print:

- NAV and cash;
- day/MTD/YTD/inception P&L when data exists;
- high-water mark and current drawdown;
- target wealth and required remaining return;
- simulated median / 25th / 75th wealth at 12m;
- `P(target reached)`;
- `P(W < $30k)`;
- `P(W < $20k)`;
- expected max drawdown;
- `P(50% drawdown)`;
- stale-data status.

### Every holding

Emit exactly one of `BUY`, `ADD`, `HOLD`, `TRIM`, `SELL`, plus:

- recommended dollar change;
- target weight;
- evidence state;
- reason codes;
- consensus target/upside;
- target/estimate revisions;
- catalyst and date;
- bear/base/bull outcomes;
- confidence/reliability;
- risk flags;
- execution flags;
- funding source for adds when applicable.

### Opportunity Radar

Rank new candidates that have sufficient data to compare against the actual book. Do not rank raw target upside alone.

### Portfolio Threats

Surface imminent binary events, downgrade clusters, thesis breaks, concentration/correlation risks, financing/dilution warnings, stale prices and liquidity problems.

### Replacement engine

A new candidate must be compared to an actual use of capital. Implement an auditable replacement concept:

`ReplacementEdge(A -> B) = PortfolioUtility(after replacing A with B) - PortfolioUtility(current) - transaction_friction`

If no candidate has positive edge, say so. Do not force turnover.

### Claim audit

Wherever possible, human-report numeric claims must bind directly to receipt/JSON fields. The LLM referee audits prose qualifiers; it should not be the primary numerical verifier.

## B4 — Analyst Alpha Engine v0

Prioritize **revisions over static levels**. Features when available:

- target upside;
- `DeltaTarget_7d`, `DeltaTarget_30d`, `DeltaTarget_90d`;
- number/breadth of raisers vs cutters;
- rating upgrades/downgrades;
- EPS/revenue estimate revision direction and magnitude;
- analyst breadth;
- target dispersion;
- freshness/staleness;
- new coverage initiations.

Penalties:

- binary-event risk;
- financing/dilution risk;
- severe analyst disagreement;
- stale coverage;
- low breadth;
- poor liquidity.

If sufficient analyst history exists, design a reliability score by analyst + firm + sector + horizon. If not, do not fabricate it.

Register a forward-scored validation ledger. Until validated, the PM may use these features as `OBSERVATIONAL` only.

## B5 — Catalyst calendar v0

Build a persistent event calendar from the sources B1 proves available. Include at least:

- earnings;
- FDA/PDUFA/clinical readouts where available;
- offerings/financings from EDGAR;
- 13D/13G changes where parseable;
- investor/company events if reliably sourced.

Each event must carry provenance and timing. Design the recomputation hook:

`new event -> structured extraction -> posterior/thesis update -> deterministic portfolio recomputation -> new recommendation`

Build the calendar now; full real-time automation can follow.

## B6 — Goal-seek Monte Carlo + risk modes

Reuse existing Monte Carlo/risk services rather than rewriting them unless the audit shows a defect.

Modes:

- `GROWTH`
- `HIGH_GROWTH`
- `MOONSHOT`

All modes consume identical signal/evidence objects. They differ only in position caps, concentration limits, risk budget and objective weighting.

A valid objective may emphasize maximizing `P(W_12m >= target)`, but the optimizer must also expose and constrain ruin/drawdown risk. Missing covariance data is never zero correlation.

## B7 — Bloomberg-era reconstruction dataset

Create the supplied intake structure for Murat's manual workflow from Sept 2025 onward.

For every considered stock preserve the **historical as-of state**:

- date considered;
- ticker and price;
- analyst target/rating known at the time;
- source/firm/analyst if known;
- revision direction if known;
- catalyst state;
- bought/rejected;
- if bought: size/entry/exit when trade history supplies it;
- subsequent 30/90/180/365d outcome;
- decision reason.

The supplied 12-page PDF is a historical seed source, not proof. Never replace its dated analyst inputs with current data. Trade history/current holdings are attended inputs supplied later.

Score separately:

- stock-selection skill;
- position-sizing skill;
- exit skill;
- analyst-source skill;
- catalyst judgment;
- regime/tape benefit.

## Minimum tests before STATUS

- no analyst history -> engine still runs, reliability explicitly unavailable;
- stale analyst target -> freshness penalty and no fabricated revision;
- conflicting firms -> conflict/dispersion widens uncertainty;
- Moonshot vs Growth -> identical evidence scores, different sizing only;
- missing/stale price -> no executable dollar recommendation;
- microcap wide spread -> execution penalty or block;
- candidate high standalone score but worsens concentration -> portfolio can reject it;
- LLM attempts to set weight -> firewall raises/ignores it;
- manually altered report number -> deterministic claim audit fails;
- private holdings file appears in staged diff -> privacy check fails.

## End-of-session STATUS

Finish with:

- exact command that produces the morning report;
- what is live / stale / stubbed / missing;
- source coverage B1 actually proved;
- deterministic recommendation logic now implemented;
- VALIDATED vs OBSERVATIONAL features;
- whether the real book can be loaded without code changes;
- failures/bugs found and preserved;
- tests passing;
- commits and manifests;
- single highest-value next build item.

Both repos pushed clean. No auto-trade. No private holdings committed.
