"""The source policy is only worth having if it is testable."""
from __future__ import annotations

from aegis_brain.analyst.source_policy import (ALLOWED, Fact, SourceTier,
                                               audit_note, classify_url)


def test_filings_and_regulators_are_primary():
    for u in ("https://www.sec.gov/Archives/edgar/data/1/x.htm",
              "https://efts.sec.gov/LATEST/search-index?q=x",
              "https://www.fda.gov/news/x",
              "https://fred.stlouisfed.org/series/GDP"):
        assert classify_url(u) is SourceTier.PRIMARY, u


def test_company_ir_subdomain_is_primary_without_being_listed():
    assert classify_url("https://ir.somecompany.com/news") is SourceTier.PRIMARY
    assert classify_url("https://investors.acme.co.uk/press") is SourceTier.PRIMARY


def test_major_wires_are_wire():
    for u in ("https://www.reuters.com/markets/x", "https://www.wsj.com/a",
              "https://apnews.com/article/x"):
        assert classify_url(u) is SourceTier.WIRE, u


def test_blogs_and_forums_are_context_only():
    for u in ("https://seekingalpha.com/article/1", "https://www.reddit.com/r/x",
              "https://x.com/someone/status/1", "https://medium.com/@a/b",
              "https://finance.yahoo.com/news/x"):
        assert classify_url(u) is SourceTier.CONTEXT_ONLY, u


def test_unknown_host_is_unknown_not_allowed():
    t = classify_url("https://randomnewsletter.example/post")
    assert t is SourceTier.UNKNOWN
    assert t not in ALLOWED


def test_subdomains_inherit_their_parent_tier():
    assert classify_url("https://old.reuters.com/x") is SourceTier.WIRE
    assert classify_url("https://amp.seekingalpha.com/x") is SourceTier.CONTEXT_ONLY


def test_garbage_url_is_unknown_and_does_not_raise():
    assert classify_url("") is SourceTier.UNKNOWN
    assert classify_url("not a url at all") is SourceTier.UNKNOWN


# ── the rule that actually matters ──────────────────────────────────────────
def test_a_fact_with_no_url_is_not_sourced():
    assert not Fact("the plant burned down").sourced


def test_a_fact_backed_only_by_a_blog_is_not_sourced():
    assert not Fact("big news", ("https://seekingalpha.com/a",)).sourced


def test_best_source_wins_within_a_fact():
    f = Fact("revenue was X", ("https://seekingalpha.com/a",
                               "https://www.sec.gov/x"))
    assert f.best_tier is SourceTier.PRIMARY
    assert f.sourced


def test_note_with_any_unsourced_fact_is_flagged():
    a = audit_note([Fact("a", ("https://www.sec.gov/x",)),
                    Fact("b", ("https://reddit.com/r/x",))])
    assert a["estimate_flagged"]
    assert a["unsourced_count"] == 1
    assert a["sourced_share"] == 0.5


def test_fully_sourced_note_is_not_flagged():
    a = audit_note([Fact("a", ("https://www.sec.gov/x",)),
                    Fact("b", ("https://www.reuters.com/y",))])
    assert not a["estimate_flagged"]
    assert a["sourced_share"] == 1.0


def test_empty_note_is_flagged_rather_than_silently_clean():
    """A note with no facts must not score as perfectly sourced."""
    a = audit_note([])
    assert a["estimate_flagged"]
    assert a["flag_reason"] == "no facts offered"


def test_unknown_share_is_reported_separately_from_context():
    a = audit_note([Fact("a", ("https://weird.example/x",)),
                    Fact("b", ("https://reddit.com/r/x",))])
    assert a["by_tier"]["UNKNOWN"] == 1
    assert a["by_tier"]["CONTEXT_ONLY"] == 1
