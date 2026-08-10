# BUILD-1 Private Data Policy

The real portfolio is user-private operational data.

Binding rules:

1. Real holdings, cost basis, cash and trade history must be stored in gitignored local files by default.
2. No real account data may appear in fixtures, tests, screenshots, README examples, committed receipts or CI logs.
3. Dummy/synthetic portfolios are used for committed tests.
4. A pre-commit/CI check should fail if known private-file paths or markers appear in a staged diff.
5. Recommendation snapshots may be persisted privately for later scoring. Public research receipts should contain only aggregated/anonymized statistics unless Murat explicitly authorizes otherwise.
6. The public/web product should prefer client-local portfolio persistence unless the user explicitly opts into server-side storage.
7. Deleting or rotating the private book must not break the research repo.

Suggested local paths:

- `private/portfolio.json`
- `private/trade_history.csv`
- `private/recommendation_history/`

Suggested `.gitignore` entries:

```gitignore
/private/
**/portfolio_private.json
**/trade_history_private.*
```
