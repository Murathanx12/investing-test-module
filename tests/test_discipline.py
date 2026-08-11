import numpy as np

from aegis_brain.discipline import (
    deflated_sharpe_from_returns,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)


def test_psr_strong_signal_high():
    rng = np.random.default_rng(0)
    r = rng.normal(0.01, 0.02, 240)  # per-obs SR ~0.5
    sr = r.mean() / r.std(ddof=1)
    assert probabilistic_sharpe_ratio(sr, len(r)) > 0.99


def test_dsr_deflates_with_trial_count():
    rng = np.random.default_rng(1)
    r = rng.normal(0.003, 0.02, 120)
    few = deflated_sharpe_from_returns(r, n_trials=2, sr_variance=0.01)
    many = deflated_sharpe_from_returns(r, n_trials=500, sr_variance=0.01)
    assert many["dsr"] < few["dsr"]


def test_expected_max_sharpe_grows_with_trials():
    assert expected_max_sharpe(100, 0.01) > expected_max_sharpe(10, 0.01) > 0


def test_pbo_detects_noise_selection():
    rng = np.random.default_rng(2)
    noise = rng.normal(0, 0.02, size=(240, 50))  # 50 configs of pure noise
    report = probability_of_backtest_overfitting(noise)
    # selecting the best of noise must NOT look robust (pbo ~0.5 in theory)
    assert report["pbo"] >= 0.3


def test_pbo_recognizes_dominant_config():
    rng = np.random.default_rng(3)
    perf = rng.normal(0, 0.02, size=(240, 10))
    perf[:, 0] += 0.02  # config 0 genuinely dominates
    report = probability_of_backtest_overfitting(perf)
    assert report["pbo"] <= 0.2


# ── batch diversity (NIGHT-10) ───────────────────────────────────────────────
#
# lint() asks "has this been tried before?" and cannot ask "are these ten
# proposals actually ten ideas?". Ten LLM hypotheses generated in one call each
# PASSED against 306 prior experiments (strongest near-match ~0.23) while 37 of
# their 45 mutual pairs sat at or above the block threshold. The batch was one
# mechanism in ten costumes and nothing in the machinery could see it.

from aegis_brain.discipline.prereg_lint import lint_batch  # noqa: E402


def _doc(topic: str, filler: str = "") -> str:
    return f"""# PREREG — {topic}

## Mechanism
{topic} measured across the cross-section of US equities, point in time.

## Economic rationale
{filler}

## Data
CRSP monthly panel, {filler}

## Falsification
The effect vanishes once {filler} is controlled for.
"""


def test_batch_of_near_identical_proposals_is_one_idea():
    props = {f"H{i}": _doc("cross-sectional drift after an analyst revision "
                           "event", "analyst revision drift underreaction")
             for i in range(5)}
    out = lint_batch(props)
    assert out["verdict"] == "SINGLE_IDEA"
    assert out["effective_distinct_ideas"] == 1


def test_batch_of_distinct_proposals_is_diverse():
    props = {
        "A": _doc("insider open-market purchase clustering",
                  "insiders trade on private information about cash flows"),
        "B": _doc("supplier revenue concentration shock propagation",
                  "customer concentration transmits demand shocks along the chain"),
        "C": _doc("post-FDA-approval revenue reassessment in biotech",
                  "binary regulatory outcomes reprice the whole pipeline"),
    }
    out = lint_batch(props)
    assert out["effective_distinct_ideas"] == 3
    assert out["verdict"] == "DIVERSE"


def test_effective_distinct_ideas_is_the_honest_denominator():
    """Two clones plus one genuine outsider is TWO ideas, not three."""
    props = {
        "A": _doc("cross-sectional drift after an analyst revision event",
                  "analyst revision drift underreaction"),
        "B": _doc("cross-sectional drift after an analyst revision event",
                  "analyst revision drift underreaction slightly reworded"),
        "C": _doc("supplier revenue concentration shock propagation",
                  "customer concentration transmits demand shocks"),
    }
    out = lint_batch(props)
    assert out["effective_distinct_ideas"] == 2
    assert out["verdict"] == "PARTIALLY_REDUNDANT"
    groups = sorted(sorted(g) for g in out["groups"])
    assert ["A", "B"] in groups and ["C"] in groups


def test_batch_reports_every_pair():
    props = {k: _doc(f"mechanism {k}", k * 4) for k in "ABCD"}
    out = lint_batch(props)
    assert out["n_pairs"] == 6
    assert all(0.0 <= p["cosine"] <= 1.0 for p in out["pairs"])
    assert out["pairs"] == sorted(out["pairs"], key=lambda p: -p["cosine"])


def test_empty_proposal_raises():
    import pytest
    with pytest.raises(ValueError):
        lint_batch({"A": _doc("something real"), "B": "   "})
