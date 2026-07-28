"""Shared acquisition pass — SEC submission histories for the in-universe filers.

ONE pass serves BOTH round-12 registrations:
  * TRIAL-EVENT-8K-FILTER  -> 8-K accessions + their `items` codes
  * TRIAL-TEXT-LAZY        -> 10-K/10-Q accessions + primaryDocument URLs

Universe = every CIK bridged (via aegis_brain.events.name_link) to a permno that
was ever in the factory segments (dollar-volume rank <= 3000) during 2004-2024.
Filers outside the panel can never enter either scan, so fetching them would be
pure waste of a rate-limited budget.

MUST NOT run concurrently with any other SEC pull: the 8/s limiter is per-process,
so two processes make 16/s and SEC's cap is 10/s.

Usage: .venv\\Scripts\\python -m scripts.fetch_sec_submissions
Output: data/events/sec_submissions.parquet
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.events.edgar_8k import _submission_pages
from aegis_brain.events.edgar_sec import STATS
from aegis_brain.events.name_link import cik_permno_windows
from aegis_brain.factory.explore import segment_mask

KEEP_FORMS = ("8-K", "10-K", "10-Q")
SHARD_SIZE = 200
WIN_START, WIN_END = "2004-01-31", "2024-12-31"


def universe_ciks() -> list[int]:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    seg = (segment_mask(panel, "largemid") | segment_mask(panel, "small")
           ).loc[WIN_START:WIN_END]
    permnos = {int(c) for c in seg.columns[seg.any(axis=0)]}
    bridge = cik_permno_windows()
    return sorted(bridge[bridge["permno"].isin(permnos)]["cik"].unique().tolist())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        stream=sys.stdout)
    t0 = time.time()
    out_dir = MODULE_ROOT / "data" / "events"
    ciks = universe_ciks()
    logging.info("in-universe filers: %d", len(ciks))

    # Shard checkpointing. An hour of rate-limited fetching must survive an
    # interruption: this pass once reached 89% and lost everything because it
    # only wrote at the end. Shards are flushed every SHARD_SIZE filers and
    # completed CIKs are skipped on restart.
    shard_dir = out_dir / "_subs_shards"
    shard_dir.mkdir(exist_ok=True)
    done: set[int] = set()
    for sh in sorted(shard_dir.glob("shard_*.parquet")):
        try:
            done |= set(pd.read_parquet(sh, columns=["cik"])["cik"].astype(int))
        except Exception:
            logging.warning("unreadable shard %s — refetching its filers", sh.name)
    if done:
        logging.info("resuming: %d filers already banked in shards", len(done))

    pending = [c for c in ciks if c not in done]
    logging.info("filers pending: %d", len(pending))

    COLUMNS = ["cik", "form", "accession", "items_raw", "filing_date",
               "primary_document"]
    rows: list[tuple] = []
    batch_ciks: list[int] = []
    n_missing = 0

    def flush(tag: int) -> None:
        if not batch_ciks:
            return
        # Filers with zero kept forms still get a marker row so a restart does not
        # refetch them forever; markers are dropped at assembly.
        recorded = {r[0] for r in rows}
        extra = [(c, "_NONE_", "", "", "", "") for c in batch_ciks if c not in recorded]
        pd.DataFrame(rows + extra, columns=COLUMNS).to_parquet(
            shard_dir / f"shard_{tag:05d}.parquet", index=False)
        rows.clear()
        batch_ciks.clear()

    for i, cik in enumerate(pending, start=1):
        batch_ciks.append(cik)
        try:
            pages = _submission_pages(cik)
        except RuntimeError:
            logging.warning("submissions unavailable for CIK %d", cik)
            n_missing += 1
            pages = []
        if not pages:
            n_missing += 1
        for page in pages:
            forms = page.get("form", [])
            n = len(forms)
            accs = page.get("accessionNumber", [""] * n)
            items = page.get("items", [""] * n) or [""] * n
            dates = page.get("filingDate", [""] * n)
            prim = page.get("primaryDocument", [""] * n) or [""] * n
            for f, a, it, d, pd_ in zip(forms, accs, items, dates, prim):
                fu = str(f).upper()
                if fu.startswith(KEEP_FORMS):
                    rows.append((cik, fu, a, it or "", d, pd_ or ""))
        if i % SHARD_SIZE == 0:
            flush(i)
            logging.info("filers %d/%d banked, fetch_stats %s", i, len(pending), STATS)
    flush(10 ** 5)

    shards = sorted(shard_dir.glob("shard_*.parquet"))
    if not shards:
        raise RuntimeError("submissions pass returned ZERO rows — treat as fetch "
                           "failure, never as 'this universe files nothing'")
    df = pd.concat([pd.read_parquet(s) for s in shards], ignore_index=True)
    df = df[df["form"] != "_NONE_"]
    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    df = df.dropna(subset=["filing_date"]).drop_duplicates(subset=["accession", "form"])
    df.to_parquet(out_dir / "sec_submissions.parquet", index=False)

    meta = {
        "n_ciks_requested": len(ciks),
        "n_ciks_missing": n_missing,
        "n_rows": int(len(df)),
        "by_form": {k: int(v) for k, v in
                    df["form"].str.split("/").str[0].value_counts().items()},
        "date_range": [str(df["filing_date"].min().date()),
                       str(df["filing_date"].max().date())],
        "fetch_stats": dict(STATS),
        "elapsed_s": round(time.time() - t0, 1),
    }
    (out_dir / "sec_submissions_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2), flush=True)


if __name__ == "__main__":
    main()
