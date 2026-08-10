"""ARENA-1 — freeze hundreds of portfolios, THEN score them.

    python -m scripts.run_arena1 --freeze          # write the manifest only
    python -m scripts.run_arena1 --synthetic       # known-answer + null tests
    python -m scripts.run_arena1 --real            # the licensed historical run
    python -m scripts.run_arena1 --all

The order is not a convenience. `--freeze` writes ARENA_MANIFEST.json and it is
committed before `--synthetic` or `--real` may run: the script REFUSES to score
a manifest whose hash does not match one already on disk, so a genome pool
cannot be edited after a result is seen and still be called the same search.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

from aegis_brain.arena import bindings, genome as GEN, synthetic as SY
from aegis_brain.arena.evaluate import evaluate
from aegis_brain.config import MODULE_ROOT

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "ARENA1"
MANIFEST_PATH = OUT / "ARENA_MANIFEST.json"

ARENA_ID = "ARENA-1"
SEED = 20260811
FIRST, LAST = "2002-01-31", "2022-12-31"


def _registry():
    """The signal registry lives in aegis-finance. One source of truth."""
    import os
    import yaml

    override = os.environ.get("AEGIS_SIGNAL_REGISTRY")
    candidates = [Path(override)] if override else []
    candidates += [
        MODULE_ROOT.parent / "aegis-finance" / "backend" / "data"
        / "signal_registry.yaml",
    ]
    for p in candidates:
        if p and p.exists():
            sys.path.insert(0, str(p.parents[2]))
            from backend.services import signal_registry as SR  # noqa: PLC0415
            return SR.load(str(p)), str(p)
    raise FileNotFoundError(
        "signal_registry.yaml not found. The Arena will not generate a genome "
        "pool without it — a pool built from memory could contain a closed "
        "mechanism and nothing would notice. Set AEGIS_SIGNAL_REGISTRY.")


def _code_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=MODULE_ROOT,
                              capture_output=True, text=True,
                              timeout=20).stdout.strip()[:12] or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


# ───────────────────────────── freeze ───────────────────────────────────────

def freeze() -> dict:
    reg, reg_path = _registry()
    evaluable, missing = bindings.evaluable(reg)

    class _Filtered:
        """A registry view containing only signals the Arena can actually run.

        The pool is built from this rather than from the full registry so the
        manifest's denominator is the number of genomes that WILL be scored,
        not the number that would have existed if every signal had a panel.
        """
        def __init__(self, r, keep):
            self._r, self._keep = r, set(keep)

        def by_role(self, role):
            return [s for s in self._r.by_role(role) if s.signal_id in self._keep]

        def get(self, sid):
            return self._r.get(sid)

    pool = _Filtered(reg, evaluable)
    genomes = GEN.generate(pool, segments=("small", "largemid"),
                           cost_models=("flat25",), max_genomes=500)

    man = GEN.manifest(
        genomes, arena_id=ARENA_ID, code_sha=_code_sha(),
        data_cutoff="crsp_panel_2002 ends 2024-12-31; holdout locked past "
                    f"{LAST}",
        window=(FIRST, LAST),
        benchmark="equal-weight eligible universe (CANON 16: the denominator "
                  "is not the winner's)",
        objectives=["net excess CAGR vs the eligible-universe control",
                    "max drawdown", "worst rolling 12m", "turnover",
                    "regime-block breadth", "concentration of the result in a "
                    "handful of months"],
        selection_rule=(
            "Finalists are chosen by a PRE-DECLARED rule: net excess CAGR > 0 "
            "AND at least half the non-overlapping 3-year blocks positive AND "
            "top-5-month share < 0.8 (a strategy that is five months is a "
            "story about five months) AND turnover under 300%/yr. Rank within "
            "the survivors by net excess terminal wealth, never by Sharpe. "
            "The Arena's own numbers are a SCREEN, not a verdict — finalists "
            "go to pf.run.Factory for adjudication with controls."),
        registry_summary={
            "path": reg_path, "written": reg.written,
            **reg.summary(),
            "evaluable_in_arena": evaluable,
            "excluded_no_panel_implementation": missing,
        },
        seed=SEED)

    OUT.mkdir(parents=True, exist_ok=True)
    if MANIFEST_PATH.exists():
        old = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if old.get("genomes_sha256") != man["genomes_sha256"]:
            raise SystemExit(
                f"REFUSING to overwrite {MANIFEST_PATH}: a manifest already "
                f"exists with a DIFFERENT genome hash.\n"
                f"  on disk: {old.get('genomes_sha256','?')[:16]} "
                f"({old.get('denominator',{}).get('n_genomes')} genomes)\n"
                f"  new:     {man['genomes_sha256'][:16]} "
                f"({man['denominator']['n_genomes']} genomes)\n"
                f"Editing the pool after results exist is a NEW arena. Give it "
                f"a new arena_id and record this one as its parent.")
        print(f"[freeze] manifest unchanged ({man['genomes_sha256'][:16]})")
        return man
    MANIFEST_PATH.write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(f"[freeze] {man['denominator']['n_genomes']} genomes, "
          f"{man['denominator']['n_signal_families']} families, "
          f"sha {man['genomes_sha256'][:16]}")
    print(f"[freeze] wrote {MANIFEST_PATH}")
    if missing:
        print(f"[freeze] {len(missing)} permitted signal(s) EXCLUDED for lack "
              f"of a panel implementation:")
        for k, v in missing.items():
            print(f"           {k}: {v[:100]}")
    return man


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise SystemExit("no manifest — run --freeze first, and commit it")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _genomes_from(man: dict) -> list[GEN.PortfolioGenome]:
    out = []
    for row in man["genomes"]:
        row = {k: v for k, v in row.items() if k != "genome_hash"}
        row["signals"] = tuple(tuple(x) for x in row["signals"])
        row["distinct_from"] = tuple(row.get("distinct_from") or ())
        row["tags"] = tuple(row.get("tags") or ())
        out.append(GEN.PortfolioGenome(**row))
    return out


def _composite(frames: list[tuple[pd.DataFrame, float]],
               eligible: pd.DataFrame) -> pd.DataFrame:
    """Weighted cross-sectional percentile-rank composite inside the eligible set."""
    num = den = None
    for f, w in frames:
        r = f.where(eligible).rank(axis=1, pct=True)
        c = r.fillna(0.0) * w
        num = c if num is None else num + c
        m = r.notna().astype(float) * w
        den = m if den is None else den + m
    total = sum(abs(w) for _, w in frames)
    ok = den >= 0.5 * total
    return (num / den).where(ok)


# ───────────────────────────── synthetic ────────────────────────────────────

def run_synthetic(man: dict, *, worlds: tuple[str, ...] = SY.WORLDS) -> dict:
    genomes = _genomes_from(man)
    out: dict = {"arena_id": man["arena_id"],
                 "manifest_sha256": man["genomes_sha256"],
                 "purpose": (
                     "CALIBRATION ONLY. Synthetic performance is never evidence "
                     "that a strategy makes money. These runs score the ARENA: "
                     "can it find a planted truth, and how large a winner does "
                     "it manufacture when there is none?"),
                 "worlds": {}}

    for wname in worlds:
        t0 = time.time()
        world = SY.make_world(wname, seed=SEED)
        check = SY.verify(world, seed=SEED)
        rows = []
        for g in genomes:
            try:
                frames = [(world.signals[bindings.synthetic_key(sid)], w)
                          for sid, w in g.signals if sid != "control:ew"]
            except bindings.BindingError:
                continue
            if not frames:      # the control genome: score everything equally
                score = pd.DataFrame(0.5, index=world.ret.index,
                                     columns=world.ret.columns)
            else:
                score = _composite(frames, world.eligible)
            r = evaluate(g, score=score.shift(1), ret=world.ret,
                         eligible=world.eligible, vol=world.vol,
                         benchmark=world.benchmark)
            d = r.as_dict()
            d["signal_family"] = g.signal_family
            d["is_truth_family"] = bool(
                world.truth and any(bindings.SYNTHETIC.get(s) == world.truth
                                    for s, _ in g.signals))
            rows.append(d)

        ok = [r for r in rows if r["status"] == "OK"]
        ok.sort(key=lambda r: -(r["excess_cagr_net"] or -9))
        truth_ranks = [i for i, r in enumerate(ok, 1) if r["is_truth_family"]]
        out["worlds"][wname] = {
            "world": world.as_dict(),
            "plant_verified": check,
            "n_scored": len(ok),
            "best_excess_cagr_net": ok[0]["excess_cagr_net"] if ok else None,
            "best_genome": ok[0]["genome_id"] if ok else None,
            "best_family": ok[0]["signal_family"] if ok else None,
            "best_t": ok[0]["t_excess"] if ok else None,
            "median_excess": float(np.median([r["excess_cagr_net"] for r in ok]))
            if ok else None,
            "truth_family_best_rank": min(truth_ranks) if truth_ranks else None,
            "truth_family_median_rank": (float(np.median(truth_ranks))
                                         if truth_ranks else None),
            "n_truth_genomes": len(truth_ranks),
            "top10_truth_share": (sum(1 for r in ok[:10] if r["is_truth_family"])
                                  / 10.0 if len(ok) >= 10 else None),
            "runtime_secs": round(time.time() - t0, 1),
            "all_results": ok,
        }
        b = out["worlds"][wname]
        print(f"[synthetic] {wname:18s} best {b['best_excess_cagr_net']:+.4f} "
              f"({b['best_family'][:28]}) truth in top10: "
              f"{b['top10_truth_share']} ({b['runtime_secs']}s)")

    null = out["worlds"].get("null")
    if null:
        out["null_calibration"] = {
            "best_excess_cagr_net_in_a_world_with_no_signal":
                null["best_excess_cagr_net"],
            "interpretation": (
                "This is what the maximum over the whole frozen pool looks "
                "like when NOTHING predicts anything. A real-data winner that "
                "does not clearly exceed it has told us nothing. Every "
                "'best of N' this programme has previously reported was "
                "compared against this number implicitly and unmeasured."),
        }
    return out


# ───────────────────────────── real ─────────────────────────────────────────

def run_real(man: dict) -> dict:
    from aegis_brain.pf.panel63 import Spine, eligibility, load_spine
    from aegis_brain.pf.signals import SignalLibrary

    reg, _ = _registry()
    genomes = _genomes_from(man)
    spine: Spine = load_spine(FIRST, LAST, allow_holdout=False)
    lib = SignalLibrary(spine.panel)
    ret = spine.panel.monthly_ret

    vol = ret.rolling(12, min_periods=6).std() * np.sqrt(12)
    vol = vol.bfill()

    elig_cache: dict[str, pd.DataFrame] = {}
    bench_cache: dict[str, pd.Series] = {}
    score_cache: dict[tuple, pd.DataFrame] = {}
    rows: list[dict] = []
    t0 = time.time()

    for i, g in enumerate(genomes, 1):
        if g.segment not in elig_cache:
            elig_cache[g.segment] = eligibility(spine, g.segment)
            e = elig_cache[g.segment].reindex(index=ret.index, columns=ret.columns)
            bench_cache[g.segment] = ret.where(e.fillna(False)).mean(axis=1)
        elig = elig_cache[g.segment].reindex(index=ret.index,
                                             columns=ret.columns).fillna(False)

        key = (g.signals, g.segment)
        if key not in score_cache:
            try:
                if g.signals == (("control:ew", 1.0),):
                    score_cache[key] = pd.DataFrame(
                        0.5, index=ret.index, columns=ret.columns)
                else:
                    frames = [(lib.get(bindings.panel_key(sid, reg)), w)
                              for sid, w in g.signals]
                    score_cache[key] = _composite(frames, elig)
            except Exception as exc:  # noqa: BLE001 - a dead family is data
                score_cache[key] = None  # type: ignore[assignment]
                logger.error("score build failed for %s: %s", g.signal_family, exc)
        score = score_cache[key]
        if score is None:
            rows.append({"genome_id": g.genome_id, "status": "FAILED",
                         "error": "score frame unavailable",
                         "signal_family": g.signal_family})
            continue

        r = evaluate(g, score=score.shift(1), ret=ret, eligible=elig,
                     vol=vol, benchmark=bench_cache[g.segment])
        d = r.as_dict()
        d.update(signal_family=g.signal_family, segment=g.segment,
                 top_k=g.top_k, weighting=g.weighting,
                 rebalance_months=g.rebalance_months,
                 max_weight=g.max_weight, tags=list(g.tags))
        rows.append(d)
        if i % 25 == 0:
            print(f"[real] {i}/{len(genomes)} ({time.time()-t0:.0f}s)", flush=True)

    return {"arena_id": man["arena_id"],
            "manifest_sha256": man["genomes_sha256"],
            "window": [FIRST, LAST],
            "provenance": dict(spine.provenance),
            "n_genomes": len(genomes),
            "runtime_secs": round(time.time() - t0, 1),
            "caveat": (
                "SCREEN, NOT VERDICT. No placebo band, no factor alpha, no "
                "multiple-testing deflation, no market impact and no delisting "
                "stub. Impact and delisting both flatter small-cap, "
                "high-turnover genomes, which is where this programme's history "
                "says to be most suspicious."),
            "results": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    OUT.mkdir(parents=True, exist_ok=True)

    if a.freeze or a.all:
        freeze()
    man = load_manifest()
    if a.synthetic or a.all:
        res = run_synthetic(man)
        (OUT / "synthetic_results.json").write_text(json.dumps(res, indent=2),
                                                    encoding="utf-8")
        print(f"wrote {OUT / 'synthetic_results.json'}")
    if a.real or a.all:
        res = run_real(man)
        (OUT / "real_results.json").write_text(json.dumps(res, indent=2),
                                               encoding="utf-8")
        print(f"wrote {OUT / 'real_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
