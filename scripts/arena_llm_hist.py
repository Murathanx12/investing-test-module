"""ABLATION-1 — the historical LLM panel. ARCHITECTURE_RESULT_ONLY.

WHAT THIS IS
============
`PREREG_ABLATION_1.md` §5 declared, before any call, a panel of 119 month-ends
(2015-01-30 → 2024-11-29), 40 names per date drawn by a seeded stratified
market-cap-quintile sample, and five of chunk 3's fourteen roles. This module
issues those calls and nothing else.

**Every record it produces is `ARCHITECTURE_RESULT_ONLY` (Amendment A6).** The
foundation model may know what these securities did after 2015. A good result
here is unfalsifiably contaminated and certifies nothing about alpha. What it
CAN do — and the only reason to spend the money — is compare architectures
against each other and against placebos **under identical contamination**. That
is what an ablation is.

THREE ARMS ARE CALLED; TWO MORE ARE DERIVED FOR FREE
----------------------------------------------------
- `swarm`     — the five declared roles (A4 arm 5)
- `generic`   — one un-specialised analyst, same contract, same parser (A4 arm 4)
- `randtext`  — the same prompt shape carrying NO security: a synthetic symbol
                and field values drawn from the cross-sectional distribution of
                other names on the same date (A4 arm 3). This measures what the
                model says when it is shown nothing, which is the only honest
                floor for "the reply looked confident".

`shuffled` (A4 arm 1, the decisive one) and `time-shifted` (arm 2) are
permutations of the swarm's own output and cost no vendor calls. They are
computed in the analysis stage, from this file's output.

POINT-IN-TIME, ENFORCED IN ONE PLACE
------------------------------------
The price frame handed to `llm_swarm.snapshot_from_panel` is truncated at the
decision date before the function is called, and the function truncates again.
The ticker shown is the CRSP ticker **valid on that date** — a ticker is not a
permanent property of a security, and showing the 2026 symbol for a 2015
decision leaks the company's later identity through the one channel the
snapshot truncation cannot close.

LEDGER ISOLATION
----------------
Nothing here touches `backend/data/optimus/predictions.jsonl`. That ledger's
first forward resolution is 2026-08-16 and its integrity is not this trial's to
risk. Historical records go to `data/factory/arena_llm_predictions.jsonl`.
Telemetry DOES go to the shared call ledger, because the budget governor must
see this spend — a campaign whose spend is invisible to its own governor is
ungoverned.

    python -m scripts.arena_llm_hist --workers 32
    python -m scripts.arena_llm_hist --workers 32 --resume      # crash-safe
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AF = Path(r"C:\Users\mrthn\aegis-finance")
if str(AF) not in sys.path:
    sys.path.insert(0, str(AF))
for _line in (AF / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in _line and not _line.strip().startswith("#"):
        k, v = _line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from aegis_brain.config import MODULE_ROOT                       # noqa: E402
from backend.services import llm_swarm                           # noqa: E402
from backend.services.llm_swarm import (SPECIALISTS, CONTRACT,  # noqa: E402
                                        SpecialistSpec, run_cell,
                                        snapshot_from_panel)
from backend.services.research_budget import (                   # noqa: E402
    ResearchBudgetExhausted)

FACTORY = MODULE_ROOT / "data" / "factory"
CELLS = FACTORY / "arena_llm_cells.parquet"
PANELF = FACTORY / "wg1_panel.npz"
AUX = FACTORY / "exit_lab_1_aux.npz"
OUT_CELLS = FACTORY / "arena_llm_calls.jsonl"
OUT_PRED = FACTORY / "arena_llm_predictions.jsonl"
OUT_META = FACTORY / "arena_llm_meta.json"

#: PREREG_ABLATION_1 §5. Five of fourteen. The reduction is a LIMITATION, not a
#: design improvement, and the report says so.
ROLES = ("company_fundamental", "analyst_revisions", "execution_momentum",
         "geopolitical", "skeptic")

#: A4 arm 4. One un-specialised analyst, same contract, same parser, same
#: ledger — so the only difference between arms 4 and 5 is the architecture.
GENERIC = SpecialistSpec(
    name="generic_analyst",
    system=("You are a securities analyst. You reason about whatever you judge "
            "relevant to this one security — its business, its price history, "
            "its valuation, its catalysts, its risks — with no assigned "
            "specialism and no assigned lens."),
    sectors=None)

#: A4 arm 3. Not a specialism either; it is the floor.
RANDTEXT = SpecialistSpec(
    name="randtext_analyst", system=GENERIC.system, sectors=None)

RANDTEXT_N = 1200          # ≤ 1500, the ceiling declared in the prereg
RANDTEXT_SEED = 20260812

_lock = threading.Lock()
_seen_pred: set[str] = set()

#: FF12 is ZERO-indexed in `wg1_features.ff12_of`, with 11 = Other. A
#: one-indexed reading here printed "Finance" for an air-ambulance operator in
#: the smoke run, which is the kind of wrong label a language model would
#: cheerfully reason from.
FF12_NAMES = {0: "Consumer nondurables", 1: "Consumer durables",
              2: "Manufacturing", 3: "Energy", 4: "Chemicals",
              5: "Business equipment", 6: "Telecoms", 7: "Utilities",
              8: "Wholesale/retail", 9: "Healthcare", 10: "Finance",
              11: "Other"}


# ── the price frames the snapshots are computed from ────────────────────────

def build_frames(cells: pd.DataFrame, lookback: int = 420) -> dict:
    """One truncated, split-and-dividend-adjusted price frame per decision date.

    The series is `PRC(as_of) × exp(LC(t) − LC(as_of))`: the level at the
    decision date is the REAL close on that date, and the history behind it is
    the total-return path. That is the pair of properties a snapshot needs — a
    price a human would recognise, and a return series that is not corrupted by
    splits.
    """
    z = np.load(PANELF, allow_pickle=False)
    dates = pd.DatetimeIndex(z["dates"].astype("datetime64[ns]"))
    PRC = z["PRC"]
    from scripts.exit_lab_core import build_position_factors, cum_series
    aux = np.load(AUX, allow_pickle=False)
    dec_ix = aux["dec_ix"].astype(int)
    dec_dates = pd.DatetimeIndex(aux["dec_dates"].astype("datetime64[ns]"))

    ff = pd.read_parquet(MODULE_ROOT / "data" / "wrds_raw" /
                         "ff_factors_daily.parquet", columns=["date", "rf"])
    ff["date"] = pd.to_datetime(ff["date"])
    rf = (pd.to_numeric(ff.set_index("date")["rf"], errors="coerce")
          .reindex(dates).fillna(0.0).to_numpy())
    LC, term, _ = build_position_factors(z["RET"], z["first_obs"], z["last_obs"],
                                         z["delist_day"], rf)
    del z

    spy = pd.read_parquet(MODULE_ROOT / "data" / "etf" /
                          "etf_adjusted_close.parquet")["SPY"]
    spy = pd.to_numeric(spy, errors="coerce").dropna()

    frames: dict[int, pd.DataFrame] = {}
    for k, g in cells.groupby("date_ix"):
        t = int(dec_ix[int(k)])
        lo = max(0, t - lookback)
        idx = dates[lo:t + 1]
        data = {}
        for row in g.itertuples():
            j = int(row.col)
            s = np.expm1(LC[lo:t + 1, j].astype(np.float64)
                         - LC[t, j].astype(np.float64))
            data[row.ticker] = float(PRC[t, j]) * (1.0 + s)
        f = pd.DataFrame(data, index=idx)
        f["SPY"] = spy.reindex(idx).ffill().to_numpy()
        frames[int(k)] = f
        if int(k) % 24 == 0:
            print(f"  frame {dec_dates[int(k)].date()} {f.shape}", flush=True)
    return frames


def make_snapshot(row, frame: pd.DataFrame) -> dict | None:
    as_of = str(pd.Timestamp(row.date).date())
    meta = {
        "company_name": row.comnam or None,
        "industry_ff12": FF12_NAMES.get(int(row.ff12)),
        "market_cap_usd_millions": (round(float(row.mcap) / 1e6, 1)
                                    if np.isfinite(row.mcap) else None),
        "median_daily_dollar_volume_usd_millions":
            (round(float(row.adv) / 1e6, 2) if np.isfinite(row.adv) else None),
    }
    return snapshot_from_panel(row.ticker, frame, as_of=as_of, meta=meta)


def randomise(snap: dict, pool: list[dict], rng: np.random.Generator) -> dict:
    """A structurally identical snapshot that belongs to NO security.

    Every scalar is replaced by the same field drawn from a DIFFERENT name on
    the same date, independently per field, and the identity is replaced by a
    synthetic symbol. The reply is therefore the model's response to a
    well-formed prompt carrying no information about anything — which is the
    only honest floor for "it sounded confident".
    """
    out = json.loads(json.dumps(snap, default=str))
    out["ticker"] = "ZQ" + "".join(rng.choice(list("ABCDEFGHJKLMNPQRSTUVWXYZ"),
                                              size=2))
    out["company_name"] = "Undisclosed Issuer"
    for key in ("last_close", "n_bars_available", "max_drawdown_1y_pct",
                "pct_below_1y_high", "pct_above_1y_low", "beta_vs_benchmark",
                "excess_return_63d_pct_vs_benchmark", "industry_ff12",
                "market_cap_usd_millions",
                "median_daily_dollar_volume_usd_millions"):
        if key in out:
            out[key] = pool[int(rng.integers(len(pool)))].get(key)
    for grp in ("trailing_return_pct", "realised_vol_annualised_pct"):
        if isinstance(out.get(grp), dict):
            for kk in out[grp]:
                d = pool[int(rng.integers(len(pool)))].get(grp) or {}
                out[grp][kk] = d.get(kk)
    return out


# ── one unit of work ────────────────────────────────────────────────────────

def work(arm: str, role: str, snap: dict, date_ix: int, permno: int) -> dict:
    res = run_cell(role, snap, made_at=f"{snap['as_of']}T00:00:00+00:00")
    row = res.as_row()
    row.update({"arm": arm, "date_ix": int(date_ix), "permno": int(permno),
                "as_of": snap["as_of"]})
    recs = []
    with _lock:
        for r in res.records:
            if r.prediction_id in _seen_pred:
                continue
            _seen_pred.add(r.prediction_id)
            recs.append(r)
    if recs:
        with _lock, OUT_PRED.open("a", encoding="utf-8") as fh:
            for r in recs:
                d = r.__dict__ if hasattr(r, "__dict__") else dict(r)
                fh.write(json.dumps({**{k: v for k, v in d.items()
                                        if k != "resolution_detail"},
                                     "arm": arm, "date_ix": int(date_ix),
                                     "permno": int(permno)},
                                    default=str) + "\n")
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    cells = pd.read_parquet(CELLS)
    print(f"{len(cells)} cells over {cells['date_ix'].nunique()} dates",
          flush=True)

    done: set[tuple] = set()
    if a.resume and OUT_CELLS.exists():
        for line in OUT_CELLS.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            done.add((r["arm"], r["specialist"], r["date_ix"], r["permno"]))
        print(f"resume: {len(done)} cells already on disk", flush=True)
        if OUT_PRED.exists():
            for line in OUT_PRED.read_text(encoding="utf-8").splitlines():
                try:
                    _seen_pred.add(json.loads(line)["prediction_id"])
                except Exception:                                # noqa: BLE001
                    pass
    elif OUT_CELLS.exists():
        OUT_CELLS.unlink()
        OUT_PRED.unlink(missing_ok=True)

    t0 = time.time()
    frames = build_frames(cells)
    print(f"frames built in {time.time()-t0:.0f}s", flush=True)

    # snapshots first, so a snapshot failure is counted as a DATA gap and never
    # billed as a vendor call
    snaps: dict[tuple[int, int], dict] = {}
    n_no_snap = 0
    for row in cells.itertuples():
        s = make_snapshot(row, frames[int(row.date_ix)])
        if s is None:
            n_no_snap += 1
            continue
        snaps[(int(row.date_ix), int(row.permno))] = s
    print(f"snapshots: {len(snaps)} built, {n_no_snap} refused (no usable "
          f"history at as_of)", flush=True)

    rng = np.random.default_rng(RANDTEXT_SEED)
    keys = sorted(snaps)
    rt_keys = set(map(tuple, rng.choice(np.array(keys), size=min(RANDTEXT_N,
                                                                len(keys)),
                                        replace=False).tolist()))
    by_date: dict[int, list[dict]] = {}
    for (k, p), s in snaps.items():
        by_date.setdefault(k, []).append(s)

    jobs: list[tuple] = []
    for (k, p), s in snaps.items():
        for role in ROLES:
            if ("swarm", role, k, p) not in done:
                jobs.append(("swarm", role, s, k, p))
        if ("generic", GENERIC.name, k, p) not in done:
            jobs.append(("generic", GENERIC.name, s, k, p))
        if (k, p) in rt_keys and ("randtext", RANDTEXT.name, k, p) not in done:
            jobs.append(("randtext", RANDTEXT.name,
                         randomise(s, by_date[k], rng), k, p))
    rng2 = np.random.default_rng(7)
    rng2.shuffle(jobs)                       # spread dates across the run
    if a.limit:
        jobs = jobs[:a.limit]
    print(f"{len(jobs)} calls queued "
          f"(swarm {sum(1 for j in jobs if j[0]=='swarm')}, "
          f"generic {sum(1 for j in jobs if j[0]=='generic')}, "
          f"randtext {sum(1 for j in jobs if j[0]=='randtext')})", flush=True)

    SPECIALISTS[GENERIC.name] = GENERIC
    SPECIALISTS[RANDTEXT.name] = RANDTEXT

    n_ok = n_abst = n_zero = n_fail = 0
    harness_errors: dict[str, int] = {}
    stopped = None
    t1 = time.time()
    with OUT_CELLS.open("a", encoding="utf-8") as fh, \
            ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs = {pool.submit(work, *j): j for j in jobs}
        for i, fu in enumerate(as_completed(futs), 1):
            try:
                row = fu.result()
            except ResearchBudgetExhausted as exc:
                stopped = str(exc)
                for f in futs:
                    f.cancel()
                break
            except Exception as exc:                             # noqa: BLE001
                # NEVER silently. The smoke run lost 24 of 24 calls to a
                # TypeError (one missing positional argument) and the counter
                # reported them as vendor failures — a harness bug wearing the
                # costume of flaky infrastructure. Every distinct exception is
                # printed once and all of them are counted by type.
                n_fail += 1
                key = f"{type(exc).__name__}: {exc}"[:200]
                harness_errors[key] = harness_errors.get(key, 0) + 1
                if harness_errors[key] == 1:
                    print(f"  HARNESS ERROR ({i}/{len(jobs)}): {key}",
                          flush=True)
                continue
            with _lock:
                fh.write(json.dumps(row, default=str) + "\n")
                fh.flush()
            st = row["status"]
            n_ok += st == "ok"
            n_abst += st == "abstained"
            n_zero += st == "zero_yield"
            n_fail += st == "failed"
            if i % 250 == 0:
                el = time.time() - t1
                print(f"  {i}/{len(jobs)}  ok {n_ok} abstain {n_abst} "
                      f"zero {n_zero} fail {n_fail}  {el/60:.1f}min  "
                      f"eta {(el/i)*(len(jobs)-i)/60:.0f}min", flush=True)

    meta = {
        "arms": {"swarm": list(ROLES), "generic": GENERIC.name,
                 "randtext": RANDTEXT.name},
        "n_cells": int(len(cells)), "n_snapshots": len(snaps),
        "snapshots_refused": n_no_snap,
        "randtext_subsample": len(rt_keys),
        "calls_queued": len(jobs), "ok": n_ok, "abstained": n_abst,
        "zero_yield": n_zero, "failed": n_fail,
        "harness_errors": harness_errors,
        "wall_minutes": round((time.time() - t1) / 60, 1),
        "stopped_by_governor": stopped,
        "label": "ARCHITECTURE_RESULT_ONLY",
    }
    OUT_META.write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
