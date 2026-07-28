"""Filing text -> token bag -> YoY similarity (TRIAL-TEXT-LAZY).

Storage strategy (this is why the pull fits on disk at all): raw filings are NEVER
persisted. Similarity is only ever computed between a firm and ITS OWN prior-year
filing, so the pipeline walks one firm at a time, holds at most two token bags in
memory, emits two floats, and discards the documents. What lands on disk is the
signal panel — kilobytes — not a text corpus.

Text handling follows Cohen-Malloy-Nguyen: strip markup, drop tables and numbers,
compare word usage. `text_cos` is cosine similarity on term frequencies,
`text_jac` is Jaccard on the token sets; both are declared (+) — higher similarity
(a "non-changer") is the hypothesised good side.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_TABLE_RE = re.compile(rb"<table[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
_SCRIPT_RE = re.compile(rb"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(rb"<[^>]+>")
_ENTITY_RE = re.compile(rb"&[a-zA-Z#0-9]{1,8};")
_TOKEN_RE = re.compile(r"[a-z]{3,}")

# Boilerplate that appears in every filing regardless of content would inflate
# similarity uniformly; standard English stopwords are the cheap, non-tuned cut.
_STOP = {
    "the", "and", "for", "that", "with", "this", "are", "was", "were", "our", "not",
    "has", "have", "had", "any", "all", "may", "such", "from", "which", "under",
    "its", "his", "her", "their", "been", "will", "would", "could", "shall",
    "other", "than", "these", "those", "into", "upon", "also", "there", "them",
    "they", "you", "your", "but", "she", "him", "who", "whom", "does", "did",
}


def tokenize(raw: bytes) -> Counter:
    """Filing bytes -> term-frequency Counter. Tables, markup and numbers dropped."""
    body = _SCRIPT_RE.sub(b" ", raw)
    body = _TABLE_RE.sub(b" ", body)
    body = _TAG_RE.sub(b" ", body)
    body = _ENTITY_RE.sub(b" ", body)
    text = body.decode("latin-1", errors="ignore").lower()
    return Counter(t for t in _TOKEN_RE.findall(text) if t not in _STOP)


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return float("nan")
    common = a.keys() & b.keys()
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return float(dot / (na * nb)) if na and nb else float("nan")


def jaccard(a: Counter, b: Counter) -> float:
    if not a or not b:
        return float("nan")
    sa, sb = set(a), set(b)
    union = len(sa | sb)
    return float(len(sa & sb) / union) if union else float("nan")


def similarity(a: Counter, b: Counter) -> tuple[float, float]:
    return cosine(a, b), jaccard(a, b)


MIN_TOKENS = 500   # below this the "document" is a cover page or a fetch stub


def usable(bag: Counter) -> bool:
    return sum(bag.values()) >= MIN_TOKENS
