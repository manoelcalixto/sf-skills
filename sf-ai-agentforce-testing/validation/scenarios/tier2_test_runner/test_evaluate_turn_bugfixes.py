"""
Tier 2 — Bug fix tests for evaluate_turn() / _run_check().

Tests for:
- action_invoked bool vs string handling
- action_uses_variable re-ask heuristic
- response_contains boolean guard
- turn_elapsed_max check
- topic_contains word-boundary matching
- execute_scenario generic exception handler
"""

import pytest
from unittest.mock import MagicMock, patch

from multi_turn_test_runner import evaluate_turn, _run_check, execute_scenario
from agent_api_client import TurnResult, AgentMessage, AgentAPIClient, AgentAPIError


# ─────────────────────────────────────────────────────────────────────────
# action_invoked — bool vs string
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_action_invoked_bool_true_passes(sample_turn_result):
    """action_invoked: true passes when action result is present."""
    turn = sample_turn_result(agent_text="Found your order.", has_action_result=True)
    result = evaluate_turn(turn, {"action_invoked": True}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_action_invoked_bool_true_fails(sample_turn_result):
    """action_invoked: true fails when no action result."""
    turn = sample_turn_result(agent_text="I can help with that.")
    result = evaluate_turn(turn, {"action_invoked": True}, [])
    assert result["passed"] is False


@pytest.mark.tier2
@pytest.mark.offline
def test_action_invoked_bool_false_passes(sample_turn_result):
    """action_invoked: false passes when no action result."""
    turn = sample_turn_result(agent_text="Hello there.")
    result = evaluate_turn(turn, {"action_invoked": False}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_action_invoked_string_passes():
    """action_invoked with string checks action name in raw_response."""
    turn = TurnResult(
        sequence_id=1,
        user_message="Look up order",
        agent_messages=[AgentMessage(
            type="Inform", id="msg-001", message="Found your order.",
            result=[{"orderId": "12345"}],
        )],
        raw_response={"messages": [
            {"type": "Inform", "message": "Found it.", "actionName": "LookupOrder"}
        ]},
        elapsed_ms=100.0,
    )
    result = evaluate_turn(turn, {"action_invoked": "LookupOrder"}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_action_invoked_string_fails_no_action(sample_turn_result):
    """action_invoked with string fails when no action result at all."""
    turn = sample_turn_result(agent_text="I don't know about that.")
    result = evaluate_turn(turn, {"action_invoked": "LookupOrder"}, [])
    assert result["passed"] is False
    assert "No action result" in result["checks"][0]["detail"]


@pytest.mark.tier2
@pytest.mark.offline
def test_action_invoked_string_fails_wrong_action():
    """action_invoked with string fails when a different action was invoked."""
    turn = TurnResult(
        sequence_id=1,
        user_message="Cancel order",
        agent_messages=[AgentMessage(
            type="Inform", id="msg-001", message="Order cancelled.",
            result=[{"status": "cancelled"}],
        )],
        raw_response={"messages": [
            {"type": "Inform", "message": "Done.", "actionName": "CancelOrder"}
        ]},
        elapsed_ms=100.0,
    )
    result = evaluate_turn(turn, {"action_invoked": "LookupOrder"}, [])
    assert result["passed"] is False
    assert "not found" in result["checks"][0]["detail"]


# ─────────────────────────────────────────────────────────────────────────
# action_uses_variable — re-ask heuristic
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_action_uses_variable_no_reask_passes(sample_turn_result):
    """Passes when agent does NOT re-ask for the variable's keyword."""
    turn = sample_turn_result(agent_text="I found the details for your account.")
    result = evaluate_turn(turn, {"action_uses_variable": "$Context.AccountId"}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_action_uses_variable_reask_fails(sample_turn_result):
    """Fails when agent re-asks for the variable's keyword."""
    turn = sample_turn_result(agent_text="Could you please provide the account number?")
    result = evaluate_turn(turn, {"action_uses_variable": "$Context.AccountId"}, [])
    assert result["passed"] is False
    assert "re-asked" in result["checks"][0]["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────
# response_contains — boolean guard
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_response_contains_bool_fails_with_message(sample_turn_result):
    """Passing a bool to response_contains should fail with helpful message."""
    turn = sample_turn_result(agent_text="Hello there")
    result = evaluate_turn(turn, {"response_contains": True}, [])
    assert result["passed"] is False
    assert "expects a string" in result["checks"][0]["detail"]


@pytest.mark.tier2
@pytest.mark.offline
def test_response_contains_string_still_works(sample_turn_result):
    """response_contains with normal string should still pass/fail correctly."""
    turn = sample_turn_result(agent_text="I can help with your order")
    result = evaluate_turn(turn, {"response_contains": "order"}, [])
    assert result["passed"] is True

    result2 = evaluate_turn(turn, {"response_contains": "invoice"}, [])
    assert result2["passed"] is False


# ─────────────────────────────────────────────────────────────────────────
# turn_elapsed_max
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_turn_elapsed_max_passes(sample_turn_result):
    """Turn within time limit should pass."""
    turn = sample_turn_result(agent_text="Quick response.", elapsed_ms=500.0)
    result = evaluate_turn(turn, {"turn_elapsed_max": 10000}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_turn_elapsed_max_fails(sample_turn_result):
    """Turn exceeding time limit should fail."""
    turn = sample_turn_result(agent_text="Slow response.", elapsed_ms=15000.0)
    result = evaluate_turn(turn, {"turn_elapsed_max": 10000}, [])
    assert result["passed"] is False
    assert "EXCEEDED" in result["checks"][0]["detail"]


@pytest.mark.tier2
@pytest.mark.offline
def test_turn_elapsed_max_exact_boundary(sample_turn_result):
    """Turn at exact boundary should pass (<=)."""
    turn = sample_turn_result(agent_text="Boundary response.", elapsed_ms=10000.0)
    result = evaluate_turn(turn, {"turn_elapsed_max": 10000}, [])
    assert result["passed"] is True


# ─────────────────────────────────────────────────────────────────────────
# topic_contains — word boundary
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_topic_contains_word_boundary_passes(sample_turn_result):
    """Exact word match should pass."""
    turn = sample_turn_result(agent_text="I can help cancel your subscription.")
    result = evaluate_turn(turn, {"topic_contains": "cancel"}, [])
    assert result["passed"] is True


@pytest.mark.tier2
@pytest.mark.offline
def test_topic_contains_word_boundary_fails_substring(sample_turn_result):
    """Substring-only match (no word boundary) should fail."""
    turn = sample_turn_result(agent_text="I can help with cancellation details.")
    result = evaluate_turn(turn, {"topic_contains": "cancel"}, [])
    assert result["passed"] is False


@pytest.mark.tier2
@pytest.mark.offline
def test_topic_contains_case_insensitive(sample_turn_result):
    """Word boundary match should be case-insensitive."""
    turn = sample_turn_result(agent_text="CANCEL your order now.")
    result = evaluate_turn(turn, {"topic_contains": "cancel"}, [])
    assert result["passed"] is True


# ─────────────────────────────────────────────────────────────────────────
# execute_scenario — generic exception handler
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_execute_scenario_generic_exception(mock_client):
    """Unexpected exception during scenario should be caught, not crash."""
    scenario = {
        "name": "exception_test",
        "description": "Tests generic handler",
        "turns": [
            {"user": "Hello", "expect": {"response_not_empty": True}},
        ],
    }
    mock_sess = MagicMock()
    mock_sess.send.side_effect = TypeError("unexpected type error")
    mock_sess.__enter__ = lambda s: s
    mock_sess.__exit__ = MagicMock(return_value=False)

    with patch.object(mock_client, "session", return_value=mock_sess):
        result = execute_scenario(mock_client, "agent-id-001", scenario)

    assert result["status"] == "error"
    assert "TypeError" in result["error"]


# ─────────────────────────────────────────────────────────────────────────
# _extract_variable_keyword helper
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_extract_variable_keyword():
    """Helper should extract meaningful keyword from variable names."""
    from multi_turn_test_runner import _extract_variable_keyword
    assert _extract_variable_keyword("$Context.AccountId") == "account"
    assert _extract_variable_keyword("$Context.EndUserLanguage") == "end"
    assert _extract_variable_keyword("CaseId") == "case"
    assert _extract_variable_keyword("Verified_Check") == "verified"


@pytest.mark.tier2
@pytest.mark.offline
def test_extract_variable_keyword_id_only():
    """Variable that is only 'Id' should return None."""
    from multi_turn_test_runner import _extract_variable_keyword
    assert _extract_variable_keyword("Id") is None
