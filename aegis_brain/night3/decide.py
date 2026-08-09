"""The deciders: engine, LLM without memory (arm A), LLM with episodic memory (arm E).

Every arm exposes the same signature — slate in, `{label: Decision}` out — so
the grading code cannot tell which arm produced a book. That symmetry is the
point: it makes the comparison paired and keeps arm-specific special-casing out
of the scoring path, where it would be invisible.

WHAT ARM E GETS, AND WHY IT IS NOT A LEAK:

  * a kNN summary over its OWN past graded decisions whose outcomes resolved
    strictly before this month, with `n` printed beside every number
    (a generalization without its n is rejected by design — taxonomy §2);
  * its own running track record on the same terms;
  * for a name it saw last month, the belief it held then and what happened,
    under the forced OLD BELIEF → NEW EVIDENCE → BELIEF UPDATE → NEW BELIEF
    schema.

None of that contains a fact dated after the formation month. The model is never
told to "be consistent" — consistency is produced by showing it its own prior
claim, and then measured by grading the delta.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from aegis_brain.night3.experience import THESES
from aegis_brain.night3.llmcache import parse_json
from aegis_brain.night3.slate import Slate, render_slate

logger = logging.getLogger(__name__)

SYSTEM = ("You are a careful equity analyst making portfolio decisions. You "
          "answer only with strict JSON matching the requested schema. You "
          "never invent facts that were not given to you. You are decisive: "
          "vague hedging across every name is not an answer.")

_THESIS_LIST = ", ".join(THESES)

# persistence block bounds — frozen here so a prompt cannot silently grow
MAX_PRIOR_AGE_M = 12
MAX_PRIOR_NAMES = 20


@dataclass(frozen=True)
class Decision:
    label: str
    direction: str            # BUY | HOLD | SELL
    conviction: float         # [0,1]
    expected_excess: float    # decimal vs market over the next month
    thesis: str
    # persistence fields — present only for names the arm has judged before
    old_belief: str = ""      # BUY | HOLD | SELL, as the model recalls it
    belief_update: str = ""   # STRENGTHEN | MAINTAIN | WEAKEN | REVERSE


def _schema_block(n: int) -> str:
    return (
        f'Return JSON exactly: {{"decisions": [{{"label": "<label>", '
        f'"direction": "BUY|HOLD|SELL", "conviction": <0.0-1.0>, '
        f'"expected_excess_return": <decimal, e.g. 0.01 means +1% versus the '
        f'market over the next month>, "thesis": "<one of: {_THESIS_LIST}>"}}, '
        f'...]}}\n'
        f"Exactly {n} entries, one for every label shown, no label repeated and "
        f"none omitted. BUY means you expect it to beat the US stock market over "
        f"the NEXT ONE MONTH; SELL means you expect it to lag; HOLD means no view."
    )


def engine_decide(slate: Slate, top_n: int = 20) -> dict[str, Decision]:
    """The control: the composite's own ranking. Deterministic, free, no LLM."""
    out = {}
    for c in slate.candidates:
        buy = c.engine_rank <= top_n
        out[c.label] = Decision(
            label=c.label, direction="BUY" if buy else "HOLD",
            # conviction descends with rank so the book-builder's tie-break
            # reproduces the engine's ordering exactly
            conviction=round(max(0.0, 1.0 - (c.engine_rank - 1) / slate.n), 4),
            expected_excess=0.0, thesis="profitability")
    return out


def _memory_block(store, slate: Slate, k: int, model_id: str) -> tuple[str, dict]:
    """Per-candidate kNN summaries + the decider's own running record."""
    ts = slate.formation_month
    pool = store.available_at(ts)
    lines, diag = [], {"pool": len(pool), "with_neighbours": 0}
    if not pool:
        return "", diag
    for c in slate.candidates:
        nb = store.retrieve(c.fingerprint, ts, k=k, event_class="monthly_slate")
        if not nb:
            continue
        s = store.summarize_neighbours(nb)
        diag["with_neighbours"] += 1
        lines.append(
            f"   {c.label}: {s['n']} similar past situations — "
            f"{s['frac_beat_benchmark']:.0%} beat the market, "
            f"mean excess {s['mean_abnormal_return']:+.2%}"
            + (f"; of those you BOUGHT ({s['n_buy']}), "
               f"{s['buy_frac_beat_benchmark']:.0%} beat the market, "
               f"mean excess {s['buy_mean_abnormal_return']:+.2%}"
               if s.get("n_buy") else ""))
    buys = [r for r in pool if r["direction"] == "BUY"]
    rec = ""
    if buys:
        ab = np.array([float(r["abnormal_return"]) for r in buys])
        err = np.array([float(r["error"]) for r in buys])
        att: dict[str, int] = {}
        for r in buys:
            if float(r["abnormal_return"]) < 0:
                att[r["attribution"]] = att.get(r["attribution"], 0) + 1
        worst = max(att.items(), key=lambda kv: kv[1])[0] if att else "n/a"
        rec = (f"\nYOUR OWN TRACK RECORD SO FAR (n={len(buys)} resolved BUY "
               f"decisions): {np.mean(ab > 0):.0%} beat the market, mean excess "
               f"{np.mean(ab):+.2%}, mean forecast error "
               f"{np.mean(err):+.2%} (positive = you under-predicted). "
               f"Most common reason your losing BUYs lost: {worst}.\n")
        diag["track_record_n"] = len(buys)
        diag["track_record_hit"] = round(float(np.mean(ab > 0)), 3)
    if not lines and not rec:
        return "", diag
    head = ("\nEXPERIENCE FROM YOUR OWN PAST DECISIONS. Every number below is "
            "computed from decisions whose outcomes were already known before "
            "today; none of it contains information about the future. Sample "
            "sizes are given so you can judge how much weight they deserve.\n")
    return head + rec + ("\n".join(lines) + "\n" if lines else ""), diag


def _persistence_block(prior: dict[str, dict], slate: Slate) -> tuple[str, list[str]]:
    """What you previously said about names still on the slate, and what happened.

    `prior` holds only judgements whose outcome resolved STRICTLY BEFORE this
    formation month — the same embargo the kNN obeys. Under this module's
    timing convention that makes the most recent usable judgement two months
    old, not one. Conservative in the safe direction, and consistent: there is
    no path by which persistence sees something the retrieval cannot.
    """
    # Bound the block: a belief from three years ago is not the "prior belief"
    # this schema is about, and an unbounded list would grow the prompt without
    # adding information. Most-recent first, capped.
    carried = [c for c in slate.candidates
               if c.permno in prior and prior[c.permno]["months_ago"] <= MAX_PRIOR_AGE_M]
    carried.sort(key=lambda c: prior[c.permno]["months_ago"])
    carried = carried[:MAX_PRIOR_NAMES]
    if not carried:
        return "", []
    rows = []
    for c in carried:
        p = prior[c.permno]
        rows.append(f"   {c.label}: {p['months_ago']} months ago you said "
                    f"{p['direction']} with conviction {p['conviction']:.2f} and "
                    f"expected {p['expected_excess']:+.2%} versus the market. Over "
                    f"the month that followed it actually returned "
                    f"{p['abnormal_return']:+.2%} versus the market.")
    block = ("\nNAMES YOU HAVE ALREADY JUDGED (your own prior belief and how it "
             "turned out):\n" + "\n".join(rows) +
             "\nFor each of these, your JSON entry must ALSO carry "
             '"old_belief": "<BUY|HOLD|SELL>" and "belief_update": '
             '"<STRENGTHEN|MAINTAIN|WEAKEN|REVERSE>" — state the belief you '
             "held, then how the new evidence moved it.\n")
    return block, [c.label for c in carried]


def build_prompt(slate: Slate, *, arm: str, store=None, prior=None, k: int = 8,
                 model_id: str = "") -> tuple[str, str, dict]:
    """(system, user, diag). Arm A and arm E differ ONLY by the memory blocks."""
    body = render_slate(slate)
    diag: dict = {"arm": arm}
    extra = ""
    if arm == "E":
        if store is None:
            raise ValueError("arm E requires an experience store")
        mem, mdiag = _memory_block(store, slate, k, model_id)
        pers, carried = _persistence_block(prior or {}, slate)
        extra = mem + pers
        diag.update({"memory": mdiag, "carried_labels": carried})
    elif arm != "A":
        raise ValueError(f"unknown arm {arm!r}")
    user = f"{body}\n{extra}\n{_schema_block(slate.n)}"
    return SYSTEM, user, diag


def parse_decisions(text: str, slate: Slate) -> tuple[dict[str, Decision], dict]:
    """Parse and validate. Missing/extra labels are reported, never patched
    silently — a book quietly built from 31 of 40 answers would look like a
    result and be an artifact."""
    d = parse_json(text)
    raw = d.get("decisions") or d.get("Decisions") or []
    valid = {c.label for c in slate.candidates}
    out: dict[str, Decision] = {}
    bad = {"unknown_label": 0, "bad_direction": 0, "duplicate": 0, "malformed": 0}
    for r in raw:
        try:
            lab = str(r["label"]).strip().upper()
            if lab not in valid:
                bad["unknown_label"] += 1
                continue
            if lab in out:
                bad["duplicate"] += 1
                continue
            dirn = str(r["direction"]).strip().upper()
            if dirn not in ("BUY", "HOLD", "SELL"):
                bad["bad_direction"] += 1
                continue
            conv = float(r.get("conviction", 0.5))
            exc = float(r.get("expected_excess_return", 0.0))
            th = str(r.get("thesis", "insufficient_information")).strip().lower()
            ob = str(r.get("old_belief", "")).strip().upper()
            bu = str(r.get("belief_update", "")).strip().upper()
            out[lab] = Decision(
                label=lab, direction=dirn,
                conviction=float(np.clip(conv, 0.0, 1.0)),
                expected_excess=float(np.clip(exc, -1.0, 1.0)),
                thesis=th if th in THESES else "insufficient_information",
                old_belief=ob if ob in ("BUY", "HOLD", "SELL") else "",
                belief_update=bu if bu in ("STRENGTHEN", "MAINTAIN", "WEAKEN",
                                           "REVERSE") else "")
        except (KeyError, TypeError, ValueError):
            bad["malformed"] += 1
    diag = {"n_parsed": len(out), "n_expected": slate.n,
            "missing": sorted(valid - set(out)), **{k: v for k, v in bad.items() if v}}
    return out, diag


def build_book(decisions: dict[str, Decision], slate: Slate, top_n: int = 20
               ) -> list[str]:
    """BUYs by conviction, padded from HOLDs by conviction, truncated to top_n.

    The padding rule is frozen here rather than decided per-run: without it, an
    arm that emits three BUYs would be compared against a 20-name book on
    concentration as well as on selection, and the two effects would be
    inseparable. Every arm holds exactly top_n names or says why it could not.
    """
    order = {"BUY": 0, "HOLD": 1, "SELL": 2}
    ranked = sorted(decisions.values(),
                    key=lambda d: (order[d.direction], -d.conviction, d.label))
    return [d.label for d in ranked[:top_n]]
