import numpy as np
import pandas as pd

from aegis_brain.signals.revisions import compute_revision_scores


def _snaps(cusip, months, meanest, numest=5, fpedats="2020-12-31"):
    """Build synthetic FY1 IBES snapshots: one per month-end, same fiscal target."""
    idx = pd.to_datetime(list(months))
    return pd.DataFrame(
        {
            "cusip": cusip,
            "statpers": idx,
            "meanest": [float(x) for x in meanest],
            "numest": numest,
            "fpedats": pd.Timestamp(fpedats),
        }
    )


def test_upward_sequence_is_positive_downward_is_negative():
    up = _snaps("AAAA0000",
                ["2020-01-15", "2020-02-15", "2020-03-15", "2020-04-15"],
                [1.00, 1.10, 1.20, 1.30])
    down = _snaps("BBBB0000",
                  ["2020-01-15", "2020-02-15", "2020-03-15", "2020-04-15"],
                  [1.30, 1.20, 1.10, 1.00])
    out = compute_revision_scores(pd.concat([up, down], ignore_index=True))

    a = out[out["cusip"] == "AAAA0000"].sort_values("month")
    b = out[out["cusip"] == "BBBB0000"].sort_values("month")
    # first month has no prior -> neutral 0.0; every revised month is signed.
    assert a["revision_score"].iloc[0] == 0.0
    assert (a["revision_score"].iloc[1:] > 0).all()
    assert (b["revision_score"].iloc[1:] < 0).all()


def test_pit_future_snapshot_does_not_affect_earlier_month():
    base = _snaps("AAAA0000",
                  ["2020-01-15", "2020-02-15", "2020-03-15"],
                  [1.00, 1.05, 1.10])
    out_base = compute_revision_scores(base)
    march = pd.Timestamp("2020-03-31")
    march_score = out_base.loc[out_base["month"] == march, "revision_score"].iloc[0]

    # Add an April snapshot with a violent revision; March must not move.
    extended = pd.concat(
        [base, _snaps("AAAA0000", ["2020-04-15"], [5.00])], ignore_index=True
    )
    out_ext = compute_revision_scores(extended)
    march_score_ext = out_ext.loc[out_ext["month"] == march, "revision_score"].iloc[0]

    assert march_score_ext == march_score
    # sanity: the April row exists and is strongly positive.
    apr = out_ext.loc[out_ext["month"] == pd.Timestamp("2020-04-30"), "revision_score"].iloc[0]
    assert apr > 0


def test_last_snapshot_in_month_wins_and_numest_carried_through():
    # Two snapshots in Feb: the later one (numest=9, meanest=2.0) must win.
    df = pd.DataFrame(
        {
            "cusip": "AAAA0000",
            "statpers": pd.to_datetime(
                ["2020-01-15", "2020-02-05", "2020-02-25"]
            ),
            "meanest": [1.00, 1.50, 2.00],
            "numest": [4, 7, 9],
            "fpedats": pd.Timestamp("2020-12-31"),
        }
    )
    out = compute_revision_scores(df).sort_values("month").reset_index(drop=True)
    feb = out[out["month"] == pd.Timestamp("2020-02-29")].iloc[0]
    assert feb["numest"] == 9  # carried from the last in-month snapshot
    assert feb["revision_score"] > 0  # 1.00 -> 2.00 is an upward revision


def test_fiscal_target_roll_is_neutralised():
    # FY1 target rolls from FY2020 to FY2021 in March: not a revision -> 0.0.
    df = pd.DataFrame(
        {
            "cusip": "AAAA0000",
            "statpers": pd.to_datetime(["2020-01-15", "2020-02-15", "2020-03-15"]),
            "meanest": [1.00, 1.10, 3.50],
            "numest": 5,
            "fpedats": pd.to_datetime(["2020-12-31", "2020-12-31", "2021-12-31"]),
        }
    )
    out = compute_revision_scores(df).sort_values("month").reset_index(drop=True)
    mar = out[out["month"] == pd.Timestamp("2020-03-31")].iloc[0]
    assert mar["revision_score"] == 0.0
