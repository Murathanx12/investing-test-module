"""Prior-check gate — run BEFORE registering any new hypothesis.

Adopted at AI-panel round 6 (2026-07-25) as the lightweight version of the
panels' "vectorized prior-check" proposal: the ledger corpus is ~50
documents, so disciplined keyword retrieval beats a vector DB (revisit at
~500 docs). Searches the registry, all trial docs, the factory protocol,
the taxonomy, and the NEGATIVE_RESULTS mirror; prints every hit with
context so a proposed idea meets its own graveyard before it earns a
registration. The gate is procedural: no new registry row without a
prior-check transcript in the freeze commit message or trial doc.

Usage:  .venv\\Scripts\\python -m scripts.prior_check dtc "days to cover" short
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODULE_ROOT = Path(__file__).resolve().parents[1]
AEGIS = Path(r"C:\Users\mrthn\aegis-finance")

CORPUS = [
    MODULE_ROOT / "TRIALS" / "registry.jsonl",
    MODULE_ROOT / "docs" / "STRATEGY_FACTORY.md",
    MODULE_ROOT / "docs" / "SIGNAL_TAXONOMY.md",
    MODULE_ROOT / "STATUS.md",
    AEGIS / "NEGATIVE_RESULTS.md",
    AEGIS / "docs" / "ROADMAP_BRAIN_V2.md",
    *sorted((MODULE_ROOT / "TRIALS").glob("*.md")),
    *sorted((AEGIS / "docs" / "research").glob("AI_PANEL_*.md")),
]


def search(terms: list[str]) -> int:
    pats = [re.compile(re.escape(t), re.IGNORECASE) for t in terms]
    n_hits = 0
    for path in CORPUS:
        if not path.exists():
            print(f"  [missing corpus file: {path}]")
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            print(f"  [unreadable {path.name}: {exc}]")
            continue
        hits = [(i + 1, ln.strip()) for i, ln in enumerate(lines)
                if any(p.search(ln) for p in pats)]
        if hits:
            print(f"\n== {path} ({len(hits)} hits)")
            for ln_no, ln in hits[:12]:
                print(f"  {ln_no}: {ln[:220]}")
            if len(hits) > 12:
                print(f"  ... {len(hits) - 12} more")
            n_hits += len(hits)
    return n_hits


def _expand(raw: list[str]) -> list[str]:
    """Split multi-word phrases into words and add crude stems (skewness->skew).

    Guards the 2026-07-26 near-miss: a whole quoted phrase searched as one
    literal string returned 0 hits on families that WERE in the graveyard.
    """
    words = {w for t in raw for w in t.split() if len(w) >= 3}
    stems = {w[:5] for w in words if len(w) >= 8}
    return sorted(words | stems)


def main() -> None:
    terms = _expand(sys.argv[1:])
    if not terms:
        print(__doc__)
        sys.exit(2)
    print(f"prior-check: {terms}")
    n = search(terms)
    print(f"\n{n} total hits across the ledger corpus.")
    if n:
        print("REVIEW EVERY HIT before registering: closed families cannot "
              "re-enter under new clothing (re-litigation ban).")
    else:
        print("No priors found — genuinely new ground. Register with the "
              "4-tag taxonomy schema (source/horizon/turnover/role).")


if __name__ == "__main__":
    main()
