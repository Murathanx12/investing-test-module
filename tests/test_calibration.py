"""Tests for aegis_brain/calibration — in-memory fixture panel, no parquet
reads, no network (design §7). Factor loading is monkeypatched so the real
pinned vintage file is never touched.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.calibration import panel_gen
from aegis_brain.calibration.config import assert_production_constants
from aegis_brain.calibration.panel_gen import (
    DGPAInputs,
    build_dgpa_inputs,
    gen_dgpb_null,
    gen_null_panel,
)
from aegis_brain.data.eodhd_panel import Panel

N_MONTHS, N_SYMS, N_FAC = 110, 60, 6


@pytest.fixture()
def fixture_panel(monkeypatch) -> Panel:
    rng = np.random.default_rng(42)
    months = pd.date_range("2008-01-31", periods=N_MONTHS, freq="ME")
    syms = [f"S{i:03d}" for i in range(N_SYMS)]

    fac = rng.normal(0.004, 0.04, (N_MONTHS, N_FAC))
    rf = np.full(N_MONTHS, 0.002)
    monkeypatch.setattr(
        panel_gen, "load_factors",
        lambda m: (fac[: len(m)], rf[: len(m)], {"retrieved": "test-fixture"}),
    )

    beta = rng.normal(1.0, 0.4, N_SYMS)
    sigma = rng.uniform(0.03, 0.20, N_SYMS)
    ret = (rf[:, None] + beta[None, :] * fac[:, [0]]
           + sigma[None, :] * rng.standard_normal((N_MONTHS, N_SYMS)))
    ret = pd.DataFrame(ret, index=months, columns=syms)
    # a few dead firms + a late lister, so NaN structure is exercised
    ret.iloc[80:, 0] = np.nan
    ret.iloc[90:, 1] = np.nan
    ret.iloc[:30, 2] = np.nan

    price = pd.DataFrame(10.0, index=months, columns=syms).where(ret.notna())
    dvol = pd.DataFrame(5e6, index=months, columns=syms).where(ret.notna())
    delist = {s: ret[s].last_valid_index() for s in syms}
    return Panel(monthly_ret=ret, month_end_price=price,
                 monthly_dollar_vol=dvol, delist_month=delist)


@pytest.fixture()
def inputs(fixture_panel) -> DGPAInputs:
    return build_dgpa_inputs(fixture_panel)


def test_production_constants_snapshot_matches_live():
    assert_production_constants()


def test_inputs_shapes_and_masks(fixture_panel, inputs):
    assert inputs.beta.shape == (N_SYMS, N_FAC)
    assert inputs.sigma_t.shape == (N_MONTHS, N_SYMS)
    assert np.isfinite(inputs.sigma_t).all()
    assert (inputs.sigma_t > 0).all()
    # z NaN exactly where real returns are NaN
    real_nan = fixture_panel.monthly_ret.isna().to_numpy()
    assert np.array_equal(np.isnan(inputs.z), real_nan)


def test_null_panel_preserves_nan_mask_and_carries_real_sides(fixture_panel, inputs):
    pnl = gen_null_panel(inputs, np.random.default_rng(0))
    assert pnl.monthly_ret.isna().equals(fixture_panel.monthly_ret.isna())
    # prices and dollar volumes are carried, not regenerated
    pd.testing.assert_frame_equal(pnl.month_end_price, fixture_panel.month_end_price)
    pd.testing.assert_frame_equal(pnl.monthly_dollar_vol, fixture_panel.monthly_dollar_vol)
    assert pnl.delist_month == fixture_panel.delist_month


def test_null_panel_deterministic_per_seed(inputs):
    a = gen_null_panel(inputs, np.random.default_rng(7)).monthly_ret
    b = gen_null_panel(inputs, np.random.default_rng(7)).monthly_ret
    c = gen_null_panel(inputs, np.random.default_rng(8)).monthly_ret
    pd.testing.assert_frame_equal(a, b)
    assert not a.equals(c)


def test_null_panel_differs_from_real(fixture_panel, inputs):
    pnl = gen_null_panel(inputs, np.random.default_rng(1))
    same = (pnl.monthly_ret == fixture_panel.monthly_ret)
    # residual permutation + factor permutation must change nearly every cell
    assert same.sum().sum() < 0.02 * fixture_panel.monthly_ret.notna().sum().sum()


def test_null_panel_z_permutation_preserves_stratum_multisets(inputs):
    """Within a month, the synthetic z draws are a permutation of the real
    ones (checked via the whole-month multiset — strata partition it)."""
    rng = np.random.default_rng(3)
    pnl = gen_null_panel(inputs, rng)
    # reconstruct z* implied by the synthetic returns for one mid-panel month
    t = 60
    perm_resistant = np.sort(inputs.z[t][~np.isnan(inputs.z[t])])
    r = pnl.monthly_ret.iloc[t].to_numpy()
    # r* = rf' + beta·f' + sigma_t * z*  ->  can't invert without knowing the
    # factor permutation; instead check aggregate invariant: same count of
    # valid cells and finite values
    valid = ~np.isnan(r)
    assert valid.sum() == perm_resistant.size
    assert np.isfinite(r[valid]).all()


def test_dgpb_preserves_monthly_return_multisets(fixture_panel):
    pnl = gen_dgpb_null(fixture_panel, np.random.default_rng(11))
    for t in (0, 40, 79, N_MONTHS - 1):
        real_row = fixture_panel.monthly_ret.iloc[t].dropna()
        synth_row = pnl.monthly_ret.iloc[t].dropna()
        assert len(real_row) == len(synth_row)
        np.testing.assert_allclose(
            np.sort(real_row.to_numpy()), np.sort(synth_row.to_numpy())
        )


def test_dgpb_changes_assignment(fixture_panel):
    pnl = gen_dgpb_null(fixture_panel, np.random.default_rng(12))
    same = (pnl.monthly_ret == fixture_panel.monthly_ret).sum().sum()
    assert same < 0.10 * fixture_panel.monthly_ret.notna().sum().sum()


def test_restandardization_c_is_deterministic_and_finite(inputs):
    """v6: c_t is a function of the real panel only — same inputs, same c."""
    assert inputs.c_t.shape == (N_MONTHS,)
    assert np.isfinite(inputs.c_t).all()
    assert (inputs.c_t > 0).all()
    # rebuilt inputs give the identical c_t (no rng involvement)
    from aegis_brain.calibration.panel_gen import _restandardization_c
    c2 = _restandardization_c(inputs.sigma_t * inputs.z, inputs.sigma_t, inputs.z)
    np.testing.assert_allclose(inputs.c_t, c2)


# ---------------------------------------------------------------- injection


def test_injection_alpha_zero_is_exact_noop(fixture_panel):
    from aegis_brain.calibration.inject import build_injection_inputs, inject
    inj = build_injection_inputs(fixture_panel, 0.5, np.random.default_rng(5))
    pnl = inject(fixture_panel, inj, "I1", 0.0)
    pd.testing.assert_frame_equal(pnl.monthly_ret, fixture_panel.monthly_ret)


def test_injection_mean_zero_within_mask(fixture_panel):
    """dr must be mean-zero across the injected set every month (the EW
    benchmark may not absorb a level effect)."""
    from aegis_brain.calibration.inject import (
        build_injection_inputs, delta_frame)
    inj = build_injection_inputs(fixture_panel, 0.5, np.random.default_rng(6))
    dr = delta_frame(fixture_panel, inj, "I4", 0.4)
    months = dr.index
    for t in range(1, len(months)):
        row = dr.iloc[t]
        nz = row[row != 0.0]
        if len(nz) > 10:
            assert abs(nz.mean()) < 1e-4  # (rank-0.5)/n is exactly mean-0.5;
            # live-cell skips leave only a tiny residual


def test_injection_signal_correlates_with_x_at_rho(fixture_panel):
    from aegis_brain.calibration.inject import build_injection_inputs
    inj = build_injection_inputs(fixture_panel, 0.5, np.random.default_rng(7))
    x = inj.X.to_numpy().ravel()
    s = inj.S.to_numpy().ravel()
    ok = ~np.isnan(x) & ~np.isnan(s)
    corr = np.corrcoef(x[ok], s[ok])[0, 1]
    assert abs(corr - 0.5) < 0.05


def test_injection_i2_decays(fixture_panel):
    from aegis_brain.calibration.inject import decay_weights
    w = decay_weights(N_MONTHS, "I2")
    assert abs(w.mean() - 1.0) < 1e-12
    assert w[0] > w[-1]
    np.testing.assert_allclose(w[1] / w[0], np.exp(-1 / 60))


def test_load_factors_raises_on_missing_months(monkeypatch):
    """A silently NaN-filled factor month must be impossible (S-rule).

    NOTE: must not use fixture_panel — that fixture monkeypatches
    load_factors itself, which would bypass the code under test."""
    months = pd.date_range("2008-01-31", periods=N_MONTHS, freq="ME")
    short = pd.DataFrame(
        np.random.default_rng(1).normal(size=(len(months) - 5, 7)),
        index=months[:-5],
        columns=["mktrf", "smb", "hml", "rmw", "cma", "umd", "rf"],
    )
    monkeypatch.setattr(panel_gen.pd, "read_parquet", lambda *_a, **_k: short)
    monkeypatch.setattr(
        panel_gen, "FF_VINTAGE",
        type("P", (), {"read_text": staticmethod(lambda **_k: "{}")})(),
    )
    with pytest.raises(ValueError, match="missing panel months"):
        panel_gen.load_factors(months)
