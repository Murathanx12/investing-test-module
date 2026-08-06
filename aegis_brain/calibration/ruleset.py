"""RECAL-1 — the parameterized ladder (candidate BRAIN-009) as pure functions.

A Ruleset is a complete description of the factory's decision ladder:
explore gate + ranking + cap, confirm wall, adoption gate. Nothing here
touches production; `BRAIN_008` is a byte-faithful replica of the FROZEN
rule the M1 grid measured, and `tests/test_recal_ruleset.py` asserts it
reproduces the banked M1 terminal states cell for cell. That replica is
what licenses reading any other ruleset off the same evidence bank.

Why a ruleset object at all: M1 cost ~170 core-seconds per cell, and 95% of
that is the 42 explore scans, which do not depend on the gate. Banking the
scan statistics once (bank.py) makes every candidate ladder a pure function
over the bank — so the ladder family is searched offline, in seconds, and
the overnight grid runs exactly once.

Ordering of the gates is fixed (explore -> cap -> confirm -> DSR -> PBO);
only thresholds, the ranking key, the segments scanned and the book the
adoption gate reads are free.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

TERMINAL_STATES = ("no_graduate", "cap_crowded_out", "confirm_fail",
                   "dsr_fail", "pbo_fail", "adopt")
INJECTED_NAME = "injected_edge"


@dataclass(frozen=True)
class Ruleset:
    """One complete decision ladder. All thresholds are >= comparisons."""

    name: str
    # ---- explore gate (per segment scan, 2004-01..2018-12)
    explore_t_ic: float | None          # None = not gated on IC
    explore_t_net: float | None         # None = t_net is a diagnostic only
    explore_rank_by: str                # "t_ic" | "t_net" — the top-N cap key
    explore_segments: tuple[str, ...]
    explore_top_n: int
    # ---- confirm wall (held-out 2019-01..2024-12, same segment)
    confirm_t_ic: float | None
    confirm_t_net: float | None
    confirm_sign_ic: bool               # KILL if mean IC <= 0
    confirm_sign_net: bool              # KILL if mean net excess <= 0
    confirm_book: str                   # "prod" | "eng" (implementation layer)
    # ---- adoption gate
    dsr_book: str                       # "prod" | "eng"
    dsr_n_trials: int                   # 42 (in-experiment) | 179 (production)
    dsr_threshold: float
    pbo_threshold: float

    def key(self) -> str:
        return (f"e{self.explore_t_ic}/{self.explore_t_net}"
                f"@{self.explore_rank_by}:{'+'.join(self.explore_segments)}"
                f"|c{self.confirm_t_ic}/{self.confirm_t_net}:{self.confirm_book}"
                f"|d{self.dsr_threshold}@{self.dsr_n_trials}:{self.dsr_book}"
                f"|p{self.pbo_threshold}")


# --------------------------------------------------------------- the rules

# The FROZEN production ladder the M1 grid measured (docs/STRATEGY_FACTORY.md
# graduation rule + run_confirm_gpsmall.py confirm rule + gate/adoption.py).
# Do not edit: this is the control arm.
BRAIN_008 = Ruleset(
    name="BRAIN-008",
    explore_t_ic=2.0, explore_t_net=1.5, explore_rank_by="t_net",
    explore_segments=("largemid",), explore_top_n=5,
    confirm_t_ic=1.5, confirm_t_net=0.8,
    confirm_sign_ic=True, confirm_sign_net=True, confirm_book="prod",
    dsr_book="prod", dsr_n_trials=42, dsr_threshold=0.95, pbo_threshold=0.5,
)

# RECAL-1 headline candidate (ratified 2026-08-06): information-gated explore,
# t_net demoted to a diagnostic, cost handled at the implementation layer
# (engineered book) and by the posterior sizing ladder. dsr_threshold is the
# CALIBRATED slot — 0.95 here is the inherited value, and select.py re-fits it
# to the pre-registered FDR budget. Not frozen until select.py freezes it.
BRAIN_009_SEED = Ruleset(
    name="BRAIN-009-seed",
    explore_t_ic=2.0, explore_t_net=None, explore_rank_by="t_ic",
    explore_segments=("largemid",), explore_top_n=5,
    confirm_t_ic=1.0, confirm_t_net=None,
    confirm_sign_ic=True, confirm_sign_net=False, confirm_book="eng",
    dsr_book="eng", dsr_n_trials=179, dsr_threshold=0.95, pbo_threshold=0.5,
)

RULESETS = {r.name: r for r in (BRAIN_008, BRAIN_009_SEED)}
# Alias so the overnight chain can name the ladder before select.py freezes
# it; the frozen ladder is read from @runs/GATE-M1/brain009_frozen.json.
RULESETS["BRAIN-009"] = BRAIN_009_SEED


def variant(base: Ruleset, name: str, **kw) -> Ruleset:
    return replace(base, name=name, **kw)


# ------------------------------------------------------------- evaluation

def _passes(stat: dict, t_ic: float | None, t_net: float | None) -> bool:
    if t_ic is not None and stat["t_ic"] < t_ic:
        return False
    if t_net is not None and stat["t_net"] < t_net:
        return False
    return True


def evaluate(cell: dict, rs: Ruleset) -> dict:
    """Run one banked cell through one ladder. Returns the M1 row shape:
    terminal state + the diagnostics the tables and the posterior map read.

    `cell` is a bank record (bank.bank_cell). Raises on a bank that cannot
    answer the ruleset (e.g. a segment that was never scanned) rather than
    silently scoring it as a kill — a missing scan is not a rejection.
    """
    quals: list[tuple[str, str, float]] = []   # (name, segment, rank value)
    for seg in rs.explore_segments:
        if seg not in cell["explore"]:
            raise KeyError(f"bank has no explore scan for segment {seg!r}")
        for name, stat in cell["explore"][seg].items():
            if stat["contaminated"]:
                continue
            if _passes(stat, rs.explore_t_ic, rs.explore_t_net):
                quals.append((name, seg, stat[rs.explore_rank_by]))
    quals.sort(key=lambda x: -x[2])
    graduates = quals[:rs.explore_top_n]

    inj_entries = [q for q in quals if q[0] == INJECTED_NAME]
    inj_stats = {seg: cell["explore"][seg][INJECTED_NAME]
                 for seg in rs.explore_segments}
    best_seg = max(inj_stats, key=lambda s: inj_stats[s][rs.explore_rank_by])
    row = {
        "ruleset": rs.name,
        "n_qualifiers": len(quals),
        "n_null_qualifiers": sum(1 for q in quals if q[0] != INJECTED_NAME),
        "inj_qualified": bool(inj_entries),
        "inj_graduated": any(q[0] == INJECTED_NAME for q in graduates),
        "inj_rank_among_qualifiers": next(
            (i + 1 for i, q in enumerate(quals) if q[0] == INJECTED_NAME), None),
        "inj_t_net": inj_stats[best_seg]["t_net"],
        "inj_t_ic": inj_stats[best_seg]["t_ic"],
        "sr_var_used": cell["sr_var_used"],
    }
    if not row["inj_qualified"]:
        row["terminal"] = "no_graduate"
        return row
    if not row["inj_graduated"]:
        row["terminal"] = "cap_crowded_out"
        return row

    # the segment the injected candidate actually graduated in
    seg = max((q for q in inj_entries), key=lambda q: q[2])[1]
    row["inj_segment"] = seg
    ckey = f"{seg}/{rs.confirm_book}"
    if ckey not in cell["confirm"]:
        raise KeyError(f"bank has no confirm read for {ckey!r}")
    c = cell["confirm"][ckey]
    row["confirm"] = {"t_net": c["t_net"], "t_ic": c["t_ic"],
                      "mean_excess_bps": c["mean_excess_bps"],
                      "ic_mean": c["ic_mean"], "months": c["months"],
                      "book": rs.confirm_book}
    killed = ((rs.confirm_sign_net and c["mean_excess_bps"] <= 0)
              or (rs.confirm_sign_ic and c["ic_mean"] <= 0))
    passed = (not killed) and _passes(c, rs.confirm_t_ic, rs.confirm_t_net)
    row["confirm"]["verdict"] = "PASS" if passed else (
        "KILL" if killed else "FAIL")
    if not passed:
        row["terminal"] = "confirm_fail"
        return row

    dkey = f"{seg}/{rs.dsr_book}_{rs.dsr_n_trials}"
    if dkey not in cell["dsr"]:
        raise KeyError(f"bank has no DSR for {dkey!r}")
    dsr = cell["dsr"][dkey]
    pbo = cell["pbo"]
    if pbo is None:
        raise RuntimeError("pbo=None reached the gate — S3 violated")
    row["gate"] = {"dsr": dsr, "pbo": pbo, "book": rs.dsr_book,
                   "n_trials": rs.dsr_n_trials}
    if dsr < rs.dsr_threshold:
        row["terminal"] = "dsr_fail"
    elif pbo >= rs.pbo_threshold:
        row["terminal"] = "pbo_fail"
    else:
        row["terminal"] = "adopt"
    return row
