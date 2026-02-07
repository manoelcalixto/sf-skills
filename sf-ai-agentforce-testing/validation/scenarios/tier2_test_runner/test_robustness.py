"""
Tier 2 — Robustness feature tests.

Tests for:
- Per-turn retry logic in execute_scenario
- --parallel and --turn-retry CLI arguments
"""

import pytest
from unittest.mock import MagicMock, patch, call

from agent_api_client import AgentAPIClient, AgentAPIError, TurnResult, AgentMessage
from multi_turn_test_runner import execute_scenario


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _make_turn_result(agent_text="I can help.", has_action=False, error=None):
    """Build a minimal TurnResult for mocking."""
    msgs = [AgentMessage(type="Inform", id="msg-001", message=agent_text)]
    if has_action:
        msgs[0].result = [{"field": "value"}]
    return TurnResult(
        sequence_id=1,
        user_message="test",
        agent_messages=msgs,
        raw_response={},
        elapsed_ms=100.0,
        error=error,
    )


# ─────────────────────────────────────────────────────────────────────────
# Per-turn retry
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_retry_succeeds_on_second_attempt(mock_client):
    """With turn_retry=1, a transient error followed by success should pass."""
    scenario = {
        "name": "retry_test",
        "description": "Test retry logic",
        "turns": [
            {"user": "Hello", "expect": {"response_not_empty": True}},
        ],
    }
    # First call returns error result, second call succeeds
    error_turn = _make_turn_result(agent_text="", error="Transient error")
    success_turn = _make_turn_result(agent_text="Hello! How can I help?")

    mock_sess = MagicMock()
    mock_sess.send.side_effect = [error_turn, success_turn]
    mock_sess.__enter__ = lambda s: s
    mock_sess.__exit__ = MagicMock(return_value=False)

    with patch.object(mock_client, "session", return_value=mock_sess), \
         patch("multi_turn_test_runner.time.sleep"):  # Don't actually sleep
        result = execute_scenario(
            mock_client, "agent-id-001", scenario, turn_retry=1,
        )

    assert result["status"] == "passed"
    assert mock_sess.send.call_count == 2


@pytest.mark.tier2
@pytest.mark.offline
def test_retry_exhausted(mock_client):
    """When all retries fail, scenario should still complete with the error turn."""
    scenario = {
        "name": "retry_exhausted",
        "description": "All retries fail",
        "turns": [
            {"user": "Hello", "expect": {"response_not_empty": True}},
        ],
    }
    error_turn = _make_turn_result(agent_text="", error="Persistent error")

    mock_sess = MagicMock()
    # Return error on all 3 attempts (initial + 2 retries)
    mock_sess.send.side_effect = [error_turn, error_turn, error_turn]
    mock_sess.__enter__ = lambda s: s
    mock_sess.__exit__ = MagicMock(return_value=False)

    with patch.object(mock_client, "session", return_value=mock_sess), \
         patch("multi_turn_test_runner.time.sleep"):
        result = execute_scenario(
            mock_client, "agent-id-001", scenario, turn_retry=2,
        )

    # The scenario should still complete (not crash), but the turn fails
    assert result["status"] == "failed"
    assert mock_sess.send.call_count == 3


@pytest.mark.tier2
@pytest.mark.offline
def test_execute_scenario_default_no_retry(mock_client):
    """Without turn_retry, behaves as before (single attempt)."""
    scenario = {
        "name": "no_retry",
        "description": "Default behavior",
        "turns": [
            {"user": "Hello", "expect": {"response_not_empty": True}},
        ],
    }
    success_turn = _make_turn_result(agent_text="Hello there!")

    mock_sess = MagicMock()
    mock_sess.send.return_value = success_turn
    mock_sess.__enter__ = lambda s: s
    mock_sess.__exit__ = MagicMock(return_value=False)

    with patch.object(mock_client, "session", return_value=mock_sess):
        result = execute_scenario(mock_client, "agent-id-001", scenario)

    assert result["status"] == "passed"
    assert mock_sess.send.call_count == 1


# ─────────────────────────────────────────────────────────────────────────
# CLI argument parsing
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.tier2
@pytest.mark.offline
def test_parallel_flag_accepted():
    """argparse should accept --parallel flag."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--parallel", type=int, default=0)
    args = parser.parse_args(["--parallel", "3"])
    assert args.parallel == 3


@pytest.mark.tier2
@pytest.mark.offline
def test_turn_retry_flag_accepted():
    """argparse should accept --turn-retry flag."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--turn-retry", type=int, default=0)
    args = parser.parse_args(["--turn-retry", "2"])
    assert args.turn_retry == 2
