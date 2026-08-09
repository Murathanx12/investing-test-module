"""Repeat probe — how much of the decider is noise? (PREREG §6, prediction N6)

Murat's observation was that LLMs "give different answers to the same question."
This measures exactly that, on the real decision task rather than a toy one:
take a seeded subsample of slates, re-ask the IDENTICAL prompt several times,
and count how many of the 40 per-name decisions change.

Two temperatures, because they answer different questions:

  * **T = 0** — the setting every graded call in this campaign uses. Any
    disagreement here is irreducible provider-side non-determinism, and it
    bounds how much of the campaign's result could be re-roll luck.
  * **T = 0.7** — a typical "creative" setting. This is the noise the cache is
    protecting us from, quantified.

Probe calls carry a nonce so they occupy their own cache keys, and they are
**never** allowed into the graded books.

    python scripts/night3_repeat_probe.py [--frac 0.10] [--repeats 3]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.night3 import decide as dec
from aegis_brain.night3.llmcache import LLMCache, SpendGuard
from aegis_brain.night3.slate import PROF_SIGNALS, build_slates
from aegis_brain.pf.panel63 import eligibility, load_spine
from aegis_brain.pf.signals import SignalLibrary, composite_score

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("probe")

RUN_DIR = MODULE_ROOT / "runs" / "NIGHT3"
MODEL = "deepseek-chat"


def agreement(a: dict, b: dict) -> dict | None:
    """Per-name agreement between two answers to the same question."""
    shared = sorted(set(a) & set(b))
    if not shared:
        return None
    same_dir = [a[k].direction == b[k].direction for k in shared]
    dconv = [abs(a[k].conviction - b[k].conviction) for k in shared]
    flips = [k for k in shared if a[k].direction != b[k].direction]
    return {"n_shared": len(shared),
            "frac_same_direction": float(np.mean(same_dir)),
            "mean_abs_conviction_delta": float(np.mean(dconv)),
            "n_flipped": len(flips)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.10)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--cap-usd", type=float, default=25.0)
    args = ap.parse_args()

    guard = SpendGuard(args.cap_usd)
    cache = LLMCache(RUN_DIR / "cache", MODEL, guard)

    spine = load_spine("2003-01-31", "2022-12-31")
    lib = SignalLibrary(spine.panel)
    lib.preload(["native:mom_12_1", "native:vol_12m_low", "osap:GP", "osap:BM",
                 "osap:OperProfRD", "osap:CBOperProf"])
    elig = eligibility(spine, "small")
    score, _ = composite_score(lib, PROF_SIGNALS, elig)
    slates = build_slates(spine, lib, score, elig, first="2005-01-31",
                          last="2021-12-31", slate_n=40)

    rng = np.random.default_rng(20260809)
    pick = sorted(rng.choice(len(slates), size=max(5, int(len(slates) * args.frac)),
                             replace=False).tolist())
    sub = [slates[i] for i in pick]
    log.info("probing %d of %d slates x %d repeats x 2 temperatures",
             len(sub), len(slates), args.repeats)

    out: dict[str, list] = {"t0": [], "t07": []}
    for s in sub:
        system, user, _ = dec.build_prompt(s, arm="A")
        for temp, key in ((0.0, "t0"), (0.7, "t07")):
            answers = []
            for r in range(args.repeats):
                rec = cache.call(system, user, temperature=temp, max_tokens=3000,
                                 nonce=f"|probe{key}r{r}",
                                 tag=f"probe|{key}|{s.formation_month}|{r}")
                if rec.get("ok"):
                    d, _ = dec.parse_decisions(rec["raw"], s)
                    answers.append(d)
            for i in range(len(answers)):
                for j in range(i + 1, len(answers)):
                    a = agreement(answers[i], answers[j])
                    if a:
                        out[key].append({"ts": s.formation_month, **a})

    def summarize(rows: list) -> dict:
        if not rows:
            return {"n_pairs": 0}
        return {
            "n_pairs": len(rows),
            "mean_frac_same_direction": round(float(np.mean(
                [r["frac_same_direction"] for r in rows])), 4),
            "mean_frac_flipped": round(1 - float(np.mean(
                [r["frac_same_direction"] for r in rows])), 4),
            "mean_abs_conviction_delta": round(float(np.mean(
                [r["mean_abs_conviction_delta"] for r in rows])), 4),
        }

    s0, s07 = summarize(out["t0"]), summarize(out["t07"])
    result = {
        "probe": "repeat-probe (PREREG §6, prediction N6)",
        "model_id": MODEL, "n_slates_probed": len(sub),
        "repeats_per_setting": args.repeats,
        "temperature_0": s0, "temperature_0.7": s07,
        "N6_temp0_ge_90pct_identical": (
            None if not s0.get("n_pairs")
            else bool(s0["mean_frac_same_direction"] >= 0.90)),
        "N6_temp07_ge_15pct_flipped": (
            None if not s07.get("n_pairs")
            else bool(s07["mean_frac_flipped"] >= 0.15)),
        "note": ("Probe calls carry a nonce, occupy separate cache keys, and "
                 "never enter the graded books."),
        "spend": guard.as_dict(), "cache": cache.stats(),
    }
    (RUN_DIR / "REPEAT_PROBE.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
