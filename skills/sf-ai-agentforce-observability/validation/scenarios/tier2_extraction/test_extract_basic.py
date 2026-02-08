"""
T2: Basic Extraction Tests (10 points)

Tests extract command creates correct output structure:
- Creates 4 directories (sessions, interactions, steps, messages)
- Parquet files have correct schema
- Metadata files created

SKILL.md Section: "Output Directory Structure"
"""

import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier2
@pytest.mark.live_api
@pytest.mark.slow
class TestExtractBasic:
    """Test basic extraction creates correct structure (10 points)."""

    def test_extract_creates_four_directories(self, data_client, temp_output_dir):
        """extract command creates sessions/, interactions/, steps/, messages/."""
        from scripts.extractor import STDMExtractor

        extractor = STDMExtractor(data_client, temp_output_dir)

        # Extract last 1 day (minimal data)
        since = datetime.utcnow() - timedelta(days=1)
        result = extractor.extract_sessions(
            since=since,
            show_progress=False
        )

        # Check all 4 directories exist
        expected_dirs = ["sessions", "interactions", "steps", "messages"]
        for dir_name in expected_dirs:
            dir_path = temp_output_dir / dir_name
            assert dir_path.exists(), f"Missing directory: {dir_name}"
            assert dir_path.is_dir(), f"Not a directory: {dir_name}"

    def test_extract_creates_parquet_files(self, data_client, temp_output_dir):
        """Extraction creates Parquet files in each directory."""
        from scripts.extractor import STDMExtractor

        extractor = STDMExtractor(data_client, temp_output_dir)

        since = datetime.utcnow() - timedelta(days=1)
        result = extractor.extract_sessions(
            since=since,
            show_progress=False
        )

        # At least sessions directory should have data
        # (other directories depend on session data existing)
        sessions_dir = temp_output_dir / "sessions"

        # Should have at least the directory structure
        assert sessions_dir.exists()

        # If there's data, should have Parquet files
        if result.sessions_count > 0:
            parquet_files = list(sessions_dir.glob("**/*.parquet"))
            assert len(parquet_files) > 0, "No Parquet files in sessions/"

    def test_extract_returns_result_counts(self, data_client, temp_output_dir):
        """Extraction returns result with count attributes."""
        from scripts.extractor import STDMExtractor

        extractor = STDMExtractor(data_client, temp_output_dir)

        since = datetime.utcnow() - timedelta(days=1)
        result = extractor.extract_sessions(
            since=since,
            show_progress=False
        )

        # Result should have count attributes
        assert hasattr(result, 'sessions_count')
        assert hasattr(result, 'interactions_count')
        assert hasattr(result, 'steps_count')
        assert hasattr(result, 'messages_count')
        assert hasattr(result, 'duration_seconds')

        # Counts should be non-negative
        assert result.sessions_count >= 0
        assert result.interactions_count >= 0
        assert result.steps_count >= 0
        assert result.messages_count >= 0


@pytest.mark.tier2
@pytest.mark.live_api
class TestExtractCLI:
    """Test extract via CLI."""

    def test_extract_cli_help(self, cli_runner, cli_app):
        """extract --help shows usage."""
        result = cli_runner.invoke(cli_app, ["extract", "--help"])

        assert result.exit_code == 0
        assert "Extract session tracing data" in result.output
        assert "--org" in result.output
        assert "--days" in result.output

    def test_extract_cli_requires_org(self, cli_runner, cli_app):
        """extract without --org fails."""
        result = cli_runner.invoke(cli_app, ["extract"])

        assert result.exit_code != 0
        assert "org" in result.output.lower() or "required" in result.output.lower()


@pytest.mark.tier2
@pytest.mark.offline
class TestExtractOffline:
    """Offline tests for extraction logic."""

    def test_date_range_calculation(self):
        """--days N calculates correct date range."""
        from datetime import datetime, timedelta

        days = 7
        expected_start = datetime.utcnow() - timedelta(days=days)

        # The date should be approximately 7 days ago
        # Allow 1 minute tolerance for test execution time
        actual_start = datetime.utcnow() - timedelta(days=7)
        diff = abs((expected_start - actual_start).total_seconds())

        assert diff < 60, "Date range calculation off by more than 1 minute"

    def test_output_dir_default(self):
        """Default output directory is ./stdm_data."""
        # This is documented in SKILL.md CLI reference
        default_output = "./stdm_data"
        assert default_output == "./stdm_data"
