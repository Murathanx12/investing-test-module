"""DIAG-PF4-BOUNDARY-1 — where could a selector still add value?

Reported, never deciding. Registered as a design input for the un-cancelled LLM
re-ranking campaign, not as evidence for anything.

If the edge is membership, the only place a selector can change the outcome is
at the MARGIN of membership — the names just inside and just outside the cut.
Stage A measured ranks 1-150 in tens. This extends the same measurement out to
rank 300, so the question "is there a live boundary, and where is it" has an
answer before a campaign is designed around it rather than after.

The statistic is the FF5+UMD alpha of each ten-name window, because raw excess
confounds signal quality with the rising size and illiquidity premia of deeper
ranks — the confound that made the banked concentration grid uninterpretable.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.WARNING)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "PF4"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"


def main() -> int:
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()
    base = StrategySpec(**d)

    f = Factory()
    elig = f.eligible(base.segment)
    score, _ = composite_score(f.lib, base.signals, elig)
    panel, rf, mkt = f.spine.panel, f.spine.rf, f.spine.mkt

    res = {"diagnostic": "DIAG-PF4-BOUNDARY-1", "is_gate": False,
           "status": "REPORTED-NEVER-DECIDING",
           "purpose": "design input for the un-cancelled re-ranking campaign",
           "windows": {}}
    for lo in range(151, 301, 10):
        hi = lo + 9
        sc = D.rank_window_score(score, elig, lo, hi)
        sp = StrategySpec(**{**d, "top_n": 10, "hold_band_mult": 1.0,
                             "min_names": 10,
                             "name": f"{base.name}__rank{lo}_{hi}"})
        try:
            o = run_book(panel, sc, elig, sp, rf)
        except RuntimeError as exc:
            res["windows"][f"{lo}-{hi}"] = {"error": str(exc)[:120]}
            continue
        net = o["monthly"]["net"].dropna()
        b = mkt.reindex(net.index)
        res["windows"][f"{lo}-{hi}"] = {
            "months": len(net),
            "excess_cagr_net": round(annualize(net) - annualize(b), 4),
            "alpha_ff5_umd": D.alpha_report(net, f.factors, D.FF6, rf=rf)}
        print(f"rank {lo}-{hi} done", flush=True)

    (OUT / "DIAG_BOUNDARY.json").write_text(json.dumps(res, indent=2),
                                            encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
