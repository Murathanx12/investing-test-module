"""Factory batch 2 — 10 fundamentals/quality signals (frozen list).

The literature's net-of-cost survivor class (low turnover by construction —
annual data changes once a year) and the formalization of Murat's "will they
still be making money in 5 years" intuition. All from local comp_funda via
the PIT FundStore (6-month reporting lag, 18-month staleness limit).
"""

from __future__ import annotations

from aegis_brain.factory.fundamentals import FundStore
from aegis_brain.factory.signals import FactorySignal


def build_batch2(store: FundStore) -> list[FactorySignal]:
    def sig(char: str):
        return lambda panel, c=char: store.get(c)

    return [
        FactorySignal("gross_prof", "Gross profitability: profitable firms "
                      "outperform, quality side of value (Novy-Marx 2013).",
                      sig("gross_prof"), +1),
        FactorySignal("oper_prof", "Operating profitability / book equity "
                      "(Fama-French 2015 RMW).", sig("oper_prof"), +1),
        FactorySignal("asset_growth_low", "Asset-growth anomaly: aggressive "
                      "balance-sheet expanders underperform (Cooper-Gulen-"
                      "Schill 2008).", sig("asset_growth"), -1),
        FactorySignal("accruals_low", "Accruals anomaly: earnings not backed "
                      "by cash flow reverse (Sloan 1996).", sig("accruals_cf"), -1),
        FactorySignal("net_issuance_low", "Issuers underperform, repurchasers "
                      "outperform (Pontiff-Woodgate 2008).", sig("net_issuance"), -1),
        FactorySignal("btm", "Value: high book-to-market compensates "
                      "distress/mispricing (Fama-French 1992).", sig("btm"), +1),
        FactorySignal("roe", "Return on equity: profitability persistence "
                      "(Haugen-Baker; q-factor ROE).", sig("roe"), +1),
        FactorySignal("cash_prof", "Cash-based operating profitability — the "
                      "strongest net-of-cost profitability variant "
                      "(Ball et al. 2016).", sig("cash_prof"), +1),
        FactorySignal("capx_low", "Investment anomaly: heavy capex spenders "
                      "underperform (q-theory).", sig("capx_at"), -1),
        FactorySignal("fscore_lite", "Piotroski 2000 composite: simple "
                      "financial-strength checklist, 0-9.", sig("fscore_lite"), +1),
    ]
