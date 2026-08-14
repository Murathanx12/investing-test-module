"""INTERNET-INVESTIGATOR-FWD-1 — the interim-look boundaries, computed not recalled.

    python -m scripts.iif1_boundaries

WHY THIS EXISTS
===============
The pre-registration froze a read FLOOR: the primary may not be read below 40
graded nights. The referee's review pointed out that a floor is not a schedule —
once past it, repeated looks are optional stopping, and a trial that may look at
40, 80 and 120 nights and stop at whichever look is favourable has three chances
to clear a bar built for one.

Declaring the checkpoints is only half the fix. Measured here rather than
asserted: three looks at the house constant (MDE_Z = 2.80, i.e. a flat two-sided
1.958) spend a family-wise **0.1079** against a single look's 0.0501 — **2.2x
the declared rate**. So the boundaries have to widen at the early looks.

THE SHAPE CHOSEN, AND WHY
-------------------------
O'Brien-Fleming: very conservative early, essentially nominal at the end. That
matches how this programme already thinks — an early peek should only be able to
stop the trial for an effect so large it would be irresponsible to keep
spending, while the final read is the one the design was powered for and should
not be heavily taxed for having looked twice.

The alternative (Pocock, a constant widened boundary) penalises the final look
just as hard as the first, which would mean paying for the peeks at the moment
the evidence is actually complete.

THE NUMBERS ARE SIMULATED, NOT QUOTED
-------------------------------------
Published OBF critical values are easy to recall approximately and easy to recall
WRONG, and a boundary that is 5% too tight is a false-positive rate nobody
notices. So the constant is found by simulating the joint distribution of the
interim test statistics directly, under the null, and solving for the multiplier
that puts the family-wise error at exactly 5%.

The statistic at look k is a cumulative mean over n_k nights, so the interim
Z-scores are a Brownian path observed at information fractions t_k = n_k / n_K.
That is the standard sequential structure and it is what is simulated here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT              # noqa: E402

OUT = MODULE_ROOT / "runs" / "INTERNET-INVESTIGATOR-FWD-1"

#: The declared checkpoints, in GRADED NIGHTS. 40 is the pre-registered read
#: floor; 80 and 120 are the two further looks the schedule permits. No look may
#: happen at any other n.
LOOKS = (40, 80, 120)

ALPHA = 0.05          #: family-wise, two-sided, across ALL looks
POWER_Z = 0.842       #: z for 80% power — the same second term as MDE_Z = 2.80
N_SIMS = 400_000
SEED = 20260814


def simulate_fwer(bounds: np.ndarray, fracs: np.ndarray,
                  rng: np.random.Generator, n_sims: int = N_SIMS) -> float:
    """P(any look crosses its boundary) under the null, for a BOUNDARY VECTOR.

    Takes the boundaries explicitly rather than a multiplier, so the O'Brien-
    Fleming shape and a flat constant boundary can be compared honestly. An
    earlier version took a multiplier and always applied the OBF shape, which
    made the "what would three naive looks cost" comparison silently measure a
    shrunken OBF boundary instead of a flat one — a comparison that looked
    reassuring because it was not the comparison being described.

    The cumulative statistic at information fraction t is `B(t)/t` where `B` is
    standard Brownian motion, so `Z_k = B(t_k)/sqrt(t_k)`. Increments are
    independent, which is what makes the interim looks correlated in exactly the
    way a sequential design has to account for.
    """
    dt = np.diff(np.concatenate([[0.0], fracs]))
    inc = rng.standard_normal((n_sims, len(fracs))) * np.sqrt(dt)
    B = np.cumsum(inc, axis=1)
    Z = B / np.sqrt(fracs)
    return float((np.abs(Z) >= np.asarray(bounds)).any(axis=1).mean())


def obf_bounds(mult: float, fracs: np.ndarray) -> np.ndarray:
    """O'Brien-Fleming: conservative early, near-nominal at the end."""
    return mult / np.sqrt(fracs)


def solve_multiplier(fracs: np.ndarray, alpha: float,
                     rng: np.random.Generator) -> float:
    """Bisect for the OBF multiplier giving exactly `alpha` family-wise."""
    lo, hi = 1.0, 5.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if simulate_fwer(obf_bounds(mid, fracs), fracs, rng) > alpha:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    looks = np.array(LOOKS, dtype=float)
    fracs = looks / looks[-1]

    mult = solve_multiplier(fracs, ALPHA, rng)
    crit = obf_bounds(mult, fracs)
    mde_z = crit + POWER_Z

    house_z = 2.80 - POWER_Z                 # the nominal two-sided 1.958
    achieved = simulate_fwer(crit, fracs, rng)
    single = simulate_fwer(np.array([house_z]), np.array([1.0]), rng)
    # The real comparison: the SAME flat constant applied at all three looks,
    # which is what "declare a schedule and keep the house MDE" would mean.
    naive = simulate_fwer(np.full(len(fracs), house_z), fracs, rng)

    print(f"looks at graded nights {LOOKS}, information fractions "
          f"{np.round(fracs, 3).tolist()}")
    print(f"OBF multiplier solved: {mult:.4f}  "
          f"(achieved family-wise alpha {achieved:.4f} against target {ALPHA})")
    print()
    print(f"{'nights':>7s} {'info frac':>10s} {'crit z':>8s} {'MDE_Z':>8s}")
    print("-" * 37)
    for n, f, c, m in zip(LOOKS, fracs, crit, mde_z):
        print(f"{int(n):>7d} {f:>10.3f} {c:>8.3f} {m:>8.3f}")
    print()
    print(f"For contrast: a SINGLE look at the house MDE_Z=2.80 spends "
          f"{single:.4f}; three looks at that same FLAT constant spend "
          f"{naive:.4f} — {naive / ALPHA:.1f}x the declared rate. That gap is "
          f"the reason this file exists.")
    print(f"\nThe final look pays almost nothing for the two peeks: "
          f"MDE_Z {mde_z[-1]:.3f} against the unadjusted 2.80.")

    meta = {
        "what": "O'Brien-Fleming interim-look boundaries for the IIF-1 primary, "
                "solved by simulation rather than quoted",
        "looks_graded_nights": list(LOOKS),
        "information_fractions": fracs.tolist(),
        "alpha_familywise_two_sided": ALPHA,
        "power_z": POWER_Z,
        "obf_multiplier": mult,
        "critical_z": crit.tolist(),
        "mde_z_by_look": mde_z.tolist(),
        "achieved_familywise_alpha": achieved,
        "single_look_alpha_at_house_constant": single,
        "three_naive_looks_alpha_at_house_constant": naive,
        "n_sims": N_SIMS, "seed": SEED,
        "note": "MDE at look k = mde_z_by_look[k] x max(HAC, IID) SE. A read at "
                "a night count NOT in `looks_graded_nights` is not a licensed "
                "look and cannot decide anything.",
    }
    (OUT / "boundaries.json").write_text(json.dumps(meta, indent=2),
                                         encoding="utf-8")
    print(f"\nwrote {OUT / 'boundaries.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
