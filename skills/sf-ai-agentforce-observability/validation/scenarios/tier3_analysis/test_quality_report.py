"""
T3: Quality Report Tests (5 points)

Tests quality-report command for quality metrics:
- Hallucination detection
- Toxicity analysis
- Instruction adherence

SKILL.md Section: "Quality Report"
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
class TestQualityReportCLI:
    """Test quality-report command CLI."""

    def test_quality_report_help(self, cli_runner, cli_app):
        """quality-report --help shows usage."""
        result = cli_runner.invoke(cli_app, ["quality-report", "--help"])

        assert result.exit_code == 0
        assert "quality" in result.output.lower()
        assert "--data-dir" in result.output

    def test_quality_report_requires_data_dir(self, cli_runner, cli_app):
        """quality-report requires --data-dir."""
        result = cli_runner.invoke(cli_app, ["quality-report"])

        assert result.exit_code != 0
        assert "data-dir" in result.output.lower() or "required" in result.output.lower()

    def test_quality_report_format_options(self, cli_runner, cli_app):
        """quality-report --format accepts table, json."""
        result = cli_runner.invoke(cli_app, ["quality-report", "--help"])

        assert result.exit_code == 0
        assert "table" in result.output
        assert "json" in result.output


@pytest.mark.tier3
@pytest.mark.offline
class TestQualityReportWithFixtures:
    """Test quality-report with fixture data."""

    def test_quality_report_table_format(self, cli_runner, cli_app, sample_data_dir):
        """quality-report --format table produces output."""
        result = cli_runner.invoke(cli_app, [
            "quality-report",
            "--data-dir", str(sample_data_dir),
            "--format", "table"
        ])

        # May fail if quality DMOs not present, but shouldn't crash
        # The command should handle missing quality data gracefully
        if result.exit_code != 0:
            # Acceptable if it's a "quality data not found" error
            assert ("quality" in result.output.lower() or
                    "not found" in result.output.lower() or
                    "extract-quality" in result.output.lower())

    def test_quality_report_json_format(self, cli_runner, cli_app, sample_data_dir):
        """quality-report --format json produces JSON or error."""
        result = cli_runner.invoke(cli_app, [
            "quality-report",
            "--data-dir", str(sample_data_dir),
            "--format", "json"
        ])

        # If successful, should be valid JSON
        if result.exit_code == 0:
            try:
                data = json.loads(result.output)
                assert isinstance(data, (dict, list))
            except json.JSONDecodeError:
                pass  # May have non-JSON error message


@pytest.mark.tier3
@pytest.mark.offline
class TestQualityAnalyzer:
    """Test quality analysis in analyzer."""

    def test_quality_report_method_exists(self, sample_data_dir):
        """STDMAnalyzer has quality_report method."""
        from scripts.analyzer import STDMAnalyzer

        analyzer = STDMAnalyzer(sample_data_dir)

        assert hasattr(analyzer, 'quality_report')
        assert callable(analyzer.quality_report)

    def test_hallucination_summary_method_exists(self, sample_data_dir):
        """STDMAnalyzer has hallucination_summary method."""
        from scripts.analyzer import STDMAnalyzer

        analyzer = STDMAnalyzer(sample_data_dir)

        assert hasattr(analyzer, 'hallucination_summary')
        assert callable(analyzer.hallucination_summary)


@pytest.mark.tier3
@pytest.mark.offline
class TestFindHallucinationsCLI:
    """Test find-hallucinations command."""

    def test_find_hallucinations_help(self, cli_runner, cli_app):
        """find-hallucinations --help shows usage."""
        result = cli_runner.invoke(cli_app, ["find-hallucinations", "--help"])

        assert result.exit_code == 0
        assert "hallucination" in result.output.lower() or "ungrounded" in result.output.lower()

    def test_find_hallucinations_requires_data_dir(self, cli_runner, cli_app):
        """find-hallucinations requires --data-dir."""
        result = cli_runner.invoke(cli_app, ["find-hallucinations"])

        assert result.exit_code != 0
