"""TRIAL-EXT-COMPOSITE-1 — EW-209 and THEME-13 composites + sign-scramble null.

Pre-registered: TRIALS/PREREG_EXT_BANK_1.md (frozen before M4 scoring).
Explore window ONLY, both segments. One shot per arm.

Design (frozen):
  EW-209   equal-weight of per-month cross-sectional pct-ranks of all 209
           OSAP signals, each multiplied by its source-paper sign.
  THEME-13 signals averaged within Chen-Zimmermann category first, then
           categories equal-weighted. Declared: THEME-13 t_net >= EW-209.
  NULL     K=200 composites from the identical rank frames with coin-flip
           signs (seed 20260808): preserves all correlation structure,
           destroys published information. Real composite t_ic and t_net
           scored as empirical p against this null; floored by the
           REAL-NULL-2 persistent CDF for t_ic.
  Predictions: composite one-way turnover < 0.10/mo (netting mechanism).
  KILL: fails empirical-p vs own scramble null, OR net t < 1.5 in both
  segments, OR turnover > 0.20/mo.

Rank frames are cached to data/osap/rank_cache/ (float32, one .npy per
signal) so the null passes stream from disk instead of re-pivoting 5.4M rows.

Run:  python scripts/run_ext_composite_1.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.calibration.replay2_eval import empirical_p
from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.osap import ScoreGridder, load_doc, meta_table
from aegis_brain.factory.signals import FactorySignal

K_NULL = 200
SEED = 20260808
SEGMENTS = ("largemid", "small")
OUT = MODULE_ROOT / "runs" / "EXT-BANK-1"
CACHE = MODULE_ROOT / "data" / "osap" / "rank_cache"
PARQUET = MODULE_ROOT / "data" / "osap" / "firm_char.parquet"


def build_rank_cache(panel) -> tuple[list[str], dict[str, str], np.ndarray]:
    """Cache per-signal signed-agnostic pct-rank frames (float32 .npy).
    Returns (acronyms, category-by-acronym, coverage count frame)."""
    cols = json.loads((MODULE_ROOT / "data" / "osap" /
                       "_wide_cols.json").read_text("utf-8"))
    cols = cols if isinstance(cols, list) else cols["columns"]
    acros = [c for c in cols if c not in ("permno", "yyyymm")]
    doc = meta_table(load_doc())
    meta = {m.acronym: m for m in doc}
    missing_doc = [a for a in acros if a not in meta]
    if missing_doc:
        raise SystemExit(f"doc rows missing for {missing_doc[:5]} — refusing")
    cats = {a: meta[a].category for a in acros}
    signs = {a: meta[a].sign for a in acros}

    CACHE.mkdir(parents=True, exist_ok=True)
    shape = panel.monthly_ret.shape
    count = np.zeros(shape, dtype="int16")
    todo = [a for a in acros if not (CACHE / f"{a}.npy").exists()]
    print(f"rank cache: {len(acros) - len(todo)} cached, {len(todo)} to build")
    for i, a in enumerate(todo):
        d = pd.read_parquet(PARQUET, columns=["permno", "yyyymm", a])
        g = ScoreGridder(d, panel)
        frame = g.grid(d[a])
        ranks = frame.rank(axis=1, pct=True).to_numpy(dtype="float32")
        np.save(CACHE / f"{a}.npy", ranks)
        if (i + 1) % 20 == 0:
            print(f"  cached {i+1}/{len(todo)}", flush=True)
    for a in acros:
        count += ~np.isnan(np.load(CACHE / f"{a}.npy"))
    (CACHE / "_signs.json").write_text(json.dumps(signs), encoding="utf-8")
    return acros, cats, count


def composite_from_signs(acros: list[str], signs: dict[str, int],
                         count: np.ndarray) -> np.ndarray:
    """Signed mean of cached pct-ranks; cells with no coverage stay NaN.
    Ranks are centered at 0.5 so a −1 sign is (1 − rank), i.e. the mirror."""
    acc = np.zeros(count.shape, dtype="float64")
    for a in acros:
        r = np.load(CACHE / f"{a}.npy").astype("float64")
        v = r if signs[a] > 0 else (1.0 - r)
        acc += np.nan_to_num(v, nan=0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = acc / count
    out[count == 0] = np.nan
    return out


def scan_composite(name: str, mat: np.ndarray, panel, seg: str,
                   cost_frame=None) -> dict:
    frame = pd.DataFrame(mat, index=panel.monthly_ret.index,
                         columns=panel.monthly_ret.columns)
    sig = FactorySignal(name, "composite", lambda p, _f=frame: _f, +1)
    return scan_signal(panel, sig, seg, ScanConfig(),
                       cost_frame=cost_frame)["summary"]


def main() -> None:
    out_file = OUT / "trial_ext_composite_1.json"
    if out_file.exists():
        raise SystemExit(f"{out_file} exists — one shot; rerun = new trial ID")
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    acros, cats, count = build_rank_cache(panel)
    signs = {a: (1 if s > 0 else -1) for a, s in json.loads(
        (CACHE / "_signs.json").read_text("utf-8")).items()}

    floors = {}
    for seg in SEGMENTS:
        meta = json.loads((MODULE_ROOT / "runs" / "REPLAY-2" /
                           f"real_null_2_{seg}_meta.json").read_text("utf-8"))
        if meta.get("status") != "OK":
            raise SystemExit(f"REAL-NULL-2 {seg} not OK — floor uncertified")
        with np.load(MODULE_ROOT / "runs" / "REPLAY-2" /
                     f"real_null_2_{seg}.npz") as z:
            floors[seg] = np.sort(z["pooled_t_explore"])

    ko = build_spread_frame(panel)
    results: dict = {"trial": "TRIAL-EXT-COMPOSITE-1", "k_null": K_NULL,
                     "seed": SEED, "n_signals": len(acros), "arms": {}}

    # ---- real arms ---------------------------------------------------------
    ew = composite_from_signs(acros, signs, count)
    by_cat: dict[str, list[str]] = {}
    for a in acros:
        by_cat.setdefault(cats[a], []).append(a)
    theme_acc = np.zeros(count.shape, dtype="float64")
    theme_n = np.zeros(count.shape, dtype="int16")
    for c, members in by_cat.items():
        ccount = np.zeros(count.shape, dtype="int16")
        for a in members:
            ccount += ~np.isnan(np.load(CACHE / f"{a}.npy"))
        cmat = composite_from_signs(members, signs, ccount)
        good = ~np.isnan(cmat)
        theme_acc[good] += cmat[good]
        theme_n += good
    with np.errstate(invalid="ignore", divide="ignore"):
        theme = theme_acc / theme_n
    theme[theme_n == 0] = np.nan
    print(f"themes: {len(by_cat)} categories")

    for arm_name, mat in (("EW209", ew), ("THEME", theme)):
        for seg in SEGMENTS:
            flat = scan_composite(f"{arm_name}_{seg}", mat, panel, seg)
            koh = scan_composite(f"{arm_name}_{seg}_ko", mat, panel, seg,
                                 cost_frame=ko)
            results["arms"][f"{arm_name}/{seg}"] = {
                "t_ic": flat["t_ic"], "t_net_flat25": flat["t_excess_net"],
                "t_net_ko_half": koh["t_excess_net"],
                "t_gross": flat["t_excess_gross"],
                "turnover_1way": flat["turnover_1way"],
                "months": flat["months"],
                "p_t_ic_vs_floor": round(
                    empirical_p(flat["t_ic"], floors[seg]), 5)}
            print(arm_name, seg, json.dumps(results["arms"][f"{arm_name}/{seg}"]))

    # ---- sign-scramble null ------------------------------------------------
    rng = np.random.default_rng(SEED)
    null_t_ic = {s: [] for s in SEGMENTS}
    null_t_net = {s: [] for s in SEGMENTS}
    for k in range(K_NULL):
        ssigns = {a: int(rng.choice((-1, 1))) for a in acros}
        mat = composite_from_signs(acros, ssigns, count)
        for seg in SEGMENTS:
            s = scan_composite(f"null{k}_{seg}", mat, panel, seg)
            null_t_ic[seg].append(s["t_ic"])
            null_t_net[seg].append(s["t_excess_net"])
        if (k + 1) % 10 == 0:
            print(f"  null {k+1}/{K_NULL}", flush=True)

    results["null"] = {
        seg: {"t_ic": null_t_ic[seg], "t_net": null_t_net[seg]}
        for seg in SEGMENTS}
    for arm_name in ("EW209", "THEME"):
        for seg in SEGMENTS:
            r = results["arms"][f"{arm_name}/{seg}"]
            r["p_t_ic_vs_scramble"] = round(empirical_p(
                r["t_ic"], np.sort(np.array(null_t_ic[seg]))), 4)
            r["p_t_net_vs_scramble"] = round(empirical_p(
                r["t_net_flat25"], np.sort(np.array(null_t_net[seg]))), 4)

    # frozen kill rules
    verdict = {}
    for arm_name in ("EW209", "THEME"):
        rs = [results["arms"][f"{arm_name}/{s}"] for s in SEGMENTS]
        scramble_pass = any(min(r["p_t_ic_vs_scramble"],
                                r["p_t_net_vs_scramble"]) <= 0.05 for r in rs)
        net_pass = any(r["t_net_flat25"] >= 1.5 for r in rs)
        turn_ok = all(r["turnover_1way"] <= 0.20 for r in rs)
        pred_netting = all(r["turnover_1way"] < 0.10 for r in rs)
        verdict[arm_name] = {
            "scramble_pass": scramble_pass, "net_pass": net_pass,
            "turnover_ok": turn_ok,
            "prediction_turnover_lt_010": pred_netting,
            "KILLED": not (scramble_pass and net_pass and turn_ok)}
    verdict["declared_THEME_ge_EW209"] = bool(
        max(results["arms"]["THEME/largemid"]["t_net_flat25"],
            results["arms"]["THEME/small"]["t_net_flat25"])
        >= max(results["arms"]["EW209/largemid"]["t_net_flat25"],
               results["arms"]["EW209/small"]["t_net_flat25"]))
    results["verdict"] = verdict

    OUT.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(verdict, indent=2))
    print(f"written -> {out_file}")


if __name__ == "__main__":
    main()
