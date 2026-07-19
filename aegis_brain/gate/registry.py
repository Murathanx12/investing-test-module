"""Local trial registry (append-only JSONL).

Mirrors the main-repo discipline: registering a trial INCREMENTS the
multiple-testing count (conservative direction), and the cumulative count
this module deflates against is MAIN_REPO_TRIAL_BASE + local trials. The
count only ever goes up; there is no delete API on purpose.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aegis_brain.config import MAIN_REPO_TRIAL_BASE, TRIALS_DIR

REGISTRY_PATH = TRIALS_DIR / "registry.jsonl"


def register_trial(
    name: str,
    hypothesis: str,
    expected_effect: str,
    kill_condition: str,
    registry_path: Path | None = None,
) -> dict:
    """Append a trial row. Idempotent on name — re-registering returns the
    existing row instead of double-counting."""
    path = registry_path or REGISTRY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    for row in _rows(path):
        if row["name"] == name:
            return row
    row = {
        "name": name,
        "hypothesis": hypothesis,
        "expected_effect": expected_effect,
        "kill_condition": kill_condition,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def cumulative_trial_count(registry_path: Path | None = None) -> int:
    """Base (main-repo cumulative at V5 close) + local registered trials."""
    path = registry_path or REGISTRY_PATH
    return MAIN_REPO_TRIAL_BASE + sum(1 for _ in _rows(path))


def _rows(path: Path):
    if not path.exists():
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)
