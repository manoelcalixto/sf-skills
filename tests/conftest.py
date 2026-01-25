"""
Shared pytest fixtures for sf-skills tests.

This module provides:
- Mock registry fixtures (minimal and full)
- stdin mocking utilities
- Temp file helpers for state tracking
"""

import importlib.util
import json
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

# Project root for locating files
PROJECT_ROOT = Path(__file__).parent.parent


def _load_skill_activation_module():
    """
    Load skill-activation-prompt.py module using importlib.
    The module has a hyphen in its filename, so we can't use regular import.
    """
    module_path = PROJECT_ROOT / "shared" / "hooks" / "skill-activation-prompt.py"
    spec = importlib.util.spec_from_file_location("skill_activation_prompt", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["skill_activation_prompt"] = module
    spec.loader.exec_module(module)
    return module


# Load the module once at import time
skill_activation_prompt = _load_skill_activation_module()


# =============================================================================
# REGISTRY FIXTURES
# =============================================================================


@pytest.fixture
def minimal_registry() -> Dict[str, Any]:
    """
    Minimal registry for fast, isolated tests.
    Contains only sf-apex and sf-flow for basic testing.
    """
    return {
        "version": "test",
        "skills": {
            "sf-apex": {
                "keywords": ["apex", "trigger", "class", "test class", "batch"],
                "intentPatterns": [
                    r"create.*apex",
                    r"write.*trigger",
                    r"implement.*batch",
                ],
                "filePatterns": [r"\.cls$", r"\.trigger$"],
                "priority": "high",
                "description": "Apex code development",
            },
            "sf-flow": {
                "keywords": ["flow", "screen flow", "record-triggered", "autolaunched"],
                "intentPatterns": [
                    r"create.*flow",
                    r"build.*automation",
                ],
                "filePatterns": [r"\.flow-meta\.xml$"],
                "priority": "high",
                "description": "Flow Builder automation",
            },
            "sf-lwc": {
                "keywords": ["lwc", "lightning web component", "wire"],
                "intentPatterns": [r"create.*component", r"build.*lwc"],
                "filePatterns": [r"lwc/[^/]+/[^/]+\.js$"],
                "priority": "high",
                "description": "Lightning Web Components",
            },
        },
        "chains": {
            "full_feature": {
                "description": "Complete feature development",
                "trigger_phrases": ["build feature", "end to end"],
                "order": ["sf-metadata", "sf-apex", "sf-flow"],
            },
        },
        "confidence_levels": {
            "3": {"label": "REQUIRED", "icon": "***"},
            "2": {"label": "RECOMMENDED", "icon": "**"},
            "1": {"label": "OPTIONAL", "icon": "*"},
        },
    }


@pytest.fixture
def full_registry() -> Dict[str, Any]:
    """
    Load the actual skills-registry.json for integration-like tests.
    """
    registry_path = PROJECT_ROOT / "shared" / "hooks" / "skills-registry.json"
    if registry_path.exists():
        with open(registry_path, "r") as f:
            return json.load(f)
    # Fallback to minimal if real registry not found
    return minimal_registry()


# =============================================================================
# STDIN MOCKING FIXTURES
# =============================================================================


@pytest.fixture
def mock_stdin():
    """
    Factory fixture to mock stdin with JSON input.

    Usage:
        def test_something(mock_stdin):
            mock_stdin({"prompt": "create apex class", "activeFiles": []})
            # Now sys.stdin.read() returns the JSON
    """
    original_stdin = sys.stdin

    def _mock(data: Dict[str, Any]):
        sys.stdin = StringIO(json.dumps(data))

    yield _mock

    sys.stdin = original_stdin


@pytest.fixture
def hook_input_factory():
    """
    Factory for creating hook input dicts with sensible defaults.

    Usage:
        def test_something(hook_input_factory):
            input_data = hook_input_factory(prompt="create apex class")
            input_data = hook_input_factory(active_files=["Account.cls"])
    """
    def _factory(
        prompt: str = "",
        active_files: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "prompt": prompt,
            "activeFiles": active_files or [],
            **kwargs,
        }

    return _factory


# =============================================================================
# STATE FILE FIXTURES
# =============================================================================


@pytest.fixture
def temp_state_file(tmp_path):
    """
    Provides a temporary state file path and cleanup.

    Returns a tuple: (state_file_path, write_function, read_function)
    """
    state_file = tmp_path / "sf-skills-active-skill.json"

    def write_state(skill_name: str, timestamp: Optional[str] = None):
        from datetime import datetime
        state = {
            "active_skill": skill_name,
            "timestamp": timestamp or datetime.now().isoformat(),
        }
        with open(state_file, "w") as f:
            json.dump(state, f)

    def read_state() -> Optional[Dict[str, Any]]:
        if state_file.exists():
            with open(state_file, "r") as f:
                return json.load(f)
        return None

    yield state_file, write_state, read_state


@pytest.fixture
def clean_state_file():
    """
    Ensures the global state file is clean before and after test.
    """
    state_file = Path("/tmp/sf-skills-active-skill.json")

    # Clean before
    if state_file.exists():
        state_file.unlink()

    yield state_file

    # Clean after
    if state_file.exists():
        state_file.unlink()


# =============================================================================
# MODULE IMPORT HELPERS
# =============================================================================


@pytest.fixture
def skill_activation_module(monkeypatch, minimal_registry, tmp_path):
    """
    Provide skill-activation-prompt.py module with mocked registry.

    This fixture:
    1. Creates a temp registry file
    2. Patches the REGISTRY_FILE constant
    3. Clears the module cache
    4. Returns the module for testing
    """
    # Write minimal registry to temp file
    registry_file = tmp_path / "skills-registry.json"
    with open(registry_file, "w") as f:
        json.dump(minimal_registry, f)

    # Use the pre-loaded module from conftest
    sap = skill_activation_prompt

    # Patch the registry file path and clear cache
    monkeypatch.setattr(sap, "REGISTRY_FILE", registry_file)
    monkeypatch.setattr(sap, "_registry_cache", None)

    # Also patch state file to temp location
    state_file = tmp_path / "active-skill.json"
    monkeypatch.setattr(sap, "ACTIVE_SKILL_FILE", state_file)

    return sap


# =============================================================================
# TEST DATA HELPERS
# =============================================================================


@pytest.fixture
def sample_prompts():
    """
    Collection of sample prompts for testing.
    Returns dict with categories of test prompts.
    """
    return {
        "apex_prompts": [
            "Create an Apex trigger for Account",
            "Write a batch class to process Opportunities",
            "I need to build a test class for ContactService",
            "Fix the apex code in AccountHandler",
        ],
        "flow_prompts": [
            "Create a record-triggered flow for Lead conversion",
            "Build an automation for updating Contact fields",
            "I want a screen flow to collect user input",
        ],
        "lwc_prompts": [
            "Create an LWC component for the Account page",
            "Build a lightning web component with wire",
        ],
        "chain_prompts": [
            "Build feature end to end for Account",
            "Complete feature implementation",
        ],
        "non_sf_prompts": [
            "Hello, how are you?",
            "What's the weather like?",
            "Help me write a Python script",
        ],
        "skill_invocations": [
            "/sf-apex",
            "/sf-flow",
            "/sf-lwc",
            "/sf-testing",
        ],
    }


@pytest.fixture
def sample_files():
    """
    Collection of sample file paths for testing file pattern matching.
    """
    return {
        "apex_files": [
            "force-app/main/default/classes/AccountService.cls",
            "src/classes/ContactTrigger.trigger",
            "AccountService.cls",
        ],
        "flow_files": [
            "force-app/main/default/flows/Account_Update.flow-meta.xml",
            "Update_Contact.flow-meta.xml",
        ],
        "lwc_files": [
            "force-app/main/default/lwc/accountCard/accountCard.js",
            "lwc/myComponent/myComponent.js",
        ],
        "non_sf_files": [
            "README.md",
            "package.json",
            "src/utils/helpers.js",
        ],
    }
