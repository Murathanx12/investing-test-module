"""Aegis Belief Network — claim schema and the tamper-evident claim ledger.

THE ARCHITECTURAL INVARIANT, stated once and enforced by code:

    The ONLY write path into the belief store is a RESOLUTION.
    Portfolio P&L may read beliefs and brake exposure. It may never write.

That is the D3 rule (resolutions teach, never P&L), and it is not a comment
here — `posterior.PosteriorStore.update` accepts a `Resolution` object and
nothing else, and `Resolution` can only be constructed by the resolver from an
observed outcome. A test asserts a P&L number cannot reach it.

Three stores, one-way flow:
    evidence (this ledger, immutable) -> belief (posteriors) -> narrative (LLM
    journal). Narrative never overwrites evidence.

The ledger is hash-chained: every record carries the hash of its predecessor,
so a silently edited history fails verification. Retrieval enforces the OUTCOME
EMBARGO (a claim's resolution is invisible until it has actually realized) and
is TICKER-BLIND by default (KTD-Fin: the ticker handle alone drives behavior).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timezone
from pathlib import Path

CLAIM_KINDS = ("direction", "reaction_size", "tradable_edge")
ABSTAIN_REASONS = ("retrieval_thin", "missing_anchor", "conjunction",
                   "imminent_resolution", "out_of_scope")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Claim:
    """One falsifiable, resolvable statement made BEFORE its outcome exists."""

    claim_class: str                 # earnings | pdufa | insider_cluster | ...
    entity_key: str                  # permno/CIK — never the ticker string
    asof: str                        # decision date (YYYY-MM-DD)
    kind: str                        # CLAIM_KINDS
    statement: str                   # human-readable, <=200 chars
    anchor: float | None             # the numeric the claim is about
    anchor_units: str                # "prob" | "bps" | "pct" | "usd"
    window_days: tuple[int, int]     # realization window relative to asof
    p_raw: float | None              # elicited probability, pre-calibration
    context_key: str = "default"     # market-state bucket (NOT the ticker)
    conjunction: bool = False        # "A and B" — the LLMs' worst class
    abstain: bool = False
    abstain_reason: str = ""
    source: str = ""                 # model id / prompt hash / analyst
    created_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if self.kind not in CLAIM_KINDS:
            raise ValueError(f"kind must be one of {CLAIM_KINDS}")
        if self.abstain and self.abstain_reason not in ABSTAIN_REASONS:
            raise ValueError(f"abstain_reason must be one of {ABSTAIN_REASONS}")
        if not self.abstain and self.p_raw is None:
            raise ValueError("a non-abstaining claim must carry p_raw")
        if self.p_raw is not None and not 0.0 <= self.p_raw <= 1.0:
            raise ValueError("p_raw out of [0,1]")
        if self.window_days[1] <= self.window_days[0]:
            raise ValueError("window_days must be (start, end) with end > start")
        if not self.abstain and self.anchor is None and self.kind != "direction":
            raise ValueError("size/edge claims require a numeric anchor "
                             "(R1: anchorless claims mis-set every prior)")

    @property
    def claim_id(self) -> str:
        payload = {k: v for k, v in asdict(self).items() if k != "created_at"}
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                          default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    @property
    def resolvable_on(self) -> date:
        from datetime import timedelta
        return date.fromisoformat(self.asof) + timedelta(days=self.window_days[1])


@dataclass(frozen=True)
class Resolution:
    """An OBSERVED outcome. The only object that may update a belief.

    Constructed by the deterministic resolver from realized data. There is no
    constructor path from a P&L number: `realized` is the claim's own anchor
    quantity, and `source` records the data that produced it.
    """

    claim_id: str
    resolved_on: str                 # date the outcome became observable
    hit: bool                        # did the directional claim come true
    realized: float                  # the anchor quantity, actually realized
    realized_units: str
    source: str                      # dataset + version that resolved it
    cohort_key: str = ""             # same-day/same-event cluster id (for DEFF)


class ClaimLedger:
    """Append-only, hash-chained JSONL. Evidence, not belief."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: list[dict] | None = None
        self._claim_ids: set[str] = set()
        self._resolved_ids: set[str] = set()

    # ── write ───────────────────────────────────────────────────────────────
    def _last_hash(self) -> str:
        recs = self.records()
        return recs[-1]["record_hash"] if recs else "GENESIS"

    def _append(self, kind: str, body: dict) -> str:
        prev = self._last_hash()
        rec = {"kind": kind, "prev_hash": prev, "body": body,
               "written_at": _now()}
        rec["record_hash"] = hashlib.sha256(
            json.dumps({k: rec[k] for k in ("kind", "prev_hash", "body")},
                       sort_keys=True, default=str).encode()).hexdigest()[:16]
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
        self.records().append(rec)
        if kind == "claim":
            self._claim_ids.add(body["claim_id"])
        elif kind == "resolution":
            self._resolved_ids.add(body["claim_id"])
        return rec["record_hash"]

    def add_claim(self, claim: Claim) -> str:
        self.records()                      # warms the id index
        if claim.claim_id in self._claim_ids:
            raise ValueError(f"claim {claim.claim_id} already in the ledger — "
                             "a claim is written once, before its outcome")
        body = asdict(claim)
        body["claim_id"] = claim.claim_id
        body["resolvable_on"] = str(claim.resolvable_on)
        return self._append("claim", body)

    def add_resolution(self, res: Resolution) -> str:
        self.records()                      # warms the id index
        if res.claim_id not in self._claim_ids:
            raise ValueError(f"resolution for unknown claim {res.claim_id}")
        if res.claim_id in self._resolved_ids:
            raise ValueError(f"claim {res.claim_id} already resolved — "
                             "resolutions are write-once")
        return self._append("resolution", asdict(res))

    # ── read ────────────────────────────────────────────────────────────────
    def records(self) -> list[dict]:
        """In-memory view of the chain. The file stays the source of truth;
        `verify()` always re-derives from what is actually on disk."""
        if self._cache is None:
            recs = ([json.loads(l) for l in
                     self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
                    if self.path.exists() else [])
            self._cache = recs
            self._claim_ids = {r["body"]["claim_id"] for r in recs
                               if r["kind"] == "claim"}
            self._resolved_ids = {r["body"]["claim_id"] for r in recs
                                  if r["kind"] == "resolution"}
        return self._cache

    def verify(self) -> bool:
        """Re-derive the chain FROM DISK; False if any record was edited."""
        self._cache = None
        prev = "GENESIS"
        for rec in self.records():
            h = hashlib.sha256(
                json.dumps({"kind": rec["kind"], "prev_hash": prev,
                            "body": rec["body"]}, sort_keys=True,
                           default=str).encode()).hexdigest()[:16]
            if rec["prev_hash"] != prev or rec["record_hash"] != h:
                return False
            prev = rec["record_hash"]
        return True

    def claims(self) -> list[dict]:
        return [r["body"] for r in self.records() if r["kind"] == "claim"]

    def resolutions(self) -> list[dict]:
        return [r["body"] for r in self.records() if r["kind"] == "resolution"]

    def retrieve(self, as_of: str, *, claim_class: str | None = None,
                 context_key: str | None = None,
                 allow_entity: bool = False) -> list[dict]:
        """Memory lookup for the LLM — embargoed and ticker-blind.

        Two guards, both from R2:
          * OUTCOME EMBARGO: a claim's resolution is only visible once the
            claim's own window has actually closed on or before `as_of`.
            Without this the ledger is a look-ahead vector (Oracle Fallacy).
          * TICKER-BLIND: entity keys are stripped unless `allow_entity` is
            explicitly set, and setting it is recorded by the caller. Retrieval
            keys on market state, never on the name.
        """
        asof = date.fromisoformat(as_of)
        res = {r["claim_id"]: r for r in self.resolutions()}
        out = []
        for c in self.claims():
            if date.fromisoformat(c["asof"]) > asof:
                continue
            if claim_class and c["claim_class"] != claim_class:
                continue
            if context_key and c["context_key"] != context_key:
                continue
            item = {k: c[k] for k in ("claim_class", "asof", "kind", "statement",
                                      "anchor", "anchor_units", "context_key",
                                      "p_raw", "claim_id")}
            if not allow_entity:
                item.pop("statement", None)          # statements name the entity
            else:
                item["entity_key"] = c["entity_key"]
            r = res.get(c["claim_id"])
            visible = (r is not None
                       and date.fromisoformat(c["resolvable_on"]) <= asof)
            item["resolution"] = ({"hit": r["hit"], "realized": r["realized"]}
                                  if visible else None)
            out.append(item)
        return out

    def resolved_pairs(self, *, claim_class: str | None = None
                       ) -> list[tuple[dict, dict]]:
        """(claim, resolution) pairs — the training signal, and the only one."""
        res = {r["claim_id"]: r for r in self.resolutions()}
        return [(c, res[c["claim_id"]]) for c in self.claims()
                if c["claim_id"] in res
                and (claim_class is None or c["claim_class"] == claim_class)]


def redact_entity(claim: Claim) -> Claim:
    """Masked copy for retrieval/prompting — the entity handle removed."""
    return replace(claim, entity_key="MASKED",
                   statement=claim.statement.replace(claim.entity_key, "MASKED"))
