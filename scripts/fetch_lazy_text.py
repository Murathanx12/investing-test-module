"""TRIAL-TEXT-LAZY acquisition + signal construction in ONE streaming pass.

Coverage: 10-K only (declared shrink, TRIAL-TEXT-LAZY pre-run addendum).

Design note — why this does not need a text corpus on disk: similarity is only
ever computed between a firm and ITS OWN prior filing, so the loop walks one
permno at a time, holds that firm's previous token bag, emits two floats and
throws the documents away. The only extra memory is a per-year reservoir of full
token bags used by Arm A (the different-firm control), capped and sampled.

Resumable: every firm's rows are appended to a jsonl checkpoint as it completes,
and completed permnos are skipped on restart. A 3-4h rate-limited pull must not
lose everything to one interruption.

MUST NOT run concurrently with any other SEC pull (8/s limiter is per-process).

Usage: .venv\\Scripts\\python -m scripts.fetch_lazy_text
Output: data/events/lazy_text_signals.parquet (+ .jsonl checkpoint)
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.events.edgar_sec import STATS, sec_get
from aegis_brain.events.filing_text import similarity, tokenize, usable
from aegis_brain.events.name_link import link_filings_by_cik

ANNUAL_FORMS = ("10-K", "10-K405", "10-KSB")
MAX_GAP_DAYS = 460      # 15-month staleness limit (frozen)
MIN_GAP_DAYS = 180      # below this it is not a year-on-year pair
RESERVOIR_PER_YEAR = 40
SEED = 20260728

EVENTS_DIR = MODULE_ROOT / "data" / "events"
DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"


def annual_filings() -> tuple[pd.DataFrame, dict]:
    subs = pd.read_parquet(EVENTS_DIR / "sec_submissions.parquet")
    f = subs[subs["form"].isin(ANNUAL_FORMS) & (subs["primary_document"] != "")]
    f = f[(f["filing_date"] >= "2003-01-01") & (f["filing_date"] <= "2024-12-31")]
    linked, report = link_filings_by_cik(f, "cik", "filing_date")
    linked = linked.sort_values(["permno", "filing_date"]).reset_index(drop=True)
    return linked, report


def fetch_bag(cik: int, accession: str, doc: str) -> Counter | None:
    url = DOC_URL.format(cik=int(cik), acc=accession.replace("-", ""), doc=doc)
    try:
        resp = sec_get(url, allow_404=True, timeout=60)
    except RuntimeError:
        logging.warning("document fetch failed: %s", url)
        return None
    if resp is None:
        return None
    bag = tokenize(resp.content)
    return bag if usable(bag) else None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        stream=sys.stdout)
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    filings, link_report = annual_filings()
    logging.info("annual filings linked: %d over %d permnos",
                 len(filings), filings["permno"].nunique())

    ckpt = EVENTS_DIR / "lazy_text_signals.jsonl"
    done: set[int] = set()
    if ckpt.exists():
        for line in ckpt.open(encoding="utf-8"):
            try:
                done.add(int(json.loads(line)["permno"]))
            except Exception:
                continue
        logging.info("resuming: %d permnos already complete", len(done))

    reservoir: dict[int, list[Counter]] = {}
    seen_per_year: Counter = Counter()
    n_docs = 0

    with ckpt.open("a", encoding="utf-8") as fh:
        for k, (permno, grp) in enumerate(filings.groupby("permno"), start=1):
            if int(permno) in done:
                continue
            prev_bag: Counter | None = None
            prev_date: pd.Timestamp | None = None
            for _, r in grp.iterrows():
                bag = fetch_bag(r["cik"], r["accession"], r["primary_document"])
                n_docs += 1
                if bag is None:
                    prev_bag, prev_date = None, None
                    continue
                d = pd.Timestamp(r["filing_date"])
                year = int(d.year)

                if prev_bag is not None:
                    gap = (d - prev_date).days
                    if MIN_GAP_DAYS <= gap <= MAX_GAP_DAYS:
                        cos, jac = similarity(bag, prev_bag)
                        pool = reservoir.get(year, [])
                        if pool:
                            other = pool[int(rng.integers(len(pool)))]
                            ctl_cos, ctl_jac = similarity(bag, other)
                        else:
                            ctl_cos = ctl_jac = float("nan")
                        fh.write(json.dumps({
                            "permno": int(permno), "filing_date": d.strftime("%Y-%m-%d"),
                            "gap_days": int(gap),
                            "text_cos": cos, "text_jac": jac,
                            "ctl_cos": ctl_cos, "ctl_jac": ctl_jac,
                        }) + "\n")

                # reservoir sampling of FULL bags, per calendar year (Arm A pool)
                seen_per_year[year] += 1
                pool = reservoir.setdefault(year, [])
                if len(pool) < RESERVOIR_PER_YEAR:
                    pool.append(bag)
                else:
                    j = int(rng.integers(seen_per_year[year]))
                    if j < RESERVOIR_PER_YEAR:
                        pool[j] = bag

                prev_bag, prev_date = bag, d
            fh.flush()
            if k % 100 == 0:
                logging.info("permnos %d/%d, docs %d, stats %s, %.1f min",
                             k, filings["permno"].nunique(), n_docs, STATS,
                             (time.time() - t0) / 60)

    rows = [json.loads(l) for l in ckpt.open(encoding="utf-8")]
    df = pd.DataFrame(rows)
    df["filing_date"] = pd.to_datetime(df["filing_date"])
    df.to_parquet(EVENTS_DIR / "lazy_text_signals.parquet", index=False)

    meta = {"n_pairs": int(len(df)), "n_permnos": int(df["permno"].nunique()),
            "n_documents_fetched": n_docs, "link_report": link_report,
            "coverage": "10-K only (declared shrink)",
            "date_range": [str(df["filing_date"].min().date()),
                           str(df["filing_date"].max().date())],
            "fetch_stats": dict(STATS),
            "elapsed_min": round((time.time() - t0) / 60, 1)}
    (EVENTS_DIR / "lazy_text_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2), flush=True)


if __name__ == "__main__":
    main()
