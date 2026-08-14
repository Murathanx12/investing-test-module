"""INTERNET-INVESTIGATOR-FWD-1 — the read gate, in executable code.

WHY THIS FILE EXISTS
====================
`iif1_config.py` already carried `READ_SCHEDULE`. Config text is not
enforcement. Before this file, the only executable check in the whole trial was
`register_internet_investigator_fwd_1.py:145`:

    if n < MIN_GRADED_NIGHTS_BEFORE_READ: raise

which refuses a read at 39 and cheerfully permits one at 41, 57, 79, 119 and
600. That is a floor, and a floor is the one thing the referee's condition said
is not enough: once past 40, an unrestricted sequence of looks is optional
stopping wearing a pre-registration.

So the schedule is enforced here, and every path that can produce a verdict goes
through `require_read`.

THE THREE DISPOSITIONS
======================
`READ`                 n is one of the licensed looks (40 / 80 / 120).
`REFUSE`               n is anything else at or below 120. Not a licensed look;
                       it cannot decide anything, in either direction.
`NEW_PREREG_REQUIRED`  n > 120. The design is powered for three looks ending at
                       120. Accruing past the last look and reading again is
                       just optional stopping relocated, so continuing requires
                       a NEW prospective pre-registration, not a longer run of
                       this one.

THE TERMINAL RULE, FROZEN BEFORE NIGHT 1
========================================
At a licensed look, the per-look O'Brien-Fleming constant is the bar (§19,
widened for multiplicity by `iif1_boundaries.py`):

  40 or 80, |t| >= MDE_Z(look)   -> substantive verdict permitted
  40 or 80, |t| <  MDE_Z(look)   -> INTERIM_UNDERPOWERED. Carries NO H1 reading:
                                    not a win, not a kill, not "trending".
  120,      |t| >= 2.845          -> substantive verdict permitted
  120,      |t| <  2.845          -> the pre-registration TERMINATES
                                    NOT_DETECTABLE. This is the trial's end.

The 120 branch is the important one. If a null at the final look merely meant
"keep accruing", the whole schedule would collapse back into a floor and every
guarantee above it would be decorative.

WHAT A REFUSED OR UNDERPOWERED LOOK MAY NOT PRODUCE
===================================================
Both a positive and a negative substantive verdict. §19's asymmetry trap is
that an underpowered null feels like a kill; it is not evidence of absence. So
`classify` refuses to emit either sign, rather than emitting a null and trusting
the reader to remember why it doesn't count.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT              # noqa: E402

from scripts import iif1_config as C                    # noqa: E402

RECEIPT = MODULE_ROOT / "runs" / "INTERNET-INVESTIGATOR-FWD-1" / "boundaries.json"

#: Dispositions. Strings rather than an enum so a receipt JSON round-trips.
READ = "READ"
REFUSE = "REFUSE"
NEW_PREREG_REQUIRED = "NEW_PREREG_REQUIRED"

#: Verdicts the gate itself can authorise. Anything else is not a verdict this
#: pre-registration can produce.
H1_SUPPORTED = "H1_SUPPORTED"
H1_DIRECTION_REJECTED = "H1_DIRECTION_REJECTED"
INTERIM_UNDERPOWERED = "INTERIM_UNDERPOWERED"
NOT_DETECTABLE = "NOT_DETECTABLE"

#: The claim language bound by the referee's Review-2 condition 1. A positive H1
#: is a statement about forecast calibration on a magnitude/volatility
#: observable. It is not a statement about picking stocks, and the trial forecasts
#: no return, so there is no return-based claim available to make.
CLAIM_LANGUAGE = (
    "autonomous investigation improves magnitude/volatility forecast "
    "calibration relative to an engineered numerical snapshot"
)

#: Substrings that may not appear in a verdict line for this trial. The kill
#: condition already forbids these conclusions in prose; this makes the
#: prohibition executable at the one place a verdict is written.
FORBIDDEN_CLAIM_SUBSTRINGS = (
    "picks stocks", "stock picking", "stock-picking", "stock selection",
    "alpha", "sharpe", "outperform", "beats the market", "tradable",
    "profitable", "skill",
)


class ReadRefused(RuntimeError):
    """Raised when something tries to read the primary at an unlicensed n."""


@dataclass(frozen=True)
class ReadDecision:
    n_graded_nights: int
    disposition: str
    look_index: int | None          # 0, 1, 2 for the 40 / 80 / 120 looks
    mde_z: float | None             # the per-look constant, None when unlicensed
    is_final_look: bool
    reason: str

    @property
    def licensed(self) -> bool:
        return self.disposition == READ

    def as_dict(self) -> dict:
        d = asdict(self)
        d["licensed"] = self.licensed
        return d


def licensed_looks() -> tuple[int, ...]:
    """The graded-night counts at which the primary may be read. Nothing else."""
    return tuple(n for n, _ in C.READ_SCHEDULE)


def check_read(n_graded_nights: int) -> ReadDecision:
    """Classify a proposed read. Never raises — use `require_read` to enforce.

    Split from `require_read` so a runner can *report* "next licensed look is at
    80" during the blind without the act of asking being a read.
    """
    # `int(40.9)` is 40, so a truncating coercion here would hand a licensed
    # look to a value that is not one. A graded-night count is a count.
    if isinstance(n_graded_nights, bool) or n_graded_nights != int(n_graded_nights):
        raise ReadRefused(
            f"graded-night count {n_graded_nights!r} is not an integer. This "
            f"gate does not round its way to a licensed look.")
    n = int(n_graded_nights)
    looks = licensed_looks()
    final = looks[-1]

    for i, (nights, mde_z) in enumerate(C.READ_SCHEDULE):
        if n == nights:
            return ReadDecision(
                n_graded_nights=n, disposition=READ, look_index=i,
                mde_z=float(mde_z), is_final_look=(i == len(looks) - 1),
                reason=(f"licensed look {i + 1} of {len(looks)} at {nights} "
                        f"graded nights; bar is |t| >= {mde_z:.3f} x "
                        f"max(HAC, IID) SE"))

    if n > final:
        return ReadDecision(
            n_graded_nights=n, disposition=NEW_PREREG_REQUIRED, look_index=None,
            mde_z=None, is_final_look=False,
            reason=(f"{n} graded nights is past the final licensed look at "
                    f"{final}. The design is powered for three looks ending "
                    f"there; reading a longer run of THIS pre-registration is "
                    f"optional stopping relocated, not extra evidence. "
                    f"Continuing requires a new prospective pre-registration "
                    f"that states why, and it accrues from its own night one."))

    below = [x for x in looks if x > n]
    return ReadDecision(
        n_graded_nights=n, disposition=REFUSE, look_index=None, mde_z=None,
        is_final_look=False,
        reason=(f"{n} graded nights is not a licensed look. The schedule is "
                f"{looks}; the next licensed look is at {below[0]}. A read here "
                f"decides nothing in either direction — it is not a weaker win "
                f"and it is not a kill."))


def require_read(n_graded_nights: int) -> ReadDecision:
    """`check_read`, but a non-`READ` disposition raises.

    Every code path that can write a verdict, a registry row or a headline goes
    through this. The refusal is the product.
    """
    d = check_read(n_graded_nights)
    if not d.licensed:
        raise ReadRefused(f"[{d.disposition}] {d.reason}")
    return d


def assert_claim_language_permitted(verdict_line: str) -> None:
    """Refuse a verdict line that makes a claim this trial cannot support.

    The trial forecasts the probability of an absolute-move threshold. It
    forecasts no return, holds no position and trades nothing, so no return,
    Sharpe, alpha, skill or tradability statement is available to it at any n —
    including a positive one at the final look.
    """
    low = verdict_line.lower()
    hits = [s for s in FORBIDDEN_CLAIM_SUBSTRINGS if s in low]
    if hits:
        raise ReadRefused(
            f"verdict line makes a claim this pre-registration forbids "
            f"{hits}. The only claim a positive H1 licenses is: "
            f"\"{CLAIM_LANGUAGE}\".")


def classify(n_graded_nights: int, t_stat: float | None) -> dict:
    """The frozen terminal rule. Returns the verdict and whether it is terminal.

    `t_stat` is the primary contrast's paired statistic (B_tools - A_snapshot on
    the magnitude observables), already differenced within the cell and divided
    by max(HAC, IID) SE. `None` means the statistic could not be computed, which
    is never a substantive verdict.
    """
    d = require_read(n_graded_nights)          # raises on an unlicensed n

    if t_stat is None:
        return {
            "verdict": INTERIM_UNDERPOWERED,
            "terminal": False,
            "substantive": False,
            "look": d.as_dict(),
            "line": ("the primary statistic could not be computed at this "
                     "look; no reading of H1 is available in either direction"),
        }

    detectable = abs(float(t_stat)) >= d.mde_z

    if detectable:
        supported = float(t_stat) > 0
        return {
            "verdict": H1_SUPPORTED if supported else H1_DIRECTION_REJECTED,
            "terminal": True,
            "substantive": True,
            "look": d.as_dict(),
            "line": (f"|t| = {abs(float(t_stat)):.3f} clears the look-{d.look_index + 1} "
                     f"bar of {d.mde_z:.3f}. "
                     + (f"Claim licensed: {CLAIM_LANGUAGE}." if supported else
                        "The effect is detectable in the direction OPPOSITE to "
                        "H1; the hypothesis is rejected on direction, not "
                        "merely unsupported.")),
        }

    if d.is_final_look:
        return {
            "verdict": NOT_DETECTABLE,
            "terminal": True,
            "substantive": True,
            "look": d.as_dict(),
            "line": (f"|t| = {abs(float(t_stat)):.3f} against a final-look bar "
                     f"of {d.mde_z:.3f}. The pre-registration TERMINATES here. "
                     f"Under S19 this is not a kill: it is a measured statement "
                     f"that an effect of this size is not detectable at this "
                     f"design's power. Accrual past {d.n_graded_nights} nights "
                     f"requires a new prospective pre-registration."),
        }

    return {
        "verdict": INTERIM_UNDERPOWERED,
        "terminal": False,
        "substantive": False,
        "look": d.as_dict(),
        "line": (f"|t| = {abs(float(t_stat)):.3f} against a look-"
                 f"{d.look_index + 1} bar of {d.mde_z:.3f}. INTERIM ONLY: this "
                 f"look carries NO H1 reading — not a win, not a kill, not a "
                 f"trend. The trial continues to the next licensed look."),
    }


def verify_schedule_matches_receipt() -> dict:
    """The config's constants must equal the simulated boundaries on disk.

    `READ_SCHEDULE` retypes numbers that `iif1_boundaries.py` computed. Retyped
    constants drift, and a bar that is silently 5% loose is a false-positive
    rate nobody notices. This is the check that the frozen text still equals the
    measurement it claims to come from.
    """
    if not RECEIPT.exists():
        raise FileNotFoundError(
            f"{RECEIPT} missing — the read schedule's constants have no "
            f"receipt. Run `python -m scripts.iif1_boundaries` before trusting "
            f"any bar in iif1_config.READ_SCHEDULE.")
    r = json.loads(RECEIPT.read_text(encoding="utf-8"))
    looks = list(r["looks_graded_nights"])
    mdes = list(r["mde_z_by_look"])
    cfg_looks = [n for n, _ in C.READ_SCHEDULE]
    cfg_mdes = [z for _, z in C.READ_SCHEDULE]

    if looks != cfg_looks:
        raise ValueError(f"look schedule drifted: config {cfg_looks} vs "
                         f"receipt {looks}")
    for n, a, b in zip(looks, cfg_mdes, mdes):
        if abs(a - b) > 5e-4:
            raise ValueError(f"MDE_Z at {n} nights drifted: config {a} vs "
                             f"receipt {b}")
    return {"looks": looks, "mde_z": mdes,
            "familywise_alpha": r["achieved_familywise_alpha"]}


def main() -> int:
    """Print the gate's own state. Reads nothing about the trial's results."""
    chk = verify_schedule_matches_receipt()
    print(f"licensed looks: {licensed_looks()}   "
          f"family-wise alpha {chk['familywise_alpha']:.4f}")
    print()
    print(f"{'n':>5s}  {'disposition':<20s} {'MDE_Z':>7s}  note")
    print("-" * 78)
    for n in (39, 40, 41, 79, 80, 81, 119, 120, 121):
        d = check_read(n)
        z = f"{d.mde_z:.3f}" if d.mde_z is not None else "—"
        print(f"{n:>5d}  {d.disposition:<20s} {z:>7s}  {d.reason[:44]}")
    print()
    print("A read at any n not printed as READ decides nothing, in either "
          "direction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
