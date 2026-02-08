"""
T3: Analyze Command Tests (5 points)

Tests analyze command for summary statistics:
- Session counts and distributions
- Output formats (table, json, csv)

SKILL.md Section: "Analysis Examples"
"""

import sys
import json
import pytest
from pathlib import Path

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier3
@pytest.mark.offline
class TestAnalyzeCLI:
    """Test analyze command CLI."""

    def test_analyze_help(self, cli_runner, cli_app):
        """analyze --help shows usage."""
        result = cli_runner.invoke(cli_app, ["analyze", "--help"])

        assert result.exit_code == 0
        assert "summary" in result.output.lower() or "statistics" in result.output.lower()
        assert "--data-dir" in result.output

    def test_analyze_requires_data_dir(self, cli_runner, cli_app):
        """analyze requires --data-dir."""
        result = cli_runner.invoke(cli_app, ["analyze"])

        assert result.exit_code != 0
        assert "data-dir" in result.output.lower() or "required" in result.output.lower()

    def test_analyze_format_options(self, cli_runner, cli_app):
        """analyze --format accepts table, json, csv."""
        result = cli_runner.invoke(cli_app, ["analyze", "--help"])

        assert result.exit_code == 0
        assert "table" in result.output
        assert "json" in result.output
        assert "csv" in result.output


@pytest.mark.tier3
@pytest.mark.offline
class TestAnalyzeWithFixtures:
    """Test analyze command with fixture data."""

    def test_analyze_table_format(self, cli_runner, cli_app, sample_data_dir):
        """analyze --format table produces table output."""
        result = cli_runner.invoke(cli_app, [
            "analyze",
            "--data-dir", str(sample_data_dir),
            "--format", "table"
        ])

        # Should succeed
        assert result.exit_code == 0, f"Failed: {result.output}"

    def test_analyze_json_format(self, cli_runner, cli_app, sample_data_dir):
        """analyze --format json produces valid JSON."""
        result = cli_runner.invoke(cli_app, [
            "analyze",
            "--data-dir", str(sample_data_dir),
            "--format", "json"
        ])

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Output should be valid JSON
        try:
            data = json.loads(result.output)
            assert isinstance(data, (dict, list))
        except json.JSONDecodeError:
            pytest.fail(f"analyze --format json did not produce valid JSON: {result.output[:200]}")

    def test_analyze_csv_format(self, cli_runner, cli_app, sample_data_dir):
        """analyze --format csv produces CSV output."""
        result = cli_runner.invoke(cli_app, [
            "analyze",
            "--data-dir", str(sample_data_dir),
            "--format", "csv"
        ])

        assert result.exit_code == 0, f"Failed: {result.output}"

        # CSV should have comma-separated values
        # First line should be headers
        lines = result.output.strip().split('\n')
        if len(lines) > 0:
            # Should have some comma-separated content
            assert ',' in lines[0] or len(lines) == 1


@pytest.mark.tier3
@pytest.mark.offline
class TestAnalyzerClass:
    """Test STDMAnalyzer class directly."""

    def test_analyzer_loads_data(self, sample_data_dir):
        """STDMAnalyzer loads Parquet data correctly."""
        from scripts.analyzer import STDMAnalyzer

        analyzer = STDMAnalyzer(sample_data_dir)

        # Should be able to access data
        assert analyzer is not None

    def test_session_summary_returns_dataframe(self, sample_data_dir):
        """session_summary() returns Polars DataFrame."""
        from scripts.analyzer import STDMAnalyzer
        import polars as pl

        analyzer = STDMAnalyzer(sample_data_dir)
        summary = analyzer.session_summary()

        # Should return a Polars DataFrame (or LazyFrame)
        assert isinstance(summary, (pl.DataFrame, pl.LazyFrame))
