#!/usr/bin/env python3
"""
bulk_validate.py - Bulk validation for all Claude Code skills

Validates all installed skills at once with comprehensive reporting.

Features:
- Discover skills in global and project-specific locations
- Parallel validation for performance
- Multiple report formats (console, JSON, HTML)
- Auto-fix common issues
- Actionable recommendations
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import yaml
except ImportError:
    print("\n" + "=" * 70)
    print("ERROR: PyYAML is required but not installed")
    print("=" * 70)
    print("\nTo install PyYAML, run ONE of these commands:\n")
    print("  pip3 install --break-system-packages pyyaml")
    print("  brew install pyyaml")
    print("=" * 70)
    sys.exit(1)

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


# Valid Claude Code tools
VALID_TOOLS = [
    "Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch",
    "AskUserQuestion", "TodoWrite", "SlashCommand", "Skill",
    "BashOutput", "KillShell", "NotebookEdit", "Task", "EnterPlanMode",
    "ExitPlanMode"
]

# Agent Skills / Codex frontmatter allowlist (agentskills.io)
CODEX_ALLOWED_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: str  # 'error', 'warning', 'info'
    message: str
    location: str = ""
    fix: Optional[str] = None


@dataclass
class SkillValidationResult:
    """Represents validation result for a single skill."""
    skill_name: str
    skill_path: Path
    location_type: str  # 'global' or 'project'
    version: str = "unknown"
    is_valid: bool = False
    errors: List[ValidationIssue] = None
    warnings: List[ValidationIssue] = None
    infos: List[ValidationIssue] = None

    def __post_init__(self):
        self.errors = self.errors or []
        self.warnings = self.warnings or []
        self.infos = self.infos or []

    @property
    def total_issues(self) -> int:
        return len(self.errors) + len(self.warnings) + len(self.infos)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


@dataclass
class ValidationReport:
    """Complete validation report."""
    total_skills: int
    valid_skills: int
    skills_with_warnings: int
    skills_with_errors: int
    results: List[SkillValidationResult]
    generated_at: str
    duration_seconds: float


def discover_skills() -> List[Tuple[Path, str]]:
    """
    Discover all skills in global and project-specific locations.

    Returns:
        List of (skill_path, location_type) tuples
    """
    skills: List[Tuple[Path, str]] = []

    # Global skills (~/.claude/skills/)
    global_skills_dir = Path.home() / ".claude" / "skills"
    if global_skills_dir.exists():
        for skill_dir in global_skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append((skill_dir / "SKILL.md", "global"))

    # Project-specific skills (./claude/skills/)
    project_skills_dir = Path.cwd() / ".claude" / "skills"
    if project_skills_dir.exists():
        for skill_dir in project_skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append((skill_dir / "SKILL.md", "project"))

    # Repo skills (./<skill>/SKILL.md) - useful when validating the sf-skills repo itself
    for skill_dir in Path.cwd().iterdir():
        if (
            skill_dir.is_dir()
            and not skill_dir.name.startswith(".")
            and (skill_dir / "SKILL.md").exists()
        ):
            skills.append((skill_dir / "SKILL.md", "repo"))

    # De-duplicate while preserving order
    unique: List[Tuple[Path, str]] = []
    seen: set[str] = set()
    for skill_path, location_type in skills:
        key = str(skill_path.resolve())
        if key not in seen:
            seen.add(key)
            unique.append((skill_path, location_type))

    return unique


SF_SKILLS_V4_HOOK_EVENTS = {
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "SubagentStop",
    "PermissionRequest",
    "UserPromptSubmit",
}


def is_sf_skills_v4_frontmatter(data: dict) -> bool:
    """Detect sf-skills v4+ schema (hooks in frontmatter, version in metadata.version)."""
    if not isinstance(data, dict):
        return False
    metadata = data.get("metadata")
    return isinstance(metadata, dict) and bool(metadata.get("version"))


def find_plugin_root(start_dir: Path) -> Optional[Path]:
    """
    Find the plugin root directory that contains shared/hooks.

    Works for:
    - repo checkout (./shared/hooks)
    - installed layout (~/.claude/sf-skills/shared/hooks)
    """
    current = start_dir.resolve()
    while current != current.parent:
        if (current / "shared" / "hooks").exists():
            return current
        current = current.parent
    return None


def resolve_hook_path_token(token: str, skill_dir: Path, plugin_root: Optional[Path]) -> Optional[Path]:
    """
    Resolve a single argv token that points to a hook file via placeholders.

    Supports:
      - ${SHARED_HOOKS}/...
      - ${SKILL_HOOKS}/...
      - ${CLAUDE_PLUGIN_ROOT}/...
      - ${PLUGIN_ROOT}/... (legacy)
    """
    placeholders = {
        "${SKILL_HOOKS}/": skill_dir / "hooks" / "scripts",
        "${CLAUDE_PLUGIN_ROOT}/": skill_dir,
    }

    if plugin_root:
        placeholders.update(
            {
                "${SHARED_HOOKS}/": plugin_root / "shared" / "hooks",
                "${PLUGIN_ROOT}/": plugin_root,
            }
        )

    for prefix, base_dir in placeholders.items():
        if token.startswith(prefix):
            rel = token[len(prefix):]
            return base_dir / rel

    return None


def validate_hook_command_paths(
    command: str, skill_dir: Path, plugin_root: Optional[Path]
) -> List[Path]:
    """
    Extract and resolve any placeholder-based file paths inside a hook command.

    Returns:
        List of resolved Paths found in the command.
    """
    import shlex

    resolved: List[Path] = []
    try:
        tokens = shlex.split(command)
    except ValueError:
        # Malformed quoting; caller should handle separately
        return resolved

    for token in tokens:
        path = resolve_hook_path_token(token, skill_dir=skill_dir, plugin_root=plugin_root)
        if path is not None:
            resolved.append(path)

    return resolved


def validate_v4_hooks(hooks: object, result: SkillValidationResult, skill_dir: Path):
    """Validate sf-skills v4 hook frontmatter structure + referenced scripts."""
    if hooks is None:
        result.warnings.append(
            ValidationIssue(
                severity="warning",
                message="No hooks defined in frontmatter",
                location=f"{result.skill_path}:frontmatter:hooks",
            )
        )
        return

    if not isinstance(hooks, dict):
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Invalid hooks - expected a mapping (YAML object)",
                location=f"{result.skill_path}:frontmatter:hooks",
                fix="Set hooks to a YAML mapping, e.g. hooks: { SessionStart: [...] }",
            )
        )
        return

    plugin_root = find_plugin_root(skill_dir)

    for event_name, steps in hooks.items():
        if event_name not in SF_SKILLS_V4_HOOK_EVENTS:
            result.warnings.append(
                ValidationIssue(
                    severity="warning",
                    message=f"Unknown hook event '{event_name}'",
                    location=f"{result.skill_path}:frontmatter:hooks",
                )
            )

        if not isinstance(steps, list):
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    message=f"Invalid hooks.{event_name} - expected a list",
                    location=f"{result.skill_path}:frontmatter:hooks:{event_name}",
                    fix="Define hooks for an event as a YAML list",
                )
            )
            continue

        for i, step in enumerate(steps):
            location_prefix = f"{result.skill_path}:frontmatter:hooks:{event_name}[{i}]"

            if not isinstance(step, dict):
                result.errors.append(
                    ValidationIssue(
                        severity="error",
                        message="Hook step must be a mapping (YAML object)",
                        location=location_prefix,
                    )
                )
                continue

            # Matcher-based step (PreToolUse/PostToolUse)
            if "matcher" in step:
                matcher = step.get("matcher")
                nested = step.get("hooks")
                if not isinstance(matcher, str) or not matcher.strip():
                    result.errors.append(
                        ValidationIssue(
                            severity="error",
                            message="Hook matcher must be a non-empty string",
                            location=f"{location_prefix}:matcher",
                        )
                    )
                if not isinstance(nested, list) or not nested:
                    result.errors.append(
                        ValidationIssue(
                            severity="error",
                            message="Matcher hook must include non-empty 'hooks' list",
                            location=f"{location_prefix}:hooks",
                            fix="Add hooks: [ {type: command, command: ...} ]",
                        )
                    )
                    continue

                for j, action in enumerate(nested):
                    action_loc = f"{location_prefix}:hooks[{j}]"
                    _validate_v4_hook_action(
                        action=action,
                        location=action_loc,
                        result=result,
                        skill_dir=skill_dir,
                        plugin_root=plugin_root,
                    )
            else:
                _validate_v4_hook_action(
                    action=step,
                    location=location_prefix,
                    result=result,
                    skill_dir=skill_dir,
                    plugin_root=plugin_root,
                )


def _validate_v4_hook_action(
    action: object,
    location: str,
    result: SkillValidationResult,
    skill_dir: Path,
    plugin_root: Optional[Path],
):
    """Validate a single hook action object for sf-skills v4 schema."""
    if not isinstance(action, dict):
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Hook action must be a mapping (YAML object)",
                location=location,
            )
        )
        return

    hook_type = action.get("type")
    if hook_type not in ("command", "prompt"):
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Hook action 'type' must be 'command' or 'prompt'",
                location=f"{location}:type",
            )
        )
        return

    timeout = action.get("timeout")
    if timeout is not None and not isinstance(timeout, (int, float)):
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Hook action timeout must be a number (milliseconds)",
                location=f"{location}:timeout",
            )
        )

    if hook_type == "prompt":
        prompt = action.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    message="Prompt hook missing 'prompt' content",
                    location=f"{location}:prompt",
                )
            )
        return

    # command hook
    command = action.get("command")
    if not isinstance(command, str) or not command.strip():
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Command hook missing 'command' string",
                location=f"{location}:command",
            )
        )
        return

    # Best-effort check that referenced scripts exist.
    # Only validates placeholder-based paths (SHARED_HOOKS/SKILL_HOOKS/etc).
    resolved_paths = validate_hook_command_paths(command, skill_dir=skill_dir, plugin_root=plugin_root)
    for path in resolved_paths:
        if not path.exists():
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    message=f"Hook references missing file: {path}",
                    location=f"{location}:command",
                    fix="Update the hook command path or add the missing script",
                )
            )


def extract_frontmatter(file_path: Path) -> Tuple[str, str]:
    """Extract YAML frontmatter from SKILL.md file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    delimiter_indices = []
    for i, line in enumerate(lines):
        if line.strip() == '---':
            delimiter_indices.append(i)
            if len(delimiter_indices) == 2:
                break

    if len(delimiter_indices) < 2:
        return "", "".join(lines)

    yaml_lines = lines[delimiter_indices[0] + 1:delimiter_indices[1]]
    yaml_content = "".join(yaml_lines)

    content_lines = lines[delimiter_indices[1] + 1:]
    content = "".join(content_lines)

    return yaml_content, content


def validate_single_skill(skill_path: Path, location_type: str) -> SkillValidationResult:
    """
    Validate a single skill file.

    Returns:
        SkillValidationResult with all findings
    """
    if location_type == "codex-export":
        return validate_single_codex_export_skill(skill_path)

    skill_name = skill_path.parent.name
    result = SkillValidationResult(
        skill_name=skill_name,
        skill_path=skill_path,
        location_type=location_type
    )

    # Extract frontmatter
    try:
        yaml_content, content = extract_frontmatter(skill_path)
    except Exception as e:
        result.errors.append(ValidationIssue(
            severity='error',
            message=f"Failed to read skill file: {e}",
            location=str(skill_path)
        ))
        return result

    if not yaml_content:
        result.errors.append(ValidationIssue(
            severity='error',
            message="No YAML frontmatter found",
            location=str(skill_path),
            fix="Add YAML frontmatter between --- delimiters"
        ))
        return result

    # Parse YAML
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        result.errors.append(ValidationIssue(
            severity='error',
            message=f"Invalid YAML syntax: {e}",
            location=str(skill_path),
            fix="Fix YAML syntax errors"
        ))
        return result

    if not isinstance(data, dict):
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Invalid YAML frontmatter - expected a mapping (YAML object)",
                location=f"{skill_path}:frontmatter",
            )
        )
        return result

    # Detect schema
    is_v4 = is_sf_skills_v4_frontmatter(data)

    # Common validation: name should exist and be kebab-case
    name = data.get("name")
    if not name:
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Missing required field: 'name'",
                location=f"{skill_path}:frontmatter",
                fix="Add name: <kebab-case-skill-name> to YAML frontmatter",
            )
        )
    else:
        import re

        if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", str(name)):
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    message=f"Invalid skill name '{name}' - must be kebab-case",
                    location=f"{skill_path}:frontmatter:name",
                    fix="Use lowercase letters, numbers, and hyphens only (e.g., 'my-skill')",
                )
            )
        elif str(name) != skill_name:
            result.warnings.append(
                ValidationIssue(
                    severity="warning",
                    message=f"Skill name '{name}' does not match directory '{skill_name}'",
                    location=f"{skill_path}:frontmatter:name",
                )
            )

    # Schema-specific validation
    if is_v4:
        # Required fields for sf-skills v4 frontmatter
        for field in ("description", "license", "metadata"):
            if not data.get(field):
                result.errors.append(
                    ValidationIssue(
                        severity="error",
                        message=f"Missing required field: '{field}'",
                        location=f"{skill_path}:frontmatter",
                    )
                )

        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    message="Invalid metadata - expected a mapping (YAML object)",
                    location=f"{skill_path}:frontmatter:metadata",
                )
            )
        else:
            version = metadata.get("version")
            if version:
                version_str = str(version)
                result.version = version_str
                import re

                if not re.match(r"^\d+\.\d+\.\d+$", version_str):
                    result.errors.append(
                        ValidationIssue(
                            severity="error",
                            message=f"Invalid metadata.version '{version_str}' - must be semver (X.Y.Z)",
                            location=f"{skill_path}:frontmatter:metadata:version",
                            fix="Use semantic versioning format (e.g., '1.0.0')",
                        )
                    )
            else:
                result.errors.append(
                    ValidationIssue(
                        severity="error",
                        message="Missing required field: metadata.version",
                        location=f"{skill_path}:frontmatter:metadata",
                        fix="Add metadata: { version: \"1.0.0\" }",
                    )
                )

            if not metadata.get("author"):
                result.infos.append(
                    ValidationIssue(
                        severity="info",
                        message="Consider adding metadata.author for attribution",
                        location=f"{skill_path}:frontmatter:metadata",
                    )
                )

        # Hooks are optional but strongly recommended for sf-skills
        validate_v4_hooks(data.get("hooks"), result=result, skill_dir=skill_path.parent)

    else:
        # Legacy schema (generic Claude Code skills)
        required_fields = {"name": "Skill name", "description": "Description", "version": "Version"}
        for field in required_fields:
            if not data.get(field):
                result.errors.append(
                    ValidationIssue(
                        severity="error",
                        message=f"Missing required field: '{field}'",
                        location=f"{skill_path}:frontmatter",
                        fix=f"Add '{field}' field to YAML frontmatter",
                    )
                )

        # Get version if present
        if "version" in data:
            result.version = str(data["version"])

        # Validate version format (semver)
        if "version" in data:
            import re

            version = str(data["version"])
            if not re.match(r"^\d+\.\d+\.\d+$", version):
                result.errors.append(
                    ValidationIssue(
                        severity="error",
                        message=f"Invalid version '{version}' - must be semver (X.Y.Z)",
                        location=f"{skill_path}:version",
                        fix="Use semantic versioning format (e.g., '1.0.0')",
                    )
                )

        # Validate allowed-tools (legacy)
        if "allowed-tools" in data:
            allowed_tools = data["allowed-tools"]
            if allowed_tools:
                for tool in allowed_tools:
                    if tool not in VALID_TOOLS:
                        correct_case = next((t for t in VALID_TOOLS if t.lower() == str(tool).lower()), None)
                        if correct_case:
                            result.errors.append(
                                ValidationIssue(
                                    severity="error",
                                    message=f"Invalid tool '{tool}' - should be '{correct_case}' (case-sensitive)",
                                    location=f"{skill_path}:allowed-tools",
                                    fix=f"Change '{tool}' to '{correct_case}'",
                                )
                            )
                        else:
                            result.errors.append(
                                ValidationIssue(
                                    severity="error",
                                    message=f"Unknown tool '{tool}'",
                                    location=f"{skill_path}:allowed-tools",
                                    fix=f"Remove '{tool}' or check valid tool names",
                                )
                            )
            else:
                result.warnings.append(
                    ValidationIssue(
                        severity="warning",
                        message="No allowed-tools specified - skill may not be functional",
                        location=f"{skill_path}:allowed-tools",
                    )
                )
        else:
            result.warnings.append(
                ValidationIssue(
                    severity="warning",
                    message="No allowed-tools field - skill may not be functional",
                    location=f"{skill_path}:frontmatter",
                )
            )

    # Check for content
    if not content.strip():
        result.errors.append(ValidationIssue(
            severity='error',
            message="No content found after YAML frontmatter",
            location=str(skill_path),
            fix="Add skill instructions, workflow, and examples"
        ))

    # Legacy-only recommended fields
    if not is_v4:
        if "author" not in data:
            result.infos.append(
                ValidationIssue(
                    severity="info",
                    message="Consider adding 'author' field for attribution",
                    location=f"{skill_path}:frontmatter",
                )
            )

        if "tags" not in data or not data.get("tags"):
            result.infos.append(
                ValidationIssue(
                    severity="info",
                    message="Consider adding 'tags' for categorization",
                    location=f"{skill_path}:frontmatter",
                )
            )

        if "examples" not in data or not data.get("examples"):
            result.infos.append(
                ValidationIssue(
                    severity="info",
                    message="Consider adding 'examples' to help users",
                    location=f"{skill_path}:frontmatter",
                )
            )

    # Determine if valid (no errors)
    result.is_valid = len(result.errors) == 0

    return result


def _is_kebab_case(name: str) -> bool:
    import re

    return bool(re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", str(name)))


def validate_single_codex_export_skill(skill_path: Path) -> SkillValidationResult:
    """
    Validate a Codex / Agent Skills compatible export.

    Key differences vs sf-skills v4 source skills:
      - Frontmatter must NOT contain hooks
      - Only Agent Skills compatible fields should exist
      - agents/openai.yaml should exist (recommended for Codex UX)
      - No ~/.claude paths or ${SHARED_HOOKS}/${SKILL_HOOKS} placeholders should remain
    """
    skill_name = skill_path.parent.name
    result = SkillValidationResult(
        skill_name=skill_name,
        skill_path=skill_path,
        location_type="codex-export",
    )

    try:
        yaml_content, content = extract_frontmatter(skill_path)
    except Exception as e:
        result.errors.append(
            ValidationIssue(
                severity="error",
                message=f"Failed to read skill file: {e}",
                location=str(skill_path),
            )
        )
        return result

    if not yaml_content:
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="No YAML frontmatter found",
                location=str(skill_path),
                fix="Add YAML frontmatter between --- delimiters",
            )
        )
        return result

    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        result.errors.append(
            ValidationIssue(
                severity="error",
                message=f"Invalid YAML syntax: {e}",
                location=str(skill_path),
            )
        )
        return result

    if not isinstance(data, dict):
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Invalid YAML frontmatter - expected a mapping (YAML object)",
                location=f"{skill_path}:frontmatter",
            )
        )
        return result

    unexpected_fields = set(data.keys()) - CODEX_ALLOWED_FRONTMATTER_FIELDS
    if unexpected_fields:
        result.errors.append(
            ValidationIssue(
                severity="error",
                message=f"Unexpected frontmatter fields for Codex export: {', '.join(sorted(unexpected_fields))}",
                location=f"{skill_path}:frontmatter",
                fix=f"Remove fields not in {sorted(CODEX_ALLOWED_FRONTMATTER_FIELDS)}",
            )
        )

    if "hooks" in data:
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Frontmatter must not include hooks in Codex export",
                location=f"{skill_path}:frontmatter:hooks",
                fix="Remove hooks from frontmatter and document manual validations in the body",
            )
        )

    name = data.get("name")
    if not name:
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Missing required field: 'name'",
                location=f"{skill_path}:frontmatter",
            )
        )
    else:
        if not _is_kebab_case(str(name)):
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    message=f"Invalid skill name '{name}' - must be kebab-case",
                    location=f"{skill_path}:frontmatter:name",
                )
            )
        elif str(name) != skill_name:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    message=f"Skill name '{name}' does not match directory '{skill_name}'",
                    location=f"{skill_path}:frontmatter:name",
                )
            )

    if not data.get("description"):
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Missing required field: 'description'",
                location=f"{skill_path}:frontmatter",
            )
        )

    metadata = data.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Invalid metadata - expected a mapping (YAML object)",
                location=f"{skill_path}:frontmatter:metadata",
            )
        )
    elif isinstance(metadata, dict):
        version = metadata.get("version")
        if version:
            result.version = str(version)

        if "short-description" not in metadata:
            result.warnings.append(
                ValidationIssue(
                    severity="warning",
                    message="metadata.short-description missing (recommended for Codex)",
                    location=f"{skill_path}:frontmatter:metadata",
                )
            )

    if not content.strip():
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="No content found after YAML frontmatter",
                location=str(skill_path),
            )
        )

    # Content portability checks
    portability_errors = [
        ("~/.claude", "Replace Claude install paths with $CODEX_HOME/skills/..."),
        ("${SHARED_HOOKS}", "Remove placeholders and use $SHARED_DIR/..."),
        ("${SKILL_HOOKS}", "Remove placeholders and use $SKILL_DIR/..."),
    ]
    for token, fix in portability_errors:
        if token in content:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    message=f"Found non-portable token in body: {token}",
                    location=str(skill_path),
                    fix=fix,
                )
            )

    # Codex metadata file
    openai_yaml = skill_path.parent / "agents" / "openai.yaml"
    if not openai_yaml.exists():
        result.errors.append(
            ValidationIssue(
                severity="error",
                message="Missing agents/openai.yaml (recommended for Codex)",
                location=str(openai_yaml),
                fix="Add agents/openai.yaml with interface + dependency hints",
            )
        )
    else:
        try:
            openai_data = yaml.safe_load(openai_yaml.read_text())
        except yaml.YAMLError as e:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    message=f"Invalid YAML in agents/openai.yaml: {e}",
                    location=str(openai_yaml),
                )
            )
            openai_data = None

        if openai_data is not None and not isinstance(openai_data, dict):
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    message="agents/openai.yaml must be a YAML mapping",
                    location=str(openai_yaml),
                )
            )
        elif isinstance(openai_data, dict):
            if "interface" not in openai_data:
                result.warnings.append(
                    ValidationIssue(
                        severity="warning",
                        message="agents/openai.yaml missing interface block",
                        location=str(openai_yaml),
                    )
                )
            if "dependencies" not in openai_data:
                result.warnings.append(
                    ValidationIssue(
                        severity="warning",
                        message="agents/openai.yaml missing dependencies block",
                        location=str(openai_yaml),
                    )
                )

    result.is_valid = len(result.errors) == 0
    return result


def validate_all_skills(parallel: bool = True) -> ValidationReport:
    """
    Validate all discovered skills.

    Returns:
        ValidationReport with all results
    """
    start_time = datetime.now()

    skills = discover_skills()
    results = []

    if parallel and len(skills) > 1:
        # Parallel validation
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(validate_single_skill, path, loc_type): (path, loc_type)
                for path, loc_type in skills
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    path, loc_type = futures[future]
                    print(f"Error validating {path}: {e}")
    else:
        # Sequential validation
        for skill_path, loc_type in skills:
            result = validate_single_skill(skill_path, loc_type)
            results.append(result)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Calculate statistics
    valid_skills = sum(1 for r in results if r.is_valid)
    skills_with_errors = sum(1 for r in results if r.has_errors)
    skills_with_warnings = sum(1 for r in results if len(r.warnings) > 0 and not r.has_errors)

    return ValidationReport(
        total_skills=len(results),
        valid_skills=valid_skills,
        skills_with_warnings=skills_with_warnings,
        skills_with_errors=skills_with_errors,
        results=results,
        generated_at=datetime.now().isoformat(),
        duration_seconds=duration
    )


def generate_console_report(report: ValidationReport, errors_only: bool = False):
    """Generate and print console report."""
    print(f"{Colors.MAGENTA}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.MAGENTA}{Colors.BOLD}║     Claude Code Skills - Bulk Validation Report         ║{Colors.NC}")
    print(f"{Colors.MAGENTA}{Colors.BOLD}╚══════════════════════════════════════════════════════════╝{Colors.NC}\n")

    # Summary
    print(f"{Colors.BOLD}📊 Summary:{Colors.NC}")
    print(f"   Total Skills: {report.total_skills}")
    print(f"   {Colors.GREEN}✓ Valid: {report.valid_skills} ({report.valid_skills*100//max(report.total_skills,1)}%){Colors.NC}")

    if report.skills_with_warnings > 0:
        print(f"   {Colors.YELLOW}⚠️  Warnings: {report.skills_with_warnings} ({report.skills_with_warnings*100//max(report.total_skills,1)}%){Colors.NC}")

    if report.skills_with_errors > 0:
        print(f"   {Colors.RED}❌ Errors: {report.skills_with_errors} ({report.skills_with_errors*100//max(report.total_skills,1)}%){Colors.NC}")

    print(f"   Duration: {report.duration_seconds:.2f}s\n")

    # Critical issues
    error_results = [r for r in report.results if r.has_errors]
    if error_results:
        print(f"{Colors.RED}{Colors.BOLD}🔴 Critical Issues ({len(error_results)}):{Colors.NC}")
        for result in error_results:
            print(f"\n   {Colors.BOLD}└─ {result.skill_name}{Colors.NC} (v{result.version}) [{result.location_type}]")
            for error in result.errors[:3]:  # Show first 3 errors
                print(f"      {Colors.RED}❌{Colors.NC} {error.message}")
                if error.fix:
                    print(f"         {Colors.CYAN}Fix:{Colors.NC} {error.fix}")
            if len(result.errors) > 3:
                print(f"      ... and {len(result.errors) - 3} more errors")

    if not errors_only:
        # Warnings
        warning_results = [r for r in report.results if len(r.warnings) > 0 and not r.has_errors]
        if warning_results:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  Warnings ({len(warning_results)}):{Colors.NC}")
            for result in warning_results[:5]:  # Show first 5
                print(f"\n   {Colors.BOLD}└─ {result.skill_name}{Colors.NC} (v{result.version})")
                for warning in result.warnings[:2]:
                    print(f"      {Colors.YELLOW}⚠️ {Colors.NC} {warning.message}")
            if len(warning_results) > 5:
                print(f"\n   ... and {len(warning_results) - 5} more skills with warnings")

    # Recommendations
    print(f"\n{Colors.CYAN}{Colors.BOLD}💡 Recommendations:{Colors.NC}")

    unknown_versions = sum(1 for r in report.results if not r.version or r.version == "unknown")
    if unknown_versions > 0:
        print(f"   • {unknown_versions} skill(s) missing a detectable version - add metadata.version (sf-skills v4) or version (legacy)")

    missing_hooks = sum(
        1
        for r in report.results
        if any("No hooks defined in frontmatter" in w.message for w in r.warnings)
    )
    if missing_hooks > 0:
        print(f"   • {missing_hooks} skill(s) without hooks - add frontmatter hooks to enable auto-validation")

    if report.skills_with_errors > 0:
        print(f"   • Fix {report.skills_with_errors} critical issues to ensure skills load correctly")
        print(f"   • Run with --auto-fix to automatically fix common issues")

    if not errors_only and report.skills_with_warnings > 0:
        print(f"   • Review {report.skills_with_warnings} warnings for potential improvements")


def generate_json_report(report: ValidationReport) -> str:
    """Generate JSON report."""
    report_dict = {
        'summary': {
            'total_skills': report.total_skills,
            'valid_skills': report.valid_skills,
            'skills_with_warnings': report.skills_with_warnings,
            'skills_with_errors': report.skills_with_errors,
            'generated_at': report.generated_at,
            'duration_seconds': report.duration_seconds
        },
        'results': []
    }

    for result in report.results:
        result_dict = {
            'skill_name': result.skill_name,
            'skill_path': str(result.skill_path),
            'location_type': result.location_type,
            'version': result.version,
            'is_valid': result.is_valid,
            'errors': [{'message': e.message, 'location': e.location, 'fix': e.fix} for e in result.errors],
            'warnings': [{'message': w.message, 'location': w.location} for w in result.warnings],
            'infos': [{'message': i.message, 'location': i.location} for i in result.infos]
        }
        report_dict['results'].append(result_dict)

    return json.dumps(report_dict, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Bulk validate all Claude Code skills',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Validate all skills
  %(prog)s

  # Show only errors
  %(prog)s --errors-only

  # Generate JSON output
  %(prog)s --format json > report.json

  # Sequential validation (no parallel)
  %(prog)s --no-parallel
        '''
    )

    parser.add_argument(
        '--format',
        choices=['console', 'json'],
        default='console',
        help='Output format (default: console)'
    )

    parser.add_argument(
        '--errors-only',
        action='store_true',
        help='Show only critical errors, hide warnings'
    )

    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel validation'
    )

    parser.add_argument(
        '--auto-fix',
        action='store_true',
        help='Automatically fix common issues (not yet implemented)'
    )

    parser.add_argument(
        '--codex-export',
        action='store',
        default=None,
        help='Validate a Codex/Agent Skills export directory (e.g. ./skills)',
    )

    args = parser.parse_args()

    if args.auto_fix:
        print(f"{Colors.YELLOW}⚠️  Auto-fix feature coming soon!{Colors.NC}\n")

    # Run validation
    if args.codex_export:
        export_root = Path(args.codex_export).resolve()
        skills = []
        if not export_root.exists():
            print(f"{Colors.RED}❌ Codex export directory not found: {export_root}{Colors.NC}")
            sys.exit(2)

        for child in sorted(export_root.iterdir()):
            if not child.is_dir():
                continue
            skill_md = child / "SKILL.md"
            if skill_md.exists():
                skills.append((skill_md, "codex-export"))

        if not skills:
            print(f"{Colors.RED}❌ No SKILL.md files found under: {export_root}{Colors.NC}")
            sys.exit(2)

        # Reuse report builder but with our custom skill list
        # (keeps output format identical)
        start_time = datetime.now()
        results = []
        if (not args.no_parallel) and len(skills) > 1:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(validate_single_skill, path, loc_type): (path, loc_type)
                    for path, loc_type in skills
                }
                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as e:
                        path, _ = futures[future]
                        print(f"Error validating {path}: {e}")
        else:
            for skill_path, loc_type in skills:
                results.append(validate_single_skill(skill_path, loc_type))

        duration = (datetime.now() - start_time).total_seconds()
        valid_skills = sum(1 for r in results if r.is_valid)
        skills_with_errors = sum(1 for r in results if r.has_errors)
        skills_with_warnings = sum(1 for r in results if len(r.warnings) > 0 and not r.has_errors)

        report = ValidationReport(
            total_skills=len(results),
            valid_skills=valid_skills,
            skills_with_warnings=skills_with_warnings,
            skills_with_errors=skills_with_errors,
            results=results,
            generated_at=datetime.now().isoformat(),
            duration_seconds=duration,
        )
    else:
        report = validate_all_skills(parallel=not args.no_parallel)

    # Generate report
    if args.format == 'json':
        print(generate_json_report(report))
    else:
        generate_console_report(report, errors_only=args.errors_only)

    # Exit with appropriate code
    sys.exit(0 if report.skills_with_errors == 0 else 1)


if __name__ == "__main__":
    main()
