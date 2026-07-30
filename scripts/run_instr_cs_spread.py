"""INSTR-CS-SPREAD — one shot. Protocol: TRIALS/INSTR-CS-SPREAD.md (frozen ab3fa49).

Corwin-Schultz (JF 2012) high-low spread from the P0 daily CRSP pull, compared
against the Kyle-Obizhaeva half-spread frame on the same name-months.

Usage:  .venv\\Scripts\\python -m scripts.run_instr_cs_spread
"""

from __future__ import annotations

import glob
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import segment_mask

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cs_spread")

K = 3.0 - 2.0 * np.sqrt(2.0)
MIN_PAIRS = 10                       # frozen: min valid daily pairs per name-month
ERAS = [("2004-2010", "2004-01-01", "2010-12-31"),
        ("2011-2018", "2011-01-01", "2018-12-31"),
        ("2019-2024", "2019-01-01", "2024-12-31")]


def corwin_schultz_monthly() -> pd.DataFrame:
    """[month x sym] one-way CS half-spread in bps, from data/wrds_raw/dsf_full."""
    files = sorted(glob.glob(str(MODULE_ROOT / "data" / "wrds_raw" / "dsf_full"
                                 / "dsf_*.parquet")))
    if not files:
        raise RuntimeError("no dsf_full files — run scripts.fetch_wrds_p0 first")

    out = []
    for f in files:
        d = pd.read_parquet(f, columns=["permno", "date", "askhi", "bidlo"])
        # CRSP arrives in pandas nullable dtypes; NA propagates into numpy
        # comparisons ambiguously, so cast to plain float64/int64 up front.
        d["hi"] = pd.to_numeric(d["askhi"], errors="coerce").astype("float64").abs()
        d["lo"] = pd.to_numeric(d["bidlo"], errors="coerce").astype("float64").abs()
        d["permno"] = pd.to_numeric(d["permno"], errors="coerce").astype("int64")
        d = d[(d["hi"] > 0) & (d["lo"] > 0) & (d["hi"] >= d["lo"])]
        d = d.sort_values(["permno", "date"])

        g = d.groupby("permno", sort=False)
        hi_n = g["hi"].shift(-1).to_numpy(dtype="float64", na_value=np.nan)
        lo_n = g["lo"].shift(-1).to_numpy(dtype="float64", na_value=np.nan)
        # consecutive-day requirement: next row must be the same permno
        same = g["permno"].shift(-1).notna().to_numpy()
        hi_t = d["hi"].to_numpy(dtype="float64")
        lo_t = d["lo"].to_numpy(dtype="float64")

        # frozen overnight-gap adjustment (part of the published method)
        gap_up = np.where(np.isnan(lo_n), False, lo_n > hi_t)
        gap_dn = np.where(np.isnan(hi_n), False, hi_n < lo_t)
        adj_up = np.where(gap_up, lo_n - hi_t, 0.0)
        adj_dn = np.where(gap_dn, lo_t - hi_n, 0.0)
        hi_n2 = hi_n - adj_up + adj_dn
        lo_n2 = lo_n - adj_up + adj_dn

        with np.errstate(divide="ignore", invalid="ignore"):
            ok = same & np.isfinite(hi_n2) & (lo_n2 > 0) & (hi_n2 >= lo_n2)
            beta = np.log(hi_t / lo_t) ** 2 + np.log(hi_n2 / lo_n2) ** 2
            gamma = np.log(np.maximum(hi_t, hi_n2) / np.minimum(lo_t, lo_n2)) ** 2
            alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / K - np.sqrt(gamma / K)
            s = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
        s = np.where(ok, s, np.nan)
        s = np.clip(s, 0.0, None)                   # frozen negative->zero rule

        tmp = pd.DataFrame({
            "permno": d["permno"].to_numpy(),
            "m": d["date"].dt.to_period("M").dt.to_timestamp("M").to_numpy(),
            "s": s})
        agg = tmp.dropna(subset=["s"]).groupby(["m", "permno"])["s"].agg(["mean", "size"])
        agg = agg[agg["size"] >= MIN_PAIRS]
        out.append(agg["mean"].rename("s").reset_index())
        log.info("%s: %d name-months", Path(f).stem, len(agg))

    allm = pd.concat(out, ignore_index=True)
    allm["sym"] = allm["permno"].astype(int).astype(str)
    allm["half_bps"] = allm["s"] * 1e4 / 2.0        # one-way half-spread, KO convention
    return allm.pivot_table(index="m", columns="sym", values="half_bps", aggfunc="last")


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    ko = build_spread_frame(panel)
    cs = corwin_schultz_monthly().reindex(index=panel.monthly_ret.index,
                                          columns=panel.monthly_ret.columns)
    log.info("CS frame: mean monthly coverage %.0f names", cs.notna().sum(axis=1).mean())

    res: dict = {"instrument": "INSTR-CS-SPREAD", "min_pairs": MIN_PAIRS, "by_cell": {}}
    elig = panel.eligible()
    pooled_cs, pooled_ko = [], []

    print(f"\n{'segment':9s} {'era':10s} {'CS med':>8s} {'KO med':>8s} "
          f"{'ratio':>7s} {'spearman':>9s} {'n':>10s}")
    for seg in ("largemid", "small"):
        mask = elig & segment_mask(panel, seg)
        for era, lo, hi in ERAS:
            m = mask.loc[lo:hi]
            a = cs.loc[lo:hi].where(m).stack().dropna()
            b = ko.loc[lo:hi].where(m).stack().dropna()
            idx = a.index.intersection(b.index)
            a, b = a.loc[idx], b.loc[idx]
            if len(a) < 1000:
                continue
            rho = float(pd.Series(a.values).corr(pd.Series(b.values), method="spearman"))
            cell = {"cs_median_bps": round(float(a.median()), 2),
                    "ko_median_bps": round(float(b.median()), 2),
                    "ratio_cs_over_ko": round(float(a.median() / b.median()), 3),
                    "spearman": round(rho, 3), "n": int(len(a))}
            res["by_cell"][f"{seg}_{era}"] = cell
            pooled_cs.append(a); pooled_ko.append(b)
            print(f"{seg:9s} {era:10s} {cell['cs_median_bps']:8.2f} "
                  f"{cell['ko_median_bps']:8.2f} {cell['ratio_cs_over_ko']:7.3f} "
                  f"{cell['spearman']:9.3f} {cell['n']:10,d}")

    pc, pk = pd.concat(pooled_cs), pd.concat(pooled_ko)
    pooled_rho = float(pd.Series(pc.values).corr(pd.Series(pk.values), method="spearman"))
    res["pooled_spearman"] = round(pooled_rho, 3)
    res["pooled_n"] = int(len(pc))

    seg_ratio = {}
    for seg in ("largemid", "small"):
        cells = [v for k, v in res["by_cell"].items() if k.startswith(seg)]
        if cells:
            seg_ratio[seg] = round(float(np.median([c["ratio_cs_over_ko"] for c in cells])), 3)
            res[f"{seg}_cs_median_bps"] = round(
                float(np.median([c["cs_median_bps"] for c in cells])), 2)
    res["segment_ratio"] = seg_ratio

    # ── frozen gates ─────────────────────────────────────────────────────────
    lm, sm = res.get("largemid_cs_median_bps"), res.get("small_cs_median_bps")
    sanity = (lm is not None and sm is not None
              and 1 <= lm <= 100 and 1 <= sm <= 100 and sm > lm)
    primary = pooled_rho >= 0.30
    level = all(0.5 <= r <= 2.0 for r in seg_ratio.values())
    res.update({"gate_sanity": bool(sanity), "gate_primary_rank": bool(primary),
                "gate_level": bool(level)})

    if not sanity:
        verdict = "SANITY GATE FAILED — estimator misimplemented, nothing downstream readable"
    elif not primary:
        verdict = "NO CONCLUSION about KO — the two estimators disagree on ranking"
    elif level:
        verdict = "KO VALIDATED — empty cost-killed cohort rests on a cross-checked ruler"
    elif all(r > 2.0 for r in seg_ratio.values()):
        verdict = "KO UNDERSTATES COSTS — NEG_RESULTS 22 must be re-derived under CS"
    elif any(r > 2.0 for r in seg_ratio.values()):
        verdict = ("KO UNDERSTATES COSTS IN " +
                   ",".join(s for s, r in seg_ratio.items() if r > 2.0).upper() +
                   " — that segment's cohort must be re-derived")
    else:
        verdict = "KO OVERSTATES COSTS — empty-cohort conclusion strengthens"
    res["verdict"] = verdict

    print(f"\npooled Spearman {pooled_rho:.3f} (n={len(pc):,})  |  segment CS/KO {seg_ratio}")
    print(f"gates: sanity={sanity} primary={primary} level={level}")
    print(f"\nVERDICT: {verdict}")

    (MODULE_ROOT / "data" / "factory" / "instr_cs_spread.json").write_text(
        json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
