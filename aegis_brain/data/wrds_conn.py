"""Non-interactive WRDS connection helper.

Reads the saved pgpass entry (with proper backslash-escape parsing) and hands
wrds.Connection BOTH credentials explicitly, so the library never fires its
empty-credential pre-flight attempt — each of those registers as a failed
login on WRDS's side and enough of them trip the account throttle
(learned 2026-07-20 the hard way).

Requires the WRDS-routable network (HKU VPN on this machine).
"""

from __future__ import annotations

import os
from pathlib import Path


def _parse_pgpass_line(line: str) -> list[str]:
    """Split a pgpass line on unescaped ':' and unescape '\\:' / '\\\\'."""
    fields: list[str] = []
    cur, esc = "", False
    for ch in line:
        if esc:
            cur += ch
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            fields.append(cur)
            cur = ""
        else:
            cur += ch
    fields.append(cur)
    return fields


def pgpass_credentials(host_substr: str = "wrds") -> tuple[str, str]:
    """(username, password) from the pgpass entry matching host_substr."""
    pgpass = Path(os.environ.get("APPDATA", "")) / "postgresql" / "pgpass.conf"
    if not pgpass.exists():
        raise FileNotFoundError(
            "pgpass.conf not found — run scripts/wrds_setup.py interactively once."
        )
    for line in pgpass.read_text().splitlines():
        if host_substr in line and not line.lstrip().startswith("#"):
            f = _parse_pgpass_line(line.strip())
            if len(f) >= 5:
                return f[3], f[4]
    raise LookupError(f"no pgpass entry matching {host_substr!r}")


def get_connection():
    """Open a wrds.Connection with explicit credentials (single auth attempt)."""
    import wrds

    user, pw = pgpass_credentials()
    return wrds.Connection(wrds_username=user, wrds_password=pw)
