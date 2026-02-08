from __future__ import annotations

from pathlib import Path

import yaml


def test_export_codex_skills_smoke(tmp_path: Path):
    from scripts.export_codex_skills import export_codex_skills

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = tmp_path / "skills"

    result = export_codex_skills(
        repo_root=repo_root,
        out_dir=out_dir,
        clean=True,
        only_skills=["sf-apex"],
    )

    assert "sf-apex" in result.exported

    exported_skill_dir = out_dir / "sf-apex"
    exported_skill_md = exported_skill_dir / "SKILL.md"
    assert exported_skill_md.exists()

    content = exported_skill_md.read_text()
    assert content.startswith("---\n")
    assert "\nhooks:\n" not in content
    assert "~/.claude" not in content
    assert "${SHARED_HOOKS}" not in content
    assert "${SKILL_HOOKS}" not in content

    openai_yaml = exported_skill_dir / "agents" / "openai.yaml"
    assert openai_yaml.exists()
    openai = yaml.safe_load(openai_yaml.read_text())
    assert isinstance(openai, dict)
    assert "interface" in openai
    assert "dependencies" in openai

    shared_dir = out_dir / "shared"
    assert (shared_dir / "hooks").exists()
    assert (shared_dir / "lsp-engine").exists()
    assert (shared_dir / "code_analyzer").exists()

