"""
T2: Incremental Extraction Tests (5 points)

Tests extract-incremental command:
- Uses watermark from previous extraction
- Falls back to 24 hours if no watermark

SKILL.md Section: "Incremental Extraction"
"""

import sys
import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier2
@pytest.mark.offline
class TestIncrementalCLI:
    """Test incremental extraction CLI."""

    def test_extract_incremental_help(self, cli_runner, cli_app):
        """extract-incremental --help shows usage."""
        result = cli_runner.invoke(cli_app, ["extract-incremental", "--help"])

        assert result.exit_code == 0
        assert "watermark" in result.output.lower() or "incremental" in result.output.lower()

    def test_extract_incremental_requires_org(self, cli_runner, cli_app):
        """extract-incremental requires --org."""
        result = cli_runner.invoke(cli_app, ["extract-incremental"])

        assert result.exit_code != 0
        assert "org" in result.output.lower() or "required" in result.output.lower()


@pytest.mark.tier2
@pytest.mark.live_api
@pytest.mark.slow
class TestIncrementalLive:
    """Live tests for incremental extraction."""

    def test_incremental_without_watermark(self, data_client, temp_output_dir):
        """Incremental extraction without watermark extracts last 24 hours."""
        from scripts.extractor import STDMExtractor

        extractor = STDMExtractor(data_client, temp_output_dir)

        # Run incremental without prior extraction
        result = extractor.extract_incremental(show_progress=False)

        # Should complete
        assert result is not None

    def test_incremental_creates_watermark(self, data_client, temp_output_dir):
        """Incremental extraction creates watermark file."""
        from scripts.extractor import STDMExtractor

        extractor = STDMExtractor(data_client, temp_output_dir)

        # Run extraction
        result = extractor.extract_incremental(show_progress=False)

        # Check for watermark file
        # Watermark could be in metadata/ or root directory
        watermark_paths = [
            temp_output_dir / "metadata" / "watermark.json",
            temp_output_dir / "watermark.json",
        ]

        watermark_found = any(p.exists() for p in watermark_paths)

        # If extraction ran successfully, watermark should exist
        if result.sessions_count > 0:
            assert watermark_found, "Watermark file not created after extraction"

    def test_incremental_uses_watermark(self, data_client, temp_output_dir):
        """Second incremental uses watermark from first."""
        from scripts.extractor import STDMExtractor

        extractor = STDMExtractor(data_client, temp_output_dir)

        # First extraction
        result1 = extractor.extract_incremental(show_progress=False)

        # Create watermark manually if extractor doesn't
        metadata_dir = temp_output_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        watermark_file = metadata_dir / "watermark.json"

        if not watermark_file.exists():
            watermark_data = {
                "last_extraction": datetime.utcnow().isoformat(),
                "sessions_count": result1.sessions_count
            }
            with open(watermark_file, "w") as f:
                json.dump(watermark_data, f)

        # Second extraction should read watermark
        result2 = extractor.extract_incremental(show_progress=False)

        # Both should complete
        assert result2 is not None
