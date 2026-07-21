"""Offline tests for the historical SEC insider-purchase collector.

All fixtures are synthetic quarterly TSVs written into ``tmp_path`` — no network.
Column names mirror the SEC Insider Transactions Data Sets readme exactly
(SUBMISSION / REPORTINGOWNER / NONDERIV_TRANS), so the parser is exercised against
the real schema.
"""

import pandas as pd

from aegis_brain.events.insider import (
    classify_routine_opportunistic,
    parse_insider_quarter,
)

# Minimal real-schema column sets (only the fields the parser reads plus keys).
NONDERIV_COLS = [
    "ACCESSION_NUMBER", "NONDERIV_TRANS_SK", "SECURITY_TITLE", "TRANS_DATE",
    "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD",
]
SUBMISSION_COLS = [
    "ACCESSION_NUMBER", "FILING_DATE", "PERIOD_OF_REPORT", "DOCUMENT_TYPE",
    "ISSUERCIK", "ISSUERNAME", "ISSUERTRADINGSYMBOL",
]
OWNER_COLS = [
    "ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNERNAME", "RPTOWNER_RELATIONSHIP",
]


def _write_tsv(path, columns, rows):
    pd.DataFrame(rows, columns=columns).to_csv(path, sep="\t", index=False)


def _make_quarter(tmp_path, nonderiv_rows, submission_rows, owner_rows, extra_nd=None):
    """Write a directory of the three TSVs and return its path."""
    d = tmp_path / "q"
    d.mkdir(exist_ok=True)
    nd_cols = NONDERIV_COLS + (list(extra_nd) if extra_nd else [])
    _write_tsv(d / "NONDERIV_TRANS.tsv", nd_cols, nonderiv_rows)
    _write_tsv(d / "SUBMISSION.tsv", SUBMISSION_COLS, submission_rows)
    _write_tsv(d / "REPORTINGOWNER.tsv", OWNER_COLS, owner_rows)
    return d


# --------------------------------------------------------------------------- #
# (a) parser keeps only code P / acquired A and computes value correctly       #
# --------------------------------------------------------------------------- #
def test_parser_keeps_only_open_market_purchases_and_computes_value(tmp_path):
    nd = [
        # a genuine open-market purchase -> KEPT
        ["0001-24-000001", "1", "COMMON", "15-JAN-2024", "P", "100", "10.00", "A"],
        # a sale (S) -> dropped
        ["0001-24-000002", "1", "COMMON", "16-JAN-2024", "S", "50", "12.00", "D"],
        # an option grant (A/acquired) -> dropped: code is 'A', not 'P'
        ["0001-24-000003", "1", "COMMON", "17-JAN-2024", "A", "200", "0", "A"],
        # code P but DISPOSED -> dropped (guard against odd filings)
        ["0001-24-000004", "1", "COMMON", "18-JAN-2024", "P", "10", "9.00", "D"],
    ]
    sub = [
        ["0001-24-000001", "02-FEB-2024", "15-JAN-2024", "4", "0000320193", "APPLE INC", "AAPL"],
        ["0001-24-000002", "02-FEB-2024", "16-JAN-2024", "4", "0000320193", "APPLE INC", "AAPL"],
        ["0001-24-000003", "02-FEB-2024", "17-JAN-2024", "4", "0000320193", "APPLE INC", "AAPL"],
        ["0001-24-000004", "02-FEB-2024", "18-JAN-2024", "4", "0000320193", "APPLE INC", "AAPL"],
    ]
    own = [
        ["0001-24-000001", "0001111111", "COOK TIMOTHY", "OFFICER"],
        ["0001-24-000002", "0001111111", "COOK TIMOTHY", "OFFICER"],
        ["0001-24-000003", "0001111111", "COOK TIMOTHY", "OFFICER"],
        ["0001-24-000004", "0001111111", "COOK TIMOTHY", "OFFICER"],
    ]
    d = _make_quarter(tmp_path, nd, sub, own)
    df = parse_insider_quarter(d)

    assert list(df.columns) == [
        "accession", "filing_date", "trans_date", "issuer_cik", "issuer_ticker",
        "rptowner_cik", "rptowner_name", "shares", "price", "value", "is_10b51",
    ]
    assert len(df) == 1  # only the P/A row survives
    row = df.iloc[0]
    assert row["accession"] == "0001-24-000001"
    assert row["shares"] == 100.0
    assert row["price"] == 10.0
    assert row["value"] == 1000.0  # 100 * 10
    assert row["issuer_ticker"] == "AAPL"
    assert row["issuer_cik"] == "0000320193"
    assert row["rptowner_cik"] == "0001111111"
    assert row["rptowner_name"] == "COOK TIMOTHY"
    assert row["filing_date"] == pd.Timestamp("2024-02-02")
    assert row["trans_date"] == pd.Timestamp("2024-01-15")


def test_parser_reads_zip(tmp_path):
    """The parser accepts a real quarterly .zip, not just a directory."""
    import zipfile

    d = _make_quarter(
        tmp_path,
        [["a-1", "1", "COMMON", "03-MAR-2020", "P", "5", "2.00", "A"]],
        [["a-1", "10-MAR-2020", "03-MAR-2020", "4", "0000000001", "CO", "CO"]],
        [["a-1", "0000000009", "INSIDER ONE", "DIRECTOR"]],
    )
    zpath = tmp_path / "2020q1_form345.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for name in ("NONDERIV_TRANS", "SUBMISSION", "REPORTINGOWNER"):
            zf.write(d / f"{name}.tsv", arcname=f"{name}.tsv")
    df = parse_insider_quarter(zpath)
    assert len(df) == 1
    assert df.iloc[0]["value"] == 10.0


def test_empty_or_missing_source_returns_typed_empty(tmp_path):
    empty = parse_insider_quarter(tmp_path / "does_not_exist")
    assert list(empty.columns)[:3] == ["accession", "filing_date", "trans_date"]
    assert len(empty) == 0


# --------------------------------------------------------------------------- #
# (c) 10b5-1 column handled when present and NA when absent                     #
# --------------------------------------------------------------------------- #
def test_is_10b51_na_when_column_absent(tmp_path):
    d = _make_quarter(
        tmp_path,
        [["a-1", "1", "COMMON", "03-MAR-2020", "P", "5", "2.00", "A"]],
        [["a-1", "10-MAR-2020", "03-MAR-2020", "4", "0000000001", "CO", "CO"]],
        [["a-1", "0000000009", "INSIDER ONE", "DIRECTOR"]],
    )
    df = parse_insider_quarter(d)
    assert df["is_10b51"].isna().all()  # no flag column in the historical schema


def test_is_10b51_parsed_when_column_present(tmp_path):
    # A hypothetical future dataset revision that surfaces the checkbox.
    nd = [
        ["a-1", "1", "COMMON", "03-MAR-2023", "P", "5", "2.00", "A", "1"],
        ["a-2", "1", "COMMON", "04-MAR-2023", "P", "5", "2.00", "A", "0"],
        ["a-3", "1", "COMMON", "05-MAR-2023", "P", "5", "2.00", "A", ""],
    ]
    sub = [
        ["a-1", "10-MAR-2023", "03-MAR-2023", "4", "0000000001", "CO", "CO"],
        ["a-2", "10-MAR-2023", "04-MAR-2023", "4", "0000000001", "CO", "CO"],
        ["a-3", "10-MAR-2023", "05-MAR-2023", "4", "0000000001", "CO", "CO"],
    ]
    own = [
        ["a-1", "0000000009", "INSIDER ONE", "DIRECTOR"],
        ["a-2", "0000000009", "INSIDER ONE", "DIRECTOR"],
        ["a-3", "0000000009", "INSIDER ONE", "DIRECTOR"],
    ]
    d = _make_quarter(tmp_path, nd, sub, own, extra_nd=["TRANS_10B5_1_FLAG"])
    df = parse_insider_quarter(d).sort_values("accession").reset_index(drop=True)
    assert df.loc[0, "is_10b51"] is True or df.loc[0, "is_10b51"]  # '1' -> True
    assert not bool(df.loc[1, "is_10b51"])  # '0' -> False
    assert pd.isna(df.loc[2, "is_10b51"])  # ''  -> NA


# --------------------------------------------------------------------------- #
# (b) routine / opportunistic / classifiability                                #
# --------------------------------------------------------------------------- #
def _purchase(cik, date, accession=None):
    """One tidy purchase row in the parser's output shape."""
    return {
        "accession": accession or f"{cik}-{date}",
        "filing_date": pd.Timestamp(date),
        "trans_date": pd.Timestamp(date),
        "issuer_cik": "0000000001",
        "issuer_ticker": "CO",
        "rptowner_cik": cik,
        "rptowner_name": f"INSIDER {cik}",
        "shares": 100.0,
        "price": 10.0,
        "value": 1000.0,
        "is_10b51": pd.NA,
    }


def test_routine_insider_same_month_three_prior_years():
    # ROUTINE: bought every June for three consecutive prior years, then June 2024.
    rows = [
        _purchase("R", "2021-06-10"),
        _purchase("R", "2022-06-12"),
        _purchase("R", "2023-06-15"),
        _purchase("R", "2024-06-18"),  # <- classify this one
    ]
    out = classify_routine_opportunistic(pd.DataFrame(rows))
    jun24 = out[out["trans_date"] == pd.Timestamp("2024-06-18")].iloc[0]
    assert bool(jun24["is_classifiable"]) is True
    assert bool(jun24["is_routine"]) is True
    assert bool(jun24["is_opportunistic"]) is False


def test_opportunistic_off_pattern_month():
    # Same insider has a full 3-year history (June 2021/2022/2023) -> classifiable,
    # but the 2024 purchase is in SEPTEMBER, off the June pattern -> opportunistic.
    rows = [
        _purchase("O", "2021-06-10"),
        _purchase("O", "2022-06-12"),
        _purchase("O", "2023-06-15"),
        _purchase("O", "2024-09-20"),  # <- classify this one
    ]
    out = classify_routine_opportunistic(pd.DataFrame(rows))
    sep24 = out[out["trans_date"] == pd.Timestamp("2024-09-20")].iloc[0]
    assert bool(sep24["is_classifiable"]) is True
    assert bool(sep24["is_routine"]) is False
    assert bool(sep24["is_opportunistic"]) is True


def test_insufficient_history_is_not_classifiable():
    # Only two prior years of purchases -> cannot be classified; must NOT default
    # to opportunistic.
    rows = [
        _purchase("N", "2022-06-10"),
        _purchase("N", "2023-06-12"),
        _purchase("N", "2024-06-15"),  # <- classify this one; only Y-1,Y-2 exist
    ]
    out = classify_routine_opportunistic(pd.DataFrame(rows))
    jun24 = out[out["trans_date"] == pd.Timestamp("2024-06-15")].iloc[0]
    assert bool(jun24["is_classifiable"]) is False
    assert bool(jun24["is_routine"]) is False
    assert bool(jun24["is_opportunistic"]) is False


def test_classification_is_point_in_time_no_lookahead():
    # A single insider: their FIRST-ever purchase (2021) has no prior history and
    # must be unclassifiable even though later purchases exist in the frame.
    rows = [
        _purchase("P", "2021-06-10"),  # first ever
        _purchase("P", "2022-06-10"),
        _purchase("P", "2023-06-10"),
        _purchase("P", "2024-06-10"),
    ]
    out = classify_routine_opportunistic(pd.DataFrame(rows)).sort_values("trans_date")
    first = out.iloc[0]
    last = out.iloc[-1]
    assert bool(first["is_classifiable"]) is False  # no look-ahead to 2022-2024
    assert bool(last["is_routine"]) is True  # 2024 sees 2021/2022/2023


def test_gap_in_history_breaks_classifiability():
    # Purchases in 2020, 2021, 2023 (2022 missing) -> the 2024 buy lacks a purchase
    # in each of Y-1..Y-3 (2022 absent) -> not classifiable.
    rows = [
        _purchase("G", "2020-06-10"),
        _purchase("G", "2021-06-10"),
        _purchase("G", "2023-06-10"),
        _purchase("G", "2024-06-10"),
    ]
    out = classify_routine_opportunistic(pd.DataFrame(rows))
    jun24 = out[out["trans_date"] == pd.Timestamp("2024-06-10")].iloc[0]
    assert bool(jun24["is_classifiable"]) is False
