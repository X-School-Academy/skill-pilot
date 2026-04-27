import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skill_pilot_agent.agents_md import load_agents_md
from skill_pilot_agent.agent import _prompt_requires_bash
from skill_pilot_agent.bash_tool import BashToolConfig, run_bash_command
from skill_pilot_agent.cli import REPO_ROOT, build_parser
from skill_pilot_agent.skills import load_skill_instructions


def test_cli_argument_defaults():
    args = build_parser().parse_args(["hello"])

    assert args.prompt == ["hello"]
    assert args.sandbox is True
    assert args.auto is True
    assert args.network is False
    assert args.model is None
    assert args.agent_dir == REPO_ROOT
    assert args.agent_file == "AGENTS.md"
    assert args.skills is None


def test_cli_supports_agent_file_none_and_skills_none():
    args = build_parser().parse_args(["--agent-file", "none", "--skills", "none", "hello"])
    assert args.agent_file == "none"
    assert args.skills == "none"


def test_cli_invalid_yes_no_fails():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--network", "maybe", "hello"])


def test_bash_command_allowlist_blocks_disallowed(tmp_path):
    config = BashToolConfig(
        agent_dir=tmp_path,
        allowed_commands={"pwd"},
        network_allowed=True,
        sandbox_enabled=False,
    )

    with pytest.raises(PermissionError):
        run_bash_command("ls", config)


def test_bash_command_allowlist_allows_command(tmp_path):
    executed_commands = []
    config = BashToolConfig(
        agent_dir=tmp_path,
        allowed_commands={"pwd"},
        network_allowed=True,
        sandbox_enabled=False,
        executed_commands=executed_commands,
    )

    result = run_bash_command("pwd", config)

    assert "exit_code: 0" in result
    assert str(tmp_path) in result
    assert executed_commands == ["pwd"]


def test_prompt_requires_bash_for_filesystem_tasks():
    assert _prompt_requires_bash("create a file .skillpilot/temp/count.md")
    assert not _prompt_requires_bash("Reply with exactly OK.")


def test_agents_md_loading_only_reads_root_file(tmp_path):
    (tmp_path / "AGENTS.md").write_text("root instructions", encoding="utf-8")
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    (nested_dir / "AGENTS.md").write_text("nested instructions", encoding="utf-8")

    instructions = load_agents_md(tmp_path)

    assert "root instructions" in instructions
    assert "nested instructions" not in instructions


def test_skill_loading_filters_selected_skills(tmp_path):
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    alpha.mkdir()
    beta.mkdir()
    (alpha / "SKILL.md").write_text("---\nname: alpha\n---\nAlpha body", encoding="utf-8")
    (beta / "SKILL.md").write_text("---\nname: beta\n---\nBeta body", encoding="utf-8")

    instructions = load_skill_instructions(tmp_path, "alpha")

    assert "Alpha body" in instructions
    assert "Beta body" not in instructions


def test_skill_loading_none_skips_all(tmp_path):
    alpha = tmp_path / "alpha"
    alpha.mkdir()
    (alpha / "SKILL.md").write_text("---\nname: alpha\n---\nAlpha body", encoding="utf-8")

    instructions = load_skill_instructions(tmp_path, "none")

    assert instructions == ""


def test_agents_md_loading_supports_custom_file(tmp_path):
    custom = tmp_path / "CUSTOM.md"
    custom.write_text("custom instructions", encoding="utf-8")

    instructions = load_agents_md(tmp_path, "CUSTOM.md")

    assert "custom instructions" in instructions
