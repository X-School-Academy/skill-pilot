import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import subagent_install


def test_parse_subagent_accepts_first_stage_metadata_only(tmp_path):
    source_root = tmp_path / "system"
    source_root.mkdir()
    subagent_path = source_root / "reviewer.md"
    subagent_path.write_text(
        """---
name: reviewer
description: Reviews implementation risks.
---
Review code and report concrete issues.
""",
        encoding="utf-8",
    )

    parsed = subagent_install.parse_subagent(subagent_path, source_root)

    assert parsed.name == "reviewer"
    assert parsed.description == "Reviews implementation risks."
    assert parsed.body == "Review code and report concrete issues.\n"
    assert parsed.level == "system"


def test_parse_subagent_rejects_unsupported_metadata(tmp_path):
    source_root = tmp_path / "user"
    source_root.mkdir()
    subagent_path = source_root / "reviewer.md"
    subagent_path.write_text(
        """---
name: reviewer
description: Reviews implementation risks.
model: sonnet
---
Review code and report concrete issues.
""",
        encoding="utf-8",
    )

    with pytest.raises(subagent_install.SubagentInstallError, match="Unsupported frontmatter"):
        subagent_install.parse_subagent(subagent_path, source_root)


def test_main_installs_to_all_supported_agent_formats(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    source_root = repo_root / "core" / "subagents" / "system"
    source_root.mkdir(parents=True)
    disabled_config = repo_root / "config" / "disabled_subagents.json5"
    disabled_config.parent.mkdir()
    disabled_config.write_text("[]", encoding="utf-8")
    (source_root / "reviewer.md").write_text(
        """---
name: reviewer
description: Reviews implementation risks.
---
Review code and report concrete issues.
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "subagent_install.py",
            "--source",
            str(source_root),
            "--project-root",
            str(repo_root),
            "--disabled-config",
            str(disabled_config),
        ],
    )

    assert subagent_install.main() == 0

    assert (repo_root / ".claude" / "agents" / "reviewer.md").read_text(encoding="utf-8") == (
        "---\n"
        "name: reviewer\n"
        'description: "Reviews implementation risks."\n'
        "---\n"
        "Review code and report concrete issues.\n"
    )
    assert (repo_root / ".gemini" / "agents" / "reviewer.md").exists()
    assert (repo_root / ".opencode" / "agents" / "reviewer.md").read_text(encoding="utf-8") == (
        "---\n"
        'description: "Reviews implementation risks."\n'
        "mode: subagent\n"
        "---\n"
        "Review code and report concrete issues.\n"
    )
    assert (repo_root / ".codex" / "agents" / "reviewer.toml").read_text(encoding="utf-8") == (
        'name = "reviewer"\n'
        'description = "Reviews implementation risks."\n'
        "\n"
        'developer_instructions = """\n'
        "Review code and report concrete issues.\n"
        '"""\n'
    )


def test_main_removes_disabled_subagents(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    source_root = repo_root / "core" / "subagents" / "system"
    source_root.mkdir(parents=True)
    disabled_config = repo_root / "config" / "disabled_subagents.json5"
    disabled_config.parent.mkdir()
    disabled_config.write_text('["reviewer"]', encoding="utf-8")
    (source_root / "reviewer.md").write_text(
        """---
name: reviewer
description: Reviews implementation risks.
---
Review code and report concrete issues.
""",
        encoding="utf-8",
    )
    stale_target = repo_root / ".claude" / "agents" / "reviewer.md"
    stale_target.parent.mkdir(parents=True)
    stale_target.write_text("stale", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "subagent_install.py",
            "--source",
            str(source_root),
            "--project-root",
            str(repo_root),
            "--disabled-config",
            str(disabled_config),
            "--targets",
            "claude",
        ],
    )

    assert subagent_install.main() == 0
    assert not stale_target.exists()


def test_main_removes_subagent_deleted_from_source_after_prior_install(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    source_root = repo_root / "core" / "subagents" / "system"
    source_root.mkdir(parents=True)
    disabled_config = repo_root / "config" / "disabled_subagents.json5"
    disabled_config.parent.mkdir()
    disabled_config.write_text("[]", encoding="utf-8")
    subagent_path = source_root / "reviewer.md"
    subagent_path.write_text(
        """---
name: reviewer
description: Reviews implementation risks.
---
Review code and report concrete issues.
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "subagent_install.py",
            "--source",
            str(source_root),
            "--project-root",
            str(repo_root),
            "--disabled-config",
            str(disabled_config),
            "--targets",
            "claude",
        ],
    )
    assert subagent_install.main() == 0
    assert (repo_root / ".claude" / "agents" / "reviewer.md").exists()

    subagent_path.unlink()

    assert subagent_install.main() == 0
    assert not (repo_root / ".claude" / "agents" / "reviewer.md").exists()


def test_main_removes_subagent_disabled_after_prior_install(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    source_root = repo_root / "core" / "subagents" / "system"
    source_root.mkdir(parents=True)
    disabled_config = repo_root / "config" / "disabled_subagents.json5"
    disabled_config.parent.mkdir()
    disabled_config.write_text("[]", encoding="utf-8")
    (source_root / "reviewer.md").write_text(
        """---
name: reviewer
description: Reviews implementation risks.
---
Review code and report concrete issues.
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "subagent_install.py",
            "--source",
            str(source_root),
            "--project-root",
            str(repo_root),
            "--disabled-config",
            str(disabled_config),
            "--targets",
            "claude",
        ],
    )
    assert subagent_install.main() == 0
    assert (repo_root / ".claude" / "agents" / "reviewer.md").exists()

    disabled_config.write_text('["reviewer"]', encoding="utf-8")

    assert subagent_install.main() == 0
    assert not (repo_root / ".claude" / "agents" / "reviewer.md").exists()
