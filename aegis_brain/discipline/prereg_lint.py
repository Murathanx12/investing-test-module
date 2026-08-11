"""The corpse check, as code instead of as a habit.

The standing rule is "check the ledger before proposing an idea". It is a good
rule and it depends entirely on a tired session remembering to run it. The
graveyard now holds 148 experiment rows and the registry 89 trials; nobody reads
237 receipts before writing a hypothesis, and the census already found that most
of that graveyard is not refuted at all — 31 POWER, 29 IMPL, 14 DATA rows that
never produced a usable number.

That distinction is the whole point of this module, because the two failure modes
are opposite:

  * Re-running something REJECTED is waste. Block it, and print the receipt.
  * Re-running something POWER/IMPL/DATA-failed is often exactly right — but only
    with an instrument that can see what the last one could not. Re-running it
    with the same instrument produces the same uninformative null, and the census
    shows this programme has done that. So: allowed, on condition that the
    proposal names what changed.

The linter does not judge whether an idea is good. It answers one question — has
this been tried, and what happened — and refuses to let the answer be skipped.
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from aegis_brain.config import MODULE_ROOT

GRAVEYARD = MODULE_ROOT / "runs" / "PF5" / "T4_graveyard_rows.csv"
REGISTRY = MODULE_ROOT / "TRIALS" / "registry.jsonl"
TRIALS_DIR = MODULE_ROOT / "TRIALS"

#: Verdicts that close a question. A match here blocks.
CLOSED = {"REJECTED", "PLACEBO_FAILED", "LEAKAGE_FAILED"}
#: Verdicts that did NOT answer the question. A match here demands a new
#: instrument, which is a different and much weaker requirement than a block.
UNANSWERED = {"POWER_FAILED", "IMPLEMENTATION_FAILED", "DATA_FAILED",
              "UNRESOLVED"}
#: The return is real and already paid by a known factor.
HARVEST = {"FACTOR_EXPLAINED"}

#: A proposal declares a deliberate resurrection with this line, naming the
#: corpse and what instrument changed. Without the instrument clause it does not
#: count — "we are trying again" is not a new instrument.
RESURRECT_RE = re.compile(
    r"^\s*Resurrects:\s*(?P<corpse>[^\n—-]+?)\s*[—-]+\s*new instrument:\s*"
    r"(?P<instrument>.+)$", re.IGNORECASE | re.MULTILINE)

_WORD = re.compile(r"[a-z][a-z_0-9]{2,}")
_STOP = {"the", "and", "for", "with", "that", "this", "from", "not", "are",
         "was", "were", "its", "into", "than", "then", "any", "all", "but",
         "our", "out", "per", "has", "had", "have", "will", "must", "may",
         "trial", "prereg", "registered", "hypothesis", "test", "tested",
         "arm", "arms", "book", "signal", "segment", "months", "month",
         "annual", "net", "gross", "yr", "vs", "does", "did", "one", "two"}


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in _STOP]


@dataclass
class Corpse:
    """One prior experiment, whatever form it was recorded in."""

    ident: str
    source: str                  # graveyard | registry | prereg
    verdict: str
    text: str
    detail: dict = field(default_factory=dict)
    tokens: Counter = field(default_factory=Counter)

    @property
    def clazz(self) -> str:
        v = self.verdict.upper()
        if v in CLOSED:
            return "closed"
        if v in UNANSWERED:
            return "unanswered"
        if v in HARVEST:
            return "harvest"
        return "other"


def _load_graveyard(path: Path) -> list[Corpse]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            ident = f"{r['signal']}/{r['segment']}"
            out.append(Corpse(
                ident=ident, source="graveyard",
                verdict=r.get("verdict", ""),
                text=f"{r['signal']} {r['segment']} {r.get('why', '')}",
                detail={k: r.get(k) for k in
                        ("point_pct_yr", "mde_pct_yr", "t_excess_net",
                         "t_ic", "turnover_1way", "months", "why")}))
    return out


#: The registry has no verdict FIELD — outcomes were written into free text
#: ("TRIAL-PF6-PRODUCT-REAL-1 UNRESOLVED: ..."). Reading only a field would
#: class every one of the 89 rows as REGISTERED and the linter would never
#: block anything.
_VERDICT_RE = re.compile(
    r"\b(REJECTED|UNRESOLVED|CONFIRMED|POWER_FAILED|IMPLEMENTATION_FAILED|"
    r"DATA_FAILED|FACTOR_EXPLAINED|PLACEBO_FAILED|LEAKAGE_FAILED|REJECT)\b")


#: A verdict must be ATTRIBUTED to count. Every preregistration lists REJECTED
#: and CONFIRMED in its decision-rule table as possible futures; reading the
#: first token anywhere in the document labels an unrun prereg REJECTED, and the
#: linter then blocks new work against a trial that never happened. Caught when
#: the IMAGE-RANK backlog item was blocked against N1's prereg, which had not run.
#: Two forms only, both of which mean a result was RECORDED rather than
#: anticipated: "Verdict: REJECT" (colon) and a "## Result"-style heading. A
#: decision-rule table headed "| outcome | state |" matches neither, which is
#: the point -- that table lists futures, not findings.
_STATES = (r"(REJECTED|UNRESOLVED|CONFIRMED|POWER_FAILED|"
           r"IMPLEMENTATION_FAILED|DATA_FAILED|FACTOR_EXPLAINED|"
           r"PLACEBO_FAILED|LEAKAGE_FAILED|REJECT)")
_ATTRIBUTED = re.compile(
    rf"\b(?:verdict|result|outcome|conclusion)\b\s*\**\s*[:—-]\s*\**\s*"
    rf"{_STATES}\b", re.IGNORECASE)
_RESULT_SECTION = re.compile(
    rf"(?:^|\n)#{{1,6}}\s*(?:\d+\.?\s*)?(?:verdict|result|outcome)\b[^\n]*\n"
    rf"(?:[^\n]*\n){{0,25}}?[^\n]*?\b{_STATES}\b", re.IGNORECASE)


def _verdict_in(text: str, fallback: str = "REGISTERED",
                *, attributed_only: bool = False) -> str:
    """The document's verdict, or `fallback` if it does not carry one.

    `attributed_only` is for long-form documents (preregs) where an unattributed
    token is almost always a decision rule rather than a result. Registry rows
    are one-liners written after the fact, so a bare token there IS the verdict.
    """
    m = _ATTRIBUTED.search(text) or _RESULT_SECTION.search(text)
    if m:
        v = m.group(1).upper()
        return "REJECTED" if v == "REJECT" else v
    if attributed_only:
        return fallback
    m = _VERDICT_RE.search(text)
    if not m:
        return fallback
    return "REJECTED" if m.group(1) == "REJECT" else m.group(1)


def _load_registry(path: Path) -> list[Corpse]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = " ".join(str(r.get(k, "")) for k in
                        ("name", "hypothesis", "expected_effect",
                         "kill_condition", "note"))
        out.append(Corpse(
            ident=r.get("name", "?"), source="registry",
            verdict=_verdict_in(text),
            text=text,
            detail={"hypothesis": r.get("hypothesis", ""),
                    "kill_condition": r.get("kill_condition", ""),
                    "note": r.get("note", "")}))
    return out


def _load_preregs(d: Path, exclude: Path | None = None) -> list[Corpse]:
    out = []
    for p in sorted(d.glob("*.md")):
        if p.name == "TEMPLATE.md" or (exclude and p.resolve() == exclude.resolve()):
            continue
        body = p.read_text(encoding="utf-8", errors="ignore")
        out.append(Corpse(ident=p.stem, source="prereg",
                          verdict=_verdict_in(body, attributed_only=True),
                          text=body))
    return out


def load_corpus(exclude: Path | None = None) -> list[Corpse]:
    corpus = (_load_graveyard(GRAVEYARD) + _load_registry(REGISTRY)
              + _load_preregs(TRIALS_DIR, exclude))
    if not corpus:
        raise RuntimeError(
            "the corpse corpus is EMPTY. A linter that silently finds nothing "
            "to compare against is worse than no linter — it prints a clean "
            "bill of health for every proposal.")
    for c in corpus:
        c.tokens = Counter(_tokens(c.text))
    return corpus


#: A token appearing in more than this share of prior experiments is house
#: boilerplate, not subject matter. Every prereg here says "power check",
#: "placebo", "Newey-West", "MDE", "pre-registered" — and with those left in,
#: TEMPLATE.md itself scored BLOCKED against 294 experiments. A linter that
#: blocks its own blank template blocks everything.
MAX_DOC_FREQ = 0.30


def _idf(corpus: list[Corpse]) -> dict[str, float]:
    """tf-idf weights, with house boilerplate zeroed.

    Document frequency is measured WITHIN each source, not across the pool. The
    pool is 148 short graveyard rows plus 89 registry lines plus ~60 long
    preregs; prereg boilerplate ("power check", "placebo gate", "Newey-West",
    "pre-registered") appears in most preregs but only ~13% of the pool, so a
    global cutoff never touches it — and the blank TEMPLATE.md scored BLOCKED
    against a rejected trial on 56 shared boilerplate terms. A word that appears
    in a third of any one source's documents is that source's furniture.
    """
    n = len(corpus)
    df, by_source = Counter(), {}
    for c in corpus:
        df.update(set(c.tokens))
        by_source.setdefault(c.source, []).append(c)

    boilerplate: set[str] = set()
    for docs in by_source.values():
        if len(docs) < 30:          # a frequency needs documents to be one
            continue
        sdf = Counter()
        for c in docs:
            sdf.update(set(c.tokens))
        cut = MAX_DOC_FREQ * len(docs)
        boilerplate |= {w for w, d in sdf.items() if d > cut}

    return {w: (0.0 if w in boilerplate else math.log(n / (1 + d)) + 1.0)
            for w, d in df.items()}


def _shared(a: Counter, b: Counter, idf: dict[str, float]) -> int:
    """How many INFORMATIVE tokens the two documents actually have in common."""
    return sum(1 for k in set(a) & set(b) if idf.get(k, 1.0) > 0.0)


def _cosine(a: Counter, b: Counter, idf: dict[str, float]) -> float:
    """tf-idf cosine, with tf damped so one repeated word cannot carry a doc."""
    if not a or not b:
        return 0.0
    keys = set(a) & set(b)
    if not keys:
        return 0.0

    def w(cnt: int, tok: str) -> float:
        return (1.0 + math.log(cnt)) * idf.get(tok, 1.0)

    num = sum(w(a[k], k) * w(b[k], k) for k in keys)
    na = math.sqrt(sum(w(v, k) ** 2 for k, v in a.items()))
    nb = math.sqrt(sum(w(v, k) ** 2 for k, v in b.items()))
    return num / (na * nb) if na and nb else 0.0


def lint(proposal: str, *, corpus: list[Corpse] | None = None,
         top_k: int = 5, block_at: float = 0.30, warn_at: float = 0.18,
         duplicate_at: float = 0.60, min_shared: int = 8) -> dict:
    """Check one proposal against everything this programme has already tried.

    Returns a verdict of PASS / RESURRECTION / BLOCKED plus the matches, so the
    caller prints receipts rather than a score. Thresholds are deliberately
    loose: a false warning costs one paragraph of reading, and a false clear
    costs a night.
    """
    corp = corpus if corpus is not None else load_corpus()
    idf = _idf(corp)
    tok = Counter(_tokens(proposal))
    if not tok:
        raise ValueError("empty proposal — nothing to check")

    scored = sorted(((_cosine(tok, c.tokens, idf), c) for c in corp),
                    key=lambda kv: -kv[0])[:top_k]
    declared = {m.group("corpse").strip().lower(): m.group("instrument").strip()
                for m in RESURRECT_RE.finditer(proposal)}

    matches, blocking, resurrect, dupes = [], [], [], []
    for score, c in scored:
        if score < warn_at:
            continue
        shared = _shared(tok, c.tokens, idf)
        rec = {"id": c.ident, "source": c.source, "verdict": c.verdict,
               "class": c.clazz, "similarity": round(score, 3),
               "shared_terms": shared, "detail": c.detail}
        matches.append(rec)
        dec = declared.get(c.ident.lower())
        if dec:
            rec["declared_new_instrument"] = dec
            continue
        # Cosine on a short document is unstable: the blank TEMPLATE.md scored
        # 0.322 against a REJECTED trial on three shared words (survivorship,
        # bps, reject). Three words is not an idea. Below the floor a match is
        # still reported, but it may not close anything.
        if shared < min_shared:
            rec["below_shared_floor"] = True
            continue
        # A refuted match is a block first and a duplicate second — "duplicate"
        # is the weaker thing to say about re-running something refuted.
        # Near-identical wording is otherwise a duplicate whatever the verdict
        # says, because the registry has no verdict field and an already-run
        # trial can sit at similarity 0.71 still labelled REGISTERED.
        if c.clazz == "closed" and score >= block_at:
            blocking.append(rec)
        elif score >= duplicate_at:
            dupes.append(rec)
        elif c.clazz in ("unanswered", "harvest") and score >= block_at:
            resurrect.append(rec)

    # Order matters: a near-identical rerun of a REFUTED idea is a block, and
    # "duplicate" would be the weaker, less useful thing to say about it.
    if blocking:
        verdict, why = "BLOCKED", (
            "this proposal closely matches an experiment that was adequately "
            "powered and refuted. Re-running it is waste. To proceed, state "
            "what is materially different in a `Resurrects: <id> — new "
            "instrument: <what>` line, or drop it.")
    elif dupes:
        verdict, why = "DUPLICATE", (
            "this is near-identical in wording to a trial already on the "
            "books. Before anything else, confirm it is not the same "
            "experiment under a new name — and if it IS the same experiment, "
            "it needs the earlier one's result, not a fresh run.")
    elif resurrect:
        verdict, why = "RESURRECTION", (
            "this matches an experiment that FAILED TO ANSWER its question "
            "(power, implementation, data) or was factor-explained. That is "
            "often worth re-running — but only with an instrument that can see "
            "what the last one could not. Name it in a `Resurrects: <id> — new "
            "instrument: <what>` line. The same instrument produces the same "
            "uninformative null.")
    else:
        verdict, why = "PASS", (
            "no close match in 148 graveyard rows, the trial registry or the "
            "prereg folder. PASS means UNMATCHED, not novel: this compares "
            "wording against what this programme has recorded, and it knows "
            "nothing about the literature.")

    return {"verdict": verdict, "why": why, "corpus_size": len(corp),
            "matches": matches, "blocking": blocking,
            "resurrections": resurrect, "duplicates": dupes,
            "declared_resurrections": declared,
            "thresholds": {"block_at": block_at, "warn_at": warn_at,
                           "duplicate_at": duplicate_at,
                           "min_shared": min_shared}}


def lint_batch(proposals: dict[str, str], *, corpus: list[Corpse] | None = None,
               block_at: float = 0.30, warn_at: float = 0.18,
               duplicate_at: float = 0.60) -> dict:
    """Check a BATCH of proposals against each other, not only against history.

    `lint()` asks "has this been tried before?". It cannot ask "are these ten
    proposals actually ten ideas?", because it sees one document at a time. A
    batch generated in one sitting — by an LLM, or by a person on a theme —
    passes proposal-by-proposal while collectively being a single bet, and the
    denominator that bet is scored against is then wrong by the batch size.

    Measured 2026-08-11 (NIGHT-10): ten hypotheses generated in one LLM call
    each PASSED against 306 prior experiments with a strongest near-match of
    ~0.23, while **37 of their 45 mutual pairs sat at or above this function's
    block threshold of 0.30**. They resembled each other far more than any of
    them resembled the entire recorded history of the programme — one mechanism
    template in ten costumes. Nothing in the machinery could see it.

    Returns per-pair cosines, a per-proposal count of how many batch-mates it
    blocks against, and an `effective_distinct_ideas` estimate: the number of
    connected components once every pair at or above `block_at` is joined.
    That count, not the proposal count, is the honest denominator.
    """
    corp = corpus if corpus is not None else load_corpus()
    idf = _idf(corp)
    toks = {k: Counter(_tokens(v)) for k, v in proposals.items()}
    for k, t in toks.items():
        if not t:
            raise ValueError(f"empty proposal {k!r} — nothing to check")

    keys = sorted(toks)
    pairs = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            pairs.append({"a": a, "b": b,
                          "cosine": round(_cosine(toks[a], toks[b], idf), 4)})
    pairs.sort(key=lambda p: -p["cosine"])

    # union-find over the "too similar to be separate ideas" graph
    parent = {k: k for k in keys}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in pairs:
        if p["cosine"] >= block_at:
            ra, rb = find(p["a"]), find(p["b"])
            if ra != rb:
                parent[ra] = rb
    groups: dict[str, list[str]] = {}
    for k in keys:
        groups.setdefault(find(k), []).append(k)

    per = {k: sum(1 for p in pairs
                  if (p["a"] == k or p["b"] == k) and p["cosine"] >= block_at)
           for k in keys}
    n_block = sum(1 for p in pairs if p["cosine"] >= block_at)
    n_dupe = sum(1 for p in pairs if p["cosine"] >= duplicate_at)
    distinct = len(groups)

    if distinct == len(keys):
        verdict, why = "DIVERSE", (
            f"all {len(keys)} proposals are mutually distinct at the "
            f"{block_at} threshold — the batch is as many ideas as it claims.")
    elif distinct == 1:
        verdict, why = "SINGLE_IDEA", (
            f"all {len(keys)} proposals collapse into ONE connected group. "
            f"This is one idea in {len(keys)} costumes; scoring it as "
            f"{len(keys)} independent tries would inflate the denominator and "
            f"understate every best-of-N bar computed from it.")
    else:
        verdict, why = "PARTIALLY_REDUNDANT", (
            f"{len(keys)} proposals collapse into {distinct} distinct "
            f"group(s). The honest denominator for anything selected out of "
            f"this batch is {distinct}, not {len(keys)}.")

    return {"verdict": verdict, "why": why,
            "n_proposals": len(keys),
            "effective_distinct_ideas": distinct,
            "groups": [sorted(v) for v in groups.values()],
            "n_pairs": len(pairs),
            "n_pairs_at_or_above_block": n_block,
            "n_pairs_at_or_above_duplicate": n_dupe,
            "blocking_batchmates_per_proposal": per,
            "pairs": pairs,
            "thresholds": {"block_at": block_at, "warn_at": warn_at,
                           "duplicate_at": duplicate_at},
            "note": ("This measures WORDING, exactly as lint() does. Two "
                     "genuinely different mechanisms described in the same "
                     "house style will score high here; that is a false alarm "
                     "costing one paragraph of reading, which is the trade this "
                     "module has always made.")}
