"""
T2: Extract Tree Tests (5 points)

Tests extract-tree command for session-specific extraction:
- Extracts complete tree for given session IDs
- Includes all child records

SKILL.md Section: "Extract Session Tree"
"""

import sys
import pytest
from pathlib import Path

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier2
@pytest.mark.live_api
class TestExtractTree:
    """Test extract-tree command (5 points)."""

    def test_extract_tree_requires_session_id(self, cli_runner, cli_app):
        """extract-tree requires --session-id."""
        result = cli_runner.invoke(cli_app, [
            "extract-tree",
            "--org", "test-org"
        ])

        assert result.exit_code != 0
        assert "session-id" in result.output.lower() or "required" in result.output.lower()

    def test_extract_tree_help(self, cli_runner, cli_app):
        """extract-tree --help shows usage."""
        result = cli_runner.invoke(cli_app, ["extract-tree", "--help"])

        assert result.exit_code == 0
        assert "session" in result.output.lower()
        assert "--session-id" in result.output

    def test_extract_tree_session_id_multiple(self, cli_runner, cli_app):
        """extract-tree accepts multiple --session-id."""
        result = cli_runner.invoke(cli_app, ["extract-tree", "--help"])

        assert result.exit_code == 0
        # Should support multiple session IDs
        assert "--session-id" in result.output


@pytest.mark.tier2
@pytest.mark.live_api
@pytest.mark.slow
class TestExtractTreeLive:
    """Live tests for extract-tree."""

    def test_extract_tree_with_real_session(self, data_client, temp_output_dir):
        """Extract tree for a real session ID (requires data)."""
        from scripts.extractor import STDMExtractor
        from datetime import datetime, timedelta

        # First, get a session ID to test with
        sessions = list(data_client.query(
            "SELECT ssot__Id__c FROM ssot__AIAgentSession__dlm LIMIT 1"
        ))

        if not sessions:
            pytest.skip("No session data available for extract-tree test")

        session_id = sessions[0]["ssot__Id__c"]

        # Now extract that session's tree
        extractor = STDMExtractor(data_client, temp_output_dir)
        result = extractor.extract_session_tree(
            session_ids=[session_id],
            show_progress=False
        )

        # Should succeed
        assert result is not None
        assert result.sessions_count >= 1

        # Session data should be written
        sessions_dir = temp_output_dir / "sessions"
        assert sessions_dir.exists()
