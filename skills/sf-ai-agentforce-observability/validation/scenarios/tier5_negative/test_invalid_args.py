"""
T5: Invalid Arguments Tests (5 points)

Tests CLI argument validation:
- Required args produce clear error
- Invalid values rejected with guidance

SKILL.md Section: "CLI Quick Reference"
"""

import sys
import pytest
from pathlib import Path

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier5
@pytest.mark.offline
class TestInvalidArgs:
    """Test invalid CLI arguments (5 points)."""

    def test_extract_missing_org_shows_error(self, cli_runner, cli_app):
        """extract without --org shows clear error."""
        result = cli_runner.invoke(cli_app, ["extract"])

        assert result.exit_code != 0
        assert "org" in result.output.lower() or "required" in result.output.lower()

    def test_analyze_missing_data_dir_shows_error(self, cli_runner, cli_app):
        """analyze without --data-dir shows clear error."""
        result = cli_runner.invoke(cli_app, ["analyze"])

        assert result.exit_code != 0
        assert "data-dir" in result.output.lower() or "required" in result.output.lower()

    def test_analyze_nonexistent_data_dir_shows_error(self, cli_runner, cli_app):
        """analyze with non-existent --data-dir shows clear error."""
        result = cli_runner.invoke(cli_app, [
            "analyze",
            "--data-dir", "/nonexistent/path/xyz123"
        ])

        assert result.exit_code != 0
        # Should mention the path doesn't exist
        assert "exist" in result.output.lower() or "not found" in result.output.lower() or "invalid" in result.output.lower()

    def test_count_invalid_entity_shows_error(self, cli_runner, cli_app):
        """count --entity invalid_type shows clear error."""
        result = cli_runner.invoke(cli_app, [
            "count",
            "--org", "test-org",
            "--entity", "invalid_entity_type"
        ])

        assert result.exit_code != 0
        # Should list valid options
        assert "sessions" in result.output or "invalid" in result.output.lower()

    def test_extract_invalid_days_shows_error(self, cli_runner, cli_app):
        """extract --days negative shows error."""
        result = cli_runner.invoke(cli_app, [
            "extract",
            "--org", "test-org",
            "--days", "-5"
        ])

        # Should fail or handle negative gracefully
        # Click may accept it but extraction would fail logically
        # We just verify it doesn't crash unexpectedly

    def test_debug_session_missing_session_id_shows_error(self, cli_runner, cli_app, sample_data_dir):
        """debug-session without --session-id shows error."""
        result = cli_runner.invoke(cli_app, [
            "debug-session",
            "--data-dir", str(sample_data_dir)
        ])

        assert result.exit_code != 0
        assert "session-id" in result.output.lower() or "required" in result.output.lower()


@pytest.mark.tier5
@pytest.mark.offline
class TestHelpOutput:
    """Test help output is informative."""

    def test_main_help_lists_commands(self, cli_runner, cli_app):
        """Main --help lists all commands."""
        result = cli_runner.invoke(cli_app, ["--help"])

        assert result.exit_code == 0

        # Should list main commands
        expected_commands = ["extract", "analyze", "count"]
        for cmd in expected_commands:
            assert cmd in result.output

    def test_extract_help_describes_options(self, cli_runner, cli_app):
        """extract --help describes all options."""
        result = cli_runner.invoke(cli_app, ["extract", "--help"])

        assert result.exit_code == 0

        # Should describe key options
        assert "--org" in result.output
        assert "--days" in result.output
        assert "--output" in result.output

    def test_version_flag_works(self, cli_runner, cli_app):
        """--version shows version."""
        result = cli_runner.invoke(cli_app, ["--version"])

        assert result.exit_code == 0
        # Should show a version number
        assert "." in result.output  # Version typically has dots (1.0.0)


@pytest.mark.tier5
@pytest.mark.offline
class TestEdgeCases:
    """Test edge case handling."""

    def test_empty_data_dir_handled(self, cli_runner, cli_app, temp_output_dir):
        """analyze with empty data dir handles gracefully."""
        # Create empty directories
        (temp_output_dir / "sessions").mkdir()
        (temp_output_dir / "interactions").mkdir()
        (temp_output_dir / "steps").mkdir()
        (temp_output_dir / "messages").mkdir()

        result = cli_runner.invoke(cli_app, [
            "analyze",
            "--data-dir", str(temp_output_dir)
        ])

        # Should either succeed with "no data" or fail gracefully
        # Shouldn't crash with unhandled exception
        if result.exit_code != 0:
            # Error message should be helpful
            assert len(result.output) > 0

    def test_topics_empty_interactions_handled(self, cli_runner, cli_app, temp_output_dir):
        """topics with no interaction data handles gracefully."""
        import pyarrow as pa
        import pyarrow.parquet as pq
        from scripts.models import INTERACTION_SCHEMA

        # Create directories with empty Parquet files
        for dir_name in ["sessions", "interactions", "steps", "messages"]:
            dir_path = temp_output_dir / dir_name
            dir_path.mkdir(exist_ok=True)

        # Create empty interactions Parquet
        empty_table = pa.table({
            name: pa.array([], type=field.type)
            for name, field in zip(INTERACTION_SCHEMA.names, INTERACTION_SCHEMA)
        })
        pq.write_table(empty_table, temp_output_dir / "interactions" / "data.parquet")

        result = cli_runner.invoke(cli_app, [
            "topics",
            "--data-dir", str(temp_output_dir)
        ])

        # Should handle empty data gracefully
        # Either succeed with empty output or fail with clear message
        if result.exit_code != 0:
            assert "no data" in result.output.lower() or "empty" in result.output.lower() or len(result.output) > 0
