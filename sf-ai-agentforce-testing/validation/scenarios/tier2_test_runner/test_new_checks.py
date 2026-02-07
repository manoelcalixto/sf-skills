"""
Tier 2 — Tests for new expectation checks added to _run_check().

Tests for:
- response_matches_regex
- response_length_min
- response_length_max
- action_result_contains
"""

import pytest

from multi_turn_test_runner import evaluate_turn, _run_check
from agent_api_client import TurnResult, AgentMessage


# ─────────────────────────────────────────────────────────────────────────
# response_matches_regex
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_regex_passes(sample_turn_result):
    """Regex that matches response text should pass."""
    turn = sample_turn_result(agent_text="Order #12345 confirmed for delivery.")
    result = evaluate_turn(turn, {"response_matches_regex": r"Order #\d+"}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_regex_fails(sample_turn_result):
    """Regex that doesn't match response text should fail."""
    turn = sample_turn_result(agent_text="Hello there, how can I help?")
    result = evaluate_turn(turn, {"response_matches_regex": r"Order #\d+"}, [])
    assert result["passed"] is False


@pytest.mark.tier2
@pytest.mark.offline
def test_regex_invalid_pattern(sample_turn_result):
    """Invalid regex should fail gracefully with error detail."""
    turn = sample_turn_result(agent_text="Hello there")
    result = evaluate_turn(turn, {"response_matches_regex": r"[invalid("}, [])
    assert result["passed"] is False
    assert "Invalid regex" in result["checks"][0]["detail"]


# ─────────────────────────────────────────────────────────────────────────
# response_length_min
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_length_min_passes(sample_turn_result):
    """Response longer than min should pass."""
    turn = sample_turn_result(agent_text="Hello world")  # 11 chars
    result = evaluate_turn(turn, {"response_length_min": 5}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_length_min_fails(sample_turn_result):
    """Response shorter than min should fail."""
    turn = sample_turn_result(agent_text="Hi")  # 2 chars
    result = evaluate_turn(turn, {"response_length_min": 5}, [])
    assert result["passed"] is False


@pytest.mark.tier2
@pytest.mark.offline
def test_length_min_strips_whitespace(sample_turn_result):
    """Length check should strip whitespace before measuring."""
    turn = sample_turn_result(agent_text="  Hi  ")  # 2 chars stripped
    result = evaluate_turn(turn, {"response_length_min": 5}, [])
    assert result["passed"] is False


# ─────────────────────────────────────────────────────────────────────────
# response_length_max
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_length_max_passes(sample_turn_result):
    """Response shorter than max should pass."""
    turn = sample_turn_result(agent_text="Hi")  # 2 chars
    result = evaluate_turn(turn, {"response_length_max": 100}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_length_max_fails(sample_turn_result):
    """Response longer than max should fail."""
    turn = sample_turn_result(agent_text="x" * 200)
    result = evaluate_turn(turn, {"response_length_max": 100}, [])
    assert result["passed"] is False


# ─────────────────────────────────────────────────────────────────────────
# action_result_contains
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_action_result_contains_passes():
    """String found in action results should pass."""
    turn = TurnResult(
        sequence_id=1,
        user_message="Check status",
        agent_messages=[AgentMessage(
            type="Inform", id="msg-001", message="Here are the results.",
            result=[{"Status": "Success", "OrderId": "ORD-123"}],
        )],
        raw_response={},
        elapsed_ms=100.0,
    )
    result = evaluate_turn(turn, {"action_result_contains": "Success"}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_action_result_contains_fails():
    """String not in action results should fail."""
    turn = TurnResult(
        sequence_id=1,
        user_message="Check status",
        agent_messages=[AgentMessage(
            type="Inform", id="msg-001", message="Here are the results.",
            result=[{"Status": "Failed", "Reason": "Not found"}],
        )],
        raw_response={},
        elapsed_ms=100.0,
    )
    result = evaluate_turn(turn, {"action_result_contains": "Success"}, [])
    assert result["passed"] is False


@pytest.mark.tier2
@pytest.mark.offline
def test_action_result_contains_no_results(sample_turn_result):
    """No action results at all should fail."""
    turn = sample_turn_result(agent_text="No results here.")
    result = evaluate_turn(turn, {"action_result_contains": "Success"}, [])
    assert result["passed"] is False
    assert "No action results" in result["checks"][0]["detail"]


@pytest.mark.tier2
@pytest.mark.offline
def test_action_result_contains_nested():
    """String in nested action result structure should pass."""
    turn = TurnResult(
        sequence_id=1,
        user_message="Get details",
        agent_messages=[AgentMessage(
            type="Inform", id="msg-001", message="Details found.",
            result=[{"data": {"nested": {"value": "SpecialToken123"}}}],
        )],
        raw_response={},
        elapsed_ms=100.0,
    )
    result = evaluate_turn(turn, {"action_result_contains": "SpecialToken123"}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_action_result_contains_case_insensitive():
    """action_result_contains should be case-insensitive."""
    turn = TurnResult(
        sequence_id=1,
        user_message="Check",
        agent_messages=[AgentMessage(
            type="Inform", id="msg-001", message="Done.",
            result=[{"Status": "SUCCESS"}],
        )],
        raw_response={},
        elapsed_ms=100.0,
    )
    result = evaluate_turn(turn, {"action_result_contains": "success"}, [])
    assert result["passed"] is True
