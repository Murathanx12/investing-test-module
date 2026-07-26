"""INSTR-CZ-CALIB + INSTR-HARNESS-VALID — one shot each.

Protocol: TRIALS/INSTR-CALIBRATION-PAIR.md (frozen mapping + bars).
Usage:  .venv\\Scripts\\python -m scripts.run_calibration_pair
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal, segment_mask
from aegis_brain.factory.batch1_price import BATCH1

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("calib")
OUT = MODULE_ROOT / "data" / "factory"

# Frozen in the registration; summary-file identifiers corrected pre-results
# (asset_growth->asset_growth_low etc. — mechanical name repairs, disclosed).
MAPPING = {
    "gross_prof": "GP", "oper_prof": "OperProf",
    "asset_growth_low": "AssetGrowth", "accruals_low": "Accruals",
    "net_issuance_low": "ShareIss1Y", "comp_issue_5y": "CompEquIss",
    "btm": "BM", "roe": "RoE", "mom_12_1": "Mom12m",
    "st_reversal": "STreversal", "ltr_36_13": "LTreversal",
    "max_ret_low": "MaxRet", "vol_6m_low": "IdioVol3F",
    "si_ratio": "ShortInterest",
    "cust_mom": "CustomerMomentum", "industry_mom": "IndMom",
}


def cz_calib() -> dict:
    sd = pd.read_csv(MODULE_ROOT / "data" / "reference"
                     / "osap_SignalDoc_snap20260726.csv")
    sd["Acronym"] = sd["Acronym"].astype(str)
    sd = sd.set_index(sd["Acronym"].str.upper())
    ours = pd.concat([pd.read_csv(p) for p in sorted(OUT.glob("batch*_summary.csv"))],
                     ignore_index=True)
    ours = ours[ours["segment"] == "largemid"].set_index("signal")

    rows, dropped = [], []
    for sig, acr_raw in MAPPING.items():
        acr = acr_raw.upper()
        if acr not in sd.index or sig not in ours.index:
            dropped.append(f"{sig}->{acr_raw}")
            continue
        osap_t = pd.to_numeric(sd.loc[acr, "T-Stat"], errors="coerce")
        if np.isnan(osap_t):
            dropped.append(f"{sig}->{acr} (no t)")
            continue
        rows.append({
            "signal": sig, "acronym": acr_raw,
            "osap_t": float(osap_t),
            "osap_sample": f"{sd.loc[acr, 'SampleStartYear']}-{sd.loc[acr, 'SampleEndYear']}",
            "our_t_ic": float(ours.loc[sig, "t_ic"]),
        })
    df = pd.DataFrame(rows)
    from scipy.stats import spearmanr
    rho, pval = spearmanr(df["osap_t"].abs(), df["our_t_ic"].abs())
    ratio = float((df["our_t_ic"].abs() / df["osap_t"].abs()).median())
    # every factory direction was declared FROM the literature prior, so
    # "agreement" = our directed t_ic still positive in-window
    sign_agree = float((df["our_t_ic"] > 0).mean())
    res = {"n_matched": len(df), "dropped": dropped,
           "rank_corr_abs_t": round(float(rho), 3), "p": round(float(pval), 4),
           "median_level_ratio": round(ratio, 3),
           "sign_agreement": round(sign_agree, 3),
           "table": df.to_dict("records")}
    log.info("CZ-CALIB: n=%d rho=%.3f ratio=%.3f sign=%.2f",
             len(df), rho, ratio, sign_agree)
    return res


def harness_valid() -> dict:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    ff = pd.read_parquet(MODULE_ROOT / "data" / "ff_factors.parquet")
    lo, hi = pd.Timestamp("2004-01-31"), pd.Timestamp("2018-12-31")
    idx = [m for m in panel.monthly_ret.index if lo <= m <= hi]

    elig = panel.eligible()
    large = segment_mask(panel, "largemid")
    small = segment_mask(panel, "small")
    mkt_ew, smb_p = {}, {}
    for m in idx:
        r = panel.monthly_ret.loc[m]
        e = elig.loc[m]
        mkt_ew[m] = float(r[e].mean())
        smb_p[m] = float(r[e & small.loc[m]].mean() - r[e & large.loc[m]].mean())
    mkt_ew = pd.Series(mkt_ew)
    smb_p = pd.Series(smb_p)

    mom = next(s for s in BATCH1 if s.name == "mom_12_1")
    monthly = scan_signal(panel, mom, "largemid", ScanConfig())["monthly"]
    umd_p = monthly["excess_gross"]

    ffw = ff.reindex(mkt_ew.index)
    res = {
        "corr_mkt": round(float(mkt_ew.corr(ffw["mktrf"] + ffw["rf"])), 3),
        "corr_smb": round(float(smb_p.corr(ffw["smb"])), 3),
        "corr_umd": round(float(umd_p.corr(ff.reindex(umd_p.index)["umd"])), 3),
        "bars": {"mkt": 0.90, "smb": 0.60, "umd": 0.40},
        "months": len(mkt_ew),
    }
    res["all_bars_met"] = bool(res["corr_mkt"] >= 0.90
                               and res["corr_smb"] >= 0.60
                               and res["corr_umd"] >= 0.40)
    log.info("HARNESS-VALID: mkt %.3f smb %.3f umd %.3f -> %s",
             res["corr_mkt"], res["corr_smb"], res["corr_umd"],
             res["all_bars_met"])
    return res


def main() -> None:
    results = {"cz_calib": cz_calib(), "harness_valid": harness_valid()}
    with open(OUT / "calibration_pair.json", "w") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "table"}
                      for k, v in results.items()}, indent=2, default=str))


if __name__ == "__main__":
    main()
