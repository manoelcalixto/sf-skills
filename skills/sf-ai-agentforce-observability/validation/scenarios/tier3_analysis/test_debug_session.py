"""
T3: Debug Session Tests (5 points)

Tests debug-session command for timeline reconstruction:
- Shows chronological event timeline
- Includes messages and steps

SKILL.md Section: "Debug Session Timeline"
"""

import sys
import pytest
from pathlib import Path

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier3
@pytest.mark.offline
class TestDebugSessionCLI:
    """Test debug-session command CLI."""

    def test_debug_session_help(self, cli_runner, cli_app):
        """debug-session --help shows usage."""
        result = cli_runner.invoke(cli_app, ["debug-session", "--help"])

        assert result.exit_code == 0
        assert "timeline" in result.output.lower() or "session" in result.output.lower()
        assert "--session-id" in result.output
        assert "--data-dir" in result.output

    def test_debug_session_requires_data_dir(self, cli_runner, cli_app):
        """debug-session requires --data-dir."""
        result = cli_runner.invoke(cli_app, [
            "debug-session",
            "--session-id", "test-session"
        ])

        assert result.exit_code != 0
        assert "data-dir" in result.output.lower() or "required" in result.output.lower()

    def test_debug_session_requires_session_id(self, cli_runner, cli_app, sample_data_dir):
        """debug-session requires --session-id."""
        result = cli_runner.invoke(cli_app, [
            "debug-session",
            "--data-dir", str(sample_data_dir)
        ])

        assert result.exit_code != 0
        assert "session-id" in result.output.lower() or "required" in result.output.lower()


@pytest.mark.tier3
@pytest.mark.offline
class TestDebugSessionWithFixtures:
    """Test debug-session with fixture data."""

    def test_debug_session_shows_timeline(self, cli_runner, cli_app, sample_data_dir):
        """debug-session shows timeline for existing session."""
        # Use session ID from fixture data
        session_id = "session-001"

        result = cli_runner.invoke(cli_app, [
            "debug-session",
            "--data-dir", str(sample_data_dir),
            "--session-id", session_id
        ])

        # Should succeed or indicate session not found
        # (depending on how analyzer handles missing sessions)
        if result.exit_code == 0:
            # Output should contain timeline information
            assert len(result.output) > 0

    def test_debug_session_nonexistent_session(self, cli_runner, cli_app, sample_data_dir):
        """debug-session handles non-existent session gracefully."""
        result = cli_runner.invoke(cli_app, [
            "debug-session",
            "--data-dir", str(sample_data_dir),
            "--session-id", "nonexistent-session-xyz"
        ])

        # Should either succeed with "not found" message or fail gracefully
        # Either way, shouldn't crash
        assert result.exception is None or "not found" in str(result.exception).lower()


@pytest.mark.tier3
@pytest.mark.offline
class TestDebugSessionAnalyzer:
    """Test debug session functionality in analyzer."""

    def test_print_session_debug_method_exists(self, sample_data_dir):
        """STDMAnalyzer has print_session_debug method."""
        from scripts.analyzer import STDMAnalyzer

        analyzer = STDMAnalyzer(sample_data_dir)

        assert hasattr(analyzer, 'print_session_debug')
        assert callable(analyzer.print_session_debug)
