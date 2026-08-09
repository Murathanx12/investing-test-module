"""T0.5 — anchor the registry so pre-registration stops being self-attested.

External review's sharpest methodological point: a git timestamp proves WHEN a
trial was written, not that only the trials we report were written. Nothing
structurally prevents ten registrations and one disclosure. That is not an
accusation, it is a gap, and it is free to close.

This submits the SHA-256 of `TRIALS/registry.jsonl` to the OpenTimestamps
calendar servers, which fold it into a Bitcoin block. Anyone can later verify
that this exact registry content existed at that time, without trusting us or
GitHub. The bundled `ots` CLI does not run on this machine (its libsecp256k1
binding fails to load under Windows), so this speaks the calendars' HTTP
protocol directly and stores the returned proofs verbatim.

The proof is only as good as the FILE it commits to, so the digest, the byte
count and the row count are all recorded beside it. A future registry with a
row removed will not match.

    python scripts/anchor_registry.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT

REGISTRY = MODULE_ROOT / "TRIALS" / "registry.jsonl"
OUT_DIR = MODULE_ROOT / "TRIALS" / "anchors"
CALENDARS = (
    "https://a.pool.opentimestamps.org",
    "https://b.pool.opentimestamps.org",
    "https://alice.btc.calendar.opentimestamps.org",
    "https://bob.btc.calendar.opentimestamps.org",
)


def main() -> int:
    raw = REGISTRY.read_bytes()
    digest = hashlib.sha256(raw).digest()
    hexd = digest.hex()
    rows = sum(1 for line in raw.decode("utf-8").splitlines() if line.strip())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for cal in CALENDARS:
        try:
            r = requests.post(
                f"{cal}/digest", data=digest, timeout=30,
                headers={"Accept": "application/vnd.opentimestamps.v1",
                         "User-Agent": "aegis-registry-anchor",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ok = r.status_code == 200 and len(r.content) > 0
            if ok:
                p = OUT_DIR / f"registry_{stamp}_{cal.split('//')[1].split('.')[0]}.otsproof"
                p.write_bytes(r.content)
            results.append({"calendar": cal, "status": r.status_code,
                            "proof_bytes": len(r.content) if ok else 0,
                            "ok": ok})
        except Exception as exc:                    # noqa: BLE001
            results.append({"calendar": cal, "ok": False,
                            "error": f"{type(exc).__name__}: {exc}"[:160]})
        print(results[-1], flush=True)

    manifest = {
        "what": "third-party anchor of the Aegis trial registry",
        "file": "TRIALS/registry.jsonl",
        "sha256": hexd,
        "bytes": len(raw),
        "registered_trials": rows,
        "submitted_utc": stamp,
        "calendars": results,
        "anchored": any(r.get("ok") for r in results),
        "how_to_verify": (
            "the .otsproof files are OpenTimestamps calendar commitments to the "
            "sha256 above. Once the calendars aggregate into a Bitcoin block "
            "(hours), `ots upgrade` and `ots verify` on a machine with a working "
            "client will show the block time. Until then the proofs are pending "
            "commitments, which is still more than a git timestamp."),
        "what_it_does_not_prove": (
            "that this registry contains every trial we ever ran. It proves this "
            "CONTENT existed at this time, so a trial cannot be back-dated INTO "
            "it and a row cannot be silently removed FROM it later. Completeness "
            "remains self-attested and should be described that way."),
    }
    (OUT_DIR / f"MANIFEST_{stamp}.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["anchored"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
