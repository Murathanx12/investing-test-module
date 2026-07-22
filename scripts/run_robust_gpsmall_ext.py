"""TRIAL-BRAIN-008-EXT — pre-registered robustness of gp-small on 1963-2001.

Same frozen mechanics as the BRAIN-008 confirm run (small segment = formation
dollar-vol ranks 1001-3000, top decile, 30% hold-band, 50 bps one-way), on the
newly harvested extension panel. Test months 1970-01..2001-12; months with
<100 small-segment names skip via the standard guard (early-decade coverage is
thin — stated a priori, not tuned).

Reading rule (frozen): SUPPORTIVE if mean net excess > 0 AND t_ic >= 1.5;
UNDERMINING if mean net excess <= 0. Either way recorded; this cannot promote
or demote BRAIN-008 by itself — it informs the forward-lane prior only.

Usage:  .venv\\Scripts\\python -m scripts.run_robust_gpsmall_ext
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.batch2_fundamentals import build_batch2
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.fundamentals import FundStore, load_characteristics
from aegis_brain.harness.benchmark import newey_west_tstat

RAW = MODULE_ROOT / "data" / "wrds_raw"

CFG = ScanConfig(cost_bps_one_way=50.0,
                 first_test_month="1970-01-31", last_test_month="2001-12-31")


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_1963")
    chars = load_characteristics(funda_path=RAW / "comp_funda_ext.parquet")
    store = FundStore(panel, chars)
    gp = [s for s in build_batch2(store) if s.name == "gross_prof"][0]

    res = scan_signal(panel, gp, "small", CFG)
    monthly, summary = res["monthly"], res["summary"]
    nw = newey_west_tstat(monthly["excess_net"])
    ic_nw = newey_west_tstat(monthly["ic"])

    supportive = (summary["mean_excess_net_bps"] > 0 and summary["t_ic"] >= 1.5)
    verdict = ("SUPPORTIVE" if supportive else
               "UNDERMINING" if summary["mean_excess_net_bps"] <= 0 else
               "MIXED (positive but IC weak)")
    out = {"trial": "TRIAL-BRAIN-008-EXT", "summary": summary,
           "nw_t_excess_net": nw, "nw_t_ic": ic_nw, "verdict": verdict,
           "first_live_month": str(monthly.index.min().date()),
           }
    (MODULE_ROOT / "data" / "factory" / "robust_gpsmall_ext.json").write_text(
        json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
