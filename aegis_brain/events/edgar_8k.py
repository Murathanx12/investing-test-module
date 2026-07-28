"""8-K event acquisition from EDGAR DAILY indexes (PIT-safe).

TRIAL-EVENT-8K-FILTER freezes the event source: **daily** indexes only. The
full/quarterly indexes are retroactively rebuilt by SEC and are BANNED here —
a filing that was amended, re-classified or re-filed years later can appear in a
quarterly index under facts that did not exist on the filing date. The daily
index for date D is the authoritative "what was disseminated on D" record.

Item codes are NOT in any index file. They live in the filing's own submission
header, exposed per-filer by data.sec.gov/submissions. We therefore:

  1. walk the daily indexes -> the authoritative (cik, date, accession) event set
  2. pull each in-scope filer's submission history -> accession -> item codes
  3. INTERSECT on accession, keeping the daily index's filing date

Step 2 is metadata enrichment of an event set already fixed by step 1; item codes
are immutable properties of the original filing, so no look-ahead enters. Any
accession that appears in the submissions history but NOT in a daily index is
dropped (that is the retroactive-rebuild tail the freeze excludes).
"""

from __future__ import annotations

import io
import logging

import pandas as pd

from aegis_brain.events.edgar_sec import sec_get

logger = logging.getLogger(__name__)

_DAILY_DIR = "https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{qtr}/"
_SUBMISSIONS = "https://data.sec.gov/submissions/{name}"


def quarter_index_files(year: int, qtr: int) -> list[str]:
    """The `master.YYYYMMDD.idx` files SEC actually published for this quarter."""
    resp = sec_get(_DAILY_DIR.format(year=year, qtr=qtr) + "index.json",
                   accept="application/json", allow_404=True)
    if resp is None:
        return []
    items = resp.json().get("directory", {}).get("item", [])
    return sorted(x["name"] for x in items
                  if x["name"].startswith("master.") and x["name"].endswith(".idx"))


def parse_master_idx(text: str) -> pd.DataFrame:
    """`CIK|Company Name|Form Type|Date Filed|Filename` after a short header."""
    rows = []
    for line in text.splitlines():
        if line.count("|") != 4:
            continue
        cik, company, form, date, fname = line.split("|")
        cik = cik.strip()
        if not cik.isdigit():          # header/separator lines
            continue
        rows.append((int(cik), company.strip(), form.strip(), date.strip(), fname.strip()))
    return pd.DataFrame(rows, columns=["cik", "company", "form", "date_filed", "filename"])


def _accession(filename: str) -> str:
    """edgar/data/320193/0000320193-04-000123.txt -> 0000320193-04-000123"""
    return filename.rsplit("/", 1)[-1].removesuffix(".txt")


def harvest_daily_8k(start_year: int, end_year: int,
                     progress_every: int = 250) -> pd.DataFrame:
    """Every 8-K (and 8-K/A) row in every daily index over [start_year, end_year]."""
    out: list[pd.DataFrame] = []
    n_files = 0
    for year in range(start_year, end_year + 1):
        for qtr in (1, 2, 3, 4):
            for name in quarter_index_files(year, qtr):
                url = _DAILY_DIR.format(year=year, qtr=qtr) + name
                resp = sec_get(url, allow_404=True)
                n_files += 1
                if resp is None:
                    continue
                df = parse_master_idx(resp.content.decode("latin-1"))
                df = df[df["form"].str.upper().str.startswith("8-K")]
                if len(df):
                    df = df.copy()
                    df["index_file"] = name
                    out.append(df)
                if n_files % progress_every == 0:
                    total = sum(len(d) for d in out)
                    logger.info("daily-index walk: %d files, %d 8-K rows (at %s)",
                                n_files, total, name)
    if not out:
        raise RuntimeError("daily-index walk produced ZERO 8-K rows — treat as a "
                           "fetch failure, never as 'no events'")
    df = pd.concat(out, ignore_index=True)
    df["date_filed"] = pd.to_datetime(df["date_filed"])
    df["accession"] = df["filename"].map(_accession)
    df["is_amendment"] = df["form"].str.upper().str.contains("/A")
    return df.drop_duplicates(subset=["accession"]).reset_index(drop=True)


# ── step 2: item codes from the filer's own submission history ──────────────

def _submission_pages(cik: int) -> list[dict]:
    """Primary submissions doc plus any older-filings shards it points to."""
    first = sec_get(_SUBMISSIONS.format(name=f"CIK{cik:010d}.json"),
                    accept="application/json", allow_404=True)
    if first is None:
        return []
    doc = first.json()
    pages = [doc.get("filings", {}).get("recent", {})]
    for extra in doc.get("filings", {}).get("files", []):
        resp = sec_get(_SUBMISSIONS.format(name=extra["name"]),
                       accept="application/json", allow_404=True)
        if resp is not None:
            pages.append(resp.json())
    return [p for p in pages if p]


def fetch_items_for_ciks(ciks, progress_every: int = 200) -> pd.DataFrame:
    """(accession, items_raw) for every 8-K these filers ever filed."""
    rows: list[tuple[int, str, str, str]] = []
    for i, cik in enumerate(sorted({int(c) for c in ciks}), start=1):
        try:
            pages = _submission_pages(cik)
        except RuntimeError:
            logger.warning("submissions unavailable for CIK %d — filer dropped", cik)
            continue
        for page in pages:
            forms = page.get("form", [])
            accs = page.get("accessionNumber", [])
            items = page.get("items", [""] * len(forms))
            dates = page.get("filingDate", [""] * len(forms))
            for f, a, it, d in zip(forms, accs, items, dates):
                if str(f).upper().startswith("8-K"):
                    rows.append((cik, a, it or "", d))
        if i % progress_every == 0:
            logger.info("submissions: %d filers, %d 8-K rows", i, len(rows))
    return pd.DataFrame(rows, columns=["cik", "accession", "items_raw", "sub_filing_date"])


def explode_items(items_df: pd.DataFrame) -> pd.DataFrame:
    """items_raw '1.03,2.04' -> one row per (accession, item)."""
    df = items_df.copy()
    df["item"] = df["items_raw"].str.split(",")
    df = df.explode("item")
    df["item"] = df["item"].str.strip()
    return df[df["item"].str.match(r"^\d+\.\d+$", na=False)].reset_index(drop=True)
