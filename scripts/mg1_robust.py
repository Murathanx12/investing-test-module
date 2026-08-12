"""MARKET-GRAPH-1 stage 6 — the two audits the prereg did not ask for.

WHY THIS EXISTS
===============
The five mandatory controls all ran and the semantic arm survived all five.
That is necessary and it is not sufficient, because none of the five closes the
one hole a sceptical reader will find first:

    `has_edge` is not spread evenly over the pair distribution. Edge-carrying
    pairs are 54.9% same-sector against 11.5% of pairs overall, and they sit at
    systematically higher trailing correlation. The baseline is a ridge on
    `rho_trail`, `rho_trail^2` and `same_sector`. If the true relation between
    trailing and forward correlation is more curved than a quadratic, then ANY
    variable that happens to be concentrated at high `rho_trail` will pick up
    the leftover curvature and look informative.

Neither placebo tests that. Node-label shuffling moves edges to pairs with a
DIFFERENT `rho_trail`; random edges are drawn uniformly. Both destroy the
concentration along with the relationships, so both would come out null whether
the effect is real or is baseline misspecification. Two arms close it:

**A. Flexible baseline.** Replace `rho_trail + rho_trail^2` with nine
   within-date decile dummies. Ten free levels is fully flexible in trailing
   correlation up to the decile grid, so there is no smooth curvature left for
   the semantic block to absorb. If dR^2 survives, misspecification is not the
   explanation.

**B. Stratified placebo.** Permute the edge labels among pairs WITHIN each
   (cut date x same-sector x rho_trail decile) cell. This is the placebo the
   other two are not: it reproduces the real edge set's position in the pair
   distribution EXACTLY — same count, same sector mix, same trailing-correlation
   decile profile — and destroys only WHICH pair inside the cell carries the
   edge. Anything it still finds is structure, not relationships.

If A survives and B is null, the headline is about the relationships. If A
collapses, the headline was about the shape of the baseline and the trial
should say so in those words.

    python -m scripts.mg1_robust
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT                       # noqa: E402
from scripts import mg1_config as C                              # noqa: E402
from scripts.mg1_grade import (BASE_FEATS, SEM_FEATS,            # noqa: E402
                               attach, edge_features, h2,
                               walk_forward)

OUT = MODULE_ROOT / "runs" / "MARKET-GRAPH-1"


def stratified_placebo(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Permute the semantic block within (date, same_sector, trail_decile).

    The edge count, the sector mix and the trailing-correlation profile of the
    placebo graph are IDENTICAL to the real one by construction — cell by cell,
    not just on average. Only the identity of the pair changes.
    """
    rng = np.random.default_rng(seed)
    out = df.copy()
    cols = SEM_FEATS
    vals = out[cols].to_numpy(dtype=np.float64)
    idx = np.arange(len(out))
    key = (out["date"].astype("int64").to_numpy(),
           out["same_sector"].to_numpy(),
           out["trail_decile"].to_numpy())
    order = np.lexsort(key)
    ks = np.column_stack([k[order] for k in key])
    # boundaries of each (date, same_sector, decile) run
    change = np.any(ks[1:] != ks[:-1], axis=1)
    bounds = np.concatenate([[0], np.where(change)[0] + 1, [len(order)]])
    new = vals.copy()
    for a, b in zip(bounds[:-1], bounds[1:]):
        cell = order[a:b]
        if len(cell) < 2:
            continue
        new[cell] = vals[cell[rng.permutation(len(cell))]]
    out[cols] = new
    assert len(out) == len(df)
    del idx
    return out


def decile_baseline(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Nine within-date decile dummies + same_sector. Fully flexible in rho."""
    out = df.copy()
    names = []
    d = out["trail_decile"].to_numpy()
    for k in range(1, 10):                    # decile 0 is the reference level
        c = f"dec_{k}"
        out[c] = (d == k).astype(float)
        names.append(c)
    names.append("same_sector")
    return out, names


def main() -> None:
    t0 = time.time()
    uni = pd.read_parquet(OUT / "universe.parquet")
    uni["date"] = pd.to_datetime(uni["date"])
    pairs = pd.read_parquet(OUT / "pairs.parquet")
    pairs["date"] = pd.to_datetime(pairs["date"])
    pairs["lo"] = np.minimum(pairs["permno_i"], pairs["permno_j"])
    pairs["hi"] = np.maximum(pairs["permno_i"], pairs["permno_j"])
    pairs["rho_trail"] = pairs["rho_trail"].astype(float)
    pairs["rho_trail2"] = pairs["rho_trail"] ** 2
    pairs["same_sector"] = pairs["same_sector"].astype(float)
    pairs["rho_fwd"] = pairs["rho_fwd"].astype(float)

    inst = pd.read_parquet(OUT / "edge_instances.parquet")
    inst["date"] = pd.to_datetime(inst["date"])
    dates = sorted(pairs["date"].unique())
    df = attach(pairs, edge_features(inst))
    print(f"pairs {len(df):,}; edge coverage "
          f"{(df['has_edge'] > 0).mean():.4%}", flush=True)

    # the concentration this module exists to neutralise, stated as a number
    on = df[df["has_edge"] > 0]
    print(f"edge pairs: same_sector {on['same_sector'].mean():.1%} "
          f"(all pairs {df['same_sector'].mean():.1%}); "
          f"mean rho_trail {on['rho_trail'].mean():.4f} "
          f"(all pairs {df['rho_trail'].mean():.4f}); "
          f"mean decile {on['trail_decile'].mean():.2f} (all 4.5)", flush=True)

    rep: dict = {"run_utc": pd.Timestamp.utcnow().isoformat(),
                 "concentration": {
                     "edge_same_sector": float(on["same_sector"].mean()),
                     "all_same_sector": float(df["same_sector"].mean()),
                     "edge_mean_rho_trail": float(on["rho_trail"].mean()),
                     "all_mean_rho_trail": float(df["rho_trail"].mean()),
                     "edge_mean_decile": float(on["trail_decile"].mean())},
                 "arms": {}}

    dfd, DEC = decile_baseline(df)
    plac = stratified_placebo(df, C.SEED_SHUFFLE + 7)
    placd, _ = decile_baseline(plac)

    # sanity: the placebo must match the real graph cell by cell
    a = df.groupby(["date", "same_sector", "trail_decile"])["has_edge"].sum()
    b = plac.groupby(["date", "same_sector", "trail_decile"])["has_edge"].sum()
    ok = bool((a.reindex(b.index).fillna(0) == b).all())
    print(f"stratified placebo preserves every cell count: {ok}", flush=True)
    rep["placebo_cell_counts_identical"] = ok
    if not ok:
        raise SystemExit("stratified placebo did not preserve cell counts")

    jobs = [
        ("A_real_quadratic_baseline", df, BASE_FEATS, 0),
        ("A_real_decile_baseline", dfd, DEC, 0),
        ("B_stratified_placebo_quadratic", plac, BASE_FEATS, 0),
        ("B_stratified_placebo_decile", placd, DEC, 0),
        # C: purged. Quarterly cut dates with a two-quarter label window mean
        # the most recent training date's outcome reaches into the test
        # window. Dropping two dates removes the overlap outright.
        ("C_real_purged2_quadratic", df, BASE_FEATS, 2),
        ("C_real_purged2_decile", dfd, DEC, 2),
        ("C_stratified_placebo_purged2", plac, BASE_FEATS, 2),
    ]
    for name, frame, base, purge in jobs:
        r = walk_forward(frame, base, SEM_FEATS, dates, purge=purge)
        rep["arms"][name] = r
        print(f"\n=== {name} ===")
        print(f"  dR^2 {r['delta_r2']:.3e}  MDE {r['delta_r2_mde']:.3e}  "
              f"t {r['t']:.3g}  detectable {r['detectable']}  "
              f"(baseline OOS R^2 {r['r2_base_oos']:.4f})")
        oe = r["on_edge_pairs"]
        print(f"  on-edge MSE reduction {oe['mse_reduction_pct']:.4f}  "
              f"MDE {oe['mse_reduction_mde_pct']:.4f}  t {oe['t']:.3g}  "
              f"detectable {oe['detectable']}")

    print("\n=== H2 under the stratified placebo ===")
    rep["h2_stratified_placebo"] = h2(plac, C.SEED_H2_MATCH)
    print(json.dumps(rep["h2_stratified_placebo"], indent=2, default=str))
    rep["h2_real_for_reference"] = h2(df, C.SEED_H2_MATCH)

    rep["elapsed_min"] = round((time.time() - t0) / 60, 2)
    (OUT / "robust_report.json").write_text(
        json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote robust_report.json  ({rep['elapsed_min']} min)")


if __name__ == "__main__":
    main()
