"""MARKET-GRAPH-1 — render the report tables from the run artifacts.

Numbers in the report are PRINTED from the JSON, never retyped. Sixty
hand-copied figures is sixty chances to publish a number the run did not
produce, and a report whose numbers disagree with its own artifacts is worse
than no report.

    python -m scripts.mg1_tables > tables.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT                       # noqa: E402

OUT = MODULE_ROOT / "runs" / "MARKET-GRAPH-1"


def j(name):
    p = OUT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def f(x, n=6):
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int,)):
        return f"{x:,}"
    try:
        return f"{float(x):.{n}g}"
    except (TypeError, ValueError):
        return str(x)


def h1_row(label, r):
    if not r or "error" in r:
        return f"| {label} | — | — | — | — | — | {r.get('error') if r else 'missing'} |"
    return (f"| {label} | {r['n_dates']} | {f(r['delta_r2'], 3)} | "
            f"{f(r['delta_r2_mde'], 3)} | {f(r['t'], 3)} | "
            f"{'YES' if r['detectable'] else 'no'} | "
            f"{r['n_pairs_graded']:,} pairs |")


def h2_row(label, r, key):
    if not r or "error" in r:
        return f"| {label} | — | — | — | — | — | {r.get('error') if r else 'missing'} |"
    s = r[key]
    return (f"| {label} | {r['n_cases']:,} / {r['n_controls']:,} | "
            f"{s['n_dates']} | {f(s['mean'], 3)} | {f(s['mde'], 3)} | "
            f"{f(s['t'], 3)} | {'YES' if s['detectable'] else 'no'} |")


def main() -> None:
    ab = j("resolution_ab.json")
    rm = j("resolve_meta.json")
    pm = j("panel_meta.json")
    gr = j("grade_report.json")
    em = j("extract_meta.json")

    print("## Resolution A/B — same edge corpus, one thing moved at a time\n")
    if ab:
        print(f"documents: {ab['n_documents']:,}; legacy universe "
              f"{ab['n_legacy_universe_permnos']} permnos, rebuilt "
              f"{ab['n_rebuilt_universe_permnos']}\n")
        print("| universe | matcher | resolved / raw edges | rate |")
        print("|---|---|---|---|")
        for k, v in ab["cells"].items():
            u, m = k.split("/")
            print(f"| {u} | {m} | {v['resolved']:,} / {v['raw_edges']:,} | "
                  f"{v['rate']:.2%} |")
        print(f"\n- matcher alone: {ab['delta_from_matcher_only']:+.2%}")
        print(f"- universe alone: {ab['delta_from_universe_only']:+.2%}")
        print(f"- both: {ab['delta_total']:+.2%}")

    if rm:
        print("\n## Where the unresolved mentions go\n")
        print("| bucket | n | share of unresolved |")
        print("|---|---|---|")
        tot = sum(rm["unresolved_residue"].values())
        for k, v in rm["unresolved_residue"].items():
            print(f"| {k} | {v:,} | {v / max(1, tot):.1%} |")
        print("\n| route | edges written |")
        print("|---|---|")
        for k, v in sorted(rm["routes_widened"].items(),
                           key=lambda kv: -kv[1]):
            print(f"| {k} | {v:,} |")
        print(f"\nedge-instances live with both ends in the universe: "
              f"{rm['n_edge_instances_live']:,}; distinct (date,pair): "
              f"{rm['n_distinct_pairs_with_edge']:,}; quote-verified "
              f"{rm['quote_verified_rate']:.1%}; mean confidence "
              f"{rm['mean_confidence']:.3f}; same-sector share "
              f"{rm['same_sector_share_of_edges']:.1%}")
        print("\n| edge type | n |")
        print("|---|---|")
        for k, v in sorted(rm["by_type"].items(), key=lambda kv: -kv[1]):
            print(f"| {k} | {v:,} |")

    if pm:
        a = pm["attrition"]
        print(f"\n## Panel\n\n{pm['n_cut_dates']} cut dates "
              f"{pm['first_cut']}..{pm['last_cut']}; {pm['n_pairs']:,} "
              f"(date,pair) rows; {pm['n_distinct_permnos']} distinct permnos; "
              f"corr(rho_trail, rho_fwd) = {pm['corr_trail_fwd']:.3f}; "
              f"same-sector share of pairs {pm['same_sector_share']:.1%}; "
              f"universe document coverage "
              f"{sum(x['universe_with_doc'] for x in a) / sum(x['universe'] for x in a):.1%}")

    # Spend is read from the TELEMETRY LEDGER, not from `extract_meta.json`.
    # The first full pass was killed mid-run to fix the governor bottleneck, so
    # it never wrote its meta block: summing the meta file would under-report
    # this campaign's cost by two thirds. The ledger is written per call and
    # survives a kill, which is exactly why the governor reads it too.
    ledger = (Path(r"C:\Users\mrthn\aegis-finance") / "backend" / "data"
              / "optimus" / "llm_calls.jsonl")
    if ledger.exists():
        n = ti = tc = to = 0
        cost = 0.0
        served: dict = {}
        for line in ledger.open(encoding="utf-8", errors="replace"):
            try:
                r = json.loads(line)
            except Exception:                                  # noqa: BLE001
                continue
            if r.get("purpose") != "market_graph_1_extract":
                continue
            n += 1
            a = int(r.get("tokens_in") or 0)
            c = int(r.get("cached_tokens") or 0)
            o = int(r.get("tokens_out") or 0)
            ti, tc, to = ti + a, tc + c, to + o
            cost += a * 0.14e-6 + c * 0.0028e-6 + o * 0.28e-6
            served[r.get("model_version")] = \
                served.get(r.get("model_version"), 0) + 1
        print(f"\n## Extraction (from the telemetry ledger)\n")
        print(f"calls {n:,}; uncached input {ti:,} tok, cached {tc:,} tok "
              f"({tc / max(1, tc + ti):.1%} hit), output {to:,} tok; "
              f"**cost ${cost:.2f}**")
        print(f"\nserved_model, read off every response: "
              + ", ".join(f"`{k}` x{v:,}" for k, v in served.items()))
    elif em:
        print(f"\n## Extraction\n\ncalls "
              f"{sum(x['n_calls'] for x in em):,}; cost "
              f"${sum(x['cost_usd'] for x in em):.2f} (meta file only)")

    if not gr:
        return
    print("\n## H1 — incremental OOS explanatory power over the trailing "
          "correlation\n")
    print("| arm | dates | dR^2 | MDE(dR^2) | t | detectable | n |")
    print("|---|---|---|---|---|---|---|")
    for name, a in gr["arms"].items():
        print(h1_row(f"{name} / all pairs", a["h1_all_pairs"]))
        print(h1_row(f"{name} / cross-sector only", a["h1_cross_sector_only"]))
        print(h1_row(f"{name} / cross-FF12 AND cross-2-digit-SIC",
                     a.get("h1_cross_sector_and_sic2")))
    print("\n### H1 restricted to pairs that carry an edge (secondary)\n")
    print("Fractional reduction in the BASELINE's own squared error on those "
          "same pairs. The model is still fitted on the whole panel.\n")
    print("| arm | dates | MSE reduction | MDE | t | detectable | n |")
    print("|---|---|---|---|---|---|---|")
    for name, a in gr["arms"].items():
        r = a["h1_all_pairs"].get("on_edge_pairs")
        if r:
            print(f"| {name} / on-edge | {r['n_dates']} | "
                  f"{f(r['mse_reduction_pct'], 3)} | "
                  f"{f(r['mse_reduction_mde_pct'], 3)} | {f(r['t'], 3)} | "
                  f"{'YES' if r['detectable'] else 'no'} | "
                  f"{r.get('n_edge_pairs_graded', 0):,} pairs |")

    print("\n## H2 — semantic YES / numeric NO vs matched semantic NO / "
          "numeric NO\n")
    print("Outcome: enters the top decile of forward residual correlation in "
          "(t, t+h].\n")
    print("| arm | cases / controls | dates | rate difference | MDE | t | "
          "detectable |")
    print("|---|---|---|---|---|---|---|")
    for name, a in gr["arms"].items():
        print(h2_row(f"{name} / all pairs", a["h2_all_pairs"], "rate_diff"))
        print(h2_row(f"{name} / cross-sector",
                     a["h2_cross_sector_only"], "rate_diff"))
        print(h2_row(f"{name} / cross-FF12 AND cross-2-digit-SIC",
                     a.get("h2_cross_sector_and_sic2"), "rate_diff"))
    print("\nSame test on the continuous outcome (mean rho_fwd difference):\n")
    print("| arm | cases / controls | dates | rho difference | MDE | t | "
          "detectable |")
    print("|---|---|---|---|---|---|---|")
    for name, a in gr["arms"].items():
        print(h2_row(f"{name} / all pairs", a["h2_all_pairs"], "rho_diff"))

    rd = gr.get("reversed_direction", {})
    print("\n## Reversed-direction control\n")
    if "error" in rd:
        print(f"DID NOT RUN: {rd['error']}")
    else:
        print(f"directed pairs graded: {rd['n_directed_pairs_graded']:,}; "
              f"unoriented dropped: {rd['n_unoriented_dropped']:,}\n")
        print("| statistic | dates | mean | MDE | t | detectable |")
        print("|---|---|---|---|---|---|")
        for k in ("asymmetry", "coinflip_placebo"):
            s = rd[k]
            print(f"| {k} | {s['n_dates']} | {f(s['mean'], 3)} | "
                  f"{f(s['mde'], 3)} | {f(s['t'], 3)} | "
                  f"{'YES' if s['detectable'] else 'no'} |")


if __name__ == "__main__":
    main()
