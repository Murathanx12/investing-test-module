"""Stage-A replay runner — synthetic fixtures only; the real candidate bank
is never read by the test suite (small-segment rows stay unexamined until
the replay fires)."""

import json

import numpy as np
import pandas as pd
import pytest

from aegis_brain.calibration.replay_runner import (
    TOP_N,
    family_bar,
    conditional_confirm_rate,
    load_candidates,
    load_floor,
    stage_a,
)

P95 = {("injected_edge", "largemid"): 1.64,
       ("injected_edge", "small"): 1.75,
       ("vol_12m_low", "largemid"): 2.97,
       ("vol_12m_low", "small"): 4.19,
       ("amihud_3m", "largemid"): -0.68,
       ("amihud_3m", "small"): -3.24}
ONTO = {"strong": {"family": "generic"},
        "noise": {"family": "generic"},
        "noise2": {"family": "generic"},
        "sigma_sig": {"family": "vol_12m_low"},
        "illiq_sig": {"family": "amihud_3m"},
        "burned": {"family": "generic"},
        "ok": {"family": "generic"},
        "fresh": {"family": "generic"},
        "gross_prof": {"family": "generic"},
        "conc_low": {"family": "generic"},
        **{f"s{i}": {"family": "generic"} for i in range(20)},
        **{f"n{i}": {"family": "generic"} for i in range(179)}}


@pytest.fixture
def cdfs():
    rng = np.random.default_rng(1)
    return {"largemid": np.sort(rng.standard_normal(4000) * 1.12),
            "small": np.sort(rng.standard_normal(4000) * 1.25)}


@pytest.fixture
def pairs():
    rng = np.random.default_rng(2)
    return {seg: np.column_stack([rng.standard_normal(4000) * 1.1,
                                  rng.standard_normal(4000) * 1.1])
            for seg in ("largemid", "small")}


def _cands(rows):
    return pd.DataFrame(rows, columns=["signal", "segment", "contaminated",
                                       "t_ic", "src"])


def test_family_bar_semantics():
    # generic candidates get the generic bar
    assert family_bar("strong", "largemid", ONTO, P95) == 1.64
    # sigma-family candidates get their (higher) family p95
    assert family_bar("sigma_sig", "small", ONTO, P95) == 4.19
    # negative-bias families never LOWER the bar below generic
    assert family_bar("illiq_sig", "small", ONTO, P95) == 1.75
    with pytest.raises(KeyError, match="ontology"):
        family_bar("unmapped_signal", "small", ONTO, P95)


def test_conditional_confirm_rate():
    pairs = np.array([[2.0, 1.0], [2.5, 0.2], [3.0, 0.7], [0.5, 9.9]])
    rate, n = conditional_confirm_rate(pairs, bar=2.0)
    assert n == 3 and rate == pytest.approx(2 / 3)
    assert conditional_confirm_rate(pairs, bar=99.0) == (
        pytest.approx(float("nan"), nan_ok=True), 0)


def test_strong_candidate_graduates_null_does_not(cdfs, pairs):
    cands = _cands([("strong", "largemid", False, 6.0, "b1"),
                    ("noise", "largemid", False, 0.3, "b1"),
                    ("noise2", "small", False, -1.0, "b2")])
    out = stage_a(cands, cdfs, pairs, ONTO, P95)
    assert [g["signal"] for g in out["graduates"]] == ["strong"]


def test_family_floor_kills_bh_passing_sigma_artifact(cdfs, pairs):
    # t_ic 3.0 in small: passes BH against the flat floor easily, but sits
    # BELOW the vol-family small p95 of 4.19 -> killed by the family floor
    cands = _cands([("sigma_sig", "small", False, 3.0, "b1"),
                    ("strong", "largemid", False, 6.0, "b1")])
    out = stage_a(cands, cdfs, pairs, ONTO, P95)
    assert [g["signal"] for g in out["graduates"]] == ["strong"]
    assert [r["signal"] for r in out["bh_pass_family_fail"]] == ["sigma_sig"]
    assert out["accounting"]["n_killed_by_family_floor"] == 1


def test_sigma_candidate_above_family_floor_graduates(cdfs, pairs):
    cands = _cands([("sigma_sig", "small", False, 5.0, "b1")])
    out = stage_a(cands, cdfs, pairs, ONTO, P95)
    assert [g["signal"] for g in out["graduates"]] == ["sigma_sig"]


def test_contaminated_string_false_is_not_contaminated(cdfs, pairs):
    cands = _cands([("ok", "largemid", "False", 6.0, "b1"),
                    ("burned", "largemid", "True", 7.0, "b1")])
    out = stage_a(cands, cdfs, pairs, ONTO, P95)
    assert [g["signal"] for g in out["graduates"]] == ["ok"]


def test_confirm_burned_receipts_excluded(cdfs, pairs):
    cands = _cands([("gross_prof", "small", False, 7.31, "b2"),
                    ("conc_low", "largemid", False, 4.46, "b7"),
                    ("fresh", "largemid", False, 6.0, "b1")])
    out = stage_a(cands, cdfs, pairs, ONTO, P95)
    assert [g["signal"] for g in out["graduates"]] == ["fresh"]
    assert len(out["excluded_contaminated_or_burned"]) == 2


def test_cap_binds_at_top_n(cdfs, pairs):
    rows = [(f"s{i}", "largemid", False, 8.0 - i * 0.1, "b1")
            for i in range(TOP_N + 5)]
    out = stage_a(_cands(rows), cdfs, pairs, ONTO, P95)
    assert out["accounting"]["n_graduates"] == TOP_N
    assert len(out["bh_survivors_below_cap"]) == 5
    assert out["graduates"][0]["signal"] == "s0"


def test_bh_respects_q_under_pure_null(cdfs, pairs):
    rng = np.random.default_rng(7)
    rows = [(f"n{i}", "largemid", False,
             float(rng.choice(cdfs["largemid"])), "b1") for i in range(179)]
    out = stage_a(_cands(rows), cdfs, pairs, ONTO, P95)
    assert out["accounting"]["n_graduates"] <= 2


def _write_universe(tmp_path, extra_row=""):
    cols = "signal,segment,contaminated,months,t_ic\n"
    (tmp_path / "batch1_summary.csv").write_text(
        cols + "x,largemid,False,180,2.0\n" + extra_row, encoding="utf-8")
    (tmp_path / "batch3a_daily_rerun.csv").write_text(
        cols + "ivol_low_D,small,False,180,7.0\n", encoding="utf-8")
    (tmp_path / "batch5_defensive_rerun.csv").write_text(
        cols + "defensive,small,False,180,6.5\n", encoding="utf-8")
    (tmp_path / "trial_tgt_rebuild.json").write_text(json.dumps({
        "explore": [{"signal": "tgt_upside", "segment": "largemid",
                     "contaminated": False, "months": 180, "t_ic": -3.47}],
        "confirm": []}), encoding="utf-8")


def test_universe_includes_rerun_files(tmp_path):
    _write_universe(tmp_path)
    df, void = load_candidates(tmp_path)
    assert set(df.signal) == {"x", "ivol_low_D", "defensive", "tgt_upside"}
    assert len(void) == 0


def test_missing_rerun_file_aborts(tmp_path):
    _write_universe(tmp_path)
    (tmp_path / "batch5_defensive_rerun.csv").unlink()
    with pytest.raises(SystemExit, match="required rerun file"):
        load_candidates(tmp_path)


def test_void_rows_removed_before_dedup(tmp_path):
    _write_universe(
        tmp_path, extra_row="")
    (tmp_path / "batch3b_summary.csv").write_text(
        "signal,segment,contaminated,months,t_ic\n"
        "tgt_upside,largemid,False,180,3.67\n", encoding="utf-8")
    df, void = load_candidates(tmp_path)
    assert len(void) == 1 and void.iloc[0].src == "batch3b_summary.csv"
    row = df[df.signal == "tgt_upside"]
    assert len(row) == 1
    assert float(row.iloc[0].t_ic) == -3.47
    assert row.iloc[0].src == "trial_tgt_rebuild.json"


def test_floor_refuses_void_and_stale(tmp_path):
    for seg, status, n in (("largemid", "VOID-REPLICATION", 10),
                           ("small", "OK", 10)):
        np.savez_compressed(tmp_path / f"real_null_2_{seg}.npz",
                            pooled_t_explore=np.zeros(n),
                            pooled_t_confirm=np.zeros(n))
        (tmp_path / f"real_null_2_{seg}_meta.json").write_text(
            json.dumps({"status": status, "n_pooled": n}), encoding="utf-8")
    with pytest.raises(SystemExit, match="not OK"):
        load_floor(tmp_path)
    # fix status but break the sample-count pairing
    (tmp_path / "real_null_2_largemid_meta.json").write_text(
        json.dumps({"status": "OK", "n_pooled": 999}), encoding="utf-8")
    with pytest.raises(SystemExit, match="stale"):
        load_floor(tmp_path)
