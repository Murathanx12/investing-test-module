"""Masked / synthetic historical scenarios — the contamination machinery.

An LLM cannot "believe it is 2015": it has read 2015. This module builds the
only two things that make historical LLM evaluation meaningful:

  1. A MASKED view of a real situation — identity, absolute dates and absolute
     magnitudes removed, facts preserved as cross-sectional percentiles.
  2. A SYNTHETIC view — the masked facts wrapped in a fabricated company, a
     scrambled date and jittered percentiles, so the scenario provably cannot
     exist in any training corpus. This is the scale path: unlimited scenarios
     can be generated from the panel that no model has memorized.

Plus the CANARY: ask the model to identify what it is looking at. If it can,
the sample is burned and the masking is not yet a control.

Everything is computed from the survivorship-free panel + OSAP + CRSP PIT
names. Nothing reads yfinance, and no arm sees a fact dated after its own
formation month.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT

logger = logging.getLogger(__name__)

STOCKNAMES = MODULE_ROOT / "data" / "wrds_raw" / "crsp_stocknames.parquet"

SIC_DIVISION = [
    (1, 999, "agriculture"), (1000, 1499, "mining"), (1500, 1799, "construction"),
    (2000, 3999, "manufacturing"), (4000, 4999, "transport or utilities"),
    (5000, 5199, "wholesale trade"), (5200, 5999, "retail trade"),
    (6000, 6799, "finance, insurance or real estate"),
    (7000, 8999, "services"), (9000, 9999, "public administration"),
]

FAKE_PREFIX = ["Arden", "Belmar", "Corvin", "Dalmoor", "Elstree", "Fennick",
               "Garvey", "Halcyon", "Iverson", "Jandra", "Kestrel", "Lindow",
               "Marrow", "Norhaven", "Orrick", "Pellham", "Quarry", "Ridgeley",
               "Selwyn", "Tarnish", "Umbrey", "Vardon", "Wexler", "Yarrow"]
FAKE_SUFFIX = ["Industries", "Holdings", "Systems", "Group", "Works",
               "Partners", "Corporation", "Enterprises", "Technologies"]


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
class Event:
    """One historical situation, with its PIT facts and its realized outcome."""

    event_id: str
    permno: str
    formation_month: str          # YYYY-MM-DD (month end)
    company: str
    ticker: str
    sector: str
    # PIT cross-sectional percentiles (0-100) among eligible peers that month
    pct_ret_12m: int
    pct_vol_12m: int
    pct_gross_profit: int
    pct_book_to_market: int
    pct_mom_12_1: int
    n_peers: int
    # outcome (never shown to the model)
    fwd12_stock: float
    fwd12_market: float
    beat_market: bool
    months_realized: int


def _pct(frame_row: pd.Series, elig: pd.Series) -> pd.Series:
    x = frame_row.where(elig)
    return (x.rank(pct=True) * 100).round()


def build_events(spine, lib, *, first="2005-01-31", last="2021-12-31",
                 segment="largemid", n_per_class=60, seed=20260808) -> list[Event]:
    """Sample outcome-balanced events with complete PIT facts."""
    from aegis_brain.pf.panel63 import eligibility

    panel = spine.panel
    elig = eligibility(spine, segment)
    ret = panel.monthly_ret
    months = ret.index

    # trailing 12m total return INCLUDING the most recent month (distinct from
    # 12-1 momentum, which skips it) — computed here so the two facts are not
    # the same number wearing two labels
    trail12 = np.log1p(ret.clip(lower=-0.99)).rolling(12, min_periods=12).sum()
    feats = {
        "pct_ret_12m": trail12,
        "pct_vol_12m": lib.get("native:vol_12m_low"),
        "pct_gross_profit": lib.get("osap:GP"),
        "pct_book_to_market": lib.get("osap:BM"),
        "pct_mom_12_1": lib.get("native:mom_12_1"),
    }
    names = pd.read_parquet(STOCKNAMES, columns=["permno", "namedt", "nameenddt",
                                                 "ticker", "comnam", "siccd"])
    names["permno"] = names["permno"].astype("int64").astype(str)

    lo, hi = pd.Timestamp(first), pd.Timestamp(last)
    form_months = [m for m in months if lo <= m <= hi]
    rng = np.random.default_rng(seed)

    pos: list[Event] = []
    neg: list[Event] = []
    order = rng.permutation(len(form_months))
    for oi in order:
        m = form_months[oi]
        pos_i = months.get_loc(m)
        fwd_idx = months[pos_i + 1: pos_i + 13]
        if len(fwd_idx) < 12:
            continue
        e = elig.loc[m]
        cand = e[e].index
        if len(cand) < 200:
            continue
        pctiles = {k: _pct(f.loc[m], e) for k, f in feats.items()}
        ok = pd.concat(pctiles.values(), axis=1).notna().all(axis=1)
        cand = [c for c in cand if ok.get(c, False)]
        if len(cand) < 100:
            continue

        mkt_cum = float((1 + spine.mkt.reindex(fwd_idx)).prod())
        for sym in rng.permutation(cand)[:6]:
            r = ret.loc[fwd_idx, sym]
            realized = int(r.notna().sum())
            if realized == 0:
                continue
            # compound realized months; a name that stops trading is treated as
            # liquidated into the index for the remainder (delisting kept, not dropped)
            stock_cum = float((1 + r.dropna()).prod())
            if realized < 12:
                rest = spine.mkt.reindex(fwd_idx).iloc[realized:]
                stock_cum *= float((1 + rest).prod())
            nm = names[(names.permno == sym) & (names.namedt <= m)
                       & (names.nameenddt >= m)]
            if nm.empty:
                continue
            row = nm.iloc[-1]
            comnam = str(row["comnam"]).title()
            ticker = str(row["ticker"])
            if not ticker or ticker == "<NA>":
                continue
            ev = Event(
                event_id=hashlib.sha256(
                    f"{sym}|{m.date()}".encode()).hexdigest()[:12],
                permno=str(sym), formation_month=str(m.date()),
                company=comnam, ticker=ticker,
                sector=sic_division(row["siccd"]),
                pct_ret_12m=int(pctiles["pct_ret_12m"][sym]),
                pct_vol_12m=int(100 - pctiles["pct_vol_12m"][sym]),  # high = volatile
                pct_gross_profit=int(pctiles["pct_gross_profit"][sym]),
                pct_book_to_market=int(pctiles["pct_book_to_market"][sym]),
                pct_mom_12_1=int(pctiles["pct_mom_12_1"][sym]),
                n_peers=int(len(cand)),
                fwd12_stock=round(stock_cum - 1, 4),
                fwd12_market=round(mkt_cum - 1, 4),
                beat_market=bool(stock_cum > mkt_cum),
                months_realized=realized)
            (pos if ev.beat_market else neg).append(ev)
        if len(pos) >= n_per_class and len(neg) >= n_per_class:
            break

    if len(pos) < n_per_class or len(neg) < n_per_class:
        raise RuntimeError(f"only found {len(pos)}/{len(neg)} events — "
                           "refusing to run an unbalanced sample")
    out = pos[:n_per_class] + neg[:n_per_class]
    rng.shuffle(out)
    logger.info("event set: %d events, %d beat / %d lag", len(out),
                sum(e.beat_market for e in out),
                sum(not e.beat_market for e in out))
    return out


# ── the four disclosure arms ────────────────────────────────────────────────
ARMS = ("A0_named_raw", "A1_named_instructed", "A2_masked", "A3_synthetic")


def _facts(e: Event, jitter: int = 0, rng: np.random.Generator | None = None) -> str:
    def j(v: int) -> int:
        if not jitter or rng is None:
            return v
        return int(np.clip(v + rng.integers(-jitter, jitter + 1), 1, 99))
    return (
        f"- Industry: {e.sector}\n"
        f"- Liquidity: among the ~{e.n_peers} most traded US-listed common stocks\n"
        f"- Trailing 12-month total return: {j(e.pct_ret_12m)}th percentile of peers\n"
        f"- Trailing 12-month volatility: {j(e.pct_vol_12m)}th percentile "
        f"(higher = more volatile)\n"
        f"- Gross profitability: {j(e.pct_gross_profit)}th percentile\n"
        f"- Book-to-market: {j(e.pct_book_to_market)}th percentile "
        f"(higher = cheaper on book value)\n"
        f"- 12-1 month momentum: {j(e.pct_mom_12_1)}th percentile"
    )


def fake_identity(e: Event) -> tuple[str, str, str]:
    """Deterministic fabricated name/ticker/date for the synthetic arm."""
    h = int(hashlib.sha256(e.event_id.encode()).hexdigest()[:8], 16)
    name = f"{FAKE_PREFIX[h % len(FAKE_PREFIX)]} {FAKE_SUFFIX[(h // 7) % len(FAKE_SUFFIX)]}"
    ticker = (FAKE_PREFIX[h % len(FAKE_PREFIX)][:3] + chr(65 + h % 26)).upper()
    year = 2100 + (h % 40)          # unambiguously outside any training corpus
    month = 1 + (h // 13) % 12
    return name, ticker, f"{year}-{month:02d}"


def forecast_prompt(e: Event, arm: str) -> tuple[str, str]:
    """(system, user) for the forecast call. Facts identical across arms."""
    system = ("You are a careful equity analyst. You answer only with strict "
              "JSON matching the requested schema. You never invent facts that "
              "were not given to you.")
    ask = ('Return JSON exactly: {"p_beat": <number 0-1>, "abstain": '
           '<true|false>, "driver": "<one of: valuation, profitability, '
           'momentum, volatility, industry, insufficient_information>"}\n'
           "p_beat = probability that this stock's TOTAL RETURN over the NEXT "
           "12 MONTHS exceeds the US stock market's total return over the same "
           "12 months.")

    if arm in ("A0_named_raw", "A1_named_instructed"):
        head = (f"Company: {e.company} (ticker {e.ticker}).\n"
                f"Today's date: {e.formation_month}.\n\n"
                f"Facts as of today:\n{_facts(e)}\n\n")
        if arm == "A1_named_instructed":
            system += (
                " CRITICAL CONSTRAINT: you are standing in the past, on the "
                "date given. You must NOT use any knowledge of events after "
                "that date. Do not use your memory of what this company's "
                "stock actually did afterwards, of later earnings, later "
                "products, later crises, or later prices. Reason ONLY from "
                "the facts stated and from general principles that were "
                "already known on that date. If you find yourself recalling "
                "the actual outcome, discard it and reason as if it were "
                "unknown.")
            head = ("[HISTORICAL SIMULATION — you are in the past; post-date "
                    "knowledge is forbidden]\n\n") + head
        return system, head + ask

    if arm == "A2_masked":
        head = ("A US-listed company, identity withheld. The date is withheld; "
                "call the present 'month 0'.\n\n"
                f"Facts as of month 0:\n{_facts(e)}\n\n")
        return system, head + ask

    if arm == "A3_synthetic":
        rng = np.random.default_rng(int(e.event_id[:8], 16) % (2 ** 32))
        name, ticker, date = fake_identity(e)
        head = ("[SIMULATED SCENARIO — this company and date are fictional; "
                "no real-world facts about them exist]\n\n"
                f"Company: {name} (ticker {ticker}).\n"
                f"Simulation date: {date}.\n\n"
                f"Facts as of the simulation date:\n"
                f"{_facts(e, jitter=3, rng=rng)}\n\n")
        return system, head + ask

    raise ValueError(f"unknown arm {arm!r}")


def canary_prompt(e: Event, arm: str) -> tuple[str, str]:
    """The contamination probe, asked BEFORE the forecast so it cannot prime it."""
    system = ("You answer only with strict JSON matching the requested schema. "
              "Honesty about uncertainty is more valuable than a guess.")
    if arm in ("A0_named_raw", "A1_named_instructed"):
        user = (f"Company: {e.company} (ticker {e.ticker}). "
                f"Date: {e.formation_month}.\n\n"
                "Do you recall, from your training data, what happened to this "
                "company's stock over the 12 months following that date?\n"
                'Return JSON exactly: {"recall": "<YES|NO>", '
                '"direction": "<UP|DOWN|UNSURE>", "what": "<=25 words>"}')
        return system, user

    _, _, fake_date = fake_identity(e)
    ctx = (_facts(e) if arm == "A2_masked"
           else _facts(e, jitter=3,
                       rng=np.random.default_rng(int(e.event_id[:8], 16) % (2 ** 32))))
    user = ("The following describes a real US-listed company at some point in "
            "history, with its identity and date removed.\n\n"
            f"{ctx}\n\n"
            "Can you identify it?\n"
            'Return JSON exactly: {"company": "<name or UNKNOWN>", '
            '"ticker": "<ticker or UNKNOWN>", "year": <4-digit year or 0>, '
            '"confidence": "<HIGH|MEDIUM|LOW>"}')
    return system, user


def events_to_frame(events: list[Event]) -> pd.DataFrame:
    return pd.DataFrame([asdict(e) for e in events])


def cache_key(arm: str, event_id: str, kind: str, model: str) -> str:
    return hashlib.sha256(f"{model}|{arm}|{kind}|{event_id}".encode()).hexdigest()[:16]


def parse_json(text: str) -> dict:
    """Tolerant JSON extraction — the model sometimes wraps in fences."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        t = t[4:] if t.lower().startswith("json") else t
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        raise ValueError(f"no JSON object in response: {text[:120]!r}")
    return json.loads(t[i:j + 1])
