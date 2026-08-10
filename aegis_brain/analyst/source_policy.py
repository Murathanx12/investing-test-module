"""Source policy for the analyst loop — what the LLM is allowed to believe.

The forward analyst ledger lets a model read the web before it estimates. That
is the whole reason it might add anything the engine cannot: the engine knows
what happened to the numbers, and it does not know that a plant burned down last
Tuesday. It is also the single largest new attack surface this programme has
ever opened, because "the model read something" is indistinguishable from "the
model read someone's position talking its own book" unless the sources are
classified.

The rule is deliberately blunt: **a claim is only as good as the best source
supporting it, and a claim with no allowed source is marked unsourced and its
estimate is flagged.** Blogs, forums and aggregators are not banned — they are
demoted to context, which is what they are: a place to notice something, never a
basis for a number.

This module classifies. It does not fetch, and it does not decide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class SourceTier(str, Enum):
    #: A primary record: the filer, the exchange, or the company itself.
    PRIMARY = "PRIMARY"
    #: A major wire or paper of record with a corrections policy.
    WIRE = "WIRE"
    #: May be read for orientation; may NEVER be the basis of an estimate.
    CONTEXT_ONLY = "CONTEXT_ONLY"
    #: Not recognised. Treated exactly as CONTEXT_ONLY, and counted separately
    #: so the unknown share of a note's diet is visible rather than assumed.
    UNKNOWN = "UNKNOWN"


#: Estimates may rest on these.
ALLOWED = {SourceTier.PRIMARY, SourceTier.WIRE}

_PRIMARY_HOSTS = {
    "sec.gov", "efts.sec.gov", "edgar.sec.gov",       # filings + full-text
    "federalreserve.gov", "bls.gov", "bea.gov", "treasury.gov",
    "fred.stlouisfed.org", "census.gov", "eia.gov",
    "fda.gov", "clinicaltrials.gov", "uspto.gov",
    "nasdaq.com", "nyse.com", "cboe.com", "otcmarkets.com",  # exchange notices
    "businesswire.com", "prnewswire.com", "globenewswire.com",  # IR wires
    "accesswire.com", "newsfilecorp.com",
}
_WIRE_HOSTS = {
    "reuters.com", "bloomberg.com", "apnews.com", "wsj.com", "ft.com",
    "barrons.com", "economist.com", "nikkei.com", "scmp.com",
    "cnbc.com", "marketwatch.com",
}
_CONTEXT_HOSTS = {
    "seekingalpha.com", "fool.com", "motleyfool.com", "benzinga.com",
    "zacks.com", "investing.com", "stocktwits.com", "reddit.com",
    "twitter.com", "x.com", "substack.com", "medium.com", "quora.com",
    "youtube.com", "tiktok.com", "discord.com", "wallstreetbets.com",
    "finance.yahoo.com", "yahoo.com", "msn.com", "simplywall.st",
    "gurufocus.com", "tipranks.com", "insidermonkey.com",
}

#: An IR subdomain of the issuer is primary; matched structurally, not listed.
_IR_PATTERN = re.compile(r"^(?:ir|investor|investors|newsroom|press)\.")


def _host(url: str) -> str:
    h = (urlparse(url if "//" in url else f"//{url}").hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def classify_url(url: str) -> SourceTier:
    """Tier of one URL. Unknown hosts are UNKNOWN, never optimistically allowed."""
    h = _host(url)
    if not h:
        return SourceTier.UNKNOWN
    for host_set, tier in ((_PRIMARY_HOSTS, SourceTier.PRIMARY),
                           (_WIRE_HOSTS, SourceTier.WIRE),
                           (_CONTEXT_HOSTS, SourceTier.CONTEXT_ONLY)):
        if h in host_set or any(h.endswith("." + k) for k in host_set):
            return tier
    if _IR_PATTERN.match(h):
        return SourceTier.PRIMARY
    return SourceTier.UNKNOWN


@dataclass(frozen=True)
class Fact:
    """One assertion in a note, with the URLs offered in support of it."""

    statement: str
    urls: tuple[str, ...] = ()

    @property
    def tiers(self) -> tuple[SourceTier, ...]:
        return tuple(classify_url(u) for u in self.urls)

    @property
    def best_tier(self) -> SourceTier:
        for t in (SourceTier.PRIMARY, SourceTier.WIRE, SourceTier.CONTEXT_ONLY):
            if t in self.tiers:
                return t
        return SourceTier.UNKNOWN

    @property
    def sourced(self) -> bool:
        """True only if some ALLOWED source backs it. No source => not sourced."""
        return self.best_tier in ALLOWED


def audit_note(facts: list[Fact]) -> dict:
    """Score a note's evidence diet. Reported with every estimate.

    `estimate_flagged` is the operative output: an estimate resting on a note
    where any load-bearing fact is unsourced is not thrown away — it is recorded
    WITH the flag, so the forward ledger can later measure whether flagged
    estimates were worse. Discarding them would destroy the only evidence that
    would settle the question.
    """
    tiers = [f.best_tier for f in facts]
    unsourced = [f.statement for f in facts if not f.sourced]
    n = len(facts)
    return {
        "facts": n,
        "by_tier": {t.value: sum(1 for x in tiers if x is t) for t in SourceTier},
        "unsourced_count": len(unsourced),
        "unsourced_statements": unsourced[:10],
        "sourced_share": round((n - len(unsourced)) / n, 3) if n else 0.0,
        "estimate_flagged": bool(unsourced) or n == 0,
        "flag_reason": ("no facts offered" if n == 0 else
                        f"{len(unsourced)} of {n} facts lack an allowed source"
                        if unsourced else ""),
        "policy": ("allowed = SEC/regulator filings, company releases and IR, "
                   "transcripts, exchange notices, major wires. Blogs, forums "
                   "and aggregators are context only and can never support an "
                   "estimate. Unknown hosts are treated as context, not "
                   "optimistically allowed."),
    }
