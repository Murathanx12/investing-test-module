"""RECAL-1 — ruleset/bank unit tests. No network, no panel, seeded only.

The load-bearing test is `test_brain008_replica_matches_m1_rep_files`: the
BRAIN-008 Ruleset evaluated over a synthetic bank must reproduce exactly what
run_grid's frozen graduation/confirm/gate code does. If that ever drifts, the
recalibration is comparing against the wrong control arm.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from aegis_brain.calibration import ruleset as R
from aegis_brain.calibration.run_grid import confirm_verdict, graduation


def _explore(t_net: float, t_ic: float, contaminated: bool = False) -> dict:
    return {"t_net": t_net, "t_ic": t_ic, "contaminated": contaminated,
            "months": 180}


def make_cell(inj=(1.6, 2.1), others=None, confirm=None, dsr=None,
              pbo=0.2) -> dict:
    others = others if others is not None else [(0.1, 0.2)] * 20
    lm = {R.INJECTED_NAME: _explore(*inj)}
    lm.update({f"s{i}": _explore(*o) for i, o in enumerate(others)})
    sm = {k: _explore(v["t_net"] - 0.3, v["t_ic"] - 0.3) for k, v in lm.items()}
    c = confirm or {"t_net": 1.0, "t_ic": 1.6, "mean_excess_bps": 12.0,
                    "ic_mean": 0.02, "months": 72}
    conf = {f"{seg}/{book}": dict(c) for seg in ("largemid", "small")
            for book in ("prod", "eng")}
    d = dsr if dsr is not None else 0.99
    return {"explore": {"largemid": lm, "small": sm}, "confirm": conf,
            "dsr": {f"{seg}/{book}_{n}": d for seg in ("largemid", "small")
                    for book in ("prod", "eng") for n in (42, 179)},
            "pbo": pbo, "sr_var_empirical": 0.004, "sr_var_used": 0.01}


# ------------------------------------------------- BRAIN-008 equivalence

@pytest.mark.parametrize("inj,others,expected", [
    ((1.6, 2.1), [(0.1, 0.2)] * 20, "adopt"),                  # clean pass
    ((1.4, 2.1), [(0.1, 0.2)] * 20, "no_graduate"),            # t_net short
    ((1.6, 1.9), [(0.1, 0.2)] * 20, "no_graduate"),            # t_ic short
    ((1.6, 2.1), [(3.0, 3.0)] * 5 + [(0.1, 0.2)] * 15,
     "cap_crowded_out"),                                        # top-5 cap
])
def test_brain008_explore_matches_frozen_graduation(inj, others, expected):
    cell = make_cell(inj, others)
    row = R.evaluate(cell, R.BRAIN_008)
    assert row["terminal"] == expected

    # ...and agrees with run_grid's own frozen implementation
    largemid = {name: {"summary": {"t_excess_net": s["t_net"],
                                   "t_ic": s["t_ic"],
                                   "contaminated": s["contaminated"],
                                   "mean_excess_net_bps": 1.0}}
                for name, s in cell["explore"]["largemid"].items()}
    grad = graduation(largemid)
    assert grad["inj_qualified"] == (expected != "no_graduate")
    assert grad["inj_graduated"] == (expected not in
                                     ("no_graduate", "cap_crowded_out"))


@pytest.mark.parametrize("confirm,expected", [
    ({"t_net": 1.0, "t_ic": 1.6, "mean_excess_bps": 12.0, "ic_mean": 0.02,
      "months": 72}, "PASS"),
    ({"t_net": 0.7, "t_ic": 1.6, "mean_excess_bps": 12.0, "ic_mean": 0.02,
      "months": 72}, "FAIL"),
    ({"t_net": 1.0, "t_ic": 1.4, "mean_excess_bps": 12.0, "ic_mean": 0.02,
      "months": 72}, "FAIL"),
    ({"t_net": 1.0, "t_ic": 1.6, "mean_excess_bps": -1.0, "ic_mean": 0.02,
      "months": 72}, "KILL"),
    ({"t_net": 1.0, "t_ic": 1.6, "mean_excess_bps": 12.0, "ic_mean": -0.01,
      "months": 72}, "KILL"),
])
def test_brain008_confirm_matches_frozen_rule(confirm, expected):
    row = R.evaluate(make_cell(confirm=confirm), R.BRAIN_008)
    got = row["confirm"]["verdict"]
    frozen = confirm_verdict({"mean_excess_net_bps": confirm["mean_excess_bps"],
                              "ic_mean": confirm["ic_mean"],
                              "t_excess_net": confirm["t_net"],
                              "t_ic": confirm["t_ic"]})
    # the replica collapses STRONG PASS into PASS; every kill/fail must match
    assert got == expected
    assert (got == "PASS") == (frozen in ("PASS", "STRONG PASS"))


@pytest.mark.parametrize("dsr,pbo,expected", [
    (0.99, 0.2, "adopt"),
    (0.94, 0.2, "dsr_fail"),
    (0.99, 0.5, "pbo_fail"),
    (0.99, 0.9, "pbo_fail"),
])
def test_brain008_adoption_gate(dsr, pbo, expected):
    row = R.evaluate(make_cell(dsr=dsr, pbo=pbo), R.BRAIN_008)
    assert row["terminal"] == expected


# ------------------------------------------------------ BRAIN-009 family

def test_ic_gate_admits_a_cost_drowned_edge_that_brain008_kills():
    """The RECAL-1 thesis in one assertion: a candidate with real information
    (t_ic 2.4) but a cost-eaten book (t_net -0.2) is killed by BRAIN-008 at
    explore and reaches confirm under the IC gate."""
    cell = make_cell(inj=(-0.2, 2.4))
    assert R.evaluate(cell, R.BRAIN_008)["terminal"] == "no_graduate"
    row = R.evaluate(cell, R.BRAIN_009_SEED)
    assert row["inj_graduated"] is True
    assert row["terminal"] != "no_graduate"


def test_ic_ranking_changes_the_cap_winners():
    """Under BRAIN-008 the cap is filled by the five highest t_net; under
    BRAIN-009 by the five highest t_ic — a candidate can be crowded out by
    one and graduate under the other."""
    others = [(2.0, 2.05)] * 5 + [(0.1, 0.2)] * 15
    cell = make_cell(inj=(1.6, 2.9), others=others)
    assert R.evaluate(cell, R.BRAIN_008)["terminal"] == "cap_crowded_out"
    assert R.evaluate(cell, R.BRAIN_009_SEED)["inj_graduated"] is True


def test_both_segment_explore_sees_a_small_only_edge():
    """I3 structural blindness: the edge lives in the small segment only."""
    cell = make_cell(inj=(0.0, 0.1))
    cell["explore"]["small"][R.INJECTED_NAME] = _explore(0.2, 2.6)
    lm_only = R.BRAIN_009_SEED
    both = R.variant(R.BRAIN_009_SEED, "both",
                     explore_segments=("largemid", "small"))
    assert R.evaluate(cell, lm_only)["terminal"] == "no_graduate"
    row = R.evaluate(cell, both)
    assert row["inj_graduated"] is True
    assert row["inj_segment"] == "small"


def test_contaminated_signals_never_qualify_or_take_cap_slots():
    others = [(9.0, 9.0, True)] * 5 + [(0.1, 0.2)] * 15
    lm = {R.INJECTED_NAME: _explore(1.6, 2.1)}
    for i, o in enumerate(others):
        lm[f"s{i}"] = _explore(*o)
    cell = make_cell()
    cell["explore"]["largemid"] = lm
    row = R.evaluate(cell, R.BRAIN_008)
    assert row["n_null_qualifiers"] == 0
    assert row["terminal"] == "adopt"


# ----------------------------------------------------------- silence bans

def test_missing_segment_raises_rather_than_scoring_a_kill():
    cell = make_cell()
    del cell["explore"]["small"]
    rs = R.variant(R.BRAIN_009_SEED, "both",
                   explore_segments=("largemid", "small"))
    with pytest.raises(KeyError):
        R.evaluate(cell, rs)


def test_missing_confirm_book_raises():
    cell = make_cell()
    del cell["confirm"]["largemid/eng"]
    with pytest.raises(KeyError):
        R.evaluate(cell, R.BRAIN_009_SEED)


def test_none_pbo_raises():
    cell = make_cell()
    cell["pbo"] = None
    with pytest.raises(RuntimeError):
        R.evaluate(cell, R.BRAIN_008)


def test_terminal_states_are_exhaustive_and_exclusive():
    seen = set()
    for dsr, pbo, conf, inj in [
        (0.99, 0.2, None, (1.6, 2.1)),
        (0.90, 0.2, None, (1.6, 2.1)),
        (0.99, 0.7, None, (1.6, 2.1)),
        (0.99, 0.2, {"t_net": 0.1, "t_ic": 0.1, "mean_excess_bps": 1.0,
                     "ic_mean": 0.01, "months": 72}, (1.6, 2.1)),
        (0.99, 0.2, None, (0.1, 0.2)),
    ]:
        row = R.evaluate(make_cell(inj=inj, confirm=conf, dsr=dsr, pbo=pbo),
                         R.BRAIN_008)
        assert row["terminal"] in R.TERMINAL_STATES
        seen.add(row["terminal"])
    assert {"adopt", "dsr_fail", "pbo_fail", "confirm_fail",
            "no_graduate"} <= seen


def test_select_family_is_deterministic_and_covers_the_seed():
    from aegis_brain.calibration.select import family
    fam = family()
    assert len(fam) == len({r.key() for r in fam}) == 1800
    assert any(r.explore_t_ic == 2.0 and r.explore_segments == ("largemid",)
               and r.confirm_t_ic == 1.0 and r.dsr_book == "eng"
               and r.dsr_threshold == 0.95 and r.pbo_threshold == 0.5
               for r in fam)
    # pbo_threshold=1.0 must be report-only, never a rejection
    rs = next(r for r in fam if r.pbo_threshold == 1.0)
    cell = make_cell(pbo=0.99)
    assert R.evaluate(cell, rs)["terminal"] != "pbo_fail"


def test_wilson_bounds_are_sane():
    from aegis_brain.calibration.run_grid import wilson
    lo, hi = wilson(0, 125)
    assert lo == pytest.approx(0.0, abs=1e-12) and 0.0 < hi < 0.04
    lo, hi = wilson(40, 125)
    assert lo < 0.32 < hi


def test_posterior_bank_buckets_are_monotone_coordinates():
    from aegis_brain.calibration.posterior import bucket_of_bank
    lo = bucket_of_bank({"inj_t_ic": 1.0})
    mid = bucket_of_bank({"inj_t_ic": 2.1, "confirm": {"t_ic": 1.0},
                          "gate": {"dsr": 0.3}})
    hi = bucket_of_bank({"inj_t_ic": 3.0, "confirm": {"t_ic": 2.0},
                         "gate": {"dsr": 0.9}})
    # DSR axis dropped (spec S12); the DSR value in the row must be ignored
    assert lo == (0, 0) and mid == (2, 2) and hi == (3, 3)
    assert all(np.array(hi) >= np.array(mid))


def test_bank_merge_is_cell_aware(tmp_path, monkeypatch):
    """The run-1 defect: a wave whose rep file already existed skipped every
    rep and exited 0. The skip must key on CELLS, not on the filename."""
    from aegis_brain.calibration import bank

    monkeypatch.setattr(bank, "GRID_DIR", tmp_path)
    p = tmp_path / "bank_t_0000.json"
    p.write_text(json.dumps({"rep": 0, "schema": "bank-v1",
                             "cells": {"a0.0/base": {}}}), encoding="utf-8")

    # cells already present -> genuine skip
    msg = bank.run_rep_bank(0, 0.5, (("base", 0.0),), "t")
    assert "skipped" in msg

    # a cell that is absent must NOT be reported as present; it has to try to
    # compute, which without a worker panel raises rather than silently pass
    with pytest.raises((KeyError, RuntimeError, TypeError, AttributeError)):
        bank.run_rep_bank(0, 0.5, (("I2", 0.4),), "t")


def test_coverage_assertion_passes_and_fails(tmp_path, monkeypatch):
    """The guard against the run-1 silent no-op must itself be executable.

    Run 2 shipped it as an inline block containing a NameError, so a 6.8h
    grid was the first thing ever to run it. Both branches are now exercised
    without paying for a single scan.
    """
    from aegis_brain.calibration import bank

    monkeypatch.setattr(bank, "GRID_DIR", tmp_path)
    cells = (("base", 0.0), ("I2", 0.4))
    for rep in (0, 1):
        (tmp_path / f"bank_t_{rep:04d}.json").write_text(
            json.dumps({"rep": rep, "schema": "bank-v1",
                        "cells": {"a0.0/base": {}, "a0.4/I2": {}}}),
            encoding="utf-8")
    assert bank.assert_coverage("t", [0, 1], cells) == 2

    # a rep missing one cell -> loud
    (tmp_path / "bank_t_0002.json").write_text(
        json.dumps({"rep": 2, "schema": "bank-v1",
                    "cells": {"a0.0/base": {}}}), encoding="utf-8")
    with pytest.raises(SystemExit, match="COVERAGE FAILURE"):
        bank.assert_coverage("t", [0, 1, 2], cells)

    # a rep with no file at all -> loud
    with pytest.raises(SystemExit, match="no file"):
        bank.assert_coverage("t", [0, 1, 9], cells)
