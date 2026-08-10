"""How big must a real mechanism be before the Arena can see it?

The known-answer test does not have a pass/fail answer, it has a THRESHOLD. In
a world where nothing predicts anything, the maximum over a 384-genome pool is
still a positive number, because a maximum over 384 draws is. The question that
decides whether any Arena ranking means anything is:

    at what planted effect size does the best truth-carrying genome reliably
    exceed the best noise genome?

Below that size, an Arena winner on real data is indistinguishable from the
luckiest of 384 coin flips, and must not be reported as a finding. This script
measures it, so the bar is a number rather than an intuition.

    python -m scripts.arena_power_curve [--effects 0.04 0.08 0.16 0.32]
                                        [--seeds 3]

Writes runs/ARENA1/power_curve.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

from aegis_brain.arena import bindings, synthetic as SY
from aegis_brain.arena.evaluate import evaluate
from aegis_brain.config import MODULE_ROOT
from scripts.run_arena1 import _composite, _genomes_from, load_manifest

OUT = MODULE_ROOT / "runs" / "ARENA1" / "power_curve.json"

#: The planted mechanism is `synth:quality`, which the registry PERMITS to lead
#: a genome (profitability_small is a PICKER). That matters: a mechanism the
#: registry only allows as a low-weight tie-breaker cannot be found by this
#: search at ANY effect size, which is a separate finding reported alongside.
TRUTH_WORLD = "quality"


def _score_world(world, genomes) -> list[dict]:
    rows = []
    cache: dict[tuple, pd.DataFrame] = {}
    for g in genomes:
        key = g.signals
        if key not in cache:
            try:
                frames = [(world.signals[bindings.synthetic_key(s)], w)
                          for s, w in g.signals if s != "control:ew"]
            except bindings.BindingError:
                cache[key] = None       # type: ignore[assignment]
                frames = []
            if key not in cache:
                cache[key] = (_composite(frames, world.eligible) if frames
                              else pd.DataFrame(0.5, index=world.ret.index,
                                                columns=world.ret.columns))
        score = cache[key]
        if score is None:
            continue
        r = evaluate(g, score=score.shift(1), ret=world.ret,
                     eligible=world.eligible, vol=world.vol,
                     benchmark=world.benchmark)
        if r.status != "OK":
            continue
        rows.append({"genome_id": g.genome_id, "family": g.signal_family,
                     "excess": r.excess_cagr_net, "t": r.t_excess,
                     "top_k": g.top_k, "weighting": g.weighting,
                     "is_truth": any(bindings.SYNTHETIC.get(s) == world.truth
                                     for s, _ in g.signals)})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--effects", type=float, nargs="*",
                    default=[0.0, 0.04, 0.08, 0.16, 0.32])
    ap.add_argument("--seeds", type=int, default=3)
    a = ap.parse_args()

    genomes = _genomes_from(load_manifest())
    out: dict = {
        "question": ("at what planted effect size does the best truth-carrying "
                     "genome reliably beat the best noise genome?"),
        "n_genomes": len(genomes),
        "truth_world": TRUTH_WORLD,
        "note": ("Effects are TOP-DECILE SPREADS per year. A long-only book "
                 "captures roughly half of a decile spread, because it holds "
                 "the top against the MEAN rather than against the bottom."),
        "points": [],
    }

    for eff in a.effects:
        per_seed = []
        for s in range(a.seeds):
            seed = 20260811 + 1000 * s
            world = SY.make_world(TRUTH_WORLD, seed=seed)
            if eff != world.effect_ann:
                # Rebuild the same world at a different planted size by
                # rescaling the plant. Regenerating from scratch keeps the
                # noise draw identical across effect sizes, which is what makes
                # the curve a curve rather than five unrelated experiments.
                world = _replant(TRUTH_WORLD, seed=seed, effect=eff)
            rows = _score_world(world, genomes)
            truth = [r for r in rows if r["is_truth"]]
            noise = [r for r in rows if not r["is_truth"]]
            if not truth or not noise:
                continue
            best_t = max(r["excess"] for r in truth)
            best_n = max(r["excess"] for r in noise)
            ranked = sorted(rows, key=lambda r: -r["excess"])
            top10 = ranked[:10]
            per_seed.append({
                "seed": seed,
                "best_truth": round(best_t, 5),
                "best_noise": round(best_n, 5),
                "margin": round(best_t - best_n, 5),
                "truth_wins": bool(best_t > best_n),
                "truth_share_top10": sum(1 for r in top10 if r["is_truth"]) / 10,
                "median_truth": round(float(np.median(
                    [r["excess"] for r in truth])), 5),
                "median_noise": round(float(np.median(
                    [r["excess"] for r in noise])), 5),
            })
        if not per_seed:
            continue
        point = {
            "planted_effect_ann": eff,
            "n_seeds": len(per_seed),
            "truth_wins_fraction": sum(p["truth_wins"] for p in per_seed)
            / len(per_seed),
            "mean_margin": round(float(np.mean([p["margin"] for p in per_seed])), 5),
            "mean_best_noise": round(float(np.mean(
                [p["best_noise"] for p in per_seed])), 5),
            "mean_best_truth": round(float(np.mean(
                [p["best_truth"] for p in per_seed])), 5),
            "mean_truth_share_top10": round(float(np.mean(
                [p["truth_share_top10"] for p in per_seed])), 3),
            "seeds": per_seed,
        }
        out["points"].append(point)
        print(f"[power] effect {eff:+.2f}  best_truth {point['mean_best_truth']:+.4f}"
              f"  best_noise {point['mean_best_noise']:+.4f}"
              f"  margin {point['mean_margin']:+.4f}"
              f"  truth_wins {point['truth_wins_fraction']:.0%}"
              f"  top10 truth {point['mean_truth_share_top10']:.0%}", flush=True)

    detected = [p for p in out["points"] if p["truth_wins_fraction"] >= 1.0
                and p["mean_margin"] > 0.005]
    out["detection_threshold_ann"] = (min(p["planted_effect_ann"] for p in detected)
                                      if detected else None)
    out["verdict"] = (
        f"The Arena reliably separates truth from noise at a planted decile "
        f"spread of {out['detection_threshold_ann']:+.2f}/yr and above."
        if detected else
        "The Arena did NOT reliably separate truth from noise at ANY tested "
        "effect size. No Arena ranking on real data may be reported as "
        "evidence of a mechanism.")
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n" + out["verdict"])
    print(f"wrote {OUT}")
    return 0


def _replant(kind: str, *, seed: int, effect: float):
    """Same world, same noise draw, different planted effect size."""
    import numpy as np

    rng = np.random.default_rng(seed)
    n_months, n_names = SY.N_MONTHS, SY.N_NAMES
    idx = SY._index(n_months)
    cols = [f"S{i:04d}" for i in range(n_names)]
    total, idio = SY._blank(rng, n_months, n_names)
    market_part = total - idio
    sig_names = ["synth:analyst_rev", "synth:momentum", "synth:quality",
                 "synth:insider", "synth:reversal"]
    raw = {s: SY._noise_signal(rng, n_months, n_names) for s in sig_names}
    truth = {"quality": "synth:quality", "momentum": "synth:momentum",
             "analyst_skill": "synth:analyst_rev"}[kind]
    if effect != 0.0:
        idio = SY._plant(idio, raw[truth], effect, rng)
    ret = pd.DataFrame(market_part + idio, index=idx, columns=cols)
    signals = {s: pd.DataFrame(v, index=idx, columns=cols).astype(np.float32)
               for s, v in raw.items()}
    eligible = pd.DataFrame(True, index=idx, columns=cols)
    vol = (ret.rolling(12, min_periods=6).std() * np.sqrt(12)).bfill().fillna(
        SY.IDIO_SIG * np.sqrt(12))
    return SY.World(name=f"{kind}@{effect}", description="power-curve replant",
                    truth=truth if effect != 0 else None, effect_ann=effect,
                    ret=ret.astype(np.float32), signals=signals,
                    benchmark=ret.mean(axis=1).astype(float),
                    eligible=eligible, vol=vol.astype(np.float32))


if __name__ == "__main__":
    raise SystemExit(main())
