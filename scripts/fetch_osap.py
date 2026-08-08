"""One-shot local materialisation of the OSAP firm-level signal panel.

Chen & Zimmermann (2022), Critical Finance Review 11(2), 207-264.
https://www.openassetpricing.com/

Writes:
    data/osap/firm_char.parquet    all downloadable firm-level signals
    data/osap/signal_doc.parquet   the 331-row documentation table
    data/osap/availability.json    which documented acronyms actually arrived

Rationale for caching rather than calling the API per scan: the openassetpricing
endpoints 503 intermittently, and an FDR measurement that silently scans a
network-truncated signal set is exactly the NEGATIVE_RESULTS 5 failure mode.
Download once, assert coverage, never touch the network during a scan.

The `openassetpricing` package is used here as an OFFLINE ETL TOOL ONLY. The
OSAP code repository is GPL-2.0; nothing from it is vendored, and no shipped
module imports this package at runtime.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

MODULE_ROOT = Path(__file__).resolve().parents[1]
OUT = MODULE_ROOT / "data" / "osap"


def main() -> None:
    import openassetpricing as oap

    OUT.mkdir(parents=True, exist_ok=True)
    o = oap.OpenAP()

    print("[1/3] signal documentation ...", flush=True)
    doc = o.dl_signal_doc("polars")
    doc.write_parquet(OUT / "signal_doc.parquet")
    print(f"      {doc.height} documented signals", flush=True)

    print("[2/3] full firm-level panel (this is the long one) ...", flush=True)
    df = o.dl_all_signals("polars")
    print(f"      {df.height:,} rows x {df.width} cols", flush=True)
    df.write_parquet(OUT / "firm_char.parquet")

    print("[3/3] availability reconciliation ...", flush=True)
    keys = {"permno", "yyyymm"}
    got = [c for c in df.columns if c not in keys]
    documented = doc.select("Acronym", "Cat.Signal").to_dicts()

    by_cat: dict[str, dict[str, list[str]]] = {}
    for row in documented:
        cat, acr = row["Cat.Signal"], row["Acronym"]
        b = by_cat.setdefault(cat, {"available": [], "missing": []})
        b["available" if acr in got else "missing"].append(acr)

    report = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Chen & Zimmermann (2022), openassetpricing.com",
        "rows": int(df.height),
        "columns_downloaded": len(got),
        "yyyymm_min": int(df["yyyymm"].min()),
        "yyyymm_max": int(df["yyyymm"].max()),
        "by_category": {
            k: {"n_documented": len(v["available"]) + len(v["missing"]),
                "n_available": len(v["available"]),
                "available": sorted(v["available"]),
                "missing": sorted(v["missing"])}
            for k, v in by_cat.items()},
        "undocumented_columns": sorted(
            set(got) - {r["Acronym"] for r in documented}),
    }
    (OUT / "availability.json").write_text(json.dumps(report, indent=2),
                                           encoding="utf-8")
    for cat, v in report["by_category"].items():
        print(f"      {cat:10s} {v['n_available']:4d} / {v['n_documented']:4d} "
              f"available at firm level", flush=True)
    print(f"written -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
