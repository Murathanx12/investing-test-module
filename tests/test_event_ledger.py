import pytest

from aegis_brain.events.ledger import EventCall, EventLedger


def _call(event_id="FDA-1", ticker="ABC", event_date="2024-06-01",
          prob_up=0.7, horizon=21, registered_at="2024-05-20T00:00:00+00:00"):
    return EventCall(
        event_id=event_id, ticker=ticker, event_type="FDA_APPROVAL",
        event_date=event_date, prob_up=prob_up, horizon_days=horizon,
        rationale="priority-review approval, positive drift expected",
        kill_condition="net 21d abnormal return < 0 across >60% of calls",
        registered_at=registered_at,
    )


def test_register_and_read(tmp_path):
    led = EventLedger(tmp_path / "ledger.jsonl")
    led.register_call(_call())
    assert len(led.calls()) == 1
    assert led.calls()[0].event_id == "FDA-1"


def test_register_rejects_lookahead(tmp_path):
    led = EventLedger(tmp_path / "ledger.jsonl")
    with pytest.raises(ValueError, match="look-ahead"):
        led.register_call(_call(registered_at="2024-06-02T00:00:00+00:00"))


def test_register_idempotent(tmp_path):
    led = EventLedger(tmp_path / "ledger.jsonl")
    led.register_call(_call())
    led.register_call(_call())  # same id
    assert len(led.calls()) == 1


def test_prob_and_horizon_validation(tmp_path):
    led = EventLedger(tmp_path / "ledger.jsonl")
    with pytest.raises(ValueError):
        led.register_call(_call(prob_up=1.4))
    with pytest.raises(ValueError):
        led.register_call(_call(horizon=0))


def test_scoring_respects_maturity_and_missing_data(tmp_path):
    led = EventLedger(tmp_path / "ledger.jsonl")
    led.register_call(_call(event_id="A", event_date="2024-06-01", horizon=21))
    # as_of before maturity -> nothing scored
    assert led.score_matured(lambda t, d, h: 0.05, as_of="2024-06-10") == []
    # data missing -> stays pending, not scored 0
    assert led.score_matured(lambda t, d, h: None, as_of="2024-08-01") == []
    assert led.scored() == []
    # data available past maturity -> scored
    new = led.score_matured(lambda t, d, h: 0.05, as_of="2024-08-01")
    assert len(new) == 1 and new[0].outcome == 1 and new[0].brier == pytest.approx((0.7 - 1) ** 2)


def test_scoring_idempotent(tmp_path):
    led = EventLedger(tmp_path / "ledger.jsonl")
    led.register_call(_call(event_id="A"))
    led.score_matured(lambda t, d, h: 0.05, as_of="2024-08-01")
    again = led.score_matured(lambda t, d, h: 0.05, as_of="2024-08-01")
    assert again == [] and len(led.scored()) == 1


def test_calibration_summary_skilled_calls_beat_baserate(tmp_path):
    # ticker encodes the id so the realized-return fn can look each call up
    led = EventLedger(tmp_path / "ledger.jsonl")
    for i in range(10):
        up = i >= 5  # high-prob calls win, low-prob calls lose -> well separated
        led.register_call(_call(event_id=f"E{i}", ticker=f"E{i}",
                                event_date="2024-06-01", prob_up=0.9 if up else 0.1))
    realized = {f"E{i}": (0.1 if i >= 5 else -0.1) for i in range(10)}
    led.score_matured(lambda t, d, h: realized[t], as_of="2024-08-01")
    summ = led.calibration_summary()
    assert summ["n"] == 10
    assert summ["realized_hit_rate"] == 0.5
    assert summ["brier_skill_vs_baserate"] > 0.5  # well-separated -> skilled


def test_calibration_summary_coinflip_has_no_skill(tmp_path):
    # every call predicts 0.5 -> zero skill vs the base rate, by construction
    led = EventLedger(tmp_path / "ledger.jsonl")
    for i in range(10):
        led.register_call(_call(event_id=f"E{i}", ticker=f"E{i}",
                                event_date="2024-06-01", prob_up=0.5))
    realized = {f"E{i}": (0.1 if i % 2 else -0.1) for i in range(10)}
    led.score_matured(lambda t, d, h: realized[t], as_of="2024-08-01")
    summ = led.calibration_summary()
    assert summ["brier_skill_vs_baserate"] == pytest.approx(0.0, abs=1e-9)
