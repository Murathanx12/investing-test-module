"""MARKET-GRAPH-1 stage 3 — the edge extractor.

THE THREE THINGS THIS FILE IS CAREFUL ABOUT
===========================================

**1. It emits no forecast.** Hard constraint 3. The contract below has no
probability field, no price target, no direction-of-move, no sentiment. If one
call both named a relationship and predicted a move, the two could never be
graded apart, and every "the graph worked" result would be unfalsifiably
confounded with "the model is good at guessing returns". The model is asked to
read, and only to read.

**2. It reads `served_model` off the response.** `deepseek-chat` and
`deepseek-reasoner` both resolve silently to `deepseek-v4-flash`; only
`deepseek-v4-pro` is distinct. Trusting the requested name voided an arm of a
running trial on 2026-08-12. Every record here carries what the vendor said it
served, not what we asked for.

**3. The system prefix is byte-frozen.** v4-flash cached input is 50x cheaper
than a miss ($0.0028 vs $0.14 per Mtok), so a constant prefix shared across
every one of ~3,300 extraction calls is the single largest cost lever
available. It contains no timestamp, no uuid, no unsorted dict — any of those
would silently destroy the cache while everything still appeared to work.

THE EVIDENCE QUOTE IS A CONTROL, NOT DECORATION
-----------------------------------------------
The prereg's stated risk is that "an LLM will assert a relationship between any
two companies if asked". Requiring a verbatim span from the document, then
checking that span actually occurs in the document, converts that risk from an
argument into a measured rate. It does not prove an edge is economically real
— a true quote can still be attached to a wrong reading — but an edge whose
quote is not in the document is manufactured, and we can count those.

    python -m scripts.mg1_extract --limit 50 --workers 8    # pilot
    python -m scripts.mg1_extract --workers 24              # full, resumable
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import threading
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AF = Path(r"C:\Users\mrthn\aegis-finance")
if str(AF) not in sys.path:
    sys.path.insert(0, str(AF))
for _line in (AF / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in _line and not _line.strip().startswith("#"):
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

from aegis_brain.config import MODULE_ROOT                       # noqa: E402
from backend.services import research_budget                     # noqa: E402
from backend.services.llm_telemetry import (extract_usage,       # noqa: E402
                                            record_call)
from backend.services.research_budget import (                   # noqa: E402
    ResearchBudgetExhausted)
from scripts import mg1_config as C                              # noqa: E402

OUT = MODULE_ROOT / "runs" / "MARKET-GRAPH-1"
DOCS = OUT / "docs"
EDGES = OUT / "edges_raw.jsonl"
META = OUT / "extract_meta.json"

# ── the byte-frozen prefix ──────────────────────────────────────────────────
# Every character below is constant across all calls. Do not interpolate.

SYSTEM = """You extract economic relationships between companies from a filing.

You are given an excerpt of one company's annual report (Form 10-K), filed on a
stated date. Read it and list the OTHER companies it names, and what economic
relationship the SUBJECT company has with each.

RULES
1. Use ONLY the supplied text. Do not use anything you know about these
   companies from elsewhere. If the text does not name a counterparty, do not
   invent one.
2. Name only OTHER COMPANIES. Not products, not government agencies, not
   indices, not trade bodies, not the subject's own subsidiaries or brands.
3. For every edge you must quote a VERBATIM span from the supplied text, 5 to
   25 words, that contains the counterparty's name and shows the relationship.
   Copy it exactly, character for character. If you cannot quote it, omit the
   edge.
4. Emit at most 20 edges. Prefer relationships that are material to the
   subject's business over passing mentions.
5. Make no prediction of any kind. No view on prices, returns, direction,
   performance, outlook or attractiveness. You are reading, not forecasting.

RELATIONSHIP TYPES - use exactly one of these eight strings:
  supplier             the counterparty supplies goods or services to SUBJECT
  customer             the counterparty buys goods or services from SUBJECT
  competitor           they compete for the same customers
  commodity_input      both depend on the same physical commodity or input
  shared_technology    both depend on the same technology, standard or platform
  shared_end_market    both sell into the same end market or customer industry
  regulatory_exposure  both are exposed to the same regulator or regime
  geographic_exposure  both are materially exposed to the same country/region

DIRECTION - use exactly one of these three strings:
  in       value, goods or dependency flows COUNTERPARTY -> SUBJECT
  out      value, goods or dependency flows SUBJECT -> COUNTERPARTY
  mutual   the relationship is symmetric

CONFIDENCE - a number in [0,1]: how clearly the supplied text establishes this
relationship. 1.0 means the text states it explicitly and unambiguously. 0.3
means it is a reasonable reading of an indirect mention. Do not use confidence
to express how important you think the relationship is.

Reply with JSON only, exactly this shape:
{"edges":[{"counterparty_name":"...","counterparty_ticker":"AAPL or null",
"type":"supplier","direction":"in","confidence":0.8,"evidence":"verbatim span"}]}

If the text names no other company, reply {"edges":[]}. An empty list is a
correct and useful answer; a list of plausible-sounding guesses is not."""

_LOCK = threading.Lock()
_STATE = {"calls": 0, "cost": 0.0, "in": 0, "out": 0, "cached": 0,
          "halted": None}

#: `research_budget.require()` reads spend out of the telemetry ledger, which
#: is the only correct source (an in-process counter resets on restart and a
#: resumed campaign would silently spend twice). But it re-parses that whole
#: file on every call, and with a concurrent 48-worker campaign writing to the
#: same ledger it grew past 20 MB mid-run: extraction throughput fell from
#: ~250 documents/minute to ~13 while vendor latency stayed flat at 2.9s. The
#: governor was not refusing anything; it was reading.
#:
#: So the wire is gated on a state at most `_BUDGET_TTL_S` seconds stale,
#: while the two HARD in-process ceilings (`SESSION_MAX_CALLS`,
#: `SESSION_MAX_USD`) stay checked on every single call as before. The
#: exposure this buys is bounded and worth stating: workers x TTL calls may
#: pass between consultations, which at 12 workers, 20 seconds and ~$0.0008 a
#: call is under $0.20. A refusal still halts the whole run on the next check.
_BUDGET_TTL_S = 20.0
_BUDGET = {"t": -1e9, "ok": True, "reason": None}


def _budget_ok(since: str) -> None:
    """Consult the governor, at most once per TTL across all workers."""
    now = time.monotonic()
    with _LOCK:
        fresh = (now - _BUDGET["t"]) < _BUDGET_TTL_S
        ok, reason = _BUDGET["ok"], _BUDGET["reason"]
    if fresh:
        if not ok:
            raise ResearchBudgetExhausted(reason or "budget refused")
        return
    st = research_budget.check(C.CAMPAIGN, since=since)
    with _LOCK:
        _BUDGET.update(t=time.monotonic(), ok=bool(st.ok), reason=st.reason)
    if not st.ok:
        raise ResearchBudgetExhausted(st.reason or "budget refused")


def _client():
    from openai import OpenAI
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is empty (keys are env-only)")
    return OpenAI(api_key=key,
                  base_url=os.getenv("DEEPSEEK_BASE_URL",
                                     "https://api.deepseek.com"),
                  timeout=180.0, max_retries=0)   # retries are ours, so gated


def user_message(rec: dict, text: str) -> str:
    """Identity + document. Deliberately AFTER the frozen system prefix."""
    return (f"SUBJECT COMPANY: {rec['comnam']}\n"
            f"TICKER AT FILING: {rec.get('ticker') or 'unknown'}\n"
            f"FORM: 10-K filed {rec['filing_date']}\n"
            f"--- BEGIN EXCERPT ---\n{text}\n--- END EXCERPT ---")


def parse(txt: str) -> tuple[list[dict], str | None]:
    try:
        obj = json.loads(txt)
    except Exception as exc:                                   # noqa: BLE001
        return [], f"json: {type(exc).__name__}"
    raw = obj.get("edges")
    if not isinstance(raw, list):
        return [], "no edges list"
    out, bad = [], 0
    for e in raw[:C.EXTRACT_MAX_EDGES]:
        if not isinstance(e, dict):
            bad += 1
            continue
        typ = str(e.get("type", "")).strip().lower()
        dirn = str(e.get("direction", "")).strip().lower()
        name = str(e.get("counterparty_name", "")).strip()
        if typ not in C.EDGE_TYPES or dirn not in ("in", "out", "mutual") \
                or not name:
            bad += 1
            continue
        try:
            conf = float(e.get("confidence"))
        except (TypeError, ValueError):
            bad += 1
            continue
        tick = e.get("counterparty_ticker")
        tick = (str(tick).strip().upper()
                if tick and str(tick).strip().lower() not in ("null", "none",
                                                              "n/a", "")
                else None)
        out.append({"counterparty_name": name, "counterparty_ticker": tick,
                    "type": typ, "direction": dirn,
                    "confidence": min(max(conf, 0.0), 1.0),
                    "evidence": str(e.get("evidence", ""))[:400]})
    return out, (f"{bad} malformed edges" if bad else None)


def _norm_ws(s: str) -> str:
    return " ".join(s.lower().split())


def one(rec: dict, cli, since: str) -> dict:
    """Extract one document. Raises ResearchBudgetExhausted; nothing else."""
    text = gzip.open(DOCS / rec["path"], "rt", encoding="utf-8").read()
    out = {"accession": rec["accession"], "permno": rec["permno"],
           "cik": rec["cik"], "ticker": rec["ticker"], "comnam": rec["comnam"],
           "filing_date": rec["filing_date"], "method": rec["method"]}

    last_err = None
    for attempt in range(4):
        with _LOCK:
            if _STATE["halted"]:
                raise ResearchBudgetExhausted(_STATE["halted"])
            if _STATE["calls"] >= C.SESSION_MAX_CALLS:
                _STATE["halted"] = "session call ceiling"
                raise ResearchBudgetExhausted("session call ceiling")
            if _STATE["cost"] >= C.SESSION_MAX_USD:
                _STATE["halted"] = "session USD ceiling"
                raise ResearchBudgetExhausted("session USD ceiling")
        _budget_ok(since)                         # governor, TTL-cached above
        t0 = time.perf_counter()
        try:
            resp = cli.chat.completions.create(
                model=C.EXTRACT_MODEL,
                temperature=C.EXTRACT_TEMPERATURE,
                max_tokens=C.EXTRACT_MAX_TOKENS,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user",
                           "content": user_message(rec, text)}])
        except Exception as exc:                               # noqa: BLE001
            last_err = f"{type(exc).__name__}: {str(exc)[:160]}"
            time.sleep(1.5 * (attempt + 1))
            continue                        # no telemetry row: nothing billed

        txt = resp.choices[0].message.content or ""
        served = str(getattr(resp, "model", C.EXTRACT_MODEL))
        # Recorded, not inferred. A truncated reply and a refusal look the same
        # downstream — both arrive as "no edges" — and the difference is the
        # whole point: one is the model telling us the filing names nobody, the
        # other is us throwing away its answer.
        finish = str(getattr(resp.choices[0], "finish_reason", "") or "")
        u = extract_usage(resp, "deepseek")
        edges, note = parse(txt)

        # Evidence check: does the quoted span actually occur in the document?
        hay = _norm_ws(text)
        for e in edges:
            q = _norm_ws(e["evidence"])
            e["quote_verified"] = bool(len(q) >= 12 and q in hay)

        with _LOCK:
            _STATE["calls"] += 1
            _STATE["in"] += int(u.get("tokens_in", 0))
            _STATE["out"] += int(u.get("tokens_out", 0))
            _STATE["cached"] += int(u.get("cached_tokens", 0))
            _STATE["cost"] += (
                int(u.get("tokens_in", 0)) * 0.14e-6
                + int(u.get("cached_tokens", 0)) * 0.0028e-6
                + int(u.get("tokens_out", 0)) * 0.28e-6)

        record_call(provider="deepseek", model=C.EXTRACT_MODEL,
                    model_version=served, purpose="market_graph_1_extract",
                    agent="edge_extractor", prompt=SYSTEM,
                    context={"accession": rec["accession"]},
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    retries=attempt, schema_valid=(note is None),
                    error=note, meta={"module": "mg1_extract/1.0.0"}, **u)

        out.update(status="ok", served_model=served, n_edges=len(edges),
                   edges=edges, parse_note=note, retries=attempt,
                   finish_reason=finish, max_tokens=C.EXTRACT_MAX_TOKENS,
                   tokens_in=u.get("tokens_in"), tokens_out=u.get("tokens_out"),
                   cached_tokens=u.get("cached_tokens"))
        return out

    out.update(status="failed", error=last_err, n_edges=0, edges=[])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--seed", type=int, default=C.SEED)
    ap.add_argument("--repair", action="store_true",
                    help="re-run ONLY the documents whose stored reply was "
                         "truncated at the token cap")
    args = ap.parse_args()

    since = str(pd.Timestamp.utcnow().date())
    idx = [json.loads(l) for l in
           (OUT / "docs_index.jsonl").open(encoding="utf-8")]
    idx = [r for r in idx if r.get("status") == "ok"]
    # Last record per accession wins: a repair pass appends rather than
    # rewrites, and the reader must agree with the writer about which line is
    # current or the repaired document is counted twice.
    latest: dict = {}
    if EDGES.exists():
        for line in EDGES.open(encoding="utf-8"):
            try:
                r = json.loads(line)
                latest[r["accession"]] = r
            except Exception:
                continue
    if args.repair:
        # A stored record is broken if it failed to parse OR the vendor said it
        # stopped on length. Both are the cap; neither is an answer.
        bad = {a for a, r in latest.items()
               if str(r.get("parse_note") or "").startswith("json")
               or r.get("finish_reason") == "length"
               or (r.get("tokens_out") or 0) >= (r.get("max_tokens") or 2000)}
        todo = [r for r in idx if r["accession"] in bad]
        print(f"repair mode: {len(bad):,} truncated documents to re-run at "
              f"max_tokens={C.EXTRACT_MAX_TOKENS}", flush=True)
    else:
        todo = [r for r in idx if r["accession"] not in latest]
    if args.limit:
        todo = (pd.DataFrame(todo).sample(n=min(args.limit, len(todo)),
                                          random_state=args.seed)
                .to_dict("records"))
    print(f"extract: {len(idx):,} documents, {len(latest):,} done, "
          f"{len(todo):,} this run, {args.workers} workers", flush=True)
    if not todo:
        return

    st = research_budget.check(C.CAMPAIGN, since=since)
    print(f"  budget gate: ok={st.ok} calls_remaining={st.calls_remaining} "
          f"usd_remaining={st.usd_remaining} reason={st.reason}", flush=True)
    if not st.ok:
        print("REFUSED by research_budget — stopping, not raising the ceiling.")
        return

    from concurrent.futures import ThreadPoolExecutor, as_completed
    cli = _client()
    t0 = time.time()
    n_ok = n_fail = n_edges = 0
    with EDGES.open("a", encoding="utf-8") as fh:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(one, r, cli, since): r for r in todo}
            try:
                for i, fut in enumerate(as_completed(futs), 1):
                    try:
                        rec = fut.result()
                    except ResearchBudgetExhausted as exc:
                        print(f"HALTED by budget: {exc}", flush=True)
                        with _LOCK:
                            _STATE["halted"] = str(exc)
                        break
                    with _LOCK:
                        fh.write(json.dumps(rec) + "\n")
                        if rec["status"] == "ok":
                            n_ok += 1
                            n_edges += rec["n_edges"]
                        else:
                            n_fail += 1
                    if i % 100 == 0:
                        fh.flush()
                        print(f"  {i}/{len(todo)} ok={n_ok} fail={n_fail} "
                              f"edges={n_edges} ${_STATE['cost']:.3f} "
                              f"cache={_STATE['cached'] / max(1, _STATE['cached'] + _STATE['in']):.1%} "
                              f"{(time.time() - t0) / 60:.1f}min", flush=True)
            finally:
                for f in futs:
                    f.cancel()

    meta = {"run_utc": since, "n_calls": _STATE["calls"],
            "n_ok": n_ok, "n_failed": n_fail, "n_edges": n_edges,
            "tokens_in_uncached": _STATE["in"],
            "tokens_cached": _STATE["cached"], "tokens_out": _STATE["out"],
            "cache_hit_share": round(_STATE["cached"]
                                     / max(1, _STATE["cached"] + _STATE["in"]),
                                     4),
            "cost_usd": round(_STATE["cost"], 4),
            "halted": _STATE["halted"],
            "elapsed_min": round((time.time() - t0) / 60, 2)}
    prev = json.loads(META.read_text()) if META.exists() else []
    if isinstance(prev, dict):
        prev = [prev]
    prev.append(meta)
    META.write_text(json.dumps(prev, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
