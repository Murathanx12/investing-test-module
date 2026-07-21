"""Offline tests for the PEAD/SUE earnings-surprise signal.

All fixtures are hand-built synthetic frames — no network. Column names mirror
the real Compustat ``comp_fundq`` and IBES ``ibes_epsus`` schemas so the pure
computational cores (``time_series_sue`` / ``analyst_sue``) are exercised against
the shapes ``build_sue_events`` feeds them.
"""

import numpy as np
import pandas as pd

from aegis_brain.signals.sue import analyst_sue, time_series_sue

# EPS panel for a single firm across 12 consecutive fiscal quarters (2010-2012).
# Same-quarter-prior-year differences (dEPS) are therefore defined from 2011 Q1.
_EPS = {
    (2010, 1): 1.0, (2010, 2): 1.1, (2010, 3): 1.2, (2010, 4): 1.3,
    (2011, 1): 1.2, (2011, 2): 1.4, (2011, 3): 1.5, (2011, 4): 1.7,
    (2012, 1): 1.5, (2012, 2): 1.6, (2012, 3): 1.9, (2012, 4): 2.2,
}


def _fundq_12q(gvkey="001000", cusip="12345678900", price=10.0):
    """A 12-quarter comp_fundq-shaped frame for one firm, quarter-end datadates."""
    rows = []
    for (fy, fq), eps in _EPS.items():
        month = fq * 3  # 3,6,9,12
        datadate = pd.Timestamp(fy, month, 1) + pd.offsets.MonthEnd(0)
        rows.append(
            {
                "gvkey": gvkey,
                "datadate": datadate,
                "fyearq": fy,
                "fqtr": fq,
                "rdq": datadate + pd.Timedelta(days=30),  # noqa: report ~a month later
                "cusip": cusip,
                "epspxq": eps,
                "prccq": price,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# (a) time-series SUE: seasonal-diff / trailing-vol computed correctly          #
# --------------------------------------------------------------------------- #
def test_time_series_sue_seasonal_diff_and_vol_scaling():
    df = time_series_sue(_fundq_12q())
    df = df.set_index(["fyearq", "fqtr"])

    # Seasonal difference is epspxq(t) - epspxq(same quarter, prior year).
    assert df.loc[(2012, 4), "deps"] == pytest_approx(2.2 - 1.7)  # 0.5
    assert df.loc[(2011, 1), "deps"] == pytest_approx(1.2 - 1.0)  # 0.2

    # At 2012 Q4 all eight dEPS observations exist (2011 Q1 .. 2012 Q4):
    deps_8 = np.array([0.2, 0.3, 0.3, 0.4, 0.3, 0.2, 0.4, 0.5])
    expected_std = deps_8.std(ddof=1)  # pandas rolling std uses ddof=1
    expected_sue = 0.5 / expected_std
    assert df.loc[(2012, 4), "sue_ts"] == pytest_approx(expected_sue)

    # min_periods guard: 2011 Q4 has only 4 dEPS observations (< 6) -> undefined.
    assert pd.isna(df.loc[(2011, 4), "sue_ts"])
    # 2012 Q2 is the first quarter reaching 6 dEPS observations -> defined.
    assert pd.notna(df.loc[(2012, 2), "sue_ts"])


# --------------------------------------------------------------------------- #
# (b) a positive earnings surprise yields a positive SUE                        #
# --------------------------------------------------------------------------- #
def test_positive_surprise_gives_positive_ts_sue():
    # 2012 Q4 EPS (2.2) is well above the year-ago quarter (1.7): dEPS > 0.
    df = time_series_sue(_fundq_12q()).set_index(["fyearq", "fqtr"])
    assert df.loc[(2012, 4), "sue_ts"] > 0


def test_positive_surprise_gives_positive_analyst_sue():
    fundq = pd.DataFrame(
        [{
            "gvkey": "001000",
            "datadate": pd.Timestamp("2012-03-31"),
            "rdq": pd.Timestamp("2012-04-20"),
            "cusip": "12345678900",
            "prccq": 20.0,
        }]
    )
    # Consensus 1.00, actual 1.50 -> a beat: (1.50 - 1.00)/20 = +0.025.
    ibes = pd.DataFrame(
        [{
            "fpi": "6",
            "cusip": "12345678",
            "fpedats": pd.Timestamp("2012-03-31"),
            "statpers": pd.Timestamp("2012-03-15"),
            "meanest": 1.00,
            "numest": 8.0,
            "actual": 1.50,
        }]
    )
    res = analyst_sue(fundq, ibes)
    assert len(res) == 1
    assert res.loc[0, "sue_analyst"] == pytest_approx((1.50 - 1.00) / 20.0)
    assert res.loc[0, "sue_analyst"] > 0
    assert res.loc[0, "numest"] == 8.0


# --------------------------------------------------------------------------- #
# (c) consensus must come from a snapshot STRICTLY BEFORE rdq (no look-ahead)   #
# --------------------------------------------------------------------------- #
def test_consensus_strictly_before_rdq_is_respected():
    fundq = pd.DataFrame(
        [{
            "gvkey": "001000",
            "datadate": pd.Timestamp("2012-03-31"),
            "rdq": pd.Timestamp("2012-04-20"),
            "cusip": "12345678900",
            "prccq": 10.0,
        }]
    )
    ibes = pd.DataFrame(
        [
            # Legitimate pre-announcement snapshot (this one must be used).
            {"fpi": "6", "cusip": "12345678", "fpedats": pd.Timestamp("2012-03-31"),
             "statpers": pd.Timestamp("2012-04-10"), "meanest": 1.00, "numest": 5.0,
             "actual": 2.00},
            # A snapshot dated ON/AFTER rdq — a look-ahead that must be ignored.
            {"fpi": "6", "cusip": "12345678", "fpedats": pd.Timestamp("2012-03-31"),
             "statpers": pd.Timestamp("2012-04-25"), "meanest": 5.00, "numest": 9.0,
             "actual": 2.00},
        ]
    )
    res = analyst_sue(fundq, ibes)
    assert len(res) == 1
    # Uses the before-rdq consensus 1.00, NOT the later 5.00.
    assert res.loc[0, "meanest_used"] == 1.00
    assert res.loc[0, "numest"] == 5.0
    assert res.loc[0, "sue_analyst"] == pytest_approx((2.00 - 1.00) / 10.0)  # +0.1


def test_no_ibes_match_yields_empty_result():
    fundq = pd.DataFrame(
        [{
            "gvkey": "001000",
            "datadate": pd.Timestamp("2012-03-31"),
            "rdq": pd.Timestamp("2012-04-20"),
            "cusip": "99999999900",  # no IBES row for this CUSIP
            "prccq": 10.0,
        }]
    )
    ibes = pd.DataFrame(
        [{"fpi": "6", "cusip": "12345678", "fpedats": pd.Timestamp("2012-03-31"),
          "statpers": pd.Timestamp("2012-04-10"), "meanest": 1.0, "numest": 5.0,
          "actual": 2.0}]
    )
    res = analyst_sue(fundq, ibes)
    assert res.empty  # no fabricated surprise


# small local approx helper to avoid importing pytest.approx at module import time
def pytest_approx(x, tol=1e-9):
    import pytest

    return pytest.approx(x, abs=tol, rel=1e-6)
