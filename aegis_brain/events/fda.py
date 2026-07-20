"""FDA approval events from openFDA (Phase 2 / L1a — the event ledger's first feed).

openFDA `drugsfda` gives HISTORICAL approval events (original NDA/BLA approvals
with dates) — the raw material for a pre-registered event-drift study once the
CRSP panel lands. Forward-looking PDUFA calendar dates are NOT in openFDA; that
feed (company PRs / calendar scrapes) is a separate, later collector.

Discipline notes:
  - Records are events-as-of-their-date; no prediction, no scoring here.
  - Sponsor -> ticker mapping is deliberately deferred: doing it lazily by
    string-match invites survivorship and matching bias. It gets its own step
    with a point-in-time name-to-listing table.
  - openFDA unauthenticated limits: 1,000 req/day, 40/min. The harvester
    paginates one year at a time and sleeps accordingly.

API: https://api.fda.gov/drug/drugsfda.json
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)

BASE = "https://api.fda.gov/drug/drugsfda.json"
PAGE = 100  # openFDA max per request


@dataclass(frozen=True)
class FdaEvent:
    """One original approval event, as-known-at approval_date."""

    application_number: str
    approval_date: str        # YYYY-MM-DD (submission_status_date of the ORIG AP)
    sponsor_name: str
    brand_name: str
    generic_name: str
    submission_type: str      # ORIG (originals only in v1)
    review_priority: str      # PRIORITY / STANDARD / '' when absent


def _get(url: str, retries: int = 3, timeout: int = 30) -> dict:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001 — retry any transient failure
            if attempt == retries - 1:
                raise
            logger.warning("openFDA retry %d after: %s", attempt + 1, exc)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def parse_applications(payload: dict) -> list[FdaEvent]:
    """Extract original-approval events from one drugsfda result page."""
    events: list[FdaEvent] = []
    for app in payload.get("results", []):
        subs = app.get("submissions", []) or []
        orig_ap = [
            s for s in subs
            if s.get("submission_type") == "ORIG"
            and s.get("submission_status") == "AP"
            and s.get("submission_status_date")
        ]
        if not orig_ap:
            continue
        # earliest ORIG approval is THE approval event
        s = min(orig_ap, key=lambda x: x["submission_status_date"])
        d = s["submission_status_date"]
        products = app.get("products") or [{}]
        openfda = app.get("openfda") or {}
        events.append(FdaEvent(
            application_number=app.get("application_number", ""),
            approval_date=f"{d[:4]}-{d[4:6]}-{d[6:8]}",
            sponsor_name=app.get("sponsor_name", ""),
            brand_name=(products[0].get("brand_name")
                        or (openfda.get("brand_name") or [""])[0] or ""),
            generic_name=(openfda.get("generic_name") or [""])[0] or "",
            submission_type="ORIG",
            review_priority=s.get("review_priority", "") or "",
        ))
    return events


def fetch_fda_approvals(year: int, pause_s: float = 1.6) -> list[FdaEvent]:
    """All original approvals whose ORIG-AP date falls in `year`.

    Paginates at 100/request with a pause that respects the 40/min
    unauthenticated limit.
    """
    search = urllib.parse.quote(
        f"submissions.submission_status_date:[{year}0101 TO {year}1231]"
        f" AND submissions.submission_type:ORIG"
        f" AND submissions.submission_status:AP"
    )
    events: list[FdaEvent] = []
    skip = 0
    while True:
        url = f"{BASE}?search={search}&limit={PAGE}&skip={skip}"
        payload = _get(url)
        page = parse_applications(payload)
        # server-side search matches the application; keep only events whose
        # own ORIG approval date is inside the year
        events.extend(e for e in page if e.approval_date.startswith(str(year)))
        total = payload.get("meta", {}).get("results", {}).get("total", 0)
        skip += PAGE
        if skip >= total or not payload.get("results"):
            break
        time.sleep(pause_s)
    # de-dup on application number (paging overlap safety)
    uniq = {e.application_number: e for e in events}
    out = sorted(uniq.values(), key=lambda e: e.approval_date)
    logger.info("openFDA %d: %d original approvals", year, len(out))
    return out


def events_to_records(events: list[FdaEvent]) -> list[dict]:
    return [asdict(e) for e in events]
