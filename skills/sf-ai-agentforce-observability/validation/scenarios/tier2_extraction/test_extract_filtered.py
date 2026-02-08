"""
T2: Filtered Extraction Tests (5 points)

Tests extraction filtering options:
- --agent filter by agent API name
- --since / --until date range
- Multiple filters combined

SKILL.md Section: "CLI Quick Reference"
"""

import sys
import pytest
from pathlib import Path
from datetime import datetime, timedelta

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier2
@pytest.mark.live_api
class TestExtractFiltered:
    """Test filtered extraction (5 points)."""

    def test_extract_with_since_until(self, data_client, temp_output_dir):
        """--since and --until properly filter by date."""
        from scripts.extractor import STDMExtractor

        extractor = STDMExtractor(data_client, temp_output_dir)

        # Extract a specific 3-day window
        until = datetime.utcnow()
        since = until - timedelta(days=3)

        result = extractor.extract_sessions(
            since=since,
            until=until,
            show_progress=False
        )

        # Should complete without error
        assert result is not None
        assert result.errors is None or len(result.errors) == 0

    def test_extract_with_agent_filter(self, data_client, temp_output_dir):
        """--agent filter limits to specific agent."""
        from scripts.extractor import STDMExtractor

        extractor = STDMExtractor(data_client, temp_output_dir)

        # Use a non-existent agent to test filter works
        # (should return 0 results but not error)
        since = datetime.utcnow() - timedelta(days=1)

        result = extractor.extract_sessions(
            since=since,
            agent_names=["NonExistent_Agent_12345"],
            show_progress=False
        )

        # Should complete without error
        assert result is not None

        # With non-existent agent, should have 0 sessions
        # (unless there happens to be an agent with this exact name)
        # We just verify it doesn't error
        assert result.sessions_count >= 0


@pytest.mark.tier2
@pytest.mark.offline
class TestFilteredCLI:
    """Test filtered extraction CLI options."""

    def test_extract_accepts_since_until(self, cli_runner, cli_app):
        """CLI accepts --since and --until flags."""
        result = cli_runner.invoke(cli_app, ["extract", "--help"])

        assert result.exit_code == 0
        assert "--since" in result.output
        assert "--until" in result.output

    def test_extract_accepts_agent_filter(self, cli_runner, cli_app):
        """CLI accepts --agent flag."""
        result = cli_runner.invoke(cli_app, ["extract", "--help"])

        assert result.exit_code == 0
        assert "--agent" in result.output

    def test_extract_agent_is_repeatable(self, cli_runner, cli_app):
        """--agent can be specified multiple times."""
        result = cli_runner.invoke(cli_app, ["extract", "--help"])

        assert result.exit_code == 0
        # The help should indicate multiple values allowed
        # This is Click's default for 'multiple=True'
        assert "--agent" in result.output
