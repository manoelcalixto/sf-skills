"""
T2: Count Command Tests (5 points)

Tests count command for checking data volume:
- count sessions
- count with --days filter

SKILL.md Section: "Count Records"
"""

import sys
import pytest
from pathlib import Path

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier2
@pytest.mark.offline
class TestCountCLI:
    """Test count command CLI."""

    def test_count_help(self, cli_runner, cli_app):
        """count --help shows usage."""
        result = cli_runner.invoke(cli_app, ["count", "--help"])

        assert result.exit_code == 0
        assert "count" in result.output.lower()
        assert "--entity" in result.output

    def test_count_entity_options(self, cli_runner, cli_app):
        """count --entity accepts valid entity types."""
        result = cli_runner.invoke(cli_app, ["count", "--help"])

        assert result.exit_code == 0
        # Should list entity choices
        assert "sessions" in result.output
        assert "interactions" in result.output
        assert "steps" in result.output
        assert "messages" in result.output

    def test_count_requires_org(self, cli_runner, cli_app):
        """count requires --org."""
        result = cli_runner.invoke(cli_app, ["count"])

        assert result.exit_code != 0
        assert "org" in result.output.lower() or "required" in result.output.lower()


@pytest.mark.tier2
@pytest.mark.live_api
class TestCountLive:
    """Live tests for count command."""

    def test_count_sessions(self, org_alias, cli_runner, cli_app, auth_client):
        """count sessions returns a number."""
        result = cli_runner.invoke(cli_app, [
            "count",
            "--org", org_alias,
            "--entity", "sessions",
            "--days", "7"
        ])

        # Should succeed
        assert result.exit_code == 0

        # Output should contain "Count:" and a number
        assert "count" in result.output.lower()

    def test_count_with_days_filter(self, org_alias, cli_runner, cli_app, auth_client):
        """count --days N filters by date."""
        result = cli_runner.invoke(cli_app, [
            "count",
            "--org", org_alias,
            "--entity", "sessions",
            "--days", "1"
        ])

        assert result.exit_code == 0

        # Should mention the period
        assert "1" in result.output or "day" in result.output.lower()

    def test_count_interactions(self, org_alias, cli_runner, cli_app, auth_client):
        """count interactions works."""
        result = cli_runner.invoke(cli_app, [
            "count",
            "--org", org_alias,
            "--entity", "interactions",
            "--days", "7"
        ])

        assert result.exit_code == 0

    def test_count_steps(self, org_alias, cli_runner, cli_app, auth_client):
        """count steps works."""
        result = cli_runner.invoke(cli_app, [
            "count",
            "--org", org_alias,
            "--entity", "steps",
            "--days", "7"
        ])

        assert result.exit_code == 0
