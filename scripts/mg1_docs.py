"""MARKET-GRAPH-1 stage 2 — the point-in-time text.

WHY EDGAR AND NOT THE MODEL'S OWN MEMORY
========================================
Hard constraint 1 of the trial: the extractor sees text only up to `t`. Asking
a 2026 foundation model "who were NVDA's suppliers in 2017" is not a
point-in-time question — the answer is drawn from a corpus that includes 2018
through 2026, and every edge it returns is contaminated by knowing which
relationships turned out to matter. Live web retrieval on a historical date has
the same defect for a stronger reason: the index itself is present-day.

EDGAR's archive is the one source with the property this trial needs. A 10-K
filed 2017-02-24 is byte-identical today to what it was then; fetching it now
is not retrieval-from-the-future, it is reading an artifact with a date on it.
So the document is the ground truth and the model's job is reduced to READING,
not recalling. That does not make the design leak-proof — the model still
carries 2026 priors and could favour the counterparty it knows became
important — but it moves the failure from "certain" to "bounded and
measurable", and the evidence-quote check in stage 3 is what measures it.

WHAT IT KEEPS
-------------
Item 1 (Business) is where suppliers, customers, competitors, commodity inputs
and end-markets are named; Item 1A (Risk Factors) is where dependencies are
confessed. The extractor takes the Item 1 span when it can find it and falls
back to the head of the document body when it cannot. Which of the two happened
is RECORDED PER DOCUMENT, because a silent fallback that quietly degrades half
the corpus to boilerplate is precisely the house failure mode.

    python -m scripts.mg1_docs               # full worklist, resumable
    python -m scripts.mg1_docs --limit 60    # pilot
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT                       # noqa: E402
from aegis_brain.events.edgar_sec import sec_get                 # noqa: E402
from scripts import mg1_config as C                              # noqa: E402

OUT = MODULE_ROOT / "runs" / "MARKET-GRAPH-1"
DOCS = OUT / "docs"
FULL = OUT / "full"
DOCS.mkdir(parents=True, exist_ok=True)
FULL.mkdir(parents=True, exist_ok=True)
INDEX = OUT / "docs_index.jsonl"

DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"

_SCRIPT_RE = re.compile(rb"<(script|style)[^>]*>.*?</\1>", re.I | re.S)
_TABLE_RE = re.compile(rb"<table[^>]*>.*?</table>", re.I | re.S)
_TAG_RE = re.compile(rb"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_NL_RE = re.compile(r"\n{3,}")

_ENTITIES = {"&nbsp;": " ", "&amp;": "&", "&#160;": " ", "&#38;": "&",
             "&quot;": '"', "&#39;": "'", "&rsquo;": "'", "&lsquo;": "'",
             "&ldquo;": '"', "&rdquo;": '"', "&mdash;": "-", "&ndash;": "-",
             "&#146;": "'", "&#147;": '"', "&#148;": '"', "&#151;": "-"}

#: "Item 1." / "ITEM 1 -" / "Item 1:" but NOT "Item 1A" and NOT "Item 10..19".
#: The `(?![0-9a])` guard is not pedantry: without it, `Item 15(a)(1)` matched
#: and the Under Armour excerpt came back as the auditor's report, which the
#: extractor then correctly reported as containing no counterparties. A wrong
#: section produces a confident, well-formed, empty answer.
_ITEM1 = re.compile(r"\bitem\s*1(?![0-9a])\s*[\.\:\-–—]?\s*"
                    r"(?=\s*business\b)", re.I)
_ITEM1_LOOSE = re.compile(r"\bitem\s*1(?![0-9a])\s*[\.\:\-–—]?", re.I)
_ITEM1A = re.compile(r"\bitem\s*1a(?![0-9])\s*[\.\:\-–—]?", re.I)
_ITEM2 = re.compile(r"\bitem\s*2(?![0-9])\s*[\.\:\-–—]?", re.I)

#: What the extractor actually needs to find in the excerpt. A section that
#: contains none of these words cannot yield a relationship edge no matter how
#: good the model is, so this is the quality gate on the SECTION FINDER — not
#: on the model, and not on the company.
_REL_RE = re.compile(r"\b(customer|supplier|suppli|competitor|compet|"
                     r"distributor|vendor|partner|licens|oem|contract "
                     r"manufactur|end market|reseller)", re.I)
MIN_REL_HITS = 8


def to_text(raw: bytes) -> str:
    """Filing bytes -> readable prose. Tables dropped, markup dropped."""
    body = _SCRIPT_RE.sub(b" ", raw)
    body = _TABLE_RE.sub(b"\n", body)          # tables are numbers, not prose
    body = _TAG_RE.sub(b"\n", body)
    text = body.decode("utf-8", errors="ignore")
    for k, v in _ENTITIES.items():
        text = text.replace(k, v)
    text = re.sub(r"&[a-zA-Z#0-9]{1,8};", " ", text)
    text = _WS_RE.sub(" ", text)
    text = _NL_RE.sub("\n\n", text)
    return text.strip()


def _spans(text: str, starts: list[int]) -> list[tuple[int, int]]:
    """Candidate Item 1 spans, each TERMINATED BY A REAL MARKER.

    A candidate with no following Item 1A / Item 2 is dropped rather than
    padded out to the character cap. Padding is how the Amgen excerpt came to
    start at a cross-reference and run 28,000 characters into the revenue-
    recognition note: the bogus span was the longest, so "longest wins" picked
    it.
    """
    out = []
    for s in starts:
        nxt = [m.start() for m in _ITEM1A.finditer(text, s + 8)]
        nxt += [m.start() for m in _ITEM2.finditer(text, s + 8)]
        if not nxt:
            continue
        e = min(nxt)
        if e - s >= 3000:
            out.append((s, e))
    return out


def keyword_window(text: str) -> tuple[int, int]:
    """The EXTRACT_MAX_DOC_CHARS window densest in relationship language.

    The last resort, and an honest one: if the section finder cannot locate a
    business section, the next best thing is the part of the filing that talks
    about other companies. Slid coarsely — this is a fallback, not a search.
    """
    W, step = C.EXTRACT_MAX_DOC_CHARS, 4000
    if len(text) <= W:
        return 0, len(text)
    best, best_n = 0, -1
    for s in range(0, len(text) - W + step, step):
        n = len(_REL_RE.findall(text[s:s + W]))
        if n > best_n:
            best, best_n = s, n
    return best, min(len(text), best + W)


def business_section(text: str) -> tuple[str, str, int]:
    """The Item 1 Business span, HOW it was found, and its relationship density.

    Returns (excerpt, method, n_rel_hits). `method` is written to disk for
    every document. A section finder that silently returns the table of
    contents for a third of the corpus leaves every downstream number looking
    fine — the model answers "no counterparties", truthfully, about the wrong
    page. So the method is recorded and the excerpt is additionally CHECKED for
    the vocabulary an edge would have to be made of; failing that check
    triggers the keyword window and says so.
    """
    method = "item1_business"
    cand = _spans(text, [m.start() for m in _ITEM1.finditer(text)])
    if not cand:
        method = "item1_loose"
        cand = _spans(text, [m.start() for m in _ITEM1_LOOSE.finditer(text)])
    if cand:
        # EARLIEST qualifying span, not longest: in a 10-K the real Item 1
        # precedes Item 1A precedes Item 2, so the first properly terminated
        # long span is the section itself. Later matches are cross-references.
        s, e = cand[0]
        exc = text[s:e][:C.EXTRACT_MAX_DOC_CHARS]
        hits = len(_REL_RE.findall(exc))
        if hits >= MIN_REL_HITS:
            return exc, method, hits
        s2, e2 = keyword_window(text)
        exc2 = text[s2:e2]
        h2 = len(_REL_RE.findall(exc2))
        if h2 > hits:
            return exc2, method + "+kwwindow", h2
        return exc, method, hits
    s2, e2 = keyword_window(text)
    exc2 = text[s2:e2]
    return exc2, "kwwindow_fallback", len(_REL_RE.findall(exc2))


def fetch_one(row) -> dict:
    url = DOC_URL.format(cik=int(row.cik),
                         acc=str(row.accession).replace("-", ""),
                         doc=row.primary_document)
    rec = {"accession": row.accession, "permno": int(row.permno),
           "cik": int(row.cik), "ticker": row.ticker, "comnam": row.comnam,
           "filing_date": str(pd.Timestamp(row.filing_date).date()),
           "url": url}
    try:
        resp = sec_get(url, allow_404=True, timeout=60)
    except RuntimeError as exc:
        rec.update(status="fetch_error", error=str(exc)[:200])
        return rec
    if resp is None:
        rec.update(status="not_found")
        return rec
    text = to_text(resp.content)
    if len(text) < 3000:
        rec.update(status="too_short", n_chars_full=len(text))
        return rec
    exc_, method, hits = business_section(text)
    # The FULL text is kept, not just the excerpt. Section selection is a
    # heuristic and heuristics get corrected; re-deriving an excerpt must not
    # mean 3,300 more requests to EDGAR.
    with gzip.open(FULL / f"{row.accession}.txt.gz", "wt",
                   encoding="utf-8") as fh:
        fh.write(text)
    p = DOCS / f"{row.accession}.txt.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        fh.write(exc_)
    rec.update(status="ok", method=method, n_chars_full=len(text),
               n_chars_excerpt=len(exc_), rel_hits=hits, path=p.name)
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=C.SEED)
    # EDGAR's own limit is 10 req/s and `edgar_sec._RATE_LIMITER` already paces
    # every thread through one lock at 8/s. Single-threaded this loop ran at
    # 0.6/s — the bottleneck was round-trip latency, not the limiter. Workers
    # only close that gap; they cannot exceed the shared pace.
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    work = pd.read_parquet(OUT / "filings.parquet")
    done = set()
    if INDEX.exists():
        for line in INDEX.open(encoding="utf-8"):
            try:
                done.add(json.loads(line)["accession"])
            except Exception:
                continue
    todo = work[~work["accession"].isin(done)]
    if args.limit:
        todo = todo.sample(n=min(args.limit, len(todo)),
                           random_state=args.seed)
    print(f"documents: {len(work):,} total, {len(done):,} done, "
          f"{len(todo):,} this run, {args.workers} workers", flush=True)
    if todo.empty:
        return

    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    t0 = time.time()
    stats: dict[str, int] = {}
    lock = threading.Lock()
    with INDEX.open("a", encoding="utf-8") as fh:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
            futs = [ex.submit(fetch_one, row) for row in todo.itertuples()]
            for i, fut in enumerate(as_completed(futs), 1):
                try:
                    rec = fut.result()
                except Exception as exc:                       # noqa: BLE001
                    # A worker that dies must be COUNTED, not swallowed into a
                    # silently shorter corpus.
                    rec = {"accession": "?", "status": "worker_error",
                           "error": f"{type(exc).__name__}: {str(exc)[:160]}"}
                key = rec["status"] + (
                    "/" + rec["method"] if rec.get("method") else "")
                with lock:
                    stats[key] = stats.get(key, 0) + 1
                    fh.write(json.dumps(rec) + "\n")
                    if i % 200 == 0:
                        fh.flush()
                        print(f"  {i}/{len(todo)}  {stats}  "
                              f"{(time.time() - t0) / 60:.1f}min", flush=True)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
