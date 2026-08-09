"""The masked decision environment: a monthly slate of candidates, and its grading.

THE DESIGN POINT, because it is what makes the night's answer worth anything:

    The engine's ranking is a deterministic function of exactly the percentile
    facts the LLM is shown. Neither decider sees anything the other does not.
    The composite SCORE and RANK are withheld, so the model cannot simply copy
    the answer; it must re-derive it, or beat it, from the same evidence.

So a difference between the two books is a difference in *reasoning over a
shared information set* — not a data advantage in either direction. Both pick
from the same 40 names in the same month, which makes the comparison paired and
kills most of the market noise that would otherwise swamp 204 observations.

Masking follows the protocol AMNESIA already validated (0/240 identifications):
no identity, no absolute date, no absolute price or size — facts as
cross-sectional percentiles among that month's eligible peers.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.night3.experience import FINGERPRINT_FEATURES

logger = logging.getLogger(__name__)

STOCKNAMES = MODULE_ROOT / "data" / "wrds_raw" / "crsp_stocknames.parquet"

# The engine under test: PF-2's PROF-COMPOSITE-150 signal, unchanged.
PROF_SIGNALS = (("osap:GP", 1.0), ("osap:OperProfRD", 1.0),
                ("osap:CBOperProf", 1.0))

SIC_DIVISION = [
    (1, 999, "agriculture"), (1000, 1499, "mining"), (1500, 1799, "construction"),
    (2000, 3999, "manufacturing"), (4000, 4999, "transport or utilities"),
    (5000, 5199, "wholesale trade"), (5200, 5999, "retail trade"),
    (6000, 6799, "finance, insurance or real estate"),
    (7000, 8999, "services"), (9000, 9999, "public administration"),
]


def sic_division(siccd) -> str:
    try:
        s = int(siccd)
    except (TypeError, ValueError):
        return "an unidentified industry"
    for lo, hi, name in SIC_DIVISION:
        if lo <= s <= hi:
            return name
    return "an unidentified industry"


@dataclass(frozen=True)
class Candidate:
    """One masked name on one slate. `label` is the model's only handle on it."""

    label: str                 # "A".."Z", "AA".. — position-shuffled, no identity
    permno: str
    sector: str
    engine_rank: int           # 1 = best by composite. NEVER shown to the model.
    pct_ret_12m: int
    pct_vol_12m: int
    pct_gross_profit: int
    pct_book_to_market: int
    pct_mom_12_1: int
    pct_size: int
    fwd_ret: float             # realized next-month total return
    prev_seen: bool = False    # was this name on last month's slate?

    @property
    def fingerprint(self) -> tuple[float, ...]:
        d = asdict(self)
        return tuple(float(d[f]) for f in FINGERPRINT_FEATURES)


@dataclass(frozen=True)
class Slate:
    formation_month: str       # YYYY-MM-DD, month end (masked from the model)
    realized_month: str
    candidates: tuple[Candidate, ...]
    benchmark_fwd: float       # market total return over the same month
    regime: str                # WALK-FORWARD label

    @property
    def n(self) -> int:
        return len(self.candidates)

    def by_label(self) -> dict[str, Candidate]:
        return {c.label: c for c in self.candidates}

    def information_state_hash(self) -> str:
        """Hash of everything a decider can see. Excludes outcomes by
        construction — if an outcome could change this hash, the hash would be
        leaking the future into the cache key."""
        payload = [
            {"label": c.label, "sector": c.sector,
             "f": [c.pct_ret_12m, c.pct_vol_12m, c.pct_gross_profit,
                   c.pct_book_to_market, c.pct_mom_12_1, c.pct_size]}
            for c in self.candidates]
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"))
            .encode()).hexdigest()[:16]


def _labels(n: int) -> list[str]:
    out = []
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i in range(n):
        out.append(alpha[i] if i < 26 else alpha[i // 26 - 1] + alpha[i % 26])
    return out


def _pct_rank(row: pd.Series, elig_row: pd.Series) -> pd.Series:
    return (row.where(elig_row).rank(pct=True) * 100).round()


def build_slates(spine, lib, score: pd.DataFrame, elig: pd.DataFrame, *,
                 first: str, last: str, slate_n: int = 40,
                 seed: int = 20260809) -> list[Slate]:
    """One slate per formation month: the engine's top `slate_n` eligible names.

    Timing is the module's standard convention and is structural: facts as of
    formation month m, realized return of month m+1. No fact used here is dated
    after its own formation month.
    """
    from aegis_brain.pf.regimes import trailing_12m_risk_on

    panel = spine.panel
    ret = panel.monthly_ret
    months = ret.index
    risk_on = trailing_12m_risk_on(spine.mkt)

    feats = {
        "pct_ret_12m": np.log1p(ret.clip(lower=-0.99)).rolling(12, min_periods=12).sum(),
        "pct_vol_12m": lib.get("native:vol_12m_low"),
        "pct_gross_profit": lib.get("osap:GP"),
        "pct_book_to_market": lib.get("osap:BM"),
        "pct_mom_12_1": lib.get("native:mom_12_1"),
        # dollar volume is the panel's PIT size/liquidity proxy — the same one
        # segment_mask uses to define small vs largemid. It is NOT market cap,
        # and is labelled as liquidity wherever the model reads it.
        "pct_size": panel.monthly_dollar_vol,
    }
    for k, v in feats.items():
        if v is None:
            raise RuntimeError(f"feature {k} is missing — refusing to build "
                               "slates with a silently absent feature")

    names = pd.read_parquet(STOCKNAMES,
                            columns=["permno", "namedt", "nameenddt", "siccd"])
    names["permno"] = names["permno"].astype("int64").astype(str)

    lo, hi = pd.Timestamp(first), pd.Timestamp(last)
    form_months = [m for m in months if lo <= m <= hi]
    rng = np.random.default_rng(seed)
    labels = _labels(slate_n)

    slates: list[Slate] = []
    prev_permnos: set[str] = set()
    skipped: dict[str, int] = {}

    for m in form_months:
        pos = months.get_loc(m)
        if pos + 1 >= len(months):
            skipped["no_forward_month"] = skipped.get("no_forward_month", 0) + 1
            continue
        nxt = months[pos + 1]
        e = elig.loc[m]
        s = score.loc[m].where(e).dropna()
        if len(s) < slate_n * 2:
            skipped["thin_universe"] = skipped.get("thin_universe", 0) + 1
            continue
        pctiles = {k: _pct_rank(f.loc[m], e) for k, f in feats.items()}
        top = s.nlargest(slate_n * 3).index          # over-select, then require
        rows: list[Candidate] = []                    # complete facts
        for sym in top:
            vals = {k: pctiles[k].get(sym) for k in feats}
            if any(v is None or not np.isfinite(v) for v in vals.values()):
                continue
            fwd = ret.at[nxt, sym] if sym in ret.columns else np.nan
            if not np.isfinite(fwd):
                # a name that stops trading is liquidated into the market for
                # the month (delisting kept, never dropped — dropping it would
                # re-import survivorship bias through the back door)
                fwd = float(spine.mkt.at[nxt])
            nm = names[(names.permno == sym) & (names.namedt <= m)
                       & (names.nameenddt >= m)]
            sector = sic_division(nm.iloc[-1]["siccd"]) if len(nm) else "an unidentified industry"
            rows.append(Candidate(
                label="", permno=str(sym), sector=sector, engine_rank=0,
                pct_ret_12m=int(vals["pct_ret_12m"]),
                pct_vol_12m=int(100 - vals["pct_vol_12m"]),   # high = volatile
                pct_gross_profit=int(vals["pct_gross_profit"]),
                pct_book_to_market=int(vals["pct_book_to_market"]),
                pct_mom_12_1=int(vals["pct_mom_12_1"]),
                pct_size=int(vals["pct_size"]),
                fwd_ret=float(fwd), prev_seen=str(sym) in prev_permnos))
            if len(rows) == slate_n:
                break
        if len(rows) < slate_n:
            skipped["incomplete_facts"] = skipped.get("incomplete_facts", 0) + 1
            continue

        # engine_rank follows the composite (rows are already in score order);
        # labels are then assigned in SHUFFLED order so position carries no
        # information about the engine's opinion
        ranked = [Candidate(**{**asdict(c), "engine_rank": i + 1})
                  for i, c in enumerate(rows)]
        order = rng.permutation(slate_n)
        final = tuple(Candidate(**{**asdict(ranked[j]), "label": labels[i]})
                      for i, j in enumerate(order))
        slates.append(Slate(
            formation_month=str(m.date()), realized_month=str(nxt.date()),
            candidates=final, benchmark_fwd=float(spine.mkt.at[nxt]),
            regime="risk_on" if bool(risk_on.get(m, True)) else "risk_off"))
        prev_permnos = {c.permno for c in final}

    if skipped:
        logger.info("slates skipped: %s", skipped)
    logger.info("built %d slates %s..%s (%d names each)", len(slates),
                slates[0].formation_month if slates else "-",
                slates[-1].formation_month if slates else "-", slate_n)
    return slates


# ── rendering: what the model actually reads ────────────────────────────────
def render_candidate(c: Candidate) -> str:
    return (f"{c.label}. {c.sector}\n"
            f"   trailing 12m return {c.pct_ret_12m}th pct | "
            f"volatility {c.pct_vol_12m}th pct (higher = more volatile) | "
            f"12-1 momentum {c.pct_mom_12_1}th pct\n"
            f"   gross profitability {c.pct_gross_profit}th pct | "
            f"book-to-market {c.pct_book_to_market}th pct (higher = cheaper) | "
            f"trading liquidity {c.pct_size}th pct")


def render_slate(slate: Slate) -> str:
    body = "\n".join(render_candidate(c) for c in slate.candidates)
    return (f"{slate.n} US-listed companies, identities withheld. The date is "
            "withheld; call the present 'month 0'. All figures are percentiles "
            "among that month's eligible peers.\n\n" + body)


# ── grading ─────────────────────────────────────────────────────────────────
def book_return(slate: Slate, picks: list[str], cost_bps: float,
                prev_picks: set[str] | None = None) -> tuple[float, float]:
    """Equal-weight one-month return of `picks`, and the turnover charged.

    Costs are charged on traded value at the same 25 bps the PF harness uses,
    so the LLM book and the engine book are penalized identically. A book that
    churns pays for it — otherwise 'the LLM adds value' could just mean 'the
    LLM trades more and we forgot to bill it'.
    """
    by = slate.by_label()
    sel = [by[p] for p in picks if p in by]
    if not sel:
        return 0.0, 0.0
    gross = float(np.mean([c.fwd_ret for c in sel]))
    cur = {c.permno for c in sel}
    if prev_picks is None:
        traded = 1.0
    else:
        traded = len(cur - prev_picks) / max(len(cur), 1)
    cost = traded * (cost_bps / 1e4)
    return gross - cost, traded
