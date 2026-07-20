"""One-time WRDS connection setup + subscription verification.

Interactive: prompts for your WRDS username/password, then offers to save a
.pgpass file so future connections need no password. Windows location:
%APPDATA%\\postgresql\\pgpass.conf (chmod-equivalent handled by the wrds lib).

Usage (must be run interactively so you can type credentials):
    .venv\\Scripts\\python -m scripts.wrds_setup
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import wrds

MUST_HAVE = {
    "crsp": "CRSP stock data — survivorship-free prices + DELISTING RETURNS (the unlock)",
    "comp": "Compustat — fundamentals (point-in-time-ish via as-first-reported items)",
}
NICE_TO_HAVE = {
    "ff": "Fama-French factor library",
    "crsp_a_stock": "CRSP annual-update stock files (msf/dsf/msedelist)",
    "comp_na_daily_all": "Compustat North America daily",
    "wrdsapps": "WRDS applications (linking tables, financial ratios)",
}


def main() -> None:
    print("Connecting to WRDS (wrds-pgdata.wharton.upenn.edu:9737)...")
    print("Enter your WRDS username and password when prompted.\n")
    db = wrds.Connection()  # prompts; then offers pgpass creation itself

    # Ensure passwordless future connections
    try:
        db.create_pgpass_file()
        print("\n.pgpass saved — future connections are passwordless.")
    except Exception as exc:
        print(f"\n(pgpass not saved: {exc} — you'll be prompted again next time)")

    libs = set(db.list_libraries())
    print(f"\nSubscribed libraries: {len(libs)}")

    print("\n=== MUST-HAVE ===")
    ok = True
    for lib, why in MUST_HAVE.items():
        have = lib in libs
        ok &= have
        print(f"  [{'OK ' if have else 'MISSING'}] {lib}: {why}")

    print("\n=== Nice-to-have ===")
    for lib, why in NICE_TO_HAVE.items():
        print(f"  [{'OK ' if lib in libs else '—  '}] {lib}: {why}")

    if "crsp" in libs:
        print("\nSanity query: CRSP monthly stock file + delisting events...")
        msf = db.raw_sql("select count(*) as n from crsp.msf")
        dl = db.raw_sql(
            "select count(*) as n from crsp.msedelist where dlret is not null"
        )
        print(f"  crsp.msf rows: {int(msf['n'][0]):,}")
        print(f"  crsp.msedelist rows with delisting returns: {int(dl['n'][0]):,}")
        sample = db.raw_sql(
            "select permno, date, prc, ret from crsp.msf "
            "where permno = 14593 order by date desc limit 3"
        )  # 14593 = AAPL
        print("  AAPL (permno 14593) latest months:")
        print(sample.to_string(index=False))

    db.close()
    print("\n" + ("ALL GOOD — WRDS is wired up." if ok else
                  "Connected, but a must-have library is missing — your HKU "
                  "subscription may not include it; check with WRDS support."))


if __name__ == "__main__":
    main()
