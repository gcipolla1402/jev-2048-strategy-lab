import pytest

from app.jev_service import JevServiceError, validate_decision_payload


def test_validates_real_jev_choice_response():
    move, probabilities, confidence = validate_decision_payload(
        "right", {"left": 0.2, "right": 0.8}, 0.6, ["left", "right"]
    )
    assert move == "right"
    assert probabilities == {"left": 0.2, "right": 0.8}
    assert confidence == 0.6


def test_rejects_move_outside_legal_options():
    with pytest.raises(JevServiceError):
        validate_decision_payload("up", {"up": 1.0}, 1.0, ["left", "right"])


def test_discards_malformed_metrics_without_inventing_values():
    move, probabilities, confidence = validate_decision_payload(
        "left", {"left": 1.2, "down": 0.4}, "high", ["left"]
    )
    assert move == "left"
    assert probabilities == {}
    assert confidence is None

