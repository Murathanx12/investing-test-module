"""EDGAR 13D/13G collector spec tests — canned index fixtures, no network.

Two things are pinned here. First the parser, because form.idx is fixed-width
and space-padded and a company name containing digits or a run of spaces is
exactly the input that shifts every column silently. Second, and more
importantly, the FAILURE behaviour: NEG_RESULTS §5 is the receipt for a
collector that passed every offline test while 403-ing on 100% of prod fetches
and writing false zeros. An HTTP error here must raise, never return empty.
"""

from __future__ import annotations

import pandas as pd
import pytest
import requests

from aegis_brain.data import edgar_13dg as e13


# A faithful form.idx excerpt: real header, real rule line, zero-padded and
# unpadded CIKs, a slash-suffixed amendment, a company name with digits, and a
# company name containing a double space.
FIXTURE = """Description:           Master Index of EDGAR Dissemination Feed by Form Type
Last Data Received:    March 31, 2010
Comments:              webmaster@sec.gov

Form Type   Company Name                                       CIK         Date Filed  File Name
---------------------------------------------------------------------------------------------
10-K        BORING CO                                          0000111111  2010-01-05  edgar/data/111111/0000111111-10-000001.txt
SC 13D      ACME CORP                                          0000320193  2010-02-16  edgar/data/320193/0000320193-10-000007.txt
SC 13D      ICAHN CARL C                                       921669      2010-02-16  edgar/data/921669/0000320193-10-000007.txt
SC 13D/A    ACME CORP                                          0000320193  2010-03-01  edgar/data/320193/0000320193-10-000009.txt
SC 13G      3M CO 2 INC                                        0000066740  2010-02-09  edgar/data/66740/0000066740-10-000003.txt
SC 13G/A    SMITH  BARNEY FUND                                 0000777777  2010-02-10  edgar/data/777777/0000777777-10-000002.txt
S-1         IRRELEVANT INC                                     0000999999  2010-02-11  edgar/data/999999/0000999999-10-000004.txt
"""


# ── parsing ──────────────────────────────────────────────────────────────────
def test_parses_only_the_four_form_types():
    df = e13.parse_form_idx(FIXTURE)
    assert len(df) == 5
    assert set(df["form_type"]) == {"SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"}
    assert "10-K" not in set(df["form_type"])
    assert "S-1" not in set(df["form_type"])


def test_extracts_fields_and_accession():
    df = e13.parse_form_idx(FIXTURE)
    row = df[(df["form_type"] == "SC 13D") & (df["cik"] == 320193)].iloc[0]
    assert row["company_name"] == "ACME CORP"
    assert row["filed_date"] == pd.Timestamp("2010-02-16")
    assert row["accession"] == "0000320193-10-000007"
    assert row["file_name"] == "edgar/data/320193/0000320193-10-000007.txt"


def test_zero_padded_and_unpadded_ciks_both_parse_to_int():
    df = e13.parse_form_idx(FIXTURE)
    assert 320193 in set(df["cik"])          # was 0000320193
    assert 921669 in set(df["cik"])          # was unpadded
    assert df["cik"].dtype.kind == "i"


def test_company_name_containing_digits_does_not_shift_columns():
    """'3M CO 2 INC' has digits mid-name; a greedy CIK match would eat the 2."""
    df = e13.parse_form_idx(FIXTURE)
    row = df[df["accession"] == "0000066740-10-000003"].iloc[0]
    assert row["company_name"] == "3M CO 2 INC"
    assert row["cik"] == 66740
    assert row["filed_date"] == pd.Timestamp("2010-02-09")


def test_company_name_with_internal_double_space_survives():
    df = e13.parse_form_idx(FIXTURE)
    row = df[df["cik"] == 777777].iloc[0]
    assert "SMITH" in row["company_name"] and "BARNEY" in row["company_name"]
    assert row["form_type"] == "SC 13G/A"


def test_one_accession_can_carry_two_ciks():
    """The structural fact a 13D trial must design around: EDGAR indexes the
    filing under BOTH the issuer and the filer, sharing one accession."""
    df = e13.parse_form_idx(FIXTURE)
    shared = df[df["accession"] == "0000320193-10-000007"]
    assert len(shared) == 2
    assert set(shared["cik"]) == {320193, 921669}


def test_header_and_rule_lines_are_ignored():
    df = e13.parse_form_idx(FIXTURE)
    assert not df["company_name"].str.contains("Company Name").any()
    assert not df["company_name"].str.startswith("---").any()


def test_empty_input_yields_typed_empty_frame():
    df = e13.parse_form_idx("no filings here\n")
    assert len(df) == 0
    assert list(df.columns) == ["form_type", "company_name", "cik",
                                "filed_date", "accession", "file_name"]


# ── fail loud ────────────────────────────────────────────────────────────────
class _Resp:
    def __init__(self, status: int, text: str = ""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


def test_sec_get_raises_on_persistent_403(monkeypatch):
    """SEC returns 403 (not 429) when the rate cap trips — NEG_RESULTS §5. It
    must surface, not degrade to empty."""
    calls = []

    def fake(url, **kw):
        calls.append(url)
        return _Resp(403)

    monkeypatch.setattr(e13.requests, "get", fake)
    monkeypatch.setattr(e13.time, "sleep", lambda s: None)
    with pytest.raises(requests.HTTPError):
        e13._sec_get("https://www.sec.gov/x")
    assert len(calls) == 2, "should attempt once, then retry once, then raise"


def test_sec_get_retries_a_transient_403_then_succeeds(monkeypatch):
    seq = [_Resp(403), _Resp(200, "ok")]
    monkeypatch.setattr(e13.requests, "get", lambda url, **kw: seq.pop(0))
    monkeypatch.setattr(e13.time, "sleep", lambda s: None)
    assert e13._sec_get("https://www.sec.gov/x").text == "ok"


def test_sec_get_raises_on_500(monkeypatch):
    monkeypatch.setattr(e13.requests, "get", lambda url, **kw: _Resp(500))
    with pytest.raises(requests.HTTPError):
        e13._sec_get("https://www.sec.gov/x")


def test_collect_propagates_the_failure_instead_of_writing_a_short_parquet(
        monkeypatch, tmp_path):
    """A quarter that 403s must abort the harvest. An empty 2008Q3 is
    indistinguishable from 'no activists filed in 2008Q3' once it is on disk."""
    def fake(url, **kw):
        return _Resp(200, FIXTURE) if "QTR1" in url else _Resp(403)

    monkeypatch.setattr(e13.requests, "get", fake)
    monkeypatch.setattr(e13.time, "sleep", lambda s: None)
    with pytest.raises(requests.HTTPError):
        e13.collect([2010], out_dir=tmp_path)
    # Q1 was checkpointed before Q2 failed — the harvest is resumable, and the
    # partial state is one file, not a silently truncated combined frame.
    assert (tmp_path / "idx_2010Q1.parquet").exists()
    assert not (tmp_path / "idx_2010Q2.parquet").exists()


def test_collect_resumes_from_checkpoints(monkeypatch, tmp_path):
    monkeypatch.setattr(e13.requests, "get", lambda url, **kw: _Resp(200, FIXTURE))
    monkeypatch.setattr(e13.time, "sleep", lambda s: None)
    e13.collect([2010], out_dir=tmp_path)

    def boom(url, **kw):
        raise AssertionError("network hit despite existing checkpoints")

    monkeypatch.setattr(e13.requests, "get", boom)
    out = e13.collect([2010], out_dir=tmp_path, resume=True)
    assert len(out) == 5 * 4 - 0 or len(out) > 0
    assert out["accession"].nunique() >= 4


# ── rate limiter ─────────────────────────────────────────────────────────────
def test_rate_limiter_paces_below_the_sec_cap():
    """8/s target: ten waits must consume at least 9 intervals of 1/8s."""
    import time as _t
    lim = e13._RateLimiter(max_per_sec=8.0)
    t0 = _t.monotonic()
    for _ in range(10):
        lim.wait()
    elapsed = _t.monotonic() - t0
    assert elapsed >= 9 * (1 / 8.0) * 0.9
    assert e13._RATE_LIMITER._min_interval >= 1 / 10.0, "must stay under 10/s"


def test_user_agent_declares_a_contact():
    """SEC 403s anonymous/default agents — the UA must carry a real contact."""
    assert "@" in e13._HEADERS["User-Agent"]
    assert e13._TIMEOUT > 0
