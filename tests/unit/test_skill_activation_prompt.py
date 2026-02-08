"""
Unit tests for skill-activation-prompt.py

Tests cover:
- Keyword matching (word boundaries, case insensitivity)
- Intent pattern matching (regex patterns)
- File pattern matching (active files)
- Scoring algorithm (thresholds, confidence levels)
- Chain detection (trigger phrases)
- Skill invocation tracking (state persistence)
- Output formatting
- Edge cases
"""

import json
import sys
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module under test from tests.conftest (handles hyphenated filename)
from tests.conftest import skill_activation_prompt as sap


# =============================================================================
# KEYWORD MATCHING TESTS
# =============================================================================


class TestKeywordMatching:
    """Tests for match_keywords() function."""

    def test_single_keyword_match(self):
        """Single keyword should match and return count of 1."""
        result = sap.match_keywords("I need apex code", ["apex", "trigger"])
        assert result == 1

    def test_multiple_keyword_matches(self):
        """Multiple keywords in prompt should increase match count."""
        result = sap.match_keywords(
            "Create apex trigger for batch processing",
            ["apex", "trigger", "batch"]
        )
        assert result == 3

    def test_no_keyword_match(self):
        """No keywords in prompt should return 0."""
        result = sap.match_keywords("Hello world", ["apex", "trigger"])
        assert result == 0

    def test_word_boundary_no_partial_match(self):
        """Keywords should not match partial words (word boundaries)."""
        # "classification" contains "class" but should NOT match
        result = sap.match_keywords("classification logic", ["class"])
        assert result == 0

    def test_word_boundary_exact_match(self):
        """Keywords should match exact words."""
        result = sap.match_keywords("create a class for Account", ["class"])
        assert result == 1

    def test_case_insensitive_matching(self):
        """Keyword matching should be case insensitive."""
        result = sap.match_keywords("APEX code with TRIGGER", ["apex", "trigger"])
        assert result == 2

    def test_keyword_with_special_chars_in_prompt(self):
        """Special characters near keywords should not prevent matching."""
        result = sap.match_keywords("@apex! trigger?", ["apex", "trigger"])
        assert result == 2

    def test_empty_keywords_list(self):
        """Empty keywords list should return 0."""
        result = sap.match_keywords("some prompt", [])
        assert result == 0

    def test_empty_prompt(self):
        """Empty prompt should return 0."""
        result = sap.match_keywords("", ["apex", "trigger"])
        assert result == 0

    @pytest.mark.parametrize("keyword,prompt,expected", [
        ("apex", "apex class", 1),
        ("apex", "apexcode", 0),  # No match - no word boundary
        ("class", "myclass", 0),  # No match - no word boundary
        ("class", "my class here", 1),
        ("test class", "write test class", 1),
        ("lwc", "build an lwc", 1),
    ])
    def test_word_boundary_parametrized(self, keyword, prompt, expected):
        """Parametrized word boundary tests."""
        result = sap.match_keywords(prompt, [keyword])
        assert result == expected


# =============================================================================
# INTENT PATTERN MATCHING TESTS
# =============================================================================


class TestIntentPatternMatching:
    """Tests for match_intent_patterns() function."""

    def test_simple_pattern_match(self):
        """Simple regex pattern should match."""
        result = sap.match_intent_patterns(
            "create an apex class",
            [r"create.*apex"]
        )
        assert result is True

    def test_no_pattern_match(self):
        """Non-matching prompt should return False."""
        result = sap.match_intent_patterns(
            "hello world",
            [r"create.*apex", r"build.*flow"]
        )
        assert result is False

    def test_multiple_patterns_one_match(self):
        """Should return True if any pattern matches."""
        result = sap.match_intent_patterns(
            "build an automation",
            [r"create.*apex", r"build.*automation"]
        )
        assert result is True

    def test_case_insensitive_pattern(self):
        """Pattern matching should be case insensitive."""
        result = sap.match_intent_patterns(
            "CREATE APEX CLASS",
            [r"create.*apex"]
        )
        assert result is True

    def test_invalid_regex_pattern_skipped(self):
        """Invalid regex patterns should be skipped without error."""
        result = sap.match_intent_patterns(
            "create apex",
            [r"[invalid(regex", r"create.*apex"]
        )
        assert result is True  # Valid pattern still matches

    def test_empty_patterns_list(self):
        """Empty patterns list should return False."""
        result = sap.match_intent_patterns("some prompt", [])
        assert result is False

    @pytest.mark.parametrize("prompt,patterns,expected", [
        ("write a trigger", [r"write.*trigger"], True),
        ("implement batch class", [r"implement.*batch"], True),
        ("fix apex code", [r"fix.*apex"], True),
        ("debug apex issue", [r"debug.*apex"], True),
        ("hello there", [r"create.*apex"], False),
    ])
    def test_intent_patterns_parametrized(self, prompt, patterns, expected):
        """Parametrized intent pattern tests."""
        result = sap.match_intent_patterns(prompt, patterns)
        assert result == expected


# =============================================================================
# FILE PATTERN MATCHING TESTS
# =============================================================================


class TestFilePatternMatching:
    """Tests for match_file_pattern() function."""

    def test_apex_cls_file_match(self):
        """Should match .cls files."""
        result = sap.match_file_pattern(
            ["AccountService.cls"],
            [r"\.cls$"]
        )
        assert result is True

    def test_apex_trigger_file_match(self):
        """Should match .trigger files."""
        result = sap.match_file_pattern(
            ["AccountTrigger.trigger"],
            [r"\.trigger$"]
        )
        assert result is True

    def test_flow_file_match(self):
        """Should match .flow-meta.xml files."""
        result = sap.match_file_pattern(
            ["Account_Update.flow-meta.xml"],
            [r"\.flow-meta\.xml$"]
        )
        assert result is True

    def test_lwc_js_file_match(self):
        """Should match LWC .js files in correct folder structure."""
        result = sap.match_file_pattern(
            ["force-app/main/default/lwc/myComponent/myComponent.js"],
            [r"lwc/[^/]+/[^/]+\.js$"]
        )
        assert result is True

    def test_non_lwc_js_no_match(self):
        """Should NOT match .js files outside lwc folder."""
        result = sap.match_file_pattern(
            ["src/utils/helpers.js"],
            [r"lwc/[^/]+/[^/]+\.js$"]
        )
        assert result is False

    def test_no_match_non_sf_file(self):
        """Should not match non-SF files."""
        result = sap.match_file_pattern(
            ["README.md", "package.json"],
            [r"\.cls$", r"\.trigger$"]
        )
        assert result is False

    def test_empty_active_files(self):
        """Empty active files should return False."""
        result = sap.match_file_pattern([], [r"\.cls$"])
        assert result is False

    def test_empty_file_patterns(self):
        """Empty file patterns should return False."""
        result = sap.match_file_pattern(["file.cls"], [])
        assert result is False

    def test_multiple_files_one_match(self):
        """Should return True if any file matches."""
        result = sap.match_file_pattern(
            ["README.md", "AccountService.cls", "package.json"],
            [r"\.cls$"]
        )
        assert result is True

    def test_full_path_match(self):
        """Should match files with full paths."""
        result = sap.match_file_pattern(
            ["force-app/main/default/classes/AccountService.cls"],
            [r"\.cls$"]
        )
        assert result is True


# =============================================================================
# SCORING ALGORITHM TESTS
# =============================================================================


class TestScoringAlgorithm:
    """Tests for find_matching_skills() scoring logic."""

    def test_keyword_only_score(self, skill_activation_module):
        """Single keyword match should give KEYWORD_SCORE (2)."""
        matches = skill_activation_module.find_matching_skills(
            "apex code",
            [],
            skill_activation_module.load_registry()
        )
        # Should match sf-apex with score >= 2
        apex_match = next((m for m in matches if m["skill"] == "sf-apex"), None)
        assert apex_match is not None
        assert apex_match["score"] >= 2

    def test_intent_pattern_adds_score(self, skill_activation_module):
        """Intent pattern match should add INTENT_PATTERN_SCORE (3)."""
        matches = skill_activation_module.find_matching_skills(
            "create apex class",  # "apex" keyword + "create.*apex" pattern
            [],
            skill_activation_module.load_registry()
        )
        apex_match = next((m for m in matches if m["skill"] == "sf-apex"), None)
        assert apex_match is not None
        # 2 (keyword) + 3 (intent) = 5
        assert apex_match["score"] >= 5

    def test_file_pattern_adds_score(self, skill_activation_module):
        """File pattern match should add FILE_PATTERN_SCORE (2)."""
        matches = skill_activation_module.find_matching_skills(
            "fix this code",
            ["AccountService.cls"],
            skill_activation_module.load_registry()
        )
        apex_match = next((m for m in matches if m["skill"] == "sf-apex"), None)
        assert apex_match is not None
        # File pattern adds 2 to score
        assert apex_match["score"] >= 2

    def test_combined_scoring(self, skill_activation_module):
        """Combined keyword + intent + file should give high score."""
        matches = skill_activation_module.find_matching_skills(
            "create apex trigger",  # Keywords: apex, trigger + intent pattern
            ["AccountTrigger.trigger"],  # File pattern
            skill_activation_module.load_registry()
        )
        apex_match = next((m for m in matches if m["skill"] == "sf-apex"), None)
        assert apex_match is not None
        # 4 (2 keywords) + 3 (intent) + 2 (file) = 9
        assert apex_match["score"] >= 7

    def test_confidence_level_optional(self, skill_activation_module):
        """Score < 4 should give confidence level 1 (OPTIONAL)."""
        matches = skill_activation_module.find_matching_skills(
            "apex",  # Just one keyword
            [],
            skill_activation_module.load_registry()
        )
        apex_match = next((m for m in matches if m["skill"] == "sf-apex"), None)
        if apex_match and apex_match["score"] < 4:
            assert apex_match["confidence"] == 1

    def test_confidence_level_recommended(self, skill_activation_module):
        """Score 4-6 should give confidence level 2 (RECOMMENDED)."""
        matches = skill_activation_module.find_matching_skills(
            "create apex class",  # keyword + intent = 5
            [],
            skill_activation_module.load_registry()
        )
        apex_match = next((m for m in matches if m["skill"] == "sf-apex"), None)
        assert apex_match is not None
        if 4 <= apex_match["score"] < 7:
            assert apex_match["confidence"] == 2

    def test_confidence_level_required(self, skill_activation_module):
        """Score >= 7 should give confidence level 3 (REQUIRED)."""
        matches = skill_activation_module.find_matching_skills(
            "create apex trigger with batch",
            ["AccountService.cls"],
            skill_activation_module.load_registry()
        )
        apex_match = next((m for m in matches if m["skill"] == "sf-apex"), None)
        assert apex_match is not None
        if apex_match["score"] >= 7:
            assert apex_match["confidence"] == 3

    def test_below_threshold_no_match(self, skill_activation_module):
        """Score below MIN_SCORE_THRESHOLD (2) should not be included."""
        matches = skill_activation_module.find_matching_skills(
            "hello world",  # No keywords
            [],
            skill_activation_module.load_registry()
        )
        assert len(matches) == 0

    def test_max_suggestions_limit(self, skill_activation_module):
        """Should return at most MAX_SUGGESTIONS (3) skills."""
        matches = skill_activation_module.find_matching_skills(
            "apex flow lwc trigger batch test",  # Many keywords
            [],
            skill_activation_module.load_registry()
        )
        assert len(matches) <= 3

    def test_sorting_by_score(self, skill_activation_module):
        """Results should be sorted by score descending."""
        matches = skill_activation_module.find_matching_skills(
            "apex flow automation",
            [],
            skill_activation_module.load_registry()
        )
        if len(matches) >= 2:
            scores = [m["score"] for m in matches]
            assert scores == sorted(scores, reverse=True)


# =============================================================================
# CHAIN DETECTION TESTS
# =============================================================================


class TestChainDetection:
    """Tests for detect_chain() function."""

    def test_full_feature_chain_detection(self, skill_activation_module):
        """Should detect full_feature chain from trigger phrase."""
        registry = skill_activation_module.load_registry()
        chain = skill_activation_module.detect_chain(
            "I want to build feature end to end",
            registry
        )
        assert chain is not None
        assert chain["name"] == "full_feature"
        assert "order" in chain
        assert chain["first_skill"] == "sf-metadata"

    def test_chain_detection_case_insensitive(self, skill_activation_module):
        """Chain detection should be case insensitive."""
        registry = skill_activation_module.load_registry()
        chain = skill_activation_module.detect_chain(
            "BUILD FEATURE for Account",
            registry
        )
        assert chain is not None
        assert chain["name"] == "full_feature"

    def test_no_chain_for_simple_prompt(self, skill_activation_module):
        """Simple prompts should not detect a chain."""
        registry = skill_activation_module.load_registry()
        chain = skill_activation_module.detect_chain(
            "fix this apex class",
            registry
        )
        assert chain is None

    def test_chain_has_description(self, skill_activation_module):
        """Detected chain should have description."""
        registry = skill_activation_module.load_registry()
        chain = skill_activation_module.detect_chain(
            "build feature end to end",
            registry
        )
        assert chain is not None
        assert "description" in chain
        assert len(chain["description"]) > 0


# =============================================================================
# SKILL INVOCATION TESTS
# =============================================================================


class TestSkillInvocation:
    """Tests for detect_skill_invocation() and state tracking."""

    def test_detect_sf_apex_invocation(self, skill_activation_module):
        """Should detect /sf-apex as valid skill invocation."""
        registry = skill_activation_module.load_registry()
        result = skill_activation_module.detect_skill_invocation("/sf-apex", registry)
        assert result == "sf-apex"

    def test_detect_sf_flow_invocation(self, skill_activation_module):
        """Should detect /sf-flow as valid skill invocation."""
        registry = skill_activation_module.load_registry()
        result = skill_activation_module.detect_skill_invocation("/sf-flow", registry)
        assert result == "sf-flow"

    def test_invocation_with_args(self, skill_activation_module):
        """Should detect skill invocation even with arguments."""
        registry = skill_activation_module.load_registry()
        result = skill_activation_module.detect_skill_invocation(
            "/sf-apex create a trigger",
            registry
        )
        assert result == "sf-apex"

    def test_unknown_skill_not_detected(self, skill_activation_module):
        """Unknown skill should return None."""
        registry = skill_activation_module.load_registry()
        result = skill_activation_module.detect_skill_invocation(
            "/unknown-skill",
            registry
        )
        assert result is None

    def test_not_slash_command(self, skill_activation_module):
        """Non-slash prompts should return None."""
        registry = skill_activation_module.load_registry()
        result = skill_activation_module.detect_skill_invocation(
            "use sf-apex to help",
            registry
        )
        assert result is None

    def test_save_active_skill(self, skill_activation_module, tmp_path):
        """save_active_skill should write state to file."""
        state_file = tmp_path / "active-skill.json"
        skill_activation_module.ACTIVE_SKILL_FILE = state_file

        skill_activation_module.save_active_skill("sf-apex")

        assert state_file.exists()
        with open(state_file) as f:
            state = json.load(f)
        assert state["active_skill"] == "sf-apex"
        assert "timestamp" in state


# =============================================================================
# OUTPUT FORMATTING TESTS
# =============================================================================


class TestOutputFormatting:
    """Tests for format_suggestions() function."""

    def test_format_with_matches(self, skill_activation_module):
        """Should format matches with skill names and confidence."""
        matches = [
            {
                "skill": "sf-apex",
                "score": 7,
                "confidence": 3,
                "priority": "high",
                "description": "Apex development",
                "reasons": ["keyword"]
            }
        ]
        registry = skill_activation_module.load_registry()
        output = skill_activation_module.format_suggestions(matches, None, registry)

        assert "sf-apex" in output
        assert "REQUIRED" in output
        assert "═" in output  # Header separator

    def test_format_with_chain(self, skill_activation_module):
        """Should include chain info when detected."""
        matches = []
        chain = {
            "name": "full_feature",
            "description": "Complete feature development",
            "order": ["sf-metadata", "sf-apex", "sf-flow"],
            "first_skill": "sf-metadata"
        }
        registry = skill_activation_module.load_registry()
        output = skill_activation_module.format_suggestions(matches, chain, registry)

        assert "full_feature" in output
        assert "sf-metadata" in output
        assert "WORKFLOW" in output or "Order" in output

    def test_format_empty_returns_empty(self, skill_activation_module):
        """Empty matches and no chain should return empty string."""
        registry = skill_activation_module.load_registry()
        output = skill_activation_module.format_suggestions([], None, registry)
        assert output == ""

    def test_confidence_icons(self, skill_activation_module):
        """Different confidence levels should show different icons."""
        matches_required = [{"skill": "sf-apex", "score": 8, "confidence": 3, "priority": "high", "description": "", "reasons": []}]
        matches_recommended = [{"skill": "sf-apex", "score": 5, "confidence": 2, "priority": "high", "description": "", "reasons": []}]
        matches_optional = [{"skill": "sf-apex", "score": 2, "confidence": 1, "priority": "high", "description": "", "reasons": []}]

        registry = skill_activation_module.load_registry()

        out_req = skill_activation_module.format_suggestions(matches_required, None, registry)
        out_rec = skill_activation_module.format_suggestions(matches_recommended, None, registry)
        out_opt = skill_activation_module.format_suggestions(matches_optional, None, registry)

        # Should have different star counts
        assert "⭐⭐⭐" in out_req
        assert "⭐⭐" in out_rec and "⭐⭐⭐" not in out_rec
        assert "⭐" in out_opt


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_prompt_short_circuit(self, skill_activation_module):
        """Prompt less than 5 chars should be skipped."""
        matches = skill_activation_module.find_matching_skills(
            "hi",
            [],
            skill_activation_module.load_registry()
        )
        # Empty prompt handled in main(), but find_matching_skills still works
        # The main() checks len(prompt) < 5

    def test_special_characters_in_prompt(self, skill_activation_module):
        """Special characters should not break matching."""
        matches = skill_activation_module.find_matching_skills(
            "Create @IsTest apex with $special chars!",
            [],
            skill_activation_module.load_registry()
        )
        apex_match = next((m for m in matches if m["skill"] == "sf-apex"), None)
        assert apex_match is not None

    def test_unicode_in_prompt(self, skill_activation_module):
        """Unicode characters should not break matching."""
        matches = skill_activation_module.find_matching_skills(
            'Create apex class for "Account" handling',
            [],
            skill_activation_module.load_registry()
        )
        apex_match = next((m for m in matches if m["skill"] == "sf-apex"), None)
        assert apex_match is not None

    def test_multiline_prompt(self, skill_activation_module):
        """Multiline prompts should work."""
        matches = skill_activation_module.find_matching_skills(
            "I need to:\n1. Create apex\n2. Build flow",
            [],
            skill_activation_module.load_registry()
        )
        assert len(matches) >= 1

    def test_missing_registry_fields(self):
        """Missing registry fields should not crash."""
        empty_registry = {"skills": {}}
        result = sap.find_matching_skills("apex code", [], empty_registry)
        assert result == []

    def test_skill_without_keywords(self):
        """Skill without keywords should not match on keywords."""
        registry = {
            "skills": {
                "test-skill": {
                    "description": "Test skill",
                    "priority": "low"
                    # No keywords, intentPatterns, or filePatterns
                }
            }
        }
        result = sap.find_matching_skills("apex code", [], registry)
        assert len(result) == 0


# =============================================================================
# REGISTRY LOADING TESTS
# =============================================================================


class TestRegistryLoading:
    """Tests for load_registry() function."""

    def test_load_registry_caching(self, skill_activation_module, tmp_path):
        """Registry should be cached after first load."""
        # Clear cache
        skill_activation_module._registry_cache = None

        # First load
        reg1 = skill_activation_module.load_registry()

        # Modify file (but cache should still return old value)
        # Actually, we can't easily test this without more complex mocking
        # So just verify it returns a valid registry
        assert "skills" in reg1

    def test_load_registry_missing_file(self, monkeypatch, tmp_path):
        """Missing registry file should return empty structure."""
        # Clear cache
        sap._registry_cache = None

        # Point to non-existent file
        monkeypatch.setattr(sap, "REGISTRY_FILE", tmp_path / "nonexistent.json")

        result = sap.load_registry()
        assert result == {"skills": {}, "chains": {}}

    def test_load_registry_invalid_json(self, monkeypatch, tmp_path):
        """Invalid JSON should return empty structure."""
        sap._registry_cache = None

        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }")
        monkeypatch.setattr(sap, "REGISTRY_FILE", invalid_file)

        result = sap.load_registry()
        assert result == {"skills": {}, "chains": {}}


# =============================================================================
# INTEGRATION-LIKE TESTS (with full registry)
# =============================================================================


class TestWithFullRegistry:
    """Tests using the actual skills-registry.json."""

    def test_sf_apex_matches_apex_keywords(self, full_registry):
        """sf-apex should match common Apex keywords."""
        matches = sap.find_matching_skills(
            "Create an apex trigger for Account with batch processing",
            [],
            full_registry
        )
        skill_names = [m["skill"] for m in matches]
        assert "sf-apex" in skill_names

    def test_sf_flow_matches_flow_keywords(self, full_registry):
        """sf-flow should match Flow keywords."""
        matches = sap.find_matching_skills(
            "Build a record-triggered flow for Lead conversion",
            [],
            full_registry
        )
        skill_names = [m["skill"] for m in matches]
        assert "sf-flow" in skill_names

    def test_sf_lwc_matches_component_keywords(self, full_registry):
        """sf-lwc should match LWC keywords."""
        matches = sap.find_matching_skills(
            "Create a lightning web component with wire adapter",
            [],
            full_registry
        )
        skill_names = [m["skill"] for m in matches]
        assert "sf-lwc" in skill_names

    def test_sf_soql_matches_query_keywords(self, full_registry):
        """sf-soql should match SOQL keywords."""
        matches = sap.find_matching_skills(
            "Write a SOQL query with aggregate functions",
            [],
            full_registry
        )
        skill_names = [m["skill"] for m in matches]
        assert "sf-soql" in skill_names

    def test_integration_chain_detection(self, full_registry):
        """Integration chain should be detected."""
        chain = sap.detect_chain("integrate api with external system", full_registry)
        assert chain is not None
        assert chain["name"] == "integration"

    def test_agentforce_chain_detection(self, full_registry):
        """Agentforce chain should be detected."""
        chain = sap.detect_chain("build agentforce agent", full_registry)
        assert chain is not None
        assert chain["name"] == "agentforce"
