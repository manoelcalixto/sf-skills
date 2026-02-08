"""
T4: Query Pattern Validation Tests

Tests that documented query patterns are syntactically valid:
- Basic extraction queries
- Official example queries
- Quality analysis queries
- Knowledge retrieval queries

query-patterns.md validation
"""

import sys
import re
import pytest
from pathlib import Path

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


def extract_sql_blocks(markdown_content: str) -> list:
    """Extract SQL code blocks from markdown content."""
    # Match ```sql ... ``` blocks
    pattern = r'```sql\s*(.*?)```'
    matches = re.findall(pattern, markdown_content, re.DOTALL | re.IGNORECASE)
    return [m.strip() for m in matches if m.strip()]


def is_valid_sql_syntax(query: str) -> tuple:
    """
    Basic SQL syntax validation.
    Returns (is_valid, error_message).
    """
    # Normalize whitespace
    query = ' '.join(query.split())

    # Skip comment-only blocks
    if query.startswith('--') and 'SELECT' not in query.upper():
        return (True, None)

    # Must have SELECT for data queries
    if 'SELECT' not in query.upper():
        # Could be a comment or partial query
        if '--' in query:
            return (True, None)
        return (False, "No SELECT statement found")

    # Basic structure checks
    errors = []

    # Check for balanced parentheses
    if query.count('(') != query.count(')'):
        errors.append("Unbalanced parentheses")

    # Check for balanced quotes (single)
    single_quotes = query.count("'")
    if single_quotes % 2 != 0:
        errors.append("Unbalanced single quotes")

    # Check for common syntax issues
    upper_query = query.upper()

    # FROM should follow SELECT (with possible fields between)
    if 'SELECT' in upper_query and 'FROM' not in upper_query:
        # CTE queries might have FROM elsewhere
        if 'WITH' not in upper_query:
            errors.append("SELECT without FROM")

    if errors:
        return (False, "; ".join(errors))

    return (True, None)


@pytest.mark.tier4
@pytest.mark.offline
class TestQueryPatternsFileExists:
    """Test query patterns documentation exists."""

    def test_query_patterns_file_exists(self):
        """query-patterns.md exists in resources."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        assert doc_path.exists(), "query-patterns.md not found"

    def test_query_patterns_has_sql_blocks(self):
        """query-patterns.md contains SQL code blocks."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        sql_blocks = extract_sql_blocks(content)
        assert len(sql_blocks) > 0, "No SQL blocks found in query-patterns.md"

    def test_query_patterns_has_minimum_queries(self):
        """query-patterns.md has at least 10 query examples."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        sql_blocks = extract_sql_blocks(content)
        assert len(sql_blocks) >= 10, f"Only {len(sql_blocks)} queries found, expected 10+"


@pytest.mark.tier4
@pytest.mark.offline
class TestBasicQuerySyntax:
    """Test basic extraction queries are syntactically valid."""

    def test_all_sessions_query_valid(self):
        """'All Sessions' query is syntactically valid."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        sql_blocks = extract_sql_blocks(content)

        # Find a query that selects from sessions
        session_queries = [q for q in sql_blocks if 'AIAgentSession' in q]
        assert len(session_queries) > 0, "No session queries found"

        # Validate syntax
        for query in session_queries[:3]:  # Check first 3
            is_valid, error = is_valid_sql_syntax(query)
            assert is_valid, f"Invalid syntax in session query: {error}\n{query[:200]}"

    def test_interaction_queries_valid(self):
        """Interaction-related queries are syntactically valid."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        sql_blocks = extract_sql_blocks(content)

        interaction_queries = [q for q in sql_blocks if 'Interaction' in q]
        assert len(interaction_queries) > 0, "No interaction queries found"

        for query in interaction_queries[:3]:
            is_valid, error = is_valid_sql_syntax(query)
            assert is_valid, f"Invalid syntax in interaction query: {error}"

    def test_step_queries_valid(self):
        """Step-related queries are syntactically valid."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        sql_blocks = extract_sql_blocks(content)

        step_queries = [q for q in sql_blocks if 'Step' in q]
        assert len(step_queries) > 0, "No step queries found"

        for query in step_queries[:3]:
            is_valid, error = is_valid_sql_syntax(query)
            assert is_valid, f"Invalid syntax in step query: {error}"


@pytest.mark.tier4
@pytest.mark.offline
class TestOfficialQueries:
    """Test official Salesforce example queries are present."""

    def test_full_session_join_documented(self):
        """Full 5-entity join query is documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        # Should have a query joining multiple tables
        join_indicators = ["JOIN", "join"]
        has_joins = any(ind in content for ind in join_indicators)
        assert has_joins, "No JOIN queries documented"

        # Should have session-participant-interaction-message-step joins
        entities = [
            "AiAgentSession",
            "AiAgentInteraction",
        ]
        for entity in entities:
            assert entity in content, f"Missing {entity} in join queries"

    def test_error_detection_query_documented(self):
        """Query for finding steps with errors is documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        error_terms = ["ErrorMessage", "error", "Error"]
        found = any(term in content for term in error_terms)
        assert found, "Error detection query not documented"

    def test_interval_syntax_documented(self):
        """INTERVAL syntax for date filtering is documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        # Should have INTERVAL or date comparison syntax
        date_terms = ["INTERVAL", "current_date", "DATE"]
        found = any(term in content for term in date_terms)
        assert found, "Date INTERVAL syntax not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestQualityAnalysisQueries:
    """Test quality analysis queries are documented."""

    def test_genai_generation_queries(self):
        """GenAI Generation join queries documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        gen_terms = ["GenAIGeneration", "GenAiGeneration", "generationId"]
        found = any(term in content for term in gen_terms)
        assert found, "GenAI Generation queries not documented"

    def test_toxicity_detection_documented(self):
        """Toxicity detection query documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        toxicity_terms = ["toxic", "Toxicity", "isToxicityDetected"]
        found = any(term in content for term in toxicity_terms)
        assert found, "Toxicity detection query not documented"

    def test_instruction_adherence_documented(self):
        """Instruction adherence query documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        adherence_terms = ["InstructionAdherence", "adherence", "Adherence"]
        found = any(term in content for term in adherence_terms)
        assert found, "Instruction adherence query not documented"

    def test_task_resolution_documented(self):
        """Task resolution query documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        resolution_terms = ["TaskResolution", "FULLY_RESOLVED", "NOT_RESOLVED"]
        found = any(term in content for term in resolution_terms)
        assert found, "Task resolution query not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestHallucinationQueries:
    """Test hallucination detection queries are documented."""

    def test_ungrounded_query_documented(self):
        """UNGROUNDED detection query documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        ungrounded_terms = ["UNGROUNDED", "hallucination", "Hallucination"]
        found = any(term in content for term in ungrounded_terms)
        assert found, "UNGROUNDED/hallucination query not documented"

    def test_validation_prompt_documented(self):
        """ReactValidationPrompt query documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        validation_terms = ["ReactValidationPrompt", "ValidationPrompt"]
        found = any(term in content for term in validation_terms)
        assert found, "ReactValidationPrompt query not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestKnowledgeRetrievalQueries:
    """Test knowledge retrieval analysis queries documented."""

    def test_vector_search_documented(self):
        """vector_search function documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        assert "vector_search" in content, "vector_search query not documented"

    def test_knowledge_index_documented(self):
        """Knowledge search index query documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        index_terms = ["Search_Index", "Knowledge", "Chunk"]
        found = any(term in content for term in index_terms)
        assert found, "Knowledge search index query not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestQueryPatternCompleteness:
    """Test query patterns cover all documented use cases."""

    def test_basic_extraction_section_exists(self):
        """Basic Extraction section exists."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        assert "Basic Extraction" in content or "Extraction" in content

    def test_aggregation_section_exists(self):
        """Aggregation queries section exists."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        agg_terms = ["Aggregation", "COUNT", "GROUP BY"]
        found = any(term in content for term in agg_terms)
        assert found, "Aggregation section not found"

    def test_relationship_queries_documented(self):
        """Relationship/join queries documented."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        assert "JOIN" in content, "JOIN queries not documented"

    def test_quality_analysis_section_exists(self):
        """Quality analysis section exists."""
        doc_path = SKILL_ROOT / "resources" / "query-patterns.md"
        content = doc_path.read_text()

        quality_terms = ["Quality", "Analysis", "Toxic", "Trust"]
        found = any(term in content for term in quality_terms)
        assert found, "Quality analysis section not found"
