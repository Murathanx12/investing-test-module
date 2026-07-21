"""Offline tests for the promotion/export interface and the insider scorer."""

from __future__ import annotations

import pandas as pd

import aegis_brain.signals.insider_scorer as sc
from aegis_brain.export import build_promotion_bundle, promotable, SIGNALS


def _synthetic_panel(path):
    df = pd.DataFrame({
        "issuer_ticker": ["ABC", "ABC", "ABC", "XYZ"],
        "filing_date": pd.to_datetime(["2020-03-01", "2020-05-01", "2019-01-01", "2020-04-01"]),
        "rptowner_cik": [1, 2, 3, 9],          # ABC has 2 distinct buyers in 2020 H1
        "is_classifiable": [True, True, True, True],
        "is_routine": [False, False, False, False],
    })
    df.to_parquet(path)


def test_scorer_counts_distinct_recent_buyers(tmp_path, monkeypatch):
    p = tmp_path / "insider_panel.parquet"
    _synthetic_panel(p)
    monkeypatch.setattr(sc, "_PANEL", p)
    sc._panel.cache_clear()
    # as of 2020-06-30, ABC has 2 distinct opportunistic buyers in the trailing 12mo
    assert sc.opportunistic_insider_score("ABC", "2020-06-30") == 2.0
    # the 2019-01-01 filing is >12mo before -> excluded
    assert sc.opportunistic_insider_score("ABC", "2020-06-30", lookback_days=365) == 2.0


def test_scorer_is_pit_and_safe(tmp_path, monkeypatch):
    p = tmp_path / "insider_panel.parquet"
    _synthetic_panel(p)
    monkeypatch.setattr(sc, "_PANEL", p)
    sc._panel.cache_clear()
    # before ANY filing is observable -> 0.0, never look-ahead
    assert sc.opportunistic_insider_score("ABC", "2018-01-01") == 0.0
    # the 2019-01-01 filing IS observable by 2019-06-30 -> counts (PIT boundary works)
    assert sc.opportunistic_insider_score("ABC", "2019-06-30") == 1.0
    # unknown ticker -> 0.0, never raises
    assert sc.opportunistic_insider_score("NOPE", "2020-06-30") == 0.0


def test_promotion_bundle_emits_artifacts(tmp_path):
    assert "opportunistic_insider" in promotable()
    d = build_promotion_bundle("opportunistic_insider", out_dir=tmp_path)
    for f in ("TRIAL_DRAFT.md", "registry_row.json", "signal_spec.json", "MANIFEST.txt"):
        assert (d / f).exists(), f
    assert SIGNALS["opportunistic_insider"].survived is True
