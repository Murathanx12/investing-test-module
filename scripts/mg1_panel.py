"""MARKET-GRAPH-1 stage 1 — the numeric spine, built before any edge exists.

WHAT THIS BUILDS, AND THE ORDER IT MATTERS IN
=============================================
The prereg's whole discipline is that edges are emitted BEFORE the evaluation
window opens. This stage is the other half of that promise: it fixes the
universe, the clock, the trailing correlation matrix and the forward
co-movement target from prices alone, with no knowledge of what any language
model will say. It runs first, it is committed first, and the extractor is
never shown any of its output.

Outputs (runs/MARKET-GRAPH-1/):
  pairs.parquet        one row per (cut date, i, j): rho_trail, rho_fwd,
                       same_sector, and the within-date rho_trail decile
  universe.parquet     one row per (cut date, permno): ticker, comnam, ff12,
                       mcap, cik, and the 10-K that will be its document
  filings.parquet      the DISTINCT (permno, accession) extraction worklist
  panel_meta.json      counts, coverage, and every attrition step

POINT-IN-TIME, IN THREE PLACES
------------------------------
1. `shrcd`, `siccd`, `ticker` and `comnam` are read from the CRSP name row
   VALID ON THE CUT DATE, not the last one. A ticker is not a permanent
   property of a security (§13), and the FF12 sector of a firm that changed
   its SIC is not its 2024 sector.
2. The document is the most recent 10-K filed STRICTLY BEFORE t, and at most
   MAX_FILING_AGE_DAYS old.
3. Forward residuals are formed with betas fitted on the TRAILING window. A
   beta fitted inside (t, t+h] would let the grading window choose its own
   market model.
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
from aegis_brain.events.name_link import link_filings_by_cik     # noqa: E402
from scripts import mg1_config as C                              # noqa: E402
from scripts.wg1_features import ff12_of                         # noqa: E402

PANELF = MODULE_ROOT / "data" / "factory" / "wg1_panel.npz"
STOCKNAMES = MODULE_ROOT / "data" / "wrds_raw" / "crsp_stocknames.parquet"
DSI = MODULE_ROOT / "data" / "wrds_raw" / "crsp_dsi.parquet"
SUBS = MODULE_ROOT / "data" / "events" / "sec_submissions.parquet"

OUT = MODULE_ROOT / "runs" / "MARKET-GRAPH-1"
OUT.mkdir(parents=True, exist_ok=True)

ANNUAL_FORMS = ("10-K", "10-K405")


# ── point-in-time CRSP identity ─────────────────────────────────────────────

def name_rows_at(dates: pd.DatetimeIndex) -> dict[pd.Timestamp, pd.DataFrame]:
    """The CRSP name row valid on each cut date, per permno.

    `namedt <= t <= nameenddt` is the only correct reading of this table. Using
    the last row per permno would stamp a 2024 ticker and a 2024 SIC on a 2015
    decision, which is exactly the leak §13 names.
    """
    sn = pd.read_parquet(STOCKNAMES, columns=["permno", "namedt", "nameenddt",
                                              "shrcd", "siccd", "ticker",
                                              "comnam"])
    sn["namedt"] = pd.to_datetime(sn["namedt"])
    sn["nameenddt"] = pd.to_datetime(sn["nameenddt"])
    out = {}
    for t in dates:
        v = sn[(sn["namedt"] <= t) & (sn["nameenddt"] >= t)]
        out[t] = v.drop_duplicates("permno").set_index("permno")
    return out


def annual_filings(permnos: np.ndarray, dates: pd.DatetimeIndex,
                   MCAP: np.ndarray) -> tuple[pd.DataFrame, dict]:
    """Every 10-K in the SEC index, linked to a permno through its CIK.

    WHY THE SHARE-CLASS BRANCH EXISTS
    ---------------------------------
    `link_filings_by_cik` drops a filing whose CIK maps to more than one permno
    at that date, and counts the drop. That is the right default — silently
    assigning the first candidate is how phantom links are made — but it has one
    systematic consequence this trial cannot live with: DUAL-CLASS issuers have
    two permnos under one CIK, always, so they are dropped ALWAYS. The first
    build of this universe therefore contained no Alphabet, at any of the 38 cut
    dates, while carrying Microsoft, Apple and Meta. A universe that silently
    omits the single most frequently named counterparty in US technology filings
    does not measure "resolution rate"; it measures who survived a share-class
    accident.

    The re-link rule: among the permnos a CIK maps to at that date, take the one
    with the LARGEST market cap on the nearest panel date. That is a share-class
    choice, made from the capitalisation table, blind to every outcome in this
    trial. Both routes are counted and the counts go in the report.
    """
    from aegis_brain.events.name_link import cik_permno_windows

    subs = pd.read_parquet(SUBS)
    f = subs[subs["form"].isin(ANNUAL_FORMS) & (subs["primary_document"] != "")]
    f = f[(f["filing_date"] >= "2013-01-01") & (f["filing_date"] <= "2024-12-31")]
    f = f.copy()
    f["filing_date"] = pd.to_datetime(f["filing_date"])
    linked, report = link_filings_by_cik(f, "cik", "filing_date")
    linked["filing_date"] = pd.to_datetime(linked["filing_date"])
    linked["link_route"] = "cik_unique"

    # ── the ambiguous residue, re-linked by share class ──────────────────────
    got = set(zip(linked["cik"].astype(int), linked["accession"]))
    rest = f[[(c, a) not in got
              for c, a in zip(f["cik"].astype(int), f["accession"])]]
    bridge = cik_permno_windows().rename(columns={"cik": "_bcik"})
    slack = pd.Timedelta(days=180)
    m = rest.merge(bridge, left_on=rest["cik"].astype(int), right_on="_bcik",
                   how="inner")
    m = m[(m["filing_date"] >= m["namedt"] - slack)
          & (m["filing_date"] <= m["nameenddt"] + slack)]
    n_amb_rows = 0
    if not m.empty:
        pos = {int(p): k for k, p in enumerate(permnos)}
        m = m[m["permno"].astype(int).isin(pos)]
        ix = np.searchsorted(dates.to_numpy(),
                             m["filing_date"].to_numpy(), side="right") - 1
        ix = np.clip(ix, 0, len(dates) - 1)
        col = np.array([pos[int(p)] for p in m["permno"]])
        m = m.assign(_mcap=np.nan_to_num(MCAP[ix, col].astype(np.float64),
                                         nan=-1.0))
        m = (m.sort_values("_mcap", ascending=False)
             .drop_duplicates(subset=["accession"]))
        m = m[m["_mcap"] > 0]
        n_amb_rows = len(m)
        add = m[["cik", "form", "accession", "filing_date", "primary_document",
                 "permno"]].copy()
        add["permno"] = add["permno"].astype(int)
        add["link_route"] = "share_class"
        linked = pd.concat([linked, add], ignore_index=True)

    report["n_relinked_share_class"] = int(n_amb_rows)
    print(f"  10-K filings linked: {len(linked):,} over "
          f"{linked['permno'].nunique():,} permnos  (cik_unique match rate "
          f"{report.get('match_rate')}, +{n_amb_rows:,} re-linked by share "
          f"class)", flush=True)
    return linked.sort_values(["permno", "filing_date"]), report


# ── the residual machinery ──────────────────────────────────────────────────

def residuals(R: np.ndarray, mkt: np.ndarray, ff12: np.ndarray,
              betas: np.ndarray | None = None
              ) -> tuple[np.ndarray, np.ndarray]:
    """Market- and sector-residual returns, and the betas used.

    `r_i - a - b_mkt*r_mkt - b_sec*r_sec(-i)`, where `r_sec(-i)` is the equal-
    weighted return of i's FF12 group EXCLUDING i. Excluding self is not
    fastidiousness: with n_g around 20, leaving i in puts a 5% piece of r_i on
    both sides of the regression and manufactures the very co-movement this
    trial is trying to measure.

    When `betas` is supplied they are APPLIED rather than fitted — that is how
    the forward window gets residuals without fitting anything inside itself.
    """
    T, N = R.shape
    sec = np.full((T, N), np.nan, dtype=np.float64)
    for g in np.unique(ff12):
        m = ff12 == g
        n_g = int(m.sum())
        if n_g < 2:
            continue                       # a group of one has no peer return
        S = np.nanmean(R[:, m], axis=1)
        sec[:, m] = ((n_g * S[:, None] - R[:, m]) / (n_g - 1))

    res = np.full((T, N), np.nan, dtype=np.float64)
    B = np.full((N, 3), np.nan, dtype=np.float64) if betas is None else betas
    for j in range(N):
        y = R[:, j]
        X = np.column_stack([np.ones(T), mkt, sec[:, j]])
        ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
        if betas is None:
            if ok.sum() < 60:
                continue
            B[j], *_ = np.linalg.lstsq(X[ok], y[ok], rcond=None)
        if not np.isfinite(B[j]).all():
            continue
        res[ok, j] = y[ok] - X[ok] @ B[j]
    return res, B


def pair_corr(res: np.ndarray, min_obs: int) -> np.ndarray:
    """Pairwise correlation of residual columns, NaN where coverage is thin."""
    X = res.copy()
    ok = np.isfinite(X)
    X[~ok] = 0.0
    n = ok.astype(np.float64)
    cnt = n.T @ n
    s1 = X.T @ n                                   # sum of x over shared rows
    s11 = (X * X).T @ n
    s12 = X.T @ X
    with np.errstate(invalid="ignore", divide="ignore"):
        cov = s12 / cnt - (s1 / cnt) * (s1.T / cnt)
        # Variance is read against the SHARED rows of each pair, not the
        # column's own full history — otherwise |rho| can exceed 1 whenever two
        # names have different missingness.
        v_i = s11 / cnt - (s1 / cnt) ** 2
        rho = cov / np.sqrt(v_i * v_i.T)
    rho[cnt < min_obs] = np.nan
    np.fill_diagonal(rho, np.nan)
    return np.clip(rho, -1.0, 1.0)


def main() -> None:
    t0 = time.time()
    z = np.load(PANELF, allow_pickle=False)
    dates = pd.DatetimeIndex(z["dates"].astype("datetime64[ns]"))
    permnos = z["permnos"].astype(int)
    RET = z["RET"]
    PRC = z["PRC"]
    MCAP = z["MCAP"]
    print(f"panel {RET.shape} {dates[0].date()}..{dates[-1].date()}", flush=True)

    dsi = pd.read_parquet(DSI, columns=["date", "vwretd"])
    dsi["date"] = pd.to_datetime(dsi["date"])
    mkt_all = (pd.to_numeric(dsi.set_index("date")["vwretd"], errors="coerce")
               .reindex(dates).to_numpy(dtype=np.float64))
    print(f"  CRSP VW market return: {np.isfinite(mkt_all).sum()}/{len(dates)} "
          f"days present", flush=True)

    try:
        q_ends = pd.date_range(C.FIRST_CUT, C.LAST_CUT, freq="QE")
    except ValueError:                                    # pandas < 2.2
        q_ends = pd.date_range(C.FIRST_CUT, C.LAST_CUT, freq="Q")
    cut_ix = [int(np.searchsorted(dates, q, side="right") - 1) for q in q_ends]
    cut_ix = sorted({k for k in cut_ix
                     if k - C.TRAIL_DAYS >= 0
                     and k + C.HORIZON_DAYS < len(dates)})
    cut_dates = dates[cut_ix]
    print(f"  cut dates: {len(cut_ix)}  "
          f"{cut_dates[0].date()}..{cut_dates[-1].date()}", flush=True)

    names = name_rows_at(cut_dates)
    filings, link_report = annual_filings(permnos, dates, MCAP)

    uni_rows, pair_frames = [], []
    attrition: list[dict] = []

    for k, (t, ix) in enumerate(zip(cut_dates, cut_ix)):
        nm = names[t]
        have = np.isin(permnos, nm.index.to_numpy())
        n0 = int(have.sum())

        shrcd = np.full(len(permnos), -1)
        siccd = np.full(len(permnos), -1)
        shrcd[have] = nm["shrcd"].reindex(permnos[have]).to_numpy()
        siccd[have] = nm["siccd"].reindex(permnos[have]).to_numpy()

        px = np.abs(PRC[ix].astype(np.float64))
        mc = MCAP[ix].astype(np.float64)
        trail_ok = np.isfinite(RET[ix - C.TRAIL_DAYS + 1:ix + 1]).sum(axis=0)
        fwd_ok = np.isfinite(RET[ix + 1:ix + 1 + C.HORIZON_DAYS]).sum(axis=0)

        elig = (have & np.isin(shrcd, C.SHRCD_OK) & (px >= C.MIN_PRICE)
                & np.isfinite(mc) & (mc > 0)
                & (trail_ok >= int(0.8 * C.TRAIL_DAYS))
                & (fwd_ok >= int(0.8 * C.HORIZON_DAYS)))
        n1 = int(elig.sum())

        # the document gate: a 10-K filed strictly before t, at most 460d old.
        #
        # AMENDED 2026-08-12, and the amendment is the point of this comment.
        # The first build required a linked 10-K for UNIVERSE MEMBERSHIP, so
        # the panel was "the 300 largest names whose CIK happened to join to a
        # permno by name". The EDGAR<->CRSP bridge is an exact match on
        # normalised company names and CRSP abbreviates ("INTL BUSINESS MACHS
        # COR" against EDGAR's "INTL BUSINESS MACHINES"), so IBM — rank 24 by
        # market cap — was absent from all 38 dates, along with 46 of every 300
        # names: measured overlap with the true top-300-eligible was 84.6%.
        # Substituting the 301st..346th largest for the largest is a selection
        # effect wearing a universe's clothes, and it is exactly the failure
        # this trial's resolution work is trying to avoid one stage later.
        #
        # Membership is now market cap alone. The document is attached WHERE IT
        # EXISTS and is required only to make a name an extraction SUBJECT — a
        # name with no 10-K can still be the TARGET of somebody else's edge,
        # which is what universe membership is for. Per-date document coverage
        # is recorded in `attrition` so the gap stays visible.
        #
        # This was decided from composition alone (a named megacap was missing)
        # and not from any outcome: the only grading run that had been executed
        # at that point carried 17 edge-instances and returned "not detectable"
        # on every arm, so it could not have motivated anything.
        f = filings[(filings["filing_date"] < t)
                    & (filings["filing_date"] >= t - pd.Timedelta(
                        days=C.MAX_FILING_AGE_DAYS))]
        latest = (f.sort_values("filing_date").groupby("permno").tail(1)
                  .set_index("permno"))
        has_doc = np.isin(permnos, latest.index.to_numpy()) & elig
        n2 = int(has_doc.sum())

        cand = np.where(elig)[0]
        cand = cand[np.argsort(-mc[cand])][:C.UNIVERSE_N]
        cand = np.sort(cand)
        N = len(cand)
        n_doc_in_uni = int(np.isin(permnos[cand], latest.index.to_numpy()).sum())
        attrition.append({"date": str(t.date()), "with_name_row": n0,
                          "eligible": n1, "with_10k": n2, "universe": N,
                          "universe_with_doc": n_doc_in_uni})

        ff = ff12_of(siccd[cand])
        Rt = RET[ix - C.TRAIL_DAYS + 1:ix + 1, cand].astype(np.float64)
        Rf = RET[ix + 1:ix + 1 + C.HORIZON_DAYS, cand].astype(np.float64)
        mt = mkt_all[ix - C.TRAIL_DAYS + 1:ix + 1]
        mf = mkt_all[ix + 1:ix + 1 + C.HORIZON_DAYS]

        res_t, B = residuals(Rt, mt, ff)
        res_f, _ = residuals(Rf, mf, ff, betas=B)

        rho_t = pair_corr(res_t, min_obs=int(0.6 * C.TRAIL_DAYS))
        rho_f = pair_corr(res_f, min_obs=int(0.6 * C.HORIZON_DAYS))

        iu, ju = np.triu_indices(N, k=1)
        keep = np.isfinite(rho_t[iu, ju]) & np.isfinite(rho_f[iu, ju])
        iu, ju = iu[keep], ju[keep]
        pi, pj = permnos[cand][iu], permnos[cand][ju]
        rt, rf_ = rho_t[iu, ju], rho_f[iu, ju]
        dec = pd.qcut(pd.Series(rt), 10, labels=False, duplicates="drop")

        pair_frames.append(pd.DataFrame({
            "date": t, "permno_i": pi, "permno_j": pj,
            "rho_trail": rt.astype(np.float32),
            "rho_fwd": rf_.astype(np.float32),
            "same_sector": (ff[iu] == ff[ju]),
            "trail_decile": dec.to_numpy().astype(np.int8),
            "numeric_yes": rt >= np.quantile(rt, C.NUMERIC_YES_Q),
        }))

        uni_rows.append(pd.DataFrame({
            "date": t, "permno": permnos[cand],
            "ticker": nm["ticker"].reindex(permnos[cand]).to_numpy(),
            "comnam": nm["comnam"].reindex(permnos[cand]).to_numpy(),
            "ff12": ff, "mcap": mc[cand], "siccd": siccd[cand],
            "cik": latest["cik"].reindex(permnos[cand]).to_numpy(),
            "accession": latest["accession"].reindex(permnos[cand]).to_numpy(),
            "primary_document": latest["primary_document"].reindex(
                permnos[cand]).to_numpy(),
            "filing_date": latest["filing_date"].reindex(
                permnos[cand]).to_numpy(),
        }))
        print(f"  [{k + 1:2d}/{len(cut_ix)}] {t.date()}  N={N}  "
              f"pairs={len(pi):,}", flush=True)

    uni = pd.concat(uni_rows, ignore_index=True)
    pairs = pd.concat(pair_frames, ignore_index=True)

    # Only universe members that HAVE a document are extraction subjects. The
    # rest are edge targets only, and `accession` is null for them.
    work = (uni[uni["accession"].notna()]
            [["permno", "cik", "accession", "primary_document",
              "filing_date", "ticker", "comnam"]]
            .drop_duplicates("accession").reset_index(drop=True))
    work["cik"] = work["cik"].astype("int64")

    uni.to_parquet(OUT / "universe.parquet", index=False)
    pairs.to_parquet(OUT / "pairs.parquet", index=False)
    work.to_parquet(OUT / "filings.parquet", index=False)

    meta = {
        "built_utc": pd.Timestamp.utcnow().isoformat(),
        "n_cut_dates": len(cut_ix),
        "first_cut": str(cut_dates[0].date()),
        "last_cut": str(cut_dates[-1].date()),
        "n_universe_rows": int(len(uni)),
        "n_distinct_permnos": int(uni["permno"].nunique()),
        "n_pairs": int(len(pairs)),
        "n_documents_to_extract": int(len(work)),
        "mean_rho_trail": float(pairs["rho_trail"].mean()),
        "mean_rho_fwd": float(pairs["rho_fwd"].mean()),
        "corr_trail_fwd": float(pairs["rho_trail"].corr(pairs["rho_fwd"])),
        "same_sector_share": float(pairs["same_sector"].mean()),
        "filing_link_report": link_report,
        "attrition": attrition,
        "params": {k: getattr(C, k) for k in dir(C) if k.isupper()},
        "elapsed_min": round((time.time() - t0) / 60, 2),
    }
    (OUT / "panel_meta.json").write_text(json.dumps(meta, indent=2,
                                                    default=str),
                                         encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items()
                      if k not in ("attrition", "params")}, indent=2,
                     default=str))


if __name__ == "__main__":
    main()
