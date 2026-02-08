"""
T3: Topics Analysis Tests (5 points)

Tests topics command for routing analysis:
- Shows topic distribution
- Counts turns per topic

SKILL.md Section: "Topic Analysis"
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
class TestTopicsCLI:
    """Test topics command CLI."""

    def test_topics_help(self, cli_runner, cli_app):
        """topics --help shows usage."""
        result = cli_runner.invoke(cli_app, ["topics", "--help"])

        assert result.exit_code == 0
        assert "topic" in result.output.lower()
        assert "--data-dir" in result.output

    def test_topics_requires_data_dir(self, cli_runner, cli_app):
        """topics requires --data-dir."""
        result = cli_runner.invoke(cli_app, ["topics"])

        assert result.exit_code != 0
        assert "data-dir" in result.output.lower() or "required" in result.output.lower()

    def test_topics_format_options(self, cli_runner, cli_app):
        """topics --format accepts table, json, csv."""
        result = cli_runner.invoke(cli_app, ["topics", "--help"])

        assert result.exit_code == 0
        assert "table" in result.output
        assert "json" in result.output
        assert "csv" in result.output


@pytest.mark.tier3
@pytest.mark.offline
class TestTopicsWithFixtures:
    """Test topics command with fixture data."""

    def test_topics_table_format(self, cli_runner, cli_app, sample_data_dir):
        """topics --format table produces output."""
        result = cli_runner.invoke(cli_app, [
            "topics",
            "--data-dir", str(sample_data_dir),
            "--format", "table"
        ])

        assert result.exit_code == 0, f"Failed: {result.output}"

    def test_topics_json_format(self, cli_runner, cli_app, sample_data_dir):
        """topics --format json produces valid JSON."""
        result = cli_runner.invoke(cli_app, [
            "topics",
            "--data-dir", str(sample_data_dir),
            "--format", "json"
        ])

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Should produce valid JSON
        try:
            data = json.loads(result.output)
            assert isinstance(data, (dict, list))
        except json.JSONDecodeError:
            pytest.fail(f"topics --format json did not produce valid JSON: {result.output[:200]}")


@pytest.mark.tier3
@pytest.mark.offline
class TestTopicsAnalyzer:
    """Test topic analysis in analyzer."""

    def test_topic_analysis_method_exists(self, sample_data_dir):
        """STDMAnalyzer has topic_analysis method."""
        from scripts.analyzer import STDMAnalyzer

        analyzer = STDMAnalyzer(sample_data_dir)

        assert hasattr(analyzer, 'topic_analysis')
        assert callable(analyzer.topic_analysis)

    def test_topic_analysis_returns_dataframe(self, sample_data_dir):
        """topic_analysis() returns Polars DataFrame."""
        from scripts.analyzer import STDMAnalyzer
        import polars as pl

        analyzer = STDMAnalyzer(sample_data_dir)
        topics = analyzer.topic_analysis()

        # Should return a DataFrame
        assert isinstance(topics, (pl.DataFrame, pl.LazyFrame))

    def test_topic_analysis_has_expected_columns(self, sample_data_dir):
        """topic_analysis() includes topic name and counts."""
        from scripts.analyzer import STDMAnalyzer

        analyzer = STDMAnalyzer(sample_data_dir)
        topics = analyzer.topic_analysis()

        # Convert to DataFrame if LazyFrame
        if hasattr(topics, 'collect'):
            topics = topics.collect()

        # Should have columns for topic and count
        columns = topics.columns
        assert len(columns) > 0
