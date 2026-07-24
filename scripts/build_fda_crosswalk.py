"""Sponsor-name -> CRSP permno point-in-time crosswalk for the FDA event study
(BRAIN-006 prep — the mapping step fda.py deliberately deferred).

Matches the 2,742 NDA/BLA original-approval sponsors to the security that was
listed AT THE APPROVAL DATE. No current-day ticker file is ever consulted —
matching a 2004 sponsor to a 2026 ticker table is exactly the M&A/rename
look-ahead this script exists to avoid.

Tiers (highest precedence first; every drop is counted, never silent):
  0. manual_overrides   data/events/fda_sponsor_overrides.csv (hand/agent
                        verified, date-bounded; blank permno = verified
                        private/foreign-unlisted at that time)
  1. stocknames-exact   normalized sponsor == normalized CRSP comnam with
                        namedt <= approval_date <= nameenddt, unique permno
  2. compustat-exact    normalized sponsor == normalized conm -> unique gvkey
                        -> CCM link window covering approval_date -> unique permno
  3. stocknames-anytime normalized name maps to exactly ONE permno across all
                        of CRSP name history (catches FDA using a slightly
                        stale/early name; unique-ever makes reuse collision
                        impossible by construction)
  4. core-name          suffix-AND-domain-word stripped variant ("X PHARMS
                        USA" -> "X"), accepted only if unique on both sides
  F. fuzzy              rapidfuzz candidates >= FUZZY_MIN emitted to the
                        review CSV for verification — NEVER auto-accepted

Universe note (disclosed, not hidden): the paper-grade panel is shrcd 10/11,
exchcd 1/2/3 — ADR-only parents (NOVARTIS, ASTRAZENECA, ...) match a permno
but carry in_panel_universe=False and cannot enter the drift book.

Outputs:
  data/events/fda_crosswalk.parquet        event-level mapping + match_source
  data/events/fda_crosswalk_report.json    tier counts, match rates, coverage
  data/events/fda_crosswalk_review.csv     unmatched sponsors + fuzzy candidates
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

MODULE_ROOT = Path(__file__).resolve().parents[1]
RAW = MODULE_ROOT / "data" / "wrds_raw"
EVENTS = MODULE_ROOT / "data" / "events"
_FAR_FUTURE = pd.Timestamp("2100-01-01")
FUZZY_MIN = 90

# stripped only as TRAILING tokens (repeatedly), so "ABBVIE INC" -> "ABBVIE"
# without mangling interior words
_SUFFIX = {
    "INC", "CORP", "CO", "COMPANY", "LLC", "LTD", "PLC", "AG", "AB", "SA",
    "NV", "SPA", "GMBH", "USA", "US", "LP", "LLP", "HOLDINGS", "HLDGS",
    "NEW", "DE", "KG", "AS", "OY", "BV",
}
# pharma domain words: stripped ONLY in the core-name tier (tier 4)
_DOMAIN = {
    "PHARMS", "PHARMA", "PHARM", "PHARMACEUTICAL", "PHARMACEUTICALS",
    "LABS", "LABORATORIES", "LAB", "HLTHCARE", "HEALTHCARE", "HLTH",
    "BIOSCIENCES", "BIOSCIENCE", "SCIENCES", "PRODUCTS", "GROUP", "INTL",
    "INTERNATIONAL", "GLOBAL", "NORTH", "AMERICA",
}


# canonical spellings so "X PHARMACEUTICALS" == "X PHARMS" etc. on both sides
_CANON = {
    "PHARMACEUTICALS": "PHARMS", "PHARMACEUTICAL": "PHARMS", "PHARMA": "PHARMS",
    "PHARM": "PHARMS", "THERAPEUTICS": "THERAPS", "THERAP": "THERAPS",
    "LABORATORIES": "LABS", "LAB": "LABS", "INDUSTRIES": "INDS",
    "INTERNATIONAL": "INTL", "HEALTHCARE": "HLTHCARE", "HLTH": "HLTHCARE",
}


def normalize(name: str, core: bool = False) -> str:
    """Uppercase, punctuation->space, canonicalize domain spellings, drop
    AND/&, repeatedly strip trailing suffix tokens (plus domain tokens when
    core=True)."""
    if not isinstance(name, str):
        return ""
    s = re.sub(r"[^A-Z0-9& ]", " ", name.upper())
    s = re.sub(r"\s+", " ", s).strip()
    toks = [_CANON.get(t, t) for t in s.split(" ") if t not in ("&", "AND")]
    drop = _SUFFIX | _DOMAIN if core else _SUFFIX
    while len(toks) > 1 and toks[-1] in drop:
        toks.pop()
    return " ".join(toks) if toks else s


def _load_events() -> pd.DataFrame:
    fda = pd.read_parquet(EVENTS / "fda_approvals.parquet")
    nb = fda[fda["application_number"].str.upper().str.startswith(("NDA", "BLA"))].copy()
    nb["approval_date"] = pd.to_datetime(nb["approval_date"])
    nb["sponsor_norm"] = nb["sponsor_name"].map(normalize)
    nb["sponsor_core"] = nb["sponsor_name"].map(lambda x: normalize(x, core=True))
    return nb.reset_index(drop=True)


def _load_stocknames() -> pd.DataFrame:
    sn = pd.read_parquet(
        RAW / "crsp_stocknames.parquet",
        columns=["permno", "namedt", "nameenddt", "comnam", "ticker", "shrcd", "exchcd"],
    ).dropna(subset=["comnam", "permno"])
    sn["permno"] = sn["permno"].astype(int)
    sn["namedt"] = pd.to_datetime(sn["namedt"])
    sn["nameenddt"] = pd.to_datetime(sn["nameenddt"]).fillna(_FAR_FUTURE)
    # each permno's LAST name row ends at the data cutoff, not because the name
    # ended — extend it so post-cutoff events (outside the study window anyway)
    # can still resolve
    last = sn.groupby("permno")["nameenddt"].transform("max")
    live = (sn["nameenddt"] == last) & (sn["nameenddt"] >= pd.Timestamp("2024-01-01"))
    sn.loc[live, "nameenddt"] = _FAR_FUTURE
    sn["name_norm"] = sn["comnam"].map(normalize)
    sn["name_core"] = sn["comnam"].map(lambda x: normalize(x, core=True))
    return sn


def _compustat_link() -> pd.DataFrame:
    """(name_norm, gvkey) unique-conm pairs crossed with date-bounded CCM."""
    funda = pd.read_parquet(RAW / "comp_funda.parquet", columns=["gvkey", "conm"])
    funda = funda.dropna().drop_duplicates()
    funda["gvkey"] = funda["gvkey"].astype(str).str.strip()
    funda["name_norm"] = funda["conm"].map(normalize)
    # a normalized name that maps to >1 gvkey is ambiguous -> dropped, counted
    per = funda.groupby("name_norm")["gvkey"].nunique()
    uniq = funda[funda["name_norm"].isin(per[per == 1].index)]
    ccm = pd.read_parquet(RAW / "ccm_link.parquet",
                          columns=["gvkey", "permno", "linkdt", "linkenddt"]).dropna(
        subset=["gvkey", "permno"])
    ccm["gvkey"] = ccm["gvkey"].astype(str).str.strip()
    ccm["permno"] = ccm["permno"].astype(int)
    ccm["linkdt"] = pd.to_datetime(ccm["linkdt"])
    ccm["linkenddt"] = pd.to_datetime(ccm["linkenddt"]).fillna(_FAR_FUTURE)
    link = uniq[["name_norm", "gvkey"]].merge(ccm, on="gvkey")
    return link, int((per > 1).sum())


def _date_valid_unique(cand: pd.DataFrame, date_col: str = "approval_date") -> pd.DataFrame:
    """Keep rows whose window covers the event date AND whose event maps to a
    single permno; ambiguous events get dropped (caller counts them)."""
    cov = cand[(cand[date_col] >= cand["from_dt"]) & (cand[date_col] <= cand["to_dt"])]
    per = cov.groupby("_row")["permno"].nunique()
    return cov[cov["_row"].isin(per[per == 1].index)].drop_duplicates("_row"), int((per > 1).sum())


def main() -> None:
    ev = _load_events()
    sn = _load_stocknames()
    ev["_row"] = np.arange(len(ev))
    ev["permno"] = pd.array([pd.NA] * len(ev), dtype="Int64")
    ev["match_source"] = "UNMATCHED"
    ambig = {}

    # ---- tier 0: manual overrides -----------------------------------------
    # CSV: sponsor_norm,status,ticker,valid_from,valid_to,confidence,note
    #   status listed         -> resolve ticker->permno date-valid via stocknames
    #   status unlisted       -> verified private/foreign-unlisted AT THE TIME
    #   status unattributable -> openFDA sponsor_name is the CURRENT app holder,
    #     which acquired the application AFTER approval (roll-ups); the
    #     approval-time sponsor is unrecoverable -> excluded and counted.
    ov_path = EVENTS / "fda_sponsor_overrides.csv"
    n_override_unlisted = 0
    if ov_path.exists():
        ov = pd.read_csv(ov_path)
        ov["valid_from"] = pd.to_datetime(ov["valid_from"])
        ov["valid_to"] = pd.to_datetime(ov["valid_to"]).fillna(_FAR_FUTURE)
        # re-normalize keys through the live normalizer so override rows stay
        # valid as normalization evolves
        ov["sponsor_norm"] = ov["sponsor_norm"].str.strip().str.upper().map(normalize)
        tick = sn.dropna(subset=["ticker"])[["ticker", "permno", "namedt", "nameenddt"]]
        for _, o in ov.iterrows():
            rows = ev[(ev["sponsor_norm"] == o["sponsor_norm"]) &
                      (ev["approval_date"] >= o["valid_from"]) &
                      (ev["approval_date"] <= o["valid_to"]) &
                      (ev["match_source"] == "UNMATCHED")]
            if rows.empty:
                continue
            if o["status"] == "listed":
                cand = tick[tick["ticker"] == str(o["ticker"]).strip().upper()]
                for idx, r in rows.iterrows():
                    valid = cand[(cand["namedt"] <= r["approval_date"]) &
                                 (cand["nameenddt"] >= r["approval_date"])]["permno"].unique()
                    if len(valid) == 1:
                        ev.loc[idx, "permno"] = int(valid[0])
                        ev.loc[idx, "match_source"] = "manual_override"
                    # 0 or >1 permnos for ticker at date -> stays UNMATCHED, honest
            elif o["status"] == "unlisted":
                ev.loc[rows.index, "match_source"] = "verified_unlisted"
                n_override_unlisted += len(rows)
            elif o["status"] == "unattributable":
                ev.loc[rows.index, "match_source"] = "retroactive_excluded"

    def _open(tier_mask=None):
        m = ev["match_source"].isin(["UNMATCHED"])
        return m if tier_mask is None else (m & tier_mask)

    # ---- tier 1: stocknames exact, date-valid -----------------------------
    cand = ev.loc[_open(), ["_row", "sponsor_norm", "approval_date"]].merge(
        sn.rename(columns={"namedt": "from_dt", "nameenddt": "to_dt"}),
        left_on="sponsor_norm", right_on="name_norm")
    hit, ambig["stocknames_exact"] = _date_valid_unique(cand)
    ev.loc[ev["_row"].isin(hit["_row"]), "match_source"] = "stocknames_exact"
    ev = ev.merge(hit[["_row", "permno"]], on="_row", how="left", suffixes=("", "_t1"))
    ev["permno"] = ev["permno"].fillna(ev.pop("permno_t1"))

    # ---- tier 2: compustat conm -> gvkey -> ccm ---------------------------
    comp, comp_ambig_names = _compustat_link()
    cand = ev.loc[_open(), ["_row", "sponsor_norm", "approval_date"]].merge(
        comp.rename(columns={"linkdt": "from_dt", "linkenddt": "to_dt"}),
        on="name_norm" if "name_norm" in ev.columns else None,
        left_on="sponsor_norm", right_on="name_norm")
    hit, ambig["compustat_exact"] = _date_valid_unique(cand)
    ev.loc[ev["_row"].isin(hit["_row"]), "match_source"] = "compustat_exact"
    ev = ev.merge(hit[["_row", "permno"]], on="_row", how="left", suffixes=("", "_t2"))
    ev["permno"] = ev["permno"].fillna(ev.pop("permno_t2"))

    # ---- tier 3: stocknames name unique across ALL history ----------------
    ever = sn.groupby("name_norm")["permno"].nunique()
    uniq_names = ever[ever == 1].index
    sn_uni = sn[sn["name_norm"].isin(uniq_names)][["name_norm", "permno"]].drop_duplicates()
    cand = ev.loc[_open(), ["_row", "sponsor_norm"]].merge(
        sn_uni, left_on="sponsor_norm", right_on="name_norm")
    ev.loc[ev["_row"].isin(cand["_row"]), "match_source"] = "stocknames_anytime"
    ev = ev.merge(cand[["_row", "permno"]], on="_row", how="left", suffixes=("", "_t3"))
    ev["permno"] = ev["permno"].fillna(ev.pop("permno_t3"))

    # ---- tier 4: core-name (domain words stripped), unique both sides -----
    core_ever = sn.groupby("name_core")["permno"].nunique()
    core_uni = sn[sn["name_core"].isin(core_ever[core_ever == 1].index)][
        ["name_core", "permno"]].drop_duplicates()
    core_uni = core_uni[core_uni["name_core"].str.len() >= 5]  # too-short cores collide
    cand = ev.loc[_open(), ["_row", "sponsor_core"]].merge(
        core_uni, left_on="sponsor_core", right_on="name_core")
    per = cand.groupby("_row")["permno"].nunique()
    cand = cand[cand["_row"].isin(per[per == 1].index)].drop_duplicates("_row")
    ev.loc[ev["_row"].isin(cand["_row"]), "match_source"] = "core_name"
    ev = ev.merge(cand[["_row", "permno"]], on="_row", how="left", suffixes=("", "_t4"))
    ev["permno"] = ev["permno"].fillna(ev.pop("permno_t4"))

    # ---- in-panel flag: shrcd 10/11 valid at approval date ----------------
    common = sn[sn["shrcd"].isin([10, 11])][["permno", "namedt", "nameenddt"]]
    matched = ev[ev["permno"].notna()][["_row", "permno", "approval_date"]].merge(
        common, on="permno")
    in_univ = matched[(matched["approval_date"] >= matched["namedt"]) &
                      (matched["approval_date"] <= matched["nameenddt"])]["_row"].unique()
    ev["in_panel_universe"] = ev["_row"].isin(in_univ)

    # ---- fuzzy candidates for review (NEVER auto-accepted) ----------------
    from rapidfuzz import fuzz, process
    open_sponsors = (ev[ev["match_source"] == "UNMATCHED"]
                     .groupby(["sponsor_name", "sponsor_norm"]).size()
                     .rename("n_events").reset_index()
                     .sort_values("n_events", ascending=False))
    name_pool = sn[["name_norm"]].drop_duplicates()["name_norm"].tolist()
    rows = []
    for _, r in open_sponsors.iterrows():
        for cand_name, score, _ in process.extract(
                r["sponsor_norm"], name_pool, scorer=fuzz.token_sort_ratio,
                limit=3, score_cutoff=FUZZY_MIN):
            permnos = sn[sn["name_norm"] == cand_name]["permno"].unique()
            rows.append({"sponsor_name": r["sponsor_name"],
                         "sponsor_norm": r["sponsor_norm"], "n_events": r["n_events"],
                         "candidate_comnam": cand_name, "score": score,
                         "candidate_permnos": ";".join(map(str, permnos))})
    review = open_sponsors.merge(
        pd.DataFrame(rows, columns=["sponsor_name", "sponsor_norm", "n_events",
                                    "candidate_comnam", "score", "candidate_permnos"]),
        on=["sponsor_name", "sponsor_norm", "n_events"], how="left")
    review.to_csv(EVENTS / "fda_crosswalk_review.csv", index=False)

    # ---- outputs ----------------------------------------------------------
    out = ev[["application_number", "approval_date", "sponsor_name", "sponsor_norm",
              "review_priority", "permno", "match_source", "in_panel_universe"]]
    out.to_parquet(EVENTS / "fda_crosswalk.parquet", index=False)

    n = len(out)
    matched_mask = out["permno"].notna()
    report = {
        "built": pd.Timestamp.utcnow().isoformat(),
        "events": n,
        "unique_sponsors": int(out["sponsor_norm"].nunique()),
        "tier_counts": out["match_source"].value_counts().to_dict(),
        "ambiguous_dropped": ambig,
        "compustat_ambiguous_names": comp_ambig_names,
        "event_match_rate": round(float(matched_mask.mean()), 3),
        "event_match_rate_in_panel": round(float(out["in_panel_universe"].mean()), 3),
        "sponsor_match_rate": round(float(
            out[matched_mask]["sponsor_norm"].nunique() / out["sponsor_norm"].nunique()), 3),
        "override_verified_unlisted_events": n_override_unlisted,
        "universe_note": "panel = shrcd 10/11 exchcd 1/2/3; ADR parents match but are not tradeable in-panel",
    }
    (EVENTS / "fda_crosswalk_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    top_unmatched = (out[out["match_source"] == "UNMATCHED"]
                     .groupby("sponsor_name").size().sort_values(ascending=False).head(25))
    print("\nTop unmatched sponsors by event count:")
    print(top_unmatched.to_string())


if __name__ == "__main__":
    main()
