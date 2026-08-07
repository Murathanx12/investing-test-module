"""Stage-A replay runner — tested entirely on synthetic fixtures so the real
candidate bank is never read by the test suite (standing rule: small-segment
rows stay unexamined until the replay fires)."""

import numpy as np
import pandas as pd
import pytest

from aegis_brain.calibration.replay_runner import (
    Q,
    TOP_N,
    load_candidates,
    load_floor,
    stage_a,
)


@pytest.fixture
def cdfs():
    rng = np.random.default_rng(1)
    return {"largemid": np.sort(rng.standard_normal(4000) * 1.12),
            "small": np.sort(rng.standard_normal(4000) * 1.25)}


def _cands(rows):
    return pd.DataFrame(rows, columns=["signal", "segment", "contaminated",
                                       "t_ic", "src"])


def test_strong_candidate_graduates_null_does_not(cdfs):
    cands = _cands([("strong", "largemid", False, 6.0, "b1"),
                    ("noise", "largemid", False, 0.3, "b1"),
                    ("noise2", "small", False, -1.0, "b2")])
    out = stage_a(cands, cdfs, {"largemid": 0.30, "small": 0.40})
    names = [g["signal"] for g in out["graduates"]]
    assert names == ["strong"]
    assert out["accounting"]["n_graduates"] == 1
    # worst-case accounting uses the graduate's segment confirm-null rate
    assert out["accounting"]["worst_case_all_null"][
        "E_false_adoptions"] == pytest.approx(0.30)


def test_contaminated_rows_excluded(cdfs):
    cands = _cands([("burned", "largemid", True, 9.0, "b1"),
                    ("ok", "largemid", False, 6.0, "b1")])
    out = stage_a(cands, cdfs, {"largemid": 0.3, "small": 0.4})
    assert [g["signal"] for g in out["graduates"]] == ["ok"]
    assert out["accounting"]["n_excluded_contaminated_or_burned"] == 1


def test_contaminated_string_false_is_not_contaminated(cdfs):
    # CSV round-trips can deliver "False" as a STRING; bare astype(bool)
    # would mark it contaminated=True and silently exclude a live candidate
    cands = _cands([("ok", "largemid", "False", 6.0, "b1"),
                    ("burned", "largemid", "True", 7.0, "b1")])
    out = stage_a(cands, cdfs, {"largemid": 0.3, "small": 0.4})
    assert [g["signal"] for g in out["graduates"]] == ["ok"]


def test_confirm_burned_receipts_excluded(cdfs):
    # gross_prof/small and conc_low/largemid were adjudicated by their own
    # registered confirm runs — the replay must not read their window twice
    cands = _cands([("gross_prof", "small", False, 7.31, "b2"),
                    ("conc_low", "largemid", False, 4.46, "b7"),
                    ("fresh", "largemid", False, 6.0, "b1")])
    out = stage_a(cands, cdfs, {"largemid": 0.3, "small": 0.4})
    assert [g["signal"] for g in out["graduates"]] == ["fresh"]
    assert out["accounting"]["n_excluded_contaminated_or_burned"] == 2


def test_void_rows_removed_before_dedup(tmp_path):
    import json as _json
    cols = "signal,segment,contaminated,months,t_ic\n"
    # VOID source row for tgt_upside...
    (tmp_path / "batch3b_summary.csv").write_text(
        cols + "tgt_upside,largemid,False,180,3.67\n", encoding="utf-8")
    # ...and the valid rebuild row of the SAME name in the extra json
    (tmp_path / "trial_tgt_rebuild.json").write_text(_json.dumps({
        "explore": [{"signal": "tgt_upside", "segment": "largemid",
                     "contaminated": False, "months": 180, "t_ic": -3.47}],
        "confirm": []}), encoding="utf-8")
    df, void = load_candidates(tmp_path)
    assert len(void) == 1 and void.iloc[0].src == "batch3b_summary.csv"
    assert len(df) == 1
    # the surviving row is the rebuild, not the VOID artifact
    assert float(df.iloc[0].t_ic) == -3.47
    assert df.iloc[0].src == "trial_tgt_rebuild.json"


def test_cap_binds_at_top_n(cdfs):
    rows = [(f"s{i}", "largemid", False, 8.0 - i * 0.1, "b1")
            for i in range(TOP_N + 5)]
    out = stage_a(_cands(rows), cdfs, {"largemid": 0.3, "small": 0.4})
    assert out["accounting"]["n_graduates"] == TOP_N
    assert len(out["bh_survivors_below_cap"]) == 5
    # cap keeps the highest t_ic
    assert out["graduates"][0]["signal"] == "s0"


def test_dedup_keeps_first_batch(tmp_path):
    cols = "signal,segment,contaminated,months,t_ic\n"
    (tmp_path / "batch1_summary.csv").write_text(
        cols + "x,largemid,False,180,2.0\n", encoding="utf-8")
    (tmp_path / "batch2_summary.csv").write_text(
        cols + "x,largemid,False,180,3.5\n", encoding="utf-8")
    df, void = load_candidates(tmp_path)
    assert len(df) == 1 and len(void) == 0
    assert float(df.iloc[0].t_ic) == 2.0
    assert df.iloc[0].src == "batch1_summary.csv"


def test_floor_refuses_void_runs(tmp_path):
    import json
    for seg in ("largemid", "small"):
        np.savez_compressed(tmp_path / f"real_null_2_{seg}.npz",
                            pooled_t_explore=np.zeros(10))
        (tmp_path / f"real_null_2_{seg}_meta.json").write_text(
            json.dumps({"status": "VOID-REPLICATION" if seg == "largemid"
                        else "OK"}), encoding="utf-8")
    with pytest.raises(SystemExit, match="not OK"):
        load_floor(tmp_path)


def test_bh_respects_q_under_pure_null(cdfs):
    # 179 null candidates drawn FROM the floor distribution: BH at q=0.10
    # should almost never pass anything (single-batch check, seeded)
    rng = np.random.default_rng(7)
    rows = [(f"n{i}", "largemid", False,
             float(rng.choice(cdfs["largemid"])), "b1") for i in range(179)]
    out = stage_a(_cands(rows), cdfs, {"largemid": 0.3, "small": 0.4})
    assert out["accounting"]["n_graduates"] <= 2
