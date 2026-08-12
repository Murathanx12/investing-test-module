"""MARKET-GRAPH-1 stage 4 — counterparty names to permnos, and edges to pairs.

THE ATTRITION THAT DECIDES THIS TRIAL
=====================================
The extractor names counterparties in English. The panel is keyed by permno.
Everything between those two facts is loss, and the loss is not random: TSMC,
Samsung, Fujitsu and Takeda are real, material, correctly-extracted edges that
CANNOT enter the study because they are not US-listed CRSP securities. Neither
can a private supplier, a subsidiary, or a customer smaller than the 300th
largest company in the country.

So the graded graph is a biased subgraph of the extracted graph — biased
towards large, US-listed counterparties — and every number in the report is a
statement about that subgraph, not about "economic relationships" in general.
This module's job is to make the size and shape of that bias VISIBLE, which is
why it records the route each edge resolved by, counts every drop, and — new in
this version — CLASSIFIES every drop into the two kinds that mean opposite
things:

  `outside_universe`  the name IS a US-listed CRSP security, just not one of
                      the 300 largest on that date. Fixable by widening N.
  `not_in_crsp`       the name is not a CRSP security at any date under any
                      spelling: foreign, private, a subsidiary, a brand.
                      NOT fixable by anything. This is the trial's ceiling.

The first build reported a 13.9% resolution rate and stopped there. 13.9% with
an unknown split between those two buckets is not a diagnosis; it is a number
that could mean "the matcher is broken" or "10-Ks mostly name foreign and
private counterparties", and those call for opposite responses.

SIX ROUTES, IN PRIORITY ORDER
-----------------------------
  `ticker`      the emitted ticker matches a CRSP ticker VALID at the filing
                date. Strongest, because a ticker is nearly unambiguous — but
                only PIT: matching a 2024 ticker against a 2015 filing is the
                §13 leak.
  `name_pit`    normalised name equals a CRSP company name valid at that date.
  `name_any`    normalised name equals ANY historical CRSP name of the permno,
                or an EDGAR name_key for a CIK that bridges to the permno. A
                filing may use a former name, so this route is real; it is
                ranked below PIT because it is looser.
  `rename`      a declared legal rename (`RENAMES` below), applied and then put
                back through the PIT lookup — so a 2014 filing saying "Google"
                still does not match ALPHABET, whose CRSP name window opens in
                October 2015. Every entry is a matter of public record and the
                whole table is printed in the report, so any reader can
                subtract this route and re-read every number without it.
  `prefix`      the emitted name is an exact leading TOKEN SEQUENCE of exactly
                one universe name — "ADOBE" for `ADOBE SYS`. Required to be
                UNIQUE in that date's universe; ambiguous prefixes are dropped
                and counted, never guessed.
  `prefix_rev`  the reverse: a universe name is an exact leading token sequence
                of the emitted name — `BANK OF AMERICA` for "Bank of America
                Merrill Lynch". The longest such match wins; ties drop.

No edit distance and no substring containment: "AMERICAN AIRLINES" must not
match "AMERICAN EXPRESS" because six characters agree. Prefix matching is on
WHOLE TOKENS, must be unique, and a ONE-TOKEN prefix must additionally be five
characters or longer and absent from `GENERIC_HEADS` — otherwise "FIRST",
"UNITED" and "GENERAL" become resolvers. A matcher that guesses manufactures
edges nobody wrote, and edges nobody wrote are this trial's entire risk.

WHY THE ROUTES WERE WIDENED, AND WHEN
-------------------------------------
Exact matching alone resolved 13.9% of a 12-document pilot, and the failures
were not exotic: "Adobe" against `ADOBE SYS`, "Intel" against `INTEL`,
"Google" against `ALPHABET`. The rule was widened at that point — BEFORE any
forward correlation, any H1 number and any H2 number had been computed or
looked at. It is a power decision taken blind to outcomes, which is the only
kind allowed after a pre-registration. To keep it honest this module computes
BOTH rules on every run and reports both rates side by side; `--strict` writes
the exact-only graph instead, so the whole trial can be re-graded on the narrow
matcher without editing a line.

ONE NAME, TWO PERMNOS
---------------------
A dual-class issuer has one name and two permnos (`ALPHABET` is 14542 and
90319). Taking whichever the dictionary happened to store first is a silent
coin-flip on which share class an edge lands on. Candidates sharing a CRSP
`permco` are the SAME company, and the largest market cap on that date wins —
a share-class choice read off the capitalisation table, blind to outcomes.
Candidates spanning different permcos are genuinely different companies and are
dropped as ambiguous, and counted.

    python -m scripts.mg1_resolve            # widened matcher (default)
    python -m scripts.mg1_resolve --strict   # exact-only, for the sensitivity
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT                       # noqa: E402
from aegis_brain.events.name_link import (crsp_name_windows,     # noqa: E402
                                          normalize_name)
from scripts import mg1_config as C                              # noqa: E402

OUT = MODULE_ROOT / "runs" / "MARKET-GRAPH-1"
STOCKNAMES = MODULE_ROOT / "data" / "wrds_raw" / "crsp_stocknames.parquet"
CIKLOOKUP = MODULE_ROOT / "data" / "events" / "cik_lookup.parquet"

FAR = pd.Timestamp("2100-01-01")

#: Declared legal renames, colloquial-name key -> the successor's name key.
#: Every row is a public corporate fact, not a judgement call, and the whole
#: table is reproduced in the report so this route can be subtracted. It is
#: deliberately SHORT: each entry is a degree of freedom, and a long alias list
#: assembled by staring at unresolved names would be tuning dressed as data
#: cleaning. Both sides are pushed through `normalize_name` before use, because
#: a hand-typed right-hand side that does not normalise to a real CRSP key is a
#: rule that never fires and never says so.
#:
#: `PHILIP MORRIS -> ALTRIA` was in the first draft of this table and is
#: DELIBERATELY ABSENT: Philip Morris International has been a separately
#: listed company since 2008, so that alias would have merged two live tickers
#: across the whole sample. A wrong alias does not fail loudly; it manufactures
#: edges between the wrong pair of companies.
#: The right-hand sides are spelled the way CRSP spells them, because CRSP's
#: `comnam` is a 32-character abbreviated field ("INTERNATIONAL BUSINESS MACHS
#: COR") and an alias pointing at the plain-English name would normalise to a
#: key that does not exist. `main` VERIFIES every entry against the universe's
#: own key set at startup and prints the dead ones: an alias that never fires
#: is the house failure mode in miniature — a rule that runs green and does
#: nothing.
RENAMES_RAW = {
    # legal successions
    "Google": "Alphabet Inc",
    "Facebook": "Meta Platforms Inc",
    "Sprint Nextel": "Sprint Corp",
    "Dow Chemical": "Dow Inc",
    "United Technologies": "Raytheon Technologies Corp",
    "Square": "Block Inc",
    "Kraft": "Kraft Heinz Co",
    "Time Warner Cable": "Charter Communications Inc",
    # universally-known initialisms, expanded to CRSP's spelling. These are
    # mechanical expansions of an acronym, not judgements about which company a
    # filing "probably" meant. HP and TI are deliberately absent: "HP" is HP
    # Inc or Hewlett Packard Enterprise depending on the year, and "TI" is not
    # unambiguous at all.
    "IBM": "International Business Machs Cor",
    "GE": "General Electric Co",
    "GM": "General Motors Co",
    "J&J": "Johnson & Johnson",
    "P&G": "Procter & Gamble Co",
    "UPS": "United Parcel Service Inc",
    "AMD": "Advanced Micro Devices Inc",
    "EMC": "E M C Corp MA",
    "HPE": "Hewlett Packard Entr Co",
}

#: `normalize_name` turns an apostrophe into a SPACE, so "Lowe's" becomes the
#: two-token key "LOWE S" and never matches CRSP's "LOWES". Folding the
#: apostrophe out first is pure punctuation folding — it changes no word — and
#: it is applied to BOTH sides so the two keys are built by the same function.
_APOS = re.compile(r"[‘’'`´]")


def nkey(s: str) -> str:
    return normalize_name(_APOS.sub("", s or ""))


RENAMES = {nkey(k): nkey(v) for k, v in RENAMES_RAW.items()}

#: One-token prefixes that are corporate wallpaper. Without this list a single
#: universe name beginning "GENERAL" turns every mention of a general anything
#: into an edge, and the uniqueness test cannot catch it because uniqueness is
#: exactly what makes it fire.
GENERIC_HEADS = {
    "FIRST", "UNITED", "GENERAL", "AMERICAN", "NATIONAL", "GLOBAL", "PACIFIC",
    "ATLANTIC", "NORTHERN", "SOUTHERN", "WESTERN", "EASTERN", "CENTRAL",
    "STANDARD", "PREMIER", "ALLIANCE", "CAPITAL", "CONTINENTAL", "FEDERAL",
    "INTERSTATE", "REPUBLIC", "UNION", "UNIVERSAL", "SUMMIT", "PIONEER",
    "LIBERTY", "HERITAGE", "INDEPENDENT", "COMMUNITY", "MERIDIAN", "CROWN",
    "EMPIRE", "FRONTIER", "HORIZON", "LEGACY", "SENTINEL", "VANGUARD",
}
MIN_SINGLE_TOKEN_CHARS = 5


# ── the index ───────────────────────────────────────────────────────────────

class NameIndex:
    """Windowed ticker/name/prefix lookups over one set of permnos."""

    def __init__(self, permnos: set[int], mcap: dict) -> None:
        self.mcap = mcap                      # (date-ordinal, permno) -> mcap
        sn = pd.read_parquet(STOCKNAMES,
                             columns=["permno", "permco", "namedt",
                                      "nameenddt", "ticker", "comnam"])
        sn["permno"] = sn["permno"].astype(int)
        sn = sn[sn["permno"].isin(permnos)].copy()
        sn["namedt"] = pd.to_datetime(sn["namedt"])
        sn["nameenddt"] = pd.to_datetime(sn["nameenddt"]).fillna(FAR)
        sn["name_key"] = sn["comnam"].map(nkey)
        self.permco = dict(zip(sn["permno"], sn["permco"].astype(int)))

        self.tick: dict[str, list] = defaultdict(list)
        self.name: dict[str, list] = defaultdict(list)
        self.pref: dict[str, list] = defaultdict(list)
        for r in sn.itertuples():
            if isinstance(r.ticker, str) and r.ticker.strip():
                self.tick[r.ticker.upper().strip()].append(
                    (r.namedt, r.nameenddt, int(r.permno)))
            if not r.name_key:
                continue
            self.name[r.name_key].append(
                (r.namedt, r.nameenddt, int(r.permno)))
            toks = r.name_key.split()
            for k in range(1, len(toks)):        # PROPER prefixes only
                self.pref[" ".join(toks[:k])].append(
                    (r.namedt, r.nameenddt, int(r.permno)))

        # any-time name -> permno, via CRSP history and the EDGAR CIK bridge
        any_map: dict[str, set] = defaultdict(set)
        for k, p in zip(sn["name_key"], sn["permno"]):
            if k:
                any_map[k].add(int(p))
        ed = pd.read_parquet(CIKLOOKUP,
                             columns=["name_key", "cik"]).drop_duplicates()
        cw = crsp_name_windows()
        cw = cw[cw["permno"].isin(permnos)]
        bridge = ed.merge(cw[["name_key", "permno"]].drop_duplicates(),
                          on="name_key", how="inner")
        cik2p: dict[int, set] = defaultdict(set)
        for c, p in zip(bridge["cik"], bridge["permno"]):
            cik2p[int(c)].add(int(p))
        for k, c in zip(ed["name_key"], ed["cik"]):
            if k and cik2p.get(int(c)):
                any_map[k].update(cik2p[int(c)])
        self.any: dict[str, set] = dict(any_map)

    # ── one candidate set -> one permno, or None ────────────────────────────
    def _pick(self, cands: set[int], when: pd.Timestamp) -> tuple:
        """(permno, why). Same-permco candidates collapse by market cap."""
        if not cands:
            return None, "none"
        if len(cands) == 1:
            return next(iter(cands)), "unique"
        cos = {self.permco.get(p) for p in cands}
        if len(cos) > 1:
            return None, "ambiguous_across_companies"
        best, best_mc = None, -1.0
        for p in cands:
            mc = self.mcap.get((when.year * 100 + when.month, p), -1.0)
            if mc > best_mc:
                best, best_mc = p, mc
        return best, "share_class"

    def _win(self, rows, when):
        return {p for a, b, p in rows if a <= when <= b}

    def by_ticker(self, tk: str, when):
        return self._pick(self._win(self.tick.get(tk, ()), when), when)

    def by_name_pit(self, key: str, when):
        return self._pick(self._win(self.name.get(key, ()), when), when)

    def by_name_any(self, key: str, when):
        return self._pick(set(self.any.get(key, ())), when)

    def by_prefix(self, key: str, when):
        toks = key.split()
        if len(toks) == 1 and (len(toks[0]) < MIN_SINGLE_TOKEN_CHARS
                               or toks[0] in GENERIC_HEADS):
            return None, "generic_head"
        return self._pick(self._win(self.pref.get(key, ()), when), when)

    def by_prefix_rev(self, key: str, when):
        """A universe name that is a leading token sequence of `key`."""
        toks = key.split()
        for k in range(len(toks) - 1, 0, -1):    # longest first = most specific
            sub = " ".join(toks[:k])
            if k == 1 and (len(sub) < MIN_SINGLE_TOKEN_CHARS
                           or sub in GENERIC_HEADS):
                break
            p, why = self._pick(self._win(self.name.get(sub, ()), when), when)
            if p is not None:
                return p, why
        return None, "none"


STRICT_ROUTES = ("ticker", "name_pit", "name_any")
WIDE_ROUTES = ("ticker", "name_pit", "name_any", "rename", "prefix",
               "prefix_rev")


def resolve_one(idx: NameIndex, name_key: str, tk: str | None,
                when: pd.Timestamp, routes) -> tuple:
    for route in routes:
        if route == "ticker":
            if not tk:
                continue
            p, why = idx.by_ticker(tk, when)
        elif route == "name_pit":
            p, why = idx.by_name_pit(name_key, when) if name_key else (None, "")
        elif route == "name_any":
            p, why = idx.by_name_any(name_key, when) if name_key else (None, "")
        elif route == "rename":
            alias = RENAMES.get(name_key)
            if not alias:
                continue
            p, why = idx.by_name_pit(alias, when)
            if p is None:
                p, why = idx.by_name_any(alias, when)
        elif route == "prefix":
            p, why = idx.by_prefix(name_key, when) if name_key else (None, "")
        else:
            p, why = (idx.by_prefix_rev(name_key, when) if name_key
                      else (None, ""))
        if p is not None:
            return int(p), route, why
    return None, None, None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="write the exact-only graph instead of the widened "
                         "one (both rates are reported either way)")
    args = ap.parse_args()

    uni = pd.read_parquet(OUT / "universe.parquet")
    uni["date"] = pd.to_datetime(uni["date"])
    # LAST record per accession wins. `mg1_extract --repair` appends a fresh
    # reply for every document that was truncated at the token cap; reading the
    # file as a flat list would count those documents twice, once with the
    # broken answer and once with the good one.
    by_acc: dict = {}
    for line in (OUT / "edges_raw.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        if r.get("status") == "ok":
            by_acc[r["accession"]] = r
    edges_rows = list(by_acc.values())
    n_trunc = sum(1 for r in edges_rows
                  if str(r.get("parse_note") or "").startswith("json"))
    print(f"documents with a reply: {len(edges_rows):,}  "
          f"(still-unparseable after any repair pass: {n_trunc:,})",
          flush=True)

    mcap = {(d.year * 100 + d.month, int(p)): float(m)
            for d, p, m in zip(uni["date"], uni["permno"], uni["mcap"])}
    uni_permnos = set(uni["permno"].astype(int))
    idx = NameIndex(uni_permnos, mcap)
    print(f"universe permnos {len(uni_permnos)}  tickers {len(idx.tick):,}  "
          f"names {len(idx.name):,}  prefixes {len(idx.pref):,}  "
          f"any-time keys {len(idx.any):,}", flush=True)

    # An alias whose target is not a real key is a rule that runs green and
    # does nothing. Say so, at startup, before it can quietly not-fire 3,000
    # times.
    dead = sorted(k for k, v in RENAMES.items()
                  if v not in idx.name and v not in idx.any)
    print(f"  alias table: {len(RENAMES)} entries, "
          f"{len(RENAMES) - len(dead)} with a live target"
          + (f"; DEAD -> {dead}" if dead else ""), flush=True)

    # The CRSP-wide index exists ONLY to classify the failures: a name it can
    # resolve is a US-listed company that the top-300 cut excluded, which is a
    # universe-size limit; a name it cannot is foreign, private or a
    # subsidiary, which is the trial's hard ceiling.
    all_permnos = set(pd.read_parquet(STOCKNAMES,
                                      columns=["permno"])["permno"].astype(int))
    wide = NameIndex(all_permnos, mcap)
    print(f"CRSP-wide diagnostic index: {len(all_permnos):,} permnos",
          flush=True)

    routes_strict, routes_wide = Counter(), Counter()
    miss_kind = Counter()
    unresolved_names = Counter()
    out_rows = []
    n_edges = 0
    for r in edges_rows:
        when = pd.Timestamp(r["filing_date"])
        subj = int(r["permno"])
        for e in r["edges"]:
            n_edges += 1
            key = nkey(e["counterparty_name"])
            tk = (e.get("counterparty_ticker") or "").upper().strip() or None

            ps, rs, _ = resolve_one(idx, key, tk, when, STRICT_ROUTES)
            if ps is not None and ps != subj:
                routes_strict[rs] += 1
            elif ps is not None:
                routes_strict["self_loop"] += 1
            else:
                routes_strict["unresolved"] += 1

            p, route, why = resolve_one(idx, key, tk, when, WIDE_ROUTES)
            if p is None:
                routes_wide["unresolved"] += 1
                unresolved_names[e["counterparty_name"]] += 1
                pw, rw, _ = resolve_one(wide, key, tk, when, WIDE_ROUTES)
                miss_kind["outside_universe" if pw is not None
                          else "not_in_crsp"] += 1
                continue
            if p == subj:
                routes_wide["self_loop_dropped"] += 1
                continue
            routes_wide[route] += 1
            out_rows.append({
                "accession": r["accession"], "subject_permno": subj,
                "counterparty_permno": int(p), "filing_date": when,
                "type": e["type"], "direction": e["direction"],
                "confidence": float(e["confidence"]),
                "quote_verified": bool(e.get("quote_verified", False)),
                "route": route, "strict_route": rs or "",
                "counterparty_name": e["counterparty_name"],
            })

    n_strict = n_edges - routes_strict["unresolved"] - routes_strict["self_loop"]
    ed = pd.DataFrame(out_rows)
    if args.strict:
        ed = ed[ed["strict_route"] != ""].copy()
    resolved = len(ed)
    print(f"\nraw edges {n_edges:,}")
    print(f"  EXACT-ONLY matcher : {n_strict:,} resolved "
          f"({n_strict / max(1, n_edges):.1%})")
    print(f"  WIDENED matcher    : {resolved:,} resolved "
          f"({resolved / max(1, n_edges):.1%})")
    print("  strict routes:", json.dumps(dict(routes_strict)))
    print("  wide routes  :", json.dumps(dict(routes_wide)))
    print("  the residue  :", json.dumps(dict(miss_kind)))
    print("  top unresolved names:",
          json.dumps(unresolved_names.most_common(30)))

    if ed.empty:
        raise SystemExit("no edges resolved — stopping rather than reporting 0")

    ed = ed.drop_duplicates(
        ["accession", "subject_permno", "counterparty_permno", "type"])
    ed.to_parquet(OUT / "edges_resolved.parquet", index=False)

    # ── attach to (cut date, pair): an edge is visible from its filing date
    # until superseded, and is therefore always older than the window it is
    # graded on.
    doc_of = uni[["date", "permno", "accession", "ff12"]].rename(
        columns={"permno": "subject_permno", "ff12": "ff12_i"})
    live = doc_of.merge(ed, on=["subject_permno", "accession"], how="inner")
    print(f"edge-instances live at some cut date: {len(live):,}")

    live["lo"] = np.minimum(live["subject_permno"],
                            live["counterparty_permno"])
    live["hi"] = np.maximum(live["subject_permno"],
                            live["counterparty_permno"])
    # An edge only counts at a cut date if BOTH ends are in that date's
    # universe. The counterparty may have been resolved from a filing at a date
    # when it was not itself among the top 300.
    memb = set(zip(uni["date"], uni["permno"]))
    live = live[[(d, p) in memb for d, p in zip(live["date"],
                                                live["counterparty_permno"])]]
    print(f"  ... with BOTH ends in that date's universe: {len(live):,}")
    ff = {(d, p): f for d, p, f in zip(uni["date"], uni["permno"], uni["ff12"])}
    live["ff12_j"] = [ff.get((d, p)) for d, p in
                      zip(live["date"], live["counterparty_permno"])]
    live["same_sector"] = live["ff12_i"] == live["ff12_j"]

    live.to_parquet(OUT / "edge_instances.parquet", index=False)

    meta = {
        "matcher_written": "strict" if args.strict else "widened",
        "n_documents": len(edges_rows),
        "n_raw_edges": n_edges,
        "n_resolved_strict": int(n_strict),
        "resolution_rate_strict": round(n_strict / max(1, n_edges), 4),
        "n_resolved_widened": int(len(out_rows)),
        "resolution_rate_widened": round(len(out_rows) / max(1, n_edges), 4),
        "routes_strict": dict(routes_strict),
        "routes_widened": dict(routes_wide),
        "unresolved_residue": dict(miss_kind),
        "top_unresolved_names": unresolved_names.most_common(50),
        "renames_applied": RENAMES,
        "n_written": int(resolved),
        "n_edge_instances_live": int(len(live)),
        "n_distinct_pairs_with_edge": int(
            live.groupby(["date", "lo", "hi"]).ngroups),
        "by_type": live["type"].value_counts().to_dict(),
        "by_route": live["route"].value_counts().to_dict(),
        "quote_verified_rate": float(live["quote_verified"].mean()),
        "mean_confidence": float(live["confidence"].mean()),
        "same_sector_share_of_edges": float(live["same_sector"].mean()),
    }
    (OUT / "resolve_meta.json").write_text(json.dumps(meta, indent=2,
                                                      default=str),
                                           encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items()
                      if k != "top_unresolved_names"}, indent=2, default=str))


if __name__ == "__main__":
    main()
