"""
T4: Parquet Output Structure Tests (5 points)

Tests Parquet output follows expected structure:
- Directory layout matches SKILL.md
- Parquet schemas match PyArrow definitions

SKILL.md Section: "Output Directory Structure"
"""

import sys
import pytest
from pathlib import Path

import pyarrow.parquet as pq

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier4
@pytest.mark.offline
class TestParquetStructure:
    """Test Parquet output structure (5 points)."""

    def test_fixture_has_four_directories(self, sample_data_dir):
        """Fixture data has all 4 entity directories."""
        expected_dirs = ["sessions", "interactions", "steps", "messages"]

        for dir_name in expected_dirs:
            dir_path = sample_data_dir / dir_name
            assert dir_path.exists(), f"Missing fixture directory: {dir_name}"
            assert dir_path.is_dir(), f"Not a directory: {dir_name}"

    def test_sessions_parquet_readable(self, sample_data_dir):
        """sessions/ Parquet files are readable."""
        sessions_dir = sample_data_dir / "sessions"
        parquet_files = list(sessions_dir.glob("**/*.parquet"))

        assert len(parquet_files) > 0, "No Parquet files in sessions/"

        # Should be readable
        for pf in parquet_files:
            table = pq.read_table(pf)
            assert len(table) >= 0

    def test_sessions_schema_matches(self, sample_data_dir):
        """sessions/ Parquet schema matches SESSION_SCHEMA."""
        from scripts.models import SESSION_SCHEMA

        sessions_dir = sample_data_dir / "sessions"
        parquet_files = list(sessions_dir.glob("**/*.parquet"))

        if not parquet_files:
            pytest.skip("No session Parquet files to validate")

        table = pq.read_table(parquet_files[0])
        actual_fields = set(table.schema.names)
        expected_fields = set(SESSION_SCHEMA.names)

        # All expected fields should be present
        missing = expected_fields - actual_fields
        assert not missing, f"Missing fields in sessions Parquet: {missing}"

    def test_interactions_parquet_readable(self, sample_data_dir):
        """interactions/ Parquet files are readable."""
        interactions_dir = sample_data_dir / "interactions"
        parquet_files = list(interactions_dir.glob("**/*.parquet"))

        assert len(parquet_files) > 0, "No Parquet files in interactions/"

        for pf in parquet_files:
            table = pq.read_table(pf)
            assert len(table) >= 0

    def test_steps_parquet_readable(self, sample_data_dir):
        """steps/ Parquet files are readable."""
        steps_dir = sample_data_dir / "steps"
        parquet_files = list(steps_dir.glob("**/*.parquet"))

        assert len(parquet_files) > 0, "No Parquet files in steps/"

        for pf in parquet_files:
            table = pq.read_table(pf)
            assert len(table) >= 0

    def test_messages_parquet_readable(self, sample_data_dir):
        """messages/ Parquet files are readable."""
        messages_dir = sample_data_dir / "messages"
        parquet_files = list(messages_dir.glob("**/*.parquet"))

        assert len(parquet_files) > 0, "No Parquet files in messages/"

        for pf in parquet_files:
            table = pq.read_table(pf)
            assert len(table) >= 0


@pytest.mark.tier4
@pytest.mark.offline
class TestSchemaRegistry:
    """Test schema registry is complete."""

    def test_schemas_dict_exists(self):
        """SCHEMAS dictionary exists with all entity types."""
        from scripts.models import SCHEMAS

        assert SCHEMAS is not None
        assert isinstance(SCHEMAS, dict)

        expected_keys = ["sessions", "interactions", "steps", "messages"]
        for key in expected_keys:
            assert key in SCHEMAS, f"Missing schema: {key}"

    def test_schemas_are_pyarrow_schemas(self):
        """All schemas are PyArrow Schema objects."""
        from scripts.models import SCHEMAS
        import pyarrow as pa

        for name, schema in SCHEMAS.items():
            assert isinstance(schema, pa.Schema), \
                f"SCHEMAS['{name}'] is not a PyArrow Schema"

    def test_models_dict_exists(self):
        """MODELS dictionary exists with Pydantic models."""
        from scripts.models import MODELS

        assert MODELS is not None
        assert isinstance(MODELS, dict)

        expected_keys = ["sessions", "interactions", "steps", "messages"]
        for key in expected_keys:
            assert key in MODELS, f"Missing model: {key}"

    def test_utility_functions_exist(self):
        """Utility functions exist in models module."""
        from scripts import models

        assert hasattr(models, 'validate_record')
        assert hasattr(models, 'get_field_mapping')
        assert hasattr(models, 'get_required_fields')
        assert hasattr(models, 'build_select_clause')
