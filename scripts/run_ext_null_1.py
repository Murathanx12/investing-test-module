"""EXT-NULL-1 / EXT-POWER-1 — external calibration of the frozen BRAIN-009 ladder.

Pre-registered in TRIALS/PREREG_EXT_NULL_1.md BEFORE any ladder statistic
existed. Read that file first; the limitation in its §6 bounds every number
this script produces.

Arms
  placebo   OSAP Cat.Signal == 'Placebo'   -> explore AND confirm (FDR arm)
  predictor OSAP Cat.Signal == 'Predictor' -> EXPLORE ONLY (wall preserved)

Guard: reproduces two banked batch-1 numbers exactly before reading anything.
Incremental: every scanned signal is appended to the output CSV immediately, so
a network failure halfway through costs time, not results.

Run:
    python scripts/run_ext_null_1.py --arm placebo
    python scripts/run_ext_null_1.py --arm predictor
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory import osap
from aegis_brain.factory.explore import ScanConfig, scan_signal

logging.basicConfig(level=logging.WARNING)
MODULE_ROOT = Path(__file__).resolve().parents[1]
PANEL_DIR = MODULE_ROOT / "data" / "crsp_panel_2002"
OSAP_DIR = MODULE_ROOT / "data" / "osap"
OUT_DIR = MODULE_ROOT / "runs" / "EXT-NULL-1"

CONFIRM_CFG = ScanConfig(first_test_month="2019-01-31",
                         last_test_month="2024-12-31")

# banked in data/factory/batch1_summary.csv — the §28 reproduction discipline
GUARD = {"vol_12m_low": 1.89, "price_level": 2.12}


def _t(x: pd.Series) -> float:
    x = x.dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else 0.0


def run_guard(panel) -> dict:
    """Abort the whole run unless the harness reproduces banked numbers."""
    from aegis_brain.factory.signals import FactorySignal

    vol = FactorySignal("vol_12m_low", "guard",
                        lambda p: p.monthly_ret.rolling(12, min_periods=9).std(),
                        -1)
    prc = FactorySignal("price_level", "guard",
                        lambda p: np.log(p.month_end_price.where(
                            p.month_end_price > 0)), +1)
    out = {}
    for sig in (vol, prc):
        got = scan_signal(panel, sig, "largemid")["summary"]["t_ic"]
        want = GUARD[sig.name]
        out[sig.name] = {"measured": got, "banked": want, "match": got == want}
        print(f"GUARD {sig.name:14s} {got:6.2f} vs banked {want:6.2f} "
              f"{'PASS' if got == want else 'FAIL'}", flush=True)
    if not all(v["match"] for v in out.values()):
        raise SystemExit("GUARD FAILED — run VOID, no statistic reported.")
    return out


class LocalWide:
    """Column-selective reader over the cached OSAP firm-level parquet.

    The wide panel is ~4M rows x 209 signals; materialising it whole costs
    several GB for no reason. Every chunk reads only the columns it scans.
    """

    def __init__(self, path: Path) -> None:
        import polars as pl

        self.path = path
        self.columns = set(pl.scan_parquet(path).collect_schema().names())

    def read(self, cols: list[str]) -> pd.DataFrame:
        import polars as pl

        return (pl.scan_parquet(self.path)
                  .select(["permno", "yyyymm"] + list(cols))
                  .collect()
                  .to_pandas())


def load_local_wide() -> "LocalWide | None":
    """Use the cached bulk panel if scripts/_osap_to_parquet.py landed it."""
    p = OSAP_DIR / "firm_char.parquet"
    if p.exists():
        w = LocalWide(p)
        print(f"using local bulk panel ({len(w.columns) - 2} signals)", flush=True)
        return w
    return None


def fetch_chunk(acronyms: list[str], tries: int = 4) -> pd.DataFrame:
    last = None
    for a in range(tries):
        try:
            return osap.download_long(acronyms)
        except ValueError:
            raise                      # missing signals: a real answer, not a retry
        except Exception as exc:       # network / 503
            last = exc
            print(f"  chunk retry {a + 1}/{tries}: {type(exc).__name__}",
                  flush=True)
            time.sleep(20 * (a + 1))
    raise RuntimeError(f"chunk failed after {tries} tries: {last}")


def probe_available(acronyms: list[str], chunk: int = 12) -> list[str]:
    """Which acronyms actually come back at firm level."""
    ok: list[str] = []
    for i in range(0, len(acronyms), chunk):
        part = acronyms[i:i + chunk]
        try:
            df = fetch_chunk(part)
            ok.extend([c for c in df.columns if c not in ("permno", "yyyymm")])
        except ValueError as exc:
            # split: keep the ones that did arrive
            msg = str(exc)
            print(f"  partial chunk: {msg[:120]}", flush=True)
            for one in part:
                try:
                    fetch_chunk([one])
                    ok.append(one)
                except Exception:
                    pass
    return sorted(set(ok))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("placebo", "predictor"), required=True)
    ap.add_argument("--chunk", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(PANEL_DIR)
    guard = run_guard(panel)
    print("GUARD PASSED\n", flush=True)

    doc = osap.load_doc()
    cat = osap.CAT_PLACEBO if args.arm == "placebo" else osap.CAT_PREDICTOR
    metas = {m.acronym: m for m in osap.meta_table(doc, cat)}
    names = sorted(metas)
    if args.limit:
        names = names[:args.limit]
    print(f"{cat}: {len(names)} documented\n", flush=True)

    wide = load_local_wide()
    out_csv = OUT_DIR / f"scan_{args.arm}.csv"
    rows: list[dict] = []
    scanned: set[str] = set()
    if out_csv.exists():                       # resume
        prev = pd.read_csv(out_csv)
        rows = prev.to_dict("records")
        scanned = set(prev["acronym"])
        print(f"resuming: {len(scanned)} already scanned", flush=True)

    todo = [n for n in names if n not in scanned]
    for i in range(0, len(todo), args.chunk):
        part = todo[i:i + args.chunk]
        if wide is not None:
            have = [c for c in part if c in wide.columns]
            long = wide.read(have) if have else None
            missing = sorted(set(part) - set(have))
        else:
            try:
                long = fetch_chunk(part)
                have, missing = part, []
            except ValueError:
                have = probe_available(part, chunk=1)
                long = fetch_chunk(have) if have else None
                missing = sorted(set(part) - set(have))
        for m in missing:
            rows.append({"acronym": m, "available": False})
        if long is None:
            pd.DataFrame(rows).to_csv(out_csv, index=False)
            continue

        # ONE gridder per chunk: the (month, permno) index map is identical for
        # every signal in the chunk, and rebuilding it per signal costs ~7s each.
        built = {s.name[5:]: s
                 for s in osap.build_signals(long, [metas[a] for a in have],
                                             panel)}
        for acr in have:
            meta = metas[acr]
            rec: dict = {"acronym": acr, "available": True,
                         "category": meta.category, "sign": meta.sign,
                         "authors": meta.authors, "year": meta.year,
                         "journal": meta.journal,
                         "sample_end": meta.sample_end}
            try:
                sig = built.get(acr)
                if sig is None:
                    rec["error"] = "no_frame"
                    rows.append(rec)
                    continue
                frame = sig.compute(panel)
                rec["coverage_names_per_month"] = round(
                    float(frame.notna().sum(axis=1).mean()), 1)
                for seg in ("largemid", "small"):
                    e = scan_signal(panel, sig, seg)["summary"]
                    rec[f"ex_{seg}_months"] = e["months"]
                    rec[f"ex_{seg}_t_ic"] = e["t_ic"]
                    rec[f"ex_{seg}_t_net"] = e["t_excess_net"]
                    rec[f"ex_{seg}_t_gross"] = e["t_excess_gross"]
                    rec[f"ex_{seg}_turnover"] = e["turnover_1way"]
                if args.arm == "placebo":      # confirm ONLY for placebos
                    for seg in ("largemid", "small"):
                        c = scan_signal(panel, sig, seg, CONFIRM_CFG)["summary"]
                        rec[f"cf_{seg}_months"] = c["months"]
                        rec[f"cf_{seg}_t_ic"] = c["t_ic"]
                        rec[f"cf_{seg}_ic_mean"] = c["ic_mean"]
                        rec[f"cf_{seg}_t_net"] = c["t_excess_net"]
            except Exception as exc:
                rec["error"] = f"{type(exc).__name__}: {exc}"[:200]
            rows.append(rec)
            print(f"  {acr:28s} lm t_ic "
                  f"{rec.get('ex_largemid_t_ic', float('nan')):6.2f} | sm "
                  f"{rec.get('ex_small_t_ic', float('nan')):6.2f}", flush=True)
        pd.DataFrame(rows).to_csv(out_csv, index=False)

    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    meta_out = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "arm": args.arm, "prereg": "TRIALS/PREREG_EXT_NULL_1.md",
        "guard": guard, "n_documented": len(names),
        "n_available": int(df.get("available", pd.Series(dtype=bool)).sum()),
        "ladder": "BRAIN-009 frozen: explore t_ic>=1.5 largemid rank t_ic "
                  "top5 -> confirm t_ic>=0.5 AND ic_mean>0; DSR/PBO inert",
    }
    (OUT_DIR / f"meta_{args.arm}.json").write_text(
        json.dumps(meta_out, indent=2), encoding="utf-8")
    print(f"\nwritten -> {out_csv}", flush=True)


if __name__ == "__main__":
    main()
