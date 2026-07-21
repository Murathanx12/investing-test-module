"""Historical SEC insider open-market-PURCHASE collector (Phase 2 / L1 event feed).

Why the bulk quarterly flat files, not per-filing XML
-----------------------------------------------------
The informative insider signal (Cohen, Malloy & Pomorski 2012, "Decoding Inside
Information", *Journal of Finance* 67(3): 1009-1043) needs, per transaction, the
transaction code (``P`` = open-market purchase — the only insider trade the
literature finds informative), the price, and the insider identity, over a
multi-decade window. Reconstructing that from raw Form-4 XML means fetching
millions of individual filings across 20 years; at SEC's hard 10 req/s fair-access
cap that is a multi-week crawl and a 403-magnet. (The live, per-ticker XML parser
at ``aegis-finance/backend/services/insider_form4.py`` is the right tool for "what
did insiders do at TICKER lately", but the wrong one for a historical panel.)

The tractable source is SEC's **Insider Transactions Data Sets** — the fillable
portion of Forms 3/4/5 extracted from EDGAR Ownership XML into quarterly,
tab-delimited, UTF-8 flat files, published one zip per quarter from **2006 Q1**
onward (SEC only began collecting the structured XML in Jan 2006).

    https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
    zip URL: https://www.sec.gov/files/structureddata/data/
             insider-transactions-data-sets/{year}q{qtr}_form345.zip

Each quarterly zip contains up to eight TSVs keyed by ``ACCESSION_NUMBER``. We use
three:

  * ``SUBMISSION.tsv``      — one row per filing: FILING_DATE, ISSUERCIK,
                              ISSUERNAME, ISSUERTRADINGSYMBOL, DOCUMENT_TYPE.
  * ``REPORTINGOWNER.tsv``  — insider identity: RPTOWNERCIK, RPTOWNERNAME
                              (keyed ACCESSION_NUMBER + RPTOWNERCIK).
  * ``NONDERIV_TRANS.tsv``  — Table-I non-derivative transactions: TRANS_CODE,
                              TRANS_ACQUIRED_DISP_CD, TRANS_DATE, TRANS_SHARES,
                              TRANS_PRICEPERSHARE (keyed ACCESSION_NUMBER +
                              NONDERIV_TRANS_SK).

Open-market purchase filter (per the Trans Code List in the SEC readme):
``TRANS_CODE == 'P'`` (open-market/private purchase) AND
``TRANS_ACQUIRED_DISP_CD == 'A'`` (acquired).

10b5-1 caveat
-------------
The published flat-file schema (SUBMISSION / REPORTINGOWNER / NONDERIV_TRANS) has
**no dedicated Rule 10b5-1 flag column** in any year. ``TRANS_TIMELINESS`` encodes
early/late filing and ``EQUITY_SWAP_INVOLVED`` encodes equity swaps — neither is a
10b5-1 indicator. The SEC Form-4 10b5-1 checkbox (mandatory for filings on/after
2023-04-01) lives only in the raw ``<rule10b5-1>`` XML element and is not surfaced
in these datasets. So ``is_10b51`` is emitted as ``pd.NA`` for every row unless a
future dataset revision adds a column whose name contains "10B5" (auto-detected).

Discipline: the network helper degrades on any error and cannot hang (hard
timeout); the parser and classifier are pure/offline and unit-tested.
"""

from __future__ import annotations

import logging
import os
import time
import zipfile
from pathlib import Path
from typing import Optional, Union
from urllib.request import Request, urlopen

import pandas as pd

logger = logging.getLogger(__name__)

# SEC fair-access: a descriptive User-Agent with a contact is mandatory; SEC hard
# -caps ~10 req/s and 403s offenders for ~10 min. Env-overridable so prod can set a
# compliant identifier without a code change (matches insider_form4._UA default).
_UA = os.environ.get(
    "SEC_USER_AGENT", "Aegis Finance Research mrthnabdullaev@gmail.com"
)
_HEADERS = {"User-Agent": _UA, "Accept-Encoding": "gzip, deflate"}

_ZIP_URL = (
    "https://www.sec.gov/files/structureddata/data/"
    "insider-transactions-data-sets/{year}q{qtr}_form345.zip"
)
FIRST_YEAR = 2006  # SEC Ownership XML (and therefore these data sets) begin 2006 Q1

# Output schema of ``parse_insider_quarter``.
_COLUMNS = [
    "accession",
    "filing_date",
    "trans_date",
    "issuer_cik",
    "issuer_ticker",
    "rptowner_cik",
    "rptowner_name",
    "shares",
    "price",
    "value",
    "is_10b51",
]

_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


# --------------------------------------------------------------------------- #
# 1. Network helper (implemented, deliberately NOT run at scale)               #
# --------------------------------------------------------------------------- #
def download_quarter(
    year: int,
    qtr: int,
    dest_dir: Union[str, Path],
    *,
    sleep_s: float = 0.5,
    timeout_s: float = 60.0,
    overwrite: bool = False,
) -> Optional[Path]:
    """Fetch ONE quarterly insider zip to ``dest_dir`` and return its path.

    Robust by construction — this is the only network-touching function here and
    it must never wedge a batch:

      * declares the mandatory SEC User-Agent with contact;
      * sleeps ``sleep_s`` *before* the request so that, if a caller loops over
        many quarters, requests stay well under SEC's ~10 req/s cap (do NOT,
        however, run a full 2006->present crawl casually — that is ~80 files);
      * enforces a hard socket ``timeout_s`` so a stalled connection cannot hang
        the process;
      * streams to a ``.part`` file and atomically renames on success;
      * degrades to ``None`` on any HTTP/IO error rather than raising.

    Args:
        year: calendar year (>= 2006; earlier years have no structured data).
        qtr: quarter 1..4.
        dest_dir: directory to write ``{year}q{qtr}_form345.zip`` into.
        sleep_s: pacing pause issued before the request.
        timeout_s: hard per-socket-operation timeout (the anti-hang guard).
        overwrite: re-download even if the destination already exists.

    Returns:
        Path to the downloaded zip, or ``None`` on any failure.
    """
    if year < FIRST_YEAR:
        logger.warning("insider data sets start %d Q1; %d requested", FIRST_YEAR, year)
        return None
    if qtr not in (1, 2, 3, 4):
        logger.warning("invalid quarter %r (expected 1..4)", qtr)
        return None

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"{year}q{qtr}_form345.zip"
    if out.exists() and not overwrite:
        logger.info("already present, skipping download: %s", out)
        return out

    url = _ZIP_URL.format(year=year, qtr=qtr)
    tmp = out.with_suffix(".zip.part")
    time.sleep(max(0.0, sleep_s))  # pace before hitting SEC
    try:
        req = Request(url, headers=_HEADERS)
        with urlopen(req, timeout=timeout_s) as resp, open(tmp, "wb") as fh:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                fh.write(chunk)
        tmp.replace(out)
        logger.info("downloaded %s (%d bytes)", out, out.stat().st_size)
        return out
    except Exception as exc:  # noqa: BLE001 — any network/IO error degrades to None
        logger.warning("download failed for %s: %s", url, exc)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return None


# --------------------------------------------------------------------------- #
# 2. Offline parser (the unit-tested core)                                     #
# --------------------------------------------------------------------------- #
def _read_table(source: Union[str, Path], name: str) -> pd.DataFrame:
    """Read one TSV (``name`` e.g. 'NONDERIV_TRANS') from a quarterly zip or from
    a directory of extracted TSVs. Everything is read as ``str`` so keys never get
    coerced (leading-zero CIKs, long accession numbers); numeric conversion is
    done explicitly downstream. Missing table -> empty frame."""
    source = Path(source)
    fname = f"{name}.tsv"
    try:
        if source.is_dir():
            path = source / fname
            if not path.exists():
                return pd.DataFrame()
            return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
        if zipfile.is_zipfile(source):
            with zipfile.ZipFile(source) as zf:
                members = {Path(n).name: n for n in zf.namelist()}
                if fname not in members:
                    return pd.DataFrame()
                with zf.open(members[fname]) as fh:
                    return pd.read_csv(fh, sep="\t", dtype=str, keep_default_na=False)
    except Exception as exc:  # noqa: BLE001 — corrupt/partial file degrades to empty
        logger.warning("failed reading %s from %s: %s", fname, source, exc)
    return pd.DataFrame()


def _parse_sec_date(series: pd.Series) -> pd.Series:
    """Parse SEC ``DD-MON-YYYY`` dates (e.g. '15-JAN-2024') to datetime,
    locale-independently. Already-ISO strings (handy for synthetic fixtures) pass
    through via a pandas fallback. Unparseable -> NaT."""
    s = series.fillna("").astype(str).str.strip()

    def _one(v: str) -> Optional[pd.Timestamp]:
        if not v:
            return None
        parts = v.replace("/", "-").split("-")
        if len(parts) == 3 and parts[1].upper() in _MONTHS:  # DD-MON-YYYY
            try:
                year = int(parts[2])
                # SEC data carries typo'd years (e.g. '0013' for 2013) that overflow
                # the ns-datetime range and would otherwise crash the whole quarter.
                if not 1900 <= year <= 2100:
                    return None
                return pd.Timestamp(
                    year=year, month=_MONTHS[parts[1].upper()], day=int(parts[0])
                )
            except (ValueError, TypeError, OutOfBoundsDatetime):
                return None
        return None

    out = s.map(_one)
    unresolved = out.isna() & (s != "")
    if unresolved.any():  # ISO / other formats — let pandas try the remainder
        out.loc[unresolved] = pd.to_datetime(
            s[unresolved], errors="coerce"
        )
    return pd.to_datetime(out, errors="coerce")


def _detect_10b51_column(cols: list[str]) -> Optional[str]:
    """Historically none of the flat-file tables carry a 10b5-1 flag. If a future
    dataset revision adds one, its name will contain '10B5' — detect it so the
    parser picks it up automatically. Returns the column name or None."""
    for c in cols:
        if "10B5" in c.upper():
            return c
    return None


_TRUE = {"1", "TRUE", "T", "Y", "YES"}
_FALSE = {"0", "FALSE", "F", "N", "NO"}  # blank stays NA (unknown), not False


def parse_insider_quarter(zip_path_or_dir: Union[str, Path]) -> pd.DataFrame:
    """Parse one quarterly insider data set into a tidy open-market-PURCHASE frame.

    Reads ``NONDERIV_TRANS``, ``SUBMISSION`` and ``REPORTINGOWNER`` from a quarterly
    zip (or a directory of the extracted TSVs), keeps only open-market purchases
    (``TRANS_CODE == 'P'`` and ``TRANS_ACQUIRED_DISP_CD == 'A'``), and joins in the
    issuer and insider identity. Offline and deterministic — this is the
    unit-tested core.

    Source: SEC Insider Transactions Data Sets (Forms 3/4/5 Ownership XML,
    flattened; 2006 Q1+). See module docstring for provenance and the 10b5-1 caveat.

    Returns a DataFrame with columns::

        accession, filing_date, trans_date, issuer_cik, issuer_ticker,
        rptowner_cik, rptowner_name, shares, price, value, is_10b51

    ``value = shares * price``. ``is_10b51`` is ``pd.NA`` unless a 10b5-1 column is
    present (see ``_detect_10b51_column``). An empty/invalid source yields an empty
    frame with the correct columns.

    Caveat — multi-owner filings: the flat schema links a transaction to a filing
    (ACCESSION_NUMBER) but not to a specific reporting owner when a filing lists
    several. Such joint filings are rare; we attribute each filing's transactions
    to its first-listed reporting owner (by RPTOWNERCIK) to avoid a fan-out.
    """
    trans = _read_table(zip_path_or_dir, "NONDERIV_TRANS")
    if trans.empty:
        return pd.DataFrame(columns=_COLUMNS)

    trans = trans.copy()
    for col in ("TRANS_CODE", "TRANS_ACQUIRED_DISP_CD"):
        if col not in trans.columns:
            return pd.DataFrame(columns=_COLUMNS)
        trans[col] = trans[col].fillna("").astype(str).str.strip().str.upper()

    # Open-market purchases only: code 'P', acquired 'A'.
    buys = trans[(trans["TRANS_CODE"] == "P") & (trans["TRANS_ACQUIRED_DISP_CD"] == "A")]
    if buys.empty:
        return pd.DataFrame(columns=_COLUMNS)
    buys = buys.copy()

    buys["shares"] = pd.to_numeric(buys.get("TRANS_SHARES"), errors="coerce")
    buys["price"] = pd.to_numeric(buys.get("TRANS_PRICEPERSHARE"), errors="coerce")
    buys["value"] = buys["shares"] * buys["price"]
    buys["trans_date"] = _parse_sec_date(buys.get("TRANS_DATE", pd.Series(dtype=str)))
    buys["accession"] = buys["ACCESSION_NUMBER"].astype(str).str.strip()

    # 10b5-1 flag: absent from the documented schema -> pd.NA; auto-picked if added.
    flag_col = _detect_10b51_column(list(trans.columns))
    if flag_col:
        norm = buys[flag_col].fillna("").astype(str).str.strip().str.upper()
        buys["is_10b51"] = norm.map(
            lambda v: True if v in _TRUE else (False if v in _FALSE else pd.NA)
        ).astype("boolean")
    else:
        buys["is_10b51"] = pd.array([pd.NA] * len(buys), dtype="boolean")

    # --- Join issuer / filing info from SUBMISSION (one row per accession) ---
    sub = _read_table(zip_path_or_dir, "SUBMISSION")
    if not sub.empty and "ACCESSION_NUMBER" in sub.columns:
        sub = sub.copy()
        sub["accession"] = sub["ACCESSION_NUMBER"].astype(str).str.strip()
        sub["filing_date"] = _parse_sec_date(
            sub.get("FILING_DATE", pd.Series(dtype=str))
        )
        keep = sub[["accession", "filing_date"]].copy()
        keep["issuer_cik"] = sub.get("ISSUERCIK", "").astype(str).str.strip()
        keep["issuer_ticker"] = sub.get("ISSUERTRADINGSYMBOL", "").astype(str).str.strip()
        keep = keep.drop_duplicates("accession")
        buys = buys.merge(keep, on="accession", how="left")
    else:
        buys["filing_date"] = pd.NaT
        buys["issuer_cik"] = pd.NA
        buys["issuer_ticker"] = pd.NA

    # --- Join insider identity from REPORTINGOWNER (first owner per accession) ---
    own = _read_table(zip_path_or_dir, "REPORTINGOWNER")
    if not own.empty and "ACCESSION_NUMBER" in own.columns:
        own = own.copy()
        own["accession"] = own["ACCESSION_NUMBER"].astype(str).str.strip()
        own["rptowner_cik"] = own.get("RPTOWNERCIK", "").astype(str).str.strip()
        own["rptowner_name"] = own.get("RPTOWNERNAME", "").astype(str).str.strip()
        own = own.drop_duplicates("accession")  # first-listed owner per filing
        buys = buys.merge(
            own[["accession", "rptowner_cik", "rptowner_name"]], on="accession", how="left"
        )
    else:
        buys["rptowner_cik"] = pd.NA
        buys["rptowner_name"] = pd.NA

    out = buys[_COLUMNS].reset_index(drop=True)
    return out


# --------------------------------------------------------------------------- #
# 3. Routine / opportunistic classifier (Cohen-Malloy-Pomorski 2012)          #
# --------------------------------------------------------------------------- #
def classify_routine_opportunistic(df: pd.DataFrame) -> pd.DataFrame:
    """Label each purchase ROUTINE vs OPPORTUNISTIC per Cohen, Malloy & Pomorski
    (2012), *Journal of Finance* 67(3): 1009-1043.

    Definition (point-in-time; uses only strictly-prior data):

      * An insider (keyed by ``rptowner_cik``) is **routine** for a purchase made
        in calendar month M of year Y if that insider also placed a purchase in the
        SAME calendar month M in each of the three consecutive prior years
        (Y-1, Y-2, Y-3) — i.e. a predictable, calendar-clustered trader.
      * An insider is **classifiable** for that purchase only if it has a three-year
        purchase history: at least one purchase in EACH of Y-1, Y-2 and Y-3.
        Insiders without that history are ``is_classifiable = False`` and are left
        UNlabelled — they are NOT defaulted to opportunistic.
      * **Opportunistic** = classifiable AND not routine.

    Because the rule only ever references years strictly before the trade, it is
    point-in-time by construction (no look-ahead), even though it is computed over
    the whole frame. Pass the FULL multi-year purchase history (concatenate the
    per-quarter outputs of ``parse_insider_quarter``) so the prior-year lookups
    have the data they need.

    Adds three boolean columns and returns the frame (a copy):
        is_routine, is_classifiable, is_opportunistic
    """
    out = df.copy()
    if out.empty:
        for c in ("is_routine", "is_classifiable", "is_opportunistic"):
            out[c] = pd.Series(dtype="boolean")
        return out

    td = pd.to_datetime(out["trans_date"], errors="coerce")
    year = td.dt.year
    month = td.dt.month
    cik = out["rptowner_cik"].astype("object")

    # Purchase occurrences the rule can consult.
    valid = cik.notna() & year.notna() & month.notna()
    month_keys = set(
        zip(cik[valid], year[valid].astype(int), month[valid].astype(int))
    )  # (insider, year, month) -> insider purchased that month that year
    year_keys = set(
        zip(cik[valid], year[valid].astype(int))
    )  # (insider, year) -> insider purchased at all that year

    def _has_month(c, y: int, m: int) -> bool:
        return (c, y, m) in month_keys

    def _has_year(c, y: int) -> bool:
        return (c, y) in year_keys

    is_routine = []
    is_classifiable = []
    for c, y, m, ok in zip(cik, year, month, valid):
        if not ok:
            is_routine.append(False)
            is_classifiable.append(False)
            continue
        y, m = int(y), int(m)
        classifiable = (
            _has_year(c, y - 1) and _has_year(c, y - 2) and _has_year(c, y - 3)
        )
        routine = (
            _has_month(c, y - 1, m)
            and _has_month(c, y - 2, m)
            and _has_month(c, y - 3, m)
        )
        is_classifiable.append(bool(classifiable))
        # routine implies the three prior-year purchases, so it implies classifiable
        is_routine.append(bool(classifiable and routine))

    out["is_routine"] = pd.array(is_routine, dtype="boolean")
    out["is_classifiable"] = pd.array(is_classifiable, dtype="boolean")
    out["is_opportunistic"] = out["is_classifiable"] & ~out["is_routine"]
    return out
