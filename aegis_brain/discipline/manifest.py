"""NIGHT manifests — binding prose to a run that an outsider can verify.

The problem this solves was found by external review, not by us. `/runs/` is in
`.gitignore` — correctly, because it holds derived market data — so every receipt
this programme cites lives on exactly one laptop. A reviewer reading
`docs/NIGHT7_VERDICT.md` can check the prose against nothing at all. The verdict
documents cite `runs/NIGHT7/T2c_TRIGGER_MOM_CONTROL.json` and GitHub returns 404.

A manifest is the small, committable half of a run: every artifact's SHA-256, the
code SHA that produced it, and the receipts' own scalar contents — which are
already sufficient statistics, not market data. It is not a substitute for the
raw artifacts. It is the thing that makes a claim falsifiable by someone who does
not have them.

The second half is `claim_coverage`. NIGHT-7's T1 established the house citation
failure: numbers that are real but arrive stripped of the qualifier that made
them true. A machine cannot check a qualifier. It CAN check that every number
printed in a verdict document exists somewhere in that night's receipts, and
report the ones that do not. An unmatched number is not necessarily wrong — most
are derived, rounded, or quoted from literature — but it is a number no receipt
backs, and that is exactly the list a reviewer should read first.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

#: Artifacts whose full content is embedded (they are sufficient statistics).
EMBED_SUFFIXES = {".json"}
#: Artifacts that are hashed but never embedded (derived series, possibly large).
HASH_ONLY_SUFFIXES = {".csv", ".parquet", ".pkl", ".md", ".txt"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha(repo: Path) -> str:
    """The code SHA, with a loud value rather than a silent one when unknown."""
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return "UNKNOWN-git-rev-parse-failed"
        sha = out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN-git-unavailable"
    dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                           capture_output=True, text=True)
    return sha + ("-DIRTY" if dirty.stdout.strip() else "")


def walk_scalars(obj: Any, prefix: str = "") -> Iterator[tuple[str, float]]:
    """Every numeric leaf in a receipt, with its dotted path."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_scalars(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_scalars(v, f"{prefix}[{i}]")
    elif isinstance(obj, bool):
        return                      # bools are ints in Python; they are not data
    elif isinstance(obj, (int, float)):
        yield prefix, float(obj)


def build(run_dir: Path, repo: Path, night: str) -> dict:
    """Hash and summarise one night's artifacts."""
    if not run_dir.is_dir():
        raise FileNotFoundError(f"no run directory: {run_dir}")
    files = sorted(p for p in run_dir.iterdir() if p.is_file())
    if not files:
        raise RuntimeError(f"{run_dir} is empty — refusing to write an empty "
                           "manifest that would look like a verified night")

    artifacts, receipts = [], {}
    for p in files:
        rec = {"name": p.name, "bytes": p.stat().st_size,
               "sha256": sha256(p), "embedded": False}
        if p.suffix.lower() in EMBED_SUFFIXES:
            try:
                receipts[p.name] = json.loads(p.read_text(encoding="utf-8"))
                rec["embedded"] = True
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                rec["embed_error"] = str(e)
        artifacts.append(rec)

    scalars = {f"{name}:{path}": val
               for name, body in receipts.items()
               for path, val in walk_scalars(body)}
    return {
        "night": night,
        "code_sha": git_sha(repo),
        "run_dir": str(run_dir.relative_to(repo)) if repo in run_dir.parents
                   else str(run_dir),
        "why_this_exists": (
            "/runs/ is gitignored, so receipts live on one machine. This is the "
            "committable half: hashes that bind prose to a specific run, plus "
            "the receipts' scalar contents, which are sufficient statistics and "
            "contain no vendor data."),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "scalar_count": len(scalars),
        "receipts": receipts,
    }


# ── claim coverage ──────────────────────────────────────────────────────────
#: Numbers as they appear in prose: 1,833 · -7.2% · $743,599 · 0.549 · $91.2m
#: The magnitude suffix is part of the number. Without it "$91.2m" is read as
#: ninety-one point two and never matches the 91,236,586 sitting in the receipt,
#: so a correctly cited figure is reported as unbacked.
#: The magnitude suffix needs a word boundary after it, or "482 months" is read
#: as "482 million" and a correctly cited month count is reported unbacked.
#: `\d[\d,]*` swallows the sentence's comma too, so "$743,599," never matches
#: the receipt's 743599. The group must END on a digit.
_NUM = re.compile(
    r"[-+−]?\$?\d(?:[\d,]*\d)?(?:\.\d+)?(?:\s?(?:bn|[mkb])\b|%)?",
    re.IGNORECASE)
_SUFFIX = {"k": 1e3, "m": 1e6, "b": 1e9, "bn": 1e9}
#: Years, section numbers, footnote markers and the like are not claims.
_IGNORE_EXACT = {1900.0, 2000.0}
_YEAR_RANGE = (1960.0, 2100.0)

#: Text that LOOKS numeric but names things. Stripped before claim extraction,
#: because "NIGHT-7" scanned naively yields a claim of "-7" and buries the real
#: unbacked numbers under identifiers. Each pattern names something, not a
#: measured quantity.
_NOT_A_CLAIM = [
    r"\d{4}-\d{2}-\d{2}",                    # ISO dates
    r"NIGHT-?\d+[A-Za-z]?",                  # night labels
    r"§\s*\d+(?:[.–-]\d+)*",                 # canon sections
    r"\bT\d+[a-z]?\b", r"\bA\d\b", r"\bP\d\b", r"\bM\d\b",  # arm/task labels
    r"\bPF-?\d+[A-Za-z]?\b", r"\bG\d\b", r"\bN\d+\b",       # family/gate labels
    r"\bGATE-M\d\b", r"\bTRIAL-[A-Za-z0-9-]+",
    r"\[\^?\d+\]",                           # footnote/citation markers
    r"^#{1,6}\s", r"\(\d{4}\)",              # headings, literature years
    r"\b\d+/\d+\b",                          # ratios like 3/5, 1.5/5
    r"[+±]\s?\d+\s?m\b",                     # forward-horizon labels: +3m, +12m
    r"https?://\S+", r"arXiv:\S+",           # URLs and preprint IDs
    r"\b[0-9a-f]{7,40}\b",                   # git SHAs
]
_NOT_A_CLAIM_RE = re.compile("|".join(_NOT_A_CLAIM))


def _to_float(tok: str) -> float | None:
    t = tok.replace(",", "").replace("$", "").replace("−", "-").strip()
    mult = 1.0
    low = t.lower()
    for suf, m in sorted(_SUFFIX.items(), key=lambda kv: -len(kv[0])):
        if low.endswith(suf):
            t, mult = t[: -len(suf)].strip(), m
            break
    is_pct = t.endswith("%")
    try:
        v = float(t.rstrip("%").strip())
    except ValueError:
        return None
    return v / 100.0 if is_pct else v * mult


@dataclass
class Claim:
    raw: str
    value: float
    line: int
    tol: float = 0.0
    matched_to: str | None = None
    collision: float | None = None


def _tolerance(tok: str, value: float) -> float:
    """Half a unit in the last PRINTED digit — the honest reading of a quote.

    The first version used a 0.5% relative tolerance for every claim. Calibration
    killed it: against 21,000 pooled scalars that rule "backed" 86.6% of
    deliberately fabricated numbers. A quote of "-7.2%" asserts precision to one
    decimal and nothing finer, so that is what it is checked at — and "$91.2m"
    asserts one decimal of MILLIONS, so its window is $50,000 wide.
    """
    t = tok.replace(",", "").replace("$", "").replace("−", "-").strip()
    mult = 1.0
    low = t.lower()
    for suf, m in sorted(_SUFFIX.items(), key=lambda kv: -len(kv[0])):
        if low.endswith(suf):
            t, mult = t[: -len(suf)].strip(), m
            break
    if t.endswith("%"):
        t, mult = t.rstrip("%").strip(), 0.01
    dec = len(t.split(".")[1]) if "." in t else 0
    return (10.0 ** (-dec)) * mult / 2.0 + abs(value) * 1e-9


def _rng(seed: int):
    import numpy as np
    return np.random.default_rng(seed)


def calibrate(scalars: dict[str, float], prior: dict[str, float] | None = None,
              *, n: int = 400, seed: int = 20260810) -> dict:
    """Feed the checker numbers that are KNOWN fabricated and count the passes.

    A gate that has not been measured against a known answer is a decoration —
    the programme learned that the expensive way (NEGATIVE_RESULTS #34, GATE-M1).
    This one nearly shipped as a decoration: with a 0.5% relative tolerance
    across a 21,000-scalar pool it "backed" 86.6% of invented numbers, which
    would have made a 100% coverage score meaningless and reassuring at once.

    The fabricated numbers are drawn in the four shapes this programme actually
    prints — percentages per year, t-statistics, counts, and dollar figures — so
    the false-positive rate is measured against the distribution that matters
    rather than against uniform noise.
    """
    rng = _rng(seed)
    toks = []
    for k in rng.integers(0, 4, n):
        if k == 0:
            toks.append(f"{rng.uniform(-15, 15):.2f}%")
        elif k == 1:
            toks.append(f"{rng.uniform(-6, 6):.2f}")
        elif k == 2:
            toks.append(str(int(rng.integers(50, 3000))))
        else:
            toks.append(f"${int(rng.integers(10_000, 2_000_000)):,}")
    doc = "\n".join(f"the measured value was {t} in the book" for t in toks)
    cc = claim_coverage(doc, scalars, prior=prior, collision_draws=40,
                        seed=seed + 1)
    m = cc["claims_found"] or 1
    return {
        "fabricated_numbers_tested": cc["claims_found"],
        "false_positive_rate": round(cc["informatively_backed"] / m, 4),
        "landed_uninformative": round(cc["matched_but_uninformative"] / m, 4),
        "correctly_unbacked": round(cc["unbacked_anywhere"] / m, 4),
        "reading": ("false_positive_rate is the share of INVENTED numbers this "
                    "checker would have called informatively backed. Read every "
                    "coverage figure against it."),
    }


def claim_coverage(doc: str, scalars: dict[str, float], *,
                   prior: dict[str, float] | None = None,
                   collision_draws: int = 60, seed: int = 20260810) -> dict:
    """Which numbers in `doc` are backed by a scalar in this night's receipts?

    Deliberately permissive about WHAT counts as a match and strict about
    reporting what did not. Matching a number does not make the sentence around
    it true — the NIGHT-7 citation failure was true numbers in false sentences,
    and no regex will catch that. The output is a reading list, not a gate.

    `prior` holds scalars from EARLIER nights. The first version lacked it and
    reported 19% of a verdict document as unbacked; most of those numbers were
    real and came from a previous night's receipt ($602,509 is NIGHT-6's clock
    comparison, quoted correctly in NIGHT-7B). Collapsing "from another night"
    into "unbacked" buries the handful of numbers that genuinely have no
    receipt anywhere — which is the only category worth a human's attention.
    """
    claims: list[Claim] = []
    for i, line in enumerate(doc.splitlines(), 1):
        if line.lstrip().startswith(("```", "|---", "[")):
            continue
        line = _NOT_A_CLAIM_RE.sub(" ", line)
        for m in _NUM.finditer(line):
            v = _to_float(m.group(0))
            if v is None or v in _IGNORE_EXACT:
                continue
            if _YEAR_RANGE[0] <= v <= _YEAR_RANGE[1] and float(v).is_integer():
                continue                       # a year, not a measurement
            if abs(v) < 1e-9:
                continue
            tok = m.group(0)
            claims.append(Claim(tok, v, i, _tolerance(tok, v)))

    pool = dict(scalars)
    origin = {k: "this_night" for k in scalars}
    for k, v in (prior or {}).items():
        pool.setdefault(k, v)
        origin.setdefault(k, "prior_night")
    items = list(pool.items())

    def find(value: float, tol: float, is_pct: bool) -> str | None:
        for key, sv in items:
            if sv == 0:
                continue
            # a percent quote may be stored as a fraction OR as the percentage
            # itself, and a sign may be flipped by which direction the sentence
            # reads. Nothing else is tried.
            for cand in ((value, value * 100.0) if is_pct else (value,)):
                scale = 100.0 if cand != value else 1.0
                if abs(cand - sv) <= tol * scale \
                        or abs(-cand - sv) <= tol * scale:
                    return key
        return None

    rng = _rng(seed)
    for c in claims:
        is_pct = c.raw.rstrip().endswith("%")
        c.matched_to = find(c.value, c.tol, is_pct)
        # PER-CLAIM COLLISION: would a DIFFERENT number of this same shape have
        # matched too? If so the match is uninformative regardless of truth.
        hits = 0
        for _ in range(collision_draws):
            d = c.value * float(rng.uniform(0.5, 2.0))
            d = round(d / (2 * c.tol)) * (2 * c.tol) if c.tol else d
            if abs(d - c.value) <= c.tol or d == 0:
                continue
            hits += find(d, c.tol, is_pct) is not None
        c.collision = round(hits / collision_draws, 3)

    def rec(c: Claim) -> dict:
        # ASCII the raw token: the docs use U+2212 MINUS SIGN and a Windows
        # console encoded cp1252 cannot print it, which killed the first run.
        return {"raw": c.raw.replace("−", "-"), "value": c.value,
                "line": c.line, "collision": c.collision,
                **({"backed_by": c.matched_to} if c.matched_to else {})}

    INFORMATIVE = 0.25
    informative = [c for c in claims
                   if c.matched_to and (c.collision or 0) < INFORMATIVE]
    coincidental = [c for c in claims
                    if c.matched_to and (c.collision or 0) >= INFORMATIVE]
    nowhere = [c for c in claims if not c.matched_to]
    return {
        "claims_found": len(claims),
        "informatively_backed": len(informative),
        "matched_but_uninformative": len(coincidental),
        "unbacked_anywhere": len(nowhere),
        "informative_threshold": INFORMATIVE,
        "pool_size": len(pool),
        "backed": [rec(c) | {"origin": origin.get(c.matched_to, "?")}
                   for c in informative],
        "uninformative": [rec(c) for c in coincidental],
        "unbacked": [rec(c) for c in nowhere],
        "reading": (
            "Three states, not two. INFORMATIVELY BACKED: a receipt holds this "
            "number and a perturbed version of it would NOT have matched, so "
            "the match carries information. MATCHED BUT UNINFORMATIVE: a "
            "receipt holds it, but so many scalars sit nearby that any number "
            "of this shape would have matched — small integers and round "
            "figures live here and the check has no power over them. UNBACKED: "
            "no receipt in the programme holds it. None of the three says "
            "anything about the QUALIFIER attached to the number in prose, "
            "which is this programme's actual citation failure mode."),
    }
