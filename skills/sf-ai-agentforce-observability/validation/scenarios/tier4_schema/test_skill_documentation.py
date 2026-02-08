"""
T4: SKILL.md Documentation Validation Tests

Tests that SKILL.md contains required documentation:
- Prerequisites checklist
- Billing considerations
- Setup instructions
- Cross-skill integration

SKILL.md validation
"""

import sys
import pytest
from pathlib import Path

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier4
@pytest.mark.offline
class TestSkillMDExists:
    """Test SKILL.md file exists and has required sections."""

    def test_skill_md_exists(self):
        """SKILL.md exists in skill root."""
        skill_md = SKILL_ROOT / "SKILL.md"
        assert skill_md.exists(), "SKILL.md not found"

    def test_skill_md_has_frontmatter(self):
        """SKILL.md has YAML frontmatter."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        # Should start with ---
        assert content.startswith("---"), "SKILL.md missing YAML frontmatter"

    def test_skill_md_minimum_length(self):
        """SKILL.md has substantial content."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        # Should have at least 5000 characters
        assert len(content) > 5000, f"SKILL.md too short: {len(content)} chars"


@pytest.mark.tier4
@pytest.mark.offline
class TestPrerequisitesSection:
    """Test prerequisites checklist is documented."""

    def test_prerequisites_section_exists(self):
        """Prerequisites section exists."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        prereq_terms = ["Prerequisites", "CRITICAL", "Before"]
        found = any(term in content for term in prereq_terms)
        assert found, "Prerequisites section not found"

    def test_data_360_prerequisite(self):
        """Data 360 enablement is listed as prerequisite."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        data_cloud_terms = ["Data 360", "Data Cloud", "data_360"]
        found = any(term in content for term in data_cloud_terms)
        assert found, "Data 360 prerequisite not documented"

    def test_session_tracing_prerequisite(self):
        """Session Tracing enablement is listed as prerequisite."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        tracing_terms = ["Session Tracing", "tracing", "Tracing"]
        found = any(term in content for term in tracing_terms)
        assert found, "Session Tracing prerequisite not documented"

    def test_jwt_auth_prerequisite(self):
        """JWT authentication is listed as prerequisite."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        jwt_terms = ["JWT", "jwt", "authentication", "Auth"]
        found = any(term in content for term in jwt_terms)
        assert found, "JWT authentication prerequisite not documented"

    def test_data_model_version_mentioned(self):
        """Salesforce Standard Data Model version mentioned."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        version_terms = ["1.124", "Data Model", "Standard Data Model"]
        found = any(term in content for term in version_terms)
        assert found, "Data Model version requirement not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestBillingSection:
    """Test billing considerations are documented."""

    def test_billing_section_exists(self):
        """Billing section exists."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        billing_terms = ["Billing", "Credit", "cost", "Cost"]
        found = any(term in content for term in billing_terms)
        assert found, "Billing section not found"

    def test_credit_consumption_documented(self):
        """Credit consumption is documented."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        credit_terms = ["credit", "Credit", "consumption", "Consumption"]
        found = any(term in content for term in credit_terms)
        assert found, "Credit consumption not documented"

    def test_records_per_llm_call_documented(self):
        """Records per LLM call estimation documented."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        # Should mention ~24 records per LLM call
        estimation_terms = ["24", "records", "LLM", "round-trip"]
        found = sum(1 for term in estimation_terms if term in content) >= 2
        assert found, "Records per LLM call estimation not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestCLIDocumentation:
    """Test CLI commands are documented."""

    def test_extract_command_documented(self):
        """extract command is documented."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        assert "extract" in content, "extract command not documented"

    def test_analyze_command_documented(self):
        """analyze command is documented."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        analyze_terms = ["analyze", "analysis", "Analyze"]
        found = any(term in content for term in analyze_terms)
        assert found, "analyze command not documented"

    def test_debug_session_documented(self):
        """debug-session command is documented."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        debug_terms = ["debug-session", "debug", "Debug"]
        found = any(term in content for term in debug_terms)
        assert found, "debug-session command not documented"

    def test_common_flags_documented(self):
        """Common CLI flags are documented."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        flags = ["--org", "--days", "--output"]
        found = sum(1 for flag in flags if flag in content) >= 2
        assert found, "Common CLI flags not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestDataModelSection:
    """Test data model overview is documented in SKILL.md."""

    def test_stdm_mentioned(self):
        """STDM (Session Tracing Data Model) mentioned."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        stdm_terms = ["STDM", "Session Tracing Data Model", "Data Model"]
        found = any(term in content for term in stdm_terms)
        assert found, "STDM not mentioned in SKILL.md"

    def test_dmo_entities_listed(self):
        """Core DMO entities are listed."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        entities = ["Session", "Interaction", "Step"]
        found = sum(1 for e in entities if e in content) >= 2
        assert found, "Core DMO entities not listed"

    def test_field_casing_note(self):
        """Field casing note (AiAgent vs AIAgent) present."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        casing_terms = ["AiAgent", "lowercase", "casing"]
        found = any(term in content for term in casing_terms)
        assert found, "Field casing note not present"


@pytest.mark.tier4
@pytest.mark.offline
class TestCrossSkillIntegration:
    """Test cross-skill integration is documented."""

    def test_related_skills_mentioned(self):
        """Related skills are mentioned."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        related_skills = [
            "sf-connected-apps",
            "sf-ai-agentscript",
            "sf-ai-agentforce-testing",
            "sf-debug",
        ]

        found = sum(1 for s in related_skills if s in content) >= 2
        assert found, "Related skills not documented"

    def test_skill_chaining_documented(self):
        """Skill chaining/integration documented."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        integration_terms = [
            "Integration",
            "integration",
            "Cross-Skill",
            "follow-up",
            "Skill(",
        ]
        found = any(term in content for term in integration_terms)
        assert found, "Skill chaining not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestDocumentMapSection:
    """Test document map/navigation is provided."""

    def test_document_map_exists(self):
        """Document map section exists."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        map_terms = ["Document Map", "documentation", "Reference"]
        found = any(term in content for term in map_terms)
        assert found, "Document map section not found"

    def test_data_model_reference_linked(self):
        """data-model-reference.md is linked."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        assert "data-model-reference.md" in content, "data-model-reference.md not linked"

    def test_query_patterns_linked(self):
        """query-patterns.md is linked."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        assert "query-patterns.md" in content, "query-patterns.md not linked"


@pytest.mark.tier4
@pytest.mark.offline
class TestKeyInsightsSection:
    """Test key insights section is documented."""

    def test_key_insights_section_exists(self):
        """Key Insights section exists."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        insight_terms = ["Key Insights", "Insights", "insights"]
        found = any(term in content for term in insight_terms)
        assert found, "Key Insights section not found"

    def test_collection_interval_documented(self):
        """5-minute collection interval documented."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        interval_terms = ["5-minute", "5 minute", "collection interval"]
        found = any(term in content for term in interval_terms)
        assert found, "Collection interval not documented"

    def test_session_lag_documented(self):
        """Session data lag is documented."""
        skill_md = SKILL_ROOT / "SKILL.md"
        content = skill_md.read_text()

        lag_terms = ["lag", "delay", "5-15 minute"]
        found = any(term in content for term in lag_terms)
        assert found, "Session data lag not documented"
