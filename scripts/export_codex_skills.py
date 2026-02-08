#!/usr/bin/env python3
"""
export_codex_skills.py

Generate a Codex / Agent Skills compatible export of this repository's skills.

Source of truth:
  - Top-level sf-* skill folders (each contains SKILL.md + scripts/resources)

Export layout (default: ./skills):
  skills/
    shared/               # shared scripts copied from ./shared/
    sf-apex/
      SKILL.md            # clean frontmatter (no hooks)
      agents/openai.yaml  # Codex UI metadata + dependency hints
      hooks/, templates/, docs/, resources/, scripts/, validation/, examples/ (copied)
    ...

Notes:
  - The export removes `hooks:` from SKILL.md frontmatter (Agent Skills spec).
  - It rewrites common Claude-specific installation paths (e.g. ~/.claude/...) to
    Codex paths (e.g. $CODEX_HOME/skills/...).
  - It adds a small "Codex Notes" prelude to each exported SKILL.md.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Install with: pip3 install pyyaml"
    ) from exc


ALLOWED_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}


SKILL_COPY_DIRS = (
    "docs",
    "resources",
    "templates",
    "hooks",
    "scripts",
    "examples",
    "validation",
)


SHARED_COPY_DIRS = (
    ("hooks", "hooks"),
    ("lsp-engine", "lsp-engine"),
    ("code_analyzer", "code_analyzer"),
)


@dataclass(frozen=True)
class ExportResult:
    exported: List[str]
    warnings: List[str]


def _extract_frontmatter_and_body(content: str, source_path: Path) -> Tuple[Dict[str, Any], str]:
    if not content.startswith("---"):
        raise ValueError(f"{source_path}: SKILL.md must start with YAML frontmatter (---)")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{source_path}: SKILL.md frontmatter not properly closed with ---")

    frontmatter_raw = parts[1]
    body = parts[2].lstrip("\n")

    data = yaml.safe_load(frontmatter_raw) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{source_path}: frontmatter must be a YAML mapping")

    return data, body


def _sanitize_single_line(text: str) -> str:
    return " ".join(str(text).strip().split())


def _derive_short_description(name: str, description: str) -> str:
    desc = _sanitize_single_line(description)
    if not desc:
        return name
    m = re.match(r"^(.{1,220}?)(?:\\.|$)", desc)
    short = m.group(1) if m else desc
    return short.strip()


def _coerce_metadata_to_str_map(metadata: Any) -> Dict[str, str]:
    if not isinstance(metadata, dict):
        return {}
    coerced: Dict[str, str] = {}
    for key, value in metadata.items():
        coerced[str(key)] = _sanitize_single_line(value)
    return coerced


def _build_clean_frontmatter(frontmatter: Dict[str, Any], source_path: Path) -> Dict[str, Any]:
    name = frontmatter.get("name")
    description = frontmatter.get("description")

    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{source_path}: missing/invalid frontmatter field: name")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"{source_path}: missing/invalid frontmatter field: description")

    license_value = frontmatter.get("license")
    if license_value is not None and not isinstance(license_value, str):
        license_value = str(license_value)

    clean_metadata = _coerce_metadata_to_str_map(frontmatter.get("metadata"))
    if "short-description" not in clean_metadata:
        clean_metadata["short-description"] = _derive_short_description(name, description)

    clean: Dict[str, Any] = {
        "name": _sanitize_single_line(name),
        "description": _sanitize_single_line(description),
    }
    if license_value:
        clean["license"] = _sanitize_single_line(license_value)
    if clean_metadata:
        clean["metadata"] = clean_metadata

    return clean


def _rewrite_codex_paths(body: str) -> str:
    out = body

    # Claude marketplace installs -> Codex skills
    out = out.replace("~/.claude/plugins/marketplaces/sf-skills/", "$CODEX_HOME/skills/")
    # Some docs refer to Claude plugin cache paths; map them to Codex installs.
    out = out.replace("~/.claude/plugins/cache/sf-skills/.../", "$CODEX_HOME/skills/")
    out = out.replace(
        "~/.claude/plugins/cache/sf-diagram-mermaid/*/sf-diagram-mermaid/",
        "$CODEX_HOME/skills/sf-diagram-mermaid/",
    )
    out = out.replace("~/.claude/sf-skills/skills/", "$CODEX_HOME/skills/")
    out = out.replace("~/.claude/skills/", "$CODEX_HOME/skills/")

    # Generic placeholders used in the source skills
    out = out.replace("{SKILL_PATH}", "$SKILL_DIR")
    out = out.replace("${SKILL_HOOKS}", "$SKILL_DIR/hooks")
    out = out.replace("${SHARED_HOOKS}", "$SHARED_DIR/hooks")
    out = out.replace("${SKILL_HOOKS}", "$SKILL_DIR/hooks")

    return out


def _rewrite_markdown_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".mdx"}:
            continue
        original = path.read_text()
        rewritten = _rewrite_codex_paths(original)
        if rewritten != original:
            path.write_text(rewritten)


def _codex_prelude(skill_name: str) -> str:
    return (
        "## Codex Notes (OpenAI)\n\n"
        "This is the Codex-compatible export of this skill.\n\n"
        "### Skill path (set once)\n\n"
        "```bash\n"
        'export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"\n'
        f'export SKILL_DIR="$CODEX_HOME/skills/{skill_name}"\n'
        'export SHARED_DIR="$CODEX_HOME/skills/shared"\n'
        "```\n\n"
        "### Automation notes\n\n"
        "The source repository uses `hooks:` for automatic validations in other runtimes.\n"
        "Codex does not run these hooks automatically. Run validations manually when needed.\n\n"
        "Common checks:\n\n"
        "```bash\n"
        "# Optional: environment / VS Code extension check\n"
        "bash \"$SHARED_DIR/lsp-engine/check_lsp_versions.sh\" --force\n"
        "\n"
        "# Optional: org preflight (requires sf auth)\n"
        "python3 \"$SHARED_DIR/hooks/scripts/org-preflight.py\" --help\n"
        "```\n"
    )


def _render_clean_skill_md(frontmatter: Dict[str, Any], body: str, skill_name: str) -> str:
    clean_front = _build_clean_frontmatter(frontmatter, source_path=Path(skill_name) / "SKILL.md")

    filtered_front = {
        key: value
        for key, value in clean_front.items()
        if key in ALLOWED_FRONTMATTER_FIELDS
    }

    front_yaml = yaml.safe_dump(
        filtered_front,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    ).rstrip()

    new_body = _rewrite_codex_paths(body)
    prelude = _codex_prelude(skill_name)

    combined_body = prelude + "\n\n" + new_body.lstrip()

    return f"---\n{front_yaml}\n---\n\n{combined_body}"


def _load_manifest(manifest_path: Path) -> Dict[str, Any]:
    if not manifest_path.exists():
        return {}
    data = yaml.safe_load(manifest_path.read_text()) or {}
    return data if isinstance(data, dict) else {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        elif (
            key in merged
            and isinstance(merged[key], list)
            and isinstance(value, list)
        ):
            merged[key] = [*merged[key], *value]
        else:
            merged[key] = value
    return merged


def _default_openai_metadata(skill_name: str, frontmatter: Dict[str, Any]) -> Dict[str, Any]:
    desc = _sanitize_single_line(frontmatter.get("description", ""))
    short = _derive_short_description(skill_name, desc)
    display = skill_name
    if display.startswith("sf-"):
        display = "SF " + display.removeprefix("sf-").replace("-", " ").title()
    else:
        display = display.replace("-", " ").title()

    return {
        "interface": {
            "display_name": display,
            "short_description": short,
            "default_prompt": desc or f"Use the {skill_name} skill.",
        },
        "dependencies": {
            "tools": [
                {
                    "type": "cli",
                    "value": "sf",
                    "description": "Salesforce CLI (sf)",
                    "command": "npm install -g @salesforce/cli",
                },
                {
                    "type": "runtime",
                    "value": "python3>=3.10",
                    "description": "Python runtime for helper scripts",
                },
            ]
        },
    }


def _render_openai_yaml(
    skill_name: str,
    frontmatter: Dict[str, Any],
    manifest: Dict[str, Any],
) -> str:
    defaults = manifest.get("defaults", {}) if isinstance(manifest.get("defaults"), dict) else {}
    skills = manifest.get("skills", {}) if isinstance(manifest.get("skills"), dict) else {}
    override = skills.get(skill_name, {}) if isinstance(skills.get(skill_name), dict) else {}

    base = _deep_merge(_default_openai_metadata(skill_name, frontmatter), defaults)
    merged = _deep_merge(base, override)

    tools = (
        merged.get("dependencies", {}).get("tools")
        if isinstance(merged.get("dependencies"), dict)
        else None
    )
    if isinstance(tools, list):
        deduped = []
        seen = set()
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            key = (
                str(tool.get("type", "")),
                str(tool.get("value", "")),
                str(tool.get("command", "")),
                str(tool.get("url", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(tool)
        merged.setdefault("dependencies", {})["tools"] = deduped

    return yaml.safe_dump(
        merged,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    ).rstrip() + "\n"


def _copytree_filtered(src: Path, dst: Path) -> None:
    def _ignore(dirpath: str, names: List[str]) -> List[str]:
        ignored: List[str] = []
        for name in names:
            if name in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}:
                ignored.append(name)
                continue
            if name.endswith(".pyc"):
                ignored.append(name)
                continue
            if name == ".claude-plugin":
                ignored.append(name)
                continue
        return ignored

    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=_ignore)


def _discover_source_skills(repo_root: Path) -> List[Path]:
    skills: List[Path] = []
    for child in repo_root.iterdir():
        if not child.is_dir():
            continue
        if not child.name.startswith("sf-"):
            continue
        if (child / "SKILL.md").exists():
            skills.append(child)
    return sorted(skills, key=lambda p: p.name)


def export_codex_skills(
    repo_root: Path,
    out_dir: Path,
    *,
    manifest_path: Optional[Path] = None,
    clean: bool = False,
    only_skills: Optional[Iterable[str]] = None,
) -> ExportResult:
    repo_root = repo_root.resolve()
    out_dir = out_dir.resolve()

    manifest_path = manifest_path or (repo_root / "scripts" / "codex_skill_manifest.yaml")
    manifest = _load_manifest(manifest_path)

    requested = set(only_skills or [])

    if clean and out_dir.exists():
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    warnings: List[str] = []
    exported: List[str] = []

    # Export shared folder
    shared_src = repo_root / "shared"
    shared_out = out_dir / "shared"
    shared_out.mkdir(parents=True, exist_ok=True)
    for src_rel, dst_rel in SHARED_COPY_DIRS:
        src = shared_src / src_rel
        dst = shared_out / dst_rel
        if not src.exists():
            warnings.append(f"missing shared dir: {src}")
            continue
        _copytree_filtered(src, dst)

    # Export sf-* skills
    for skill_dir in _discover_source_skills(repo_root):
        skill_name = skill_dir.name
        if requested and skill_name not in requested:
            continue

        source_skill_md = skill_dir / "SKILL.md"
        front, body = _extract_frontmatter_and_body(source_skill_md.read_text(), source_skill_md)

        target_dir = out_dir / skill_name
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy directories
        for dirname in SKILL_COPY_DIRS:
            src = skill_dir / dirname
            if not src.exists():
                continue
            dst = target_dir / dirname
            _copytree_filtered(src, dst)

        # Write clean SKILL.md
        (target_dir / "SKILL.md").write_text(_render_clean_skill_md(front, body, skill_name))

        # Write Codex metadata (openai.yaml)
        agents_dir = target_dir / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "openai.yaml").write_text(_render_openai_yaml(skill_name, front, manifest))

        # Rewrite any embedded ~/.claude paths inside copied markdown assets.
        _rewrite_markdown_tree(target_dir)

        exported.append(skill_name)

    return ExportResult(exported=exported, warnings=warnings)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export sf-skills for OpenAI Codex / Agent Skills.")
    parser.add_argument(
        "--out",
        default="skills",
        help="Output directory (default: ./skills)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete the output directory before exporting",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Export only specific skill(s). Repeatable. Example: --only sf-apex",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    result = export_codex_skills(
        repo_root=repo_root,
        out_dir=Path(args.out),
        manifest_path=repo_root / "scripts" / "codex_skill_manifest.yaml",
        clean=args.clean,
        only_skills=args.only,
    )

    print(f"Exported {len(result.exported)} skill(s) to {Path(args.out).resolve()}")
    for name in result.exported:
        print(f"  - {name}")
    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  - {w}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
