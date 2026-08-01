"""EDGAR 13D/13G collector — quarterly form-index harvest, free data, no WRDS.

`wrdssec` is NOT SUBSCRIBED on our account (manifest_p0c.json:
"NotSubscribedError"), so the activist-stake event family has no WRDS path. This
module builds the event dates from EDGAR's public quarterly form index instead.

RATE DISCIPLINE — this is the part that has already bitten us once. The prod
insider collector made raw unpaced `requests.get` calls and failed on 100% of
prod fetches with HTTP 403 (NOT 429 — SEC returns 403 when the rate threshold
trips), silently, while passing every offline test (NEG_RESULTS §5, fixed
2026-06-17). Every request here goes through ONE choke point, `_sec_get`:
process-wide limiter at 8/s (under SEC's 10/s cap), a mandatory declared
User-Agent with contact, a hard per-request timeout, and one 403 retry. This
mirrors `backend/services/insider_form4._sec_get` deliberately; it is
reimplemented rather than imported because the module and the product are
separate trees with separate environments.

FAIL LOUD. A failed quarter raises. It does not return an empty frame, and it
does not get skipped with a warning — an empty 13D index for 2008Q3 is
indistinguishable from "no activists filed in 2008Q3" once it lands in a
parquet, and that is exactly the silent-fragility failure the house rule exists
to prevent. Completed quarters are checkpointed to disk, so a raise costs the
failed quarter and nothing else.

WHAT THE INDEX CAN AND CANNOT RESOLVE — read before designing a trial on it.
A form.idx line carries: form type, company name, CIK, filed date, file name.
It does NOT carry the filer/subject ROLE. A Schedule 13D has two parties — the
activist that filed it and the issuer whose stock was bought — and EDGAR indexes
the filing under BOTH CIKs, as separate lines sharing one accession number. From
the index alone you can see that an accession has two CIKs; you cannot see which
one is the target. Resolving the role for certain requires fetching the filing
header or body (`-index.htm` / the SGML `SUBJECT COMPANY` block), which is
~400k additional requests and is NOT done here.

What this module does instead is measure how far the index alone gets you:
`resolution_report` counts, per accession, how many of its CIKs resolve to a
CRSP permno through the existing survivorship-neutral bridge. An accession with
exactly ONE CRSP-resolvable CIK has an unambiguous subject CANDIDATE (activists
are typically funds and partnerships absent from CRSP; issuers are listed
equities present in it). That is a measured heuristic with a reported rate, not
a verified role assignment, and any registration built on it must say so.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path

import pandas as pd
import requests

from aegis_brain.config import MODULE_ROOT

logger = logging.getLogger(__name__)
OUT_DIR = MODULE_ROOT / "data" / "events" / "edgar_13dg"

FORM_TYPES = ("SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A")
_IDX_URL = "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{qtr}/form.idx"

_UA = os.environ.get("SEC_USER_AGENT",
                     "Aegis Finance Research mrthnabdullaev@gmail.com")
_HEADERS = {"User-Agent": _UA, "Accept-Encoding": "gzip, deflate"}
_TIMEOUT = 60          # index files are multi-MB; higher than the prod 10s
_RETRY_403 = 1
_RETRY_BACKOFF_S = 2.0


class _RateLimiter:
    """SEC enforces a hard 10 req/s cap; exceeding it triggers an IP block and
    a 403 (not a 429). Process-wide, with headroom. ALL EDGAR HTTP goes here."""

    def __init__(self, max_per_sec: float = 8.0) -> None:
        self._min_interval = 1.0 / max_per_sec
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            delta = time.monotonic() - self._last
            if delta < self._min_interval:
                time.sleep(self._min_interval - delta)
            self._last = time.monotonic()


_RATE_LIMITER = _RateLimiter(max_per_sec=8.0)


def _sec_get(url: str) -> requests.Response:
    """The ONE choke point for every SEC request in this module.

    Paces through the shared limiter, sends the mandatory UA, retries once on a
    403, and RAISES on a persistent non-2xx. Callers must not catch this into an
    empty frame.
    """
    last: requests.Response | None = None
    for attempt in range(_RETRY_403 + 1):
        _RATE_LIMITER.wait()
        last = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if last.status_code != 403:
            break
        if attempt < _RETRY_403:
            logger.warning("SEC 403 (rate threshold?) on %s — backing off %.1fs",
                           url, _RETRY_BACKOFF_S)
            time.sleep(_RETRY_BACKOFF_S)
    assert last is not None
    last.raise_for_status()
    return last


# ── parsing ──────────────────────────────────────────────────────────────────
# form.idx is fixed-width and space-padded. Anchored on the unambiguous tail
# (CIK digits, ISO date, edgar/data path) so a company name containing digits or
# runs of spaces backtracks correctly instead of shifting every column.
_LINE = re.compile(
    r"^(?P<form>.+?)\s{2,}"
    r"(?P<company>.+?)\s+"
    r"(?P<cik>\d{1,10})\s+"
    r"(?P<filed>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<fname>edgar/data/\S+)\s*$"
)


def parse_form_idx(text: str,
                   form_types: tuple[str, ...] = FORM_TYPES) -> pd.DataFrame:
    """Parse a form.idx body into (form_type, company_name, cik, filed_date,
    accession, file_name), keeping only `form_types`."""
    wanted = {f.upper() for f in form_types}
    rows = []
    for line in text.splitlines():
        if "edgar/data/" not in line:
            continue                      # header, rule lines, blanks
        m = _LINE.match(line.rstrip())
        if not m:
            continue
        form = m.group("form").strip().upper()
        if form not in wanted:
            continue
        fname = m.group("fname")
        rows.append({
            "form_type": form,
            "company_name": m.group("company").strip(),
            "cik": int(m.group("cik")),
            "filed_date": m.group("filed"),
            "accession": Path(fname).stem,
            "file_name": fname,
        })
    df = pd.DataFrame(rows, columns=["form_type", "company_name", "cik",
                                     "filed_date", "accession", "file_name"])
    if len(df):
        df["filed_date"] = pd.to_datetime(df["filed_date"])
    return df


def fetch_quarter(year: int, qtr: int) -> pd.DataFrame:
    """One quarter's 13D/13G index rows. Raises on any HTTP failure."""
    r = _sec_get(_IDX_URL.format(year=year, qtr=qtr))
    df = parse_form_idx(r.text)
    df["year"], df["qtr"] = year, qtr
    logger.info("%dQ%d: %d 13D/13G index rows", year, qtr, len(df))
    return df


def collect(years: range | list[int], out_dir: Path | None = None,
            resume: bool = True) -> pd.DataFrame:
    """Harvest every quarter in `years`, checkpointing per quarter.

    Raises on the first quarter that fails — the caller sees the failure rather
    than a short parquet. Already-written quarters are reused when `resume`.
    """
    out = Path(out_dir) if out_dir else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    parts = []
    for y in years:
        for q in (1, 2, 3, 4):
            p = out / f"idx_{y}Q{q}.parquet"
            if resume and p.exists():
                parts.append(pd.read_parquet(p))
                continue
            df = fetch_quarter(y, q)
            df.to_parquet(p, index=False)
            parts.append(df)
    all_rows = pd.concat(parts, ignore_index=True)
    all_rows = all_rows.drop_duplicates(["accession", "cik"])
    logger.info("collected %d index rows, %d distinct accessions",
                len(all_rows), all_rows["accession"].nunique())
    return all_rows


# ── what the index alone can resolve ─────────────────────────────────────────
def resolution_report(idx: pd.DataFrame) -> dict:
    """Measure how far the index gets us toward (subject permno, event date).

    Reported, never assumed. `ciks_per_accession` is the structural fact that a
    13D names two parties; `exactly_one_crsp_cik` is the fraction where the
    subject candidate is unambiguous under the CRSP bridge.
    """
    from aegis_brain.events.name_link import link_filings_by_cik

    rep: dict = {
        "index_rows": int(len(idx)),
        "accessions": int(idx["accession"].nunique()),
        "by_form_type": {k: int(v) for k, v in
                         idx["form_type"].value_counts().items()},
    }
    per = idx.groupby("accession")["cik"].nunique()
    rep["ciks_per_accession"] = {str(k): int(v) for k, v in
                                 per.value_counts().sort_index().items()}

    linked, link_diag = link_filings_by_cik(idx, cik_col="cik",
                                            date_col="filed_date")
    rep["link_diag"] = link_diag
    rep["rows_linked_to_permno"] = int(len(linked))

    n_crsp = linked.groupby("accession")["permno"].nunique()
    all_acc = set(idx["accession"].unique())
    exactly_one = set(n_crsp[n_crsp == 1].index)
    rep["accessions_with_crsp_cik"] = int(len(n_crsp))
    rep["accessions_exactly_one_crsp_cik"] = int(len(exactly_one))
    rep["subject_resolution_rate"] = round(len(exactly_one) / max(len(all_acc), 1), 4)
    rep["accessions_multi_crsp_cik"] = int((n_crsp > 1).sum())
    rep["accessions_no_crsp_cik"] = int(len(all_acc) - len(n_crsp))
    return rep


def events_from_index(idx: pd.DataFrame) -> pd.DataFrame:
    """Candidate (permno, event_date, form_type, accession) event rows.

    Uses the exactly-one-CRSP-CIK heuristic described in the module docstring.
    These are subject CANDIDATES, not verified subjects — a registration built
    on this must carry the measured resolution rate as a disclosed limitation.
    """
    from aegis_brain.events.name_link import link_filings_by_cik

    linked, _ = link_filings_by_cik(idx, cik_col="cik", date_col="filed_date")
    n = linked.groupby("accession")["permno"].nunique()
    keep = linked[linked["accession"].isin(n[n == 1].index)]
    ev = (keep.drop_duplicates(["accession", "permno"])
          [["permno", "filed_date", "form_type", "accession"]]
          .rename(columns={"filed_date": "event_date"})
          .sort_values(["event_date", "permno"], ignore_index=True))
    return ev
