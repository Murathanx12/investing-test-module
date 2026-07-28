"""AUDIT-CIK-BRIDGE — data-quality profile of the CIK<->permno bridge.

Binding: `aegis-finance docs/research/AI_PANEL_2026-07-28.md` §3.1 (from §1 row
2.2). REPORTED-NEVER-DECIDING. This audit moves no bar, opens no gate and cannot
kill or graduate anything; it exists so the TEXT-LAZY explore result is read next
to an honest statement of WHICH names the bridge can see.

The question is NOT "is coverage high" (it is 88.5% of universe permnos). It is
"are the names the bridge MISSES random, or are they concentrated in the small
and the dead?" — because the small segment is where TEXT-LAZY's live shot is, and
a bridge that quietly drops dead micro names would flatter any long-only result
exactly the way survivorship bias does.

One correction to the review that requested this, recorded in the panel doc: the
bridge is ALREADY built survivorship-neutral (CRSP historical name rows x EDGAR
`cik-lookup-data.txt`, which carries every former name a CIK ever filed under;
SEC's `company_tickers.json` current-filer snapshot was explicitly rejected).
This audit VERIFIES that property empirically rather than adding it.

Usage: .venv\\Scripts\\python -m scripts.audit_cik_bridge
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.events.name_link import cik_permno_windows

PANEL_DIR = MODULE_ROOT / "data" / "crsp_panel_2002"
OUT = MODULE_ROOT / "runs" / "AUDIT-CIK-BRIDGE"

# CRSP delisting codes 500 and 520-584 are the performance/liquidity ("bad")
# deaths; 200s are mergers/acquisitions. Only a terminal row carries a code.
_BAD_DELIST = {500} | set(range(520, 585))


def _size_decile(panel) -> pd.Series:
    """Per-permno size bucket = decile of its median monthly dollar volume over
    its own live months. Dollar volume (not market cap) because it is the
    factory's OWN segmentation variable — `explore.segment_mask` ranks on it, so
    this is the axis on which a coverage hole would actually distort a scan."""
    med = panel.monthly_dollar_vol.median(axis=0, skipna=True).dropna()
    med = med[med > 0]
    # decile 1 = smallest, 10 = largest
    return pd.Series(
        pd.qcut(med.rank(method="first"), 10, labels=range(1, 11)).astype(int),
        index=med.index, name="size_decile",
    )


def _died_in_panel(panel) -> pd.Series:
    """True if the permno's return series ENDS before the panel does.

    Primary delist proxy on purpose: `crsp_msf.dlstcd` is populated on only 4,724
    of 1.1M rows in this pull (terminal stamps, and incomplete), so keying the
    audit to it would itself be a coverage-biased measurement. Panel death is
    complete, survivorship-neutral, and is the property that matters here.
    """
    ret = panel.monthly_ret
    last_month = ret.index[-1]
    alive = ret.notna()
    last_alive = alive.apply(lambda c: ret.index[np.where(c.values)[0][-1]]
                             if c.any() else pd.NaT)
    return (last_alive < last_month).rename("died_in_panel")


def _bad_delists() -> set[str]:
    msf = pd.read_parquet(MODULE_ROOT / "data" / "wrds_raw" / "crsp_msf.parquet",
                          columns=["permno", "dlstcd"]).dropna(subset=["dlstcd"])
    bad = msf[msf["dlstcd"].astype(int).isin(_BAD_DELIST)]
    return set(bad["permno"].astype(int).astype(str))


def _profile(df: pd.DataFrame, by: str) -> pd.DataFrame:
    g = df.groupby(by, observed=True)
    out = pd.DataFrame({
        "n_universe": g.size(),
        "n_bridged": g["bridged"].sum(),
    })
    out["coverage"] = (out["n_bridged"] / out["n_universe"]).round(4)
    return out.reset_index()


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(PANEL_DIR)

    bridge = cik_permno_windows()
    bridged_permnos = set(bridge["permno"].astype(int).astype(str))

    universe = pd.Index(panel.monthly_ret.columns, name="permno")
    dec = _size_decile(panel)
    died = _died_in_panel(panel)

    df = pd.DataFrame(index=universe)
    df["bridged"] = df.index.isin(bridged_permnos)
    df["size_decile"] = dec.reindex(df.index)
    df["died_in_panel"] = died.reindex(df.index).fillna(False)
    df = df[df["size_decile"].notna()].copy()
    df["size_decile"] = df["size_decile"].astype(int)

    bad = _bad_delists()
    df["bad_delist"] = df.index.isin(bad)

    by_decile = _profile(df, "size_decile")
    by_death = _profile(df, "died_in_panel")
    by_bad = _profile(df, "bad_delist")
    cross = (df.groupby(["died_in_panel", "size_decile"], observed=True)["bridged"]
             .agg(["size", "sum"]).reset_index()
             .rename(columns={"size": "n_universe", "sum": "n_bridged"}))
    cross["coverage"] = (cross["n_bridged"] / cross["n_universe"]).round(4)

    overall = float(df["bridged"].mean())
    spread_decile = float(by_decile["coverage"].max() - by_decile["coverage"].min())
    cov_dead = float(df.loc[df["died_in_panel"], "bridged"].mean())
    cov_alive = float(df.loc[~df["died_in_panel"], "bridged"].mean())
    cov_small = float(df.loc[df["size_decile"] <= 3, "bridged"].mean())
    cov_large = float(df.loc[df["size_decile"] >= 8, "bridged"].mean())

    # bridge-side multiplicity (the "ambiguous" mechanism, measured at the bridge
    # rather than per filing): how often does one CIK reach several permnos?
    per_cik = bridge.groupby("cik")["permno"].nunique()
    per_permno = bridge.groupby("permno")["cik"].nunique()

    # per-filing ambiguity actually incurred by the two round-12 pulls
    filing_reports = {}
    for tag, path in (("text_lazy", MODULE_ROOT / "data" / "events" / "lazy_link_report.json"),
                      ("text_lazy_run", MODULE_ROOT / "runs" / "TRIAL-TEXT-LAZY" / "results_explore.json"),
                      ("event_8k", MODULE_ROOT / "runs" / "TRIAL-EVENT-8K-FILTER" / "results_explore.json")):
        if path.exists():
            try:
                blob = json.loads(path.read_text())
                filing_reports[tag] = blob.get("link_report", blob.get("link", blob))
            except Exception:
                filing_reports[tag] = "unreadable"

    out = {
        "audit": "AUDIT-CIK-BRIDGE",
        "binding": "AI_PANEL_2026-07-28.md §3.1 (row 2.2) — reported, never deciding",
        "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "universe_permnos": int(len(df)),
        "coverage_overall": round(overall, 4),
        "coverage_by_size_decile": by_decile.to_dict("records"),
        "coverage_by_panel_death": by_death.to_dict("records"),
        "coverage_by_bad_delist_code": by_bad.to_dict("records"),
        "coverage_cross_death_x_decile": cross.to_dict("records"),
        "headline_gaps": {
            "decile_coverage_spread": round(spread_decile, 4),
            "coverage_dead_names": round(cov_dead, 4),
            "coverage_surviving_names": round(cov_alive, 4),
            "dead_minus_alive": round(cov_dead - cov_alive, 4),
            "coverage_deciles_1_3": round(cov_small, 4),
            "coverage_deciles_8_10": round(cov_large, 4),
            "small_minus_large": round(cov_small - cov_large, 4),
        },
        "bridge_multiplicity": {
            "n_bridge_rows": int(len(bridge)),
            "n_ciks": int(bridge["cik"].nunique()),
            "n_permnos": int(bridge["permno"].nunique()),
            "ciks_reaching_multiple_permnos": int((per_cik > 1).sum()),
            "permnos_reached_by_multiple_ciks": int((per_permno > 1).sum()),
            "pct_ciks_multi": round(float((per_cik > 1).mean()), 4),
        },
        "per_filing_link_reports": filing_reports,
        "elapsed_s": round(time.time() - t0, 1),
    }
    (OUT / "results.json").write_text(json.dumps(out, indent=2, default=str))

    print(json.dumps(out["headline_gaps"], indent=2))
    print("\ncoverage by size decile (1=smallest):")
    print(by_decile.to_string(index=False))
    print("\ncoverage by panel death:")
    print(by_death.to_string(index=False))
    print("\nbridge multiplicity:", json.dumps(out["bridge_multiplicity"], indent=2))
    print(f"\nwrote {OUT / 'results.json'}")


if __name__ == "__main__":
    main()
