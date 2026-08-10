"""Probe the WRDS connection for IBES entitlement — status codes, never a claim.

The house rule (feedback_test_before_declaring_blocked) is that nothing may be
called unavailable until it has been CALLED and the failure printed. WRDS needs
the HKU VPN and a Duo push, so an unattended run is expected to fail — but it
must fail with a printed reason, and the reason must distinguish:

    NO_CREDENTIALS   pgpass.conf absent          -> attended setup needed
    NO_ROUTE         DNS / TCP to wrds-cloud     -> VPN down, retry attended
    AUTH_REJECTED    server answered, said no    -> account/2FA problem
    CONNECTED        we are in                   -> then, and only then, ask
                                                    what is entitled

Entitlement is NOT visibility. `list_libraries()` returns everything catalogued;
`list_tables()` returns what the schema exposes; only a SELECT proves read
access. This probe does all three and reports them separately, because the
optionm lesson (578 tables catalogued, zero readable) is exactly this trap.

Usage:  python -m scripts.probe_wrds_ibes [--timeout 180]
Writes: runs/ARENA1/wrds_ibes_probe.json
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT

OUT = MODULE_ROOT / "runs" / "ARENA1" / "wrds_ibes_probe.json"

WRDS_HOST = "wrds-pgdata.wharton.upenn.edu"
WRDS_PORT = 9737

# Tables we care about if IBES is readable, and why.
IBES_TARGETS = {
    "ibes.ptgdet": "per-analyst PRICE TARGET detail — the ONE table that answers B1",
    "ibes.ptgsumu": "price target summary (unadjusted) — consensus target history",
    "ibes.recddet": "per-analyst RECOMMENDATION detail — rating revisions",
    "ibes.detu_epsus": "per-analyst EPS estimate detail — estimate revisions",
    "ibes.statsumu_epsus": "EPS consensus summary — the revision breadth spine",
    "ibes.actu_epsus": "actuals — needed to compute surprise PIT",
    "ibes.id": "IBES ticker <-> CUSIP identity, for the CRSP link",
}


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _reachable(host: str, port: int, timeout: float = 8.0) -> dict:
    """Is the WRDS host routable at all? Distinguishes VPN-down from auth-fail."""
    out = {"host": host, "port": port}
    try:
        addrs = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        out["dns"] = "OK"
        out["resolved"] = sorted({a[4][0] for a in addrs})
    except Exception as exc:  # noqa: BLE001 - the reason IS the result
        out["dns"] = "FAIL"
        out["dns_error"] = f"{type(exc).__name__}: {exc}"
        return out
    t0 = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            out["tcp"] = "OK"
    except Exception as exc:  # noqa: BLE001
        out["tcp"] = "FAIL"
        out["tcp_error"] = f"{type(exc).__name__}: {exc}"
    out["tcp_seconds"] = round(time.time() - t0, 2)
    return out


def probe(timeout: int = 180) -> dict:
    result: dict = {
        "probe": "WRDS/IBES entitlement",
        "at": _stamp(),
        "verdict": "UNKNOWN",
        "network": None,
        "credentials": None,
        "libraries_visible": None,
        "ibes_tables_visible": None,
        "reads": {},
        "note": (
            "Visibility is not entitlement. A library in list_libraries() and a "
            "table in list_tables() may still refuse SELECT — that is what the "
            "optionm probe found (578 tables catalogued, zero readable)."
        ),
    }

    result["network"] = _reachable(WRDS_HOST, WRDS_PORT)
    if result["network"].get("tcp") != "OK":
        result["verdict"] = "NO_ROUTE"
        result["what_this_means"] = (
            "The WRDS host was not reachable from this machine. This is the "
            "expected unattended result: the pull needs the HKU VPN. It is NOT "
            "evidence that IBES is unavailable — the question is unanswered, and "
            "ANALYST-UPSIDE-1 / ANALYST-REVISION-1 stay REGISTERED-QUEUED."
        )
        return result

    from aegis_brain.data.wrds_conn import pgpass_credentials  # noqa: PLC0415

    try:
        user, _pw = pgpass_credentials()
        result["credentials"] = {"pgpass": "FOUND", "username": user}
    except Exception as exc:  # noqa: BLE001
        result["credentials"] = {
            "pgpass": "MISSING",
            "error": f"{type(exc).__name__}: {exc}",
        }
        result["verdict"] = "NO_CREDENTIALS"
        result["what_this_means"] = (
            "Run scripts/wrds_setup.py attended once. Unanswered, not negative."
        )
        return result

    try:
        from aegis_brain.data.wrds_conn import get_connection  # noqa: PLC0415

        conn = get_connection()
    except Exception as exc:  # noqa: BLE001
        result["verdict"] = "AUTH_REJECTED"
        result["auth_error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()[-2000:]
        result["what_this_means"] = (
            "The server answered and refused. Could be Duo (2FA push not "
            "acknowledged), a throttle, or an expired password. Attended retry."
        )
        return result

    try:
        libs = sorted(conn.list_libraries())
        result["libraries_visible"] = {
            "n": len(libs),
            "ibes_like": [x for x in libs if "ibes" in x.lower()],
        }
        if not result["libraries_visible"]["ibes_like"]:
            result["verdict"] = "CONNECTED_NO_IBES"
            result["what_this_means"] = (
                "Connected, and no IBES library is even catalogued for this "
                "account. That IS an answer: the HKU subscription does not "
                "include IBES, so the analyst backtest cannot be run on it."
            )
            return result

        try:
            tables = sorted(conn.list_tables(library="ibes"))
            result["ibes_tables_visible"] = {"n": len(tables), "sample": tables[:60]}
        except Exception as exc:  # noqa: BLE001
            result["ibes_tables_visible"] = {"error": f"{type(exc).__name__}: {exc}"}

        # The only question that matters: does a SELECT return rows?
        for table, why in IBES_TARGETS.items():
            entry = {"why_it_matters": why}
            try:
                df = conn.raw_sql(f"select * from {table} limit 5")
                entry["read"] = "OK"
                entry["n_rows_sampled"] = int(len(df))
                entry["columns"] = list(df.columns)[:40]
            except Exception as exc:  # noqa: BLE001
                entry["read"] = "DENIED_OR_MISSING"
                entry["error"] = f"{type(exc).__name__}: {str(exc)[:400]}"
            result["reads"][table] = entry

        readable = [t for t, e in result["reads"].items() if e.get("read") == "OK"]
        result["readable_tables"] = readable
        if "ibes.ptgdet" in readable or "ibes.ptgsumu" in readable:
            result["verdict"] = "IBES_TARGETS_READABLE"
            result["what_this_means"] = (
                "Decades of point-in-time analyst price targets are readable. "
                "ANALYST-UPSIDE-1 and ANALYST-REVISION-1 become runnable on real "
                "PIT data, and the PM's analyst family can move from OBSERVATIONAL "
                "toward an evidence grade."
            )
        elif readable:
            result["verdict"] = "IBES_PARTIAL"
            result["what_this_means"] = (
                "Some IBES tables read, but not the price-target spine. State "
                "exactly which, and register only what the readable tables support."
            )
        else:
            result["verdict"] = "IBES_VISIBLE_NOT_READABLE"
            result["what_this_means"] = (
                "Catalogued but not entitled — the optionm pattern exactly. "
                "This is a real answer and closes the WRDS route for targets."
            )
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001, S110
            pass
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    res = probe(timeout=args.timeout)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2)[:8000])
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
