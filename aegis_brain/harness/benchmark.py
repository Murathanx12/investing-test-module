"""Honest evaluation layer: Newey-West t-stats and factor-model alpha.

A strategy's headline number is not its mean return — it is the t-stat on the intercept
of a factor regression, computed with HAC (Newey-West) standard errors, benchmarked
against the hurdle t >= 3.0 (Harvey-Liu-Zhu 2016). This module reports a portfolio's
excess return three ways — raw, and as CAPM / FF5+UMD alpha — so a "signal" that is
really just factor exposure is exposed as such.

Pure numpy (no statsmodels dependency). Fama-French factors are loaded from Ken French's
data library CSV (fetched once, cached under data/).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def newey_west_tstat(x: pd.Series, lags: int = 6) -> dict:
    """Mean of x and its Newey-West (HAC) t-stat — the honest t on a return series."""
    x = pd.Series(x).dropna().astype(float)
    n = len(x)
    if n < 12 or x.std(ddof=1) == 0:
        return {"mean": float(x.mean()) if n else float("nan"), "t": None, "n": n}
    mu = x.mean()
    e = (x - mu).values
    # long-run variance of the mean via Bartlett-weighted autocovariances
    gamma0 = np.dot(e, e) / n
    lrv = gamma0
    for L in range(1, min(lags, n - 1) + 1):
        w = 1.0 - L / (lags + 1.0)
        cov = np.dot(e[L:], e[:-L]) / n
        lrv += 2.0 * w * cov
    se = np.sqrt(max(lrv, 1e-16) / n)
    return {"mean": float(mu), "t": float(mu / se), "n": n, "lags": lags}


def factor_alpha(port_excess: pd.Series, factors: pd.DataFrame,
                 cols: list[str], lags: int = 6) -> dict:
    """Regress portfolio EXCESS return on factor columns; return annualized alpha and
    its Newey-West t-stat (the intercept test). `factors` is indexed like port_excess
    (monthly). Alpha is monthly; ann_alpha = alpha*12."""
    df = pd.concat([port_excess.rename("y"), factors[cols]], axis=1).dropna()
    df = df.astype(float)  # coerce nullable Float64 -> plain float for numpy matrix ops
    if len(df) < 24:
        return {"alpha_m": None, "t_alpha": None, "n": len(df)}
    y = df["y"].values
    X = np.column_stack([np.ones(len(df))] + [df[c].values for c in cols])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    # HAC covariance of OLS coefficients (Newey-West)
    XtX_inv = np.linalg.inv(X.T @ X)
    n, k = X.shape
    S = (X * resid[:, None]).T @ (X * resid[:, None]) / n
    for L in range(1, lags + 1):
        w = 1.0 - L / (lags + 1.0)
        Xe_t = (X * resid[:, None])[L:]
        Xe_tL = (X * resid[:, None])[:-L]
        G = Xe_t.T @ Xe_tL / n
        S += w * (G + G.T)
    cov = XtX_inv @ (n * S) @ XtX_inv
    se = np.sqrt(np.diag(cov))
    return {
        "alpha_m": float(beta[0]), "ann_alpha": float(beta[0] * 12),
        "t_alpha": float(beta[0] / se[0]),
        "betas": {c: float(b) for c, b in zip(cols, beta[1:])},
        "n": int(n), "lags": lags,
    }


def load_ff_factors(cache_dir) -> pd.DataFrame:
    """FF5 + momentum monthly factors from Ken French's library (fetched once, cached).
    Returns a DataFrame indexed by month-end with columns
    [mktrf, smb, hml, rmw, cma, umd, rf] in DECIMAL (not percent)."""
    from pathlib import Path
    import io
    import zipfile
    import requests

    cache = Path(cache_dir) / "ff_factors.parquet"
    if cache.exists():
        return pd.read_parquet(cache)

    base = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"

    def _grab(url, skip, valcols):
        raw = requests.get(url, timeout=60).content
        zf = zipfile.ZipFile(io.BytesIO(raw))
        txt = zf.read(zf.namelist()[0]).decode("latin-1")
        rows = []
        for line in txt.splitlines():
            p = line.split(",")
            if len(p) >= len(valcols) + 1 and p[0].strip().isdigit() and len(p[0].strip()) == 6:
                try:
                    rows.append([p[0].strip()] + [float(x) for x in p[1:len(valcols) + 1]])
                except ValueError:
                    continue
        d = pd.DataFrame(rows, columns=["ym"] + valcols)
        d["month"] = pd.to_datetime(d["ym"], format="%Y%m") + pd.offsets.MonthEnd(0)
        return d.set_index("month")[valcols] / 100.0

    ff5 = _grab(f"{base}/F-F_Research_Data_5_Factors_2x3_CSV.zip", 3,
                ["mktrf", "smb", "hml", "rmw", "cma", "rf"])
    mom = _grab(f"{base}/F-F_Momentum_Factor_CSV.zip", 13, ["umd"])
    out = ff5.join(mom, how="left")
    cache.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache)
    return out
