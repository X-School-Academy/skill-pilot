"""Tests for model/effort selection in command builders.

Verifies the changes from the model+effort web UI feature:
- Model resolution (CLI override > provider config > None)
- Template-aware flag placement (no duplicate when template has {{model}}/{{effort}})
- {{effort}} template replacement
- format_command_for_log rendering of --effort
- _build_codex_terminal_args model/effort passthrough
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm_service import (
    build_llm_command,
    build_terminal_command,
    format_command_for_log,
    _build_codex_terminal_args,
)


# ============================================================
# build_llm_command — model parameter
# ============================================================

def test_build_llm_command_model_cli_override():
    """CLI model overrides provider config model."""
    provider = {"bin": "test-llm", "args": ["{{prompt}}"], "model": "provider-default"}
    result = build_llm_command(provider, "hello", model="cli-model")
    assert "--model" in result
    assert "cli-model" in result
    assert "provider-default" not in result


def test_build_llm_command_model_falls_back_to_provider_config():
    """Without CLI override, uses provider config model."""
    provider = {"bin": "test-llm", "args": ["{{prompt}}"], "model": "provider-default"}
    result = build_llm_command(provider, "hello")
    assert "--model" in result
    assert "provider-default" in result


def test_build_llm_command_model_none_when_no_config():
    """No model at all -> no --model flag."""
    provider = {"bin": "test-llm", "args": ["{{prompt}}"]}
    result = build_llm_command(provider, "hello")
    assert "--model" not in result


# ============================================================
# build_llm_command — effort parameter
# ============================================================

def test_build_llm_command_effort_prepended():
    """Effort is prepended as --effort flag."""
    provider = {"bin": "test-llm", "args": ["{{prompt}}"]}
    result = build_llm_command(provider, "hello", effort="xhigh")
    assert "--effort" in result
    assert "xhigh" in result


def test_build_llm_command_effort_none_omitted():
    """No effort -> no --effort flag."""
    provider = {"bin": "test-llm", "args": ["{{prompt}}"]}
    result = build_llm_command(provider, "hello")
    assert "--effort" not in result


# ============================================================
# build_llm_command — template-aware prepend (no duplicates)
# ============================================================

def test_build_llm_command_template_model_skips_prepend():
    """When template has {{model}}, don't prepend --model (avoid dup)."""
    provider = {"bin": "uv", "args": ["run", "agent", "--model={{model}}", "{{prompt}}"]}
    result = build_llm_command(provider, "hello", model="sonnet")
    # Template replaces "--model={{model}}" → "--model=sonnet" (combined arg)
    assert "--model=sonnet" in result
    # No separate "--model" element (would be a prepend duplicate)
    assert "--model" not in result


def test_build_llm_command_template_effort_skips_prepend():
    """When template has {{effort}}, don't prepend --effort (avoid dup)."""
    provider = {"bin": "uv", "args": ["run", "agent", "--effort={{effort}}", "{{prompt}}"]}
    result = build_llm_command(provider, "hello", effort="high")
    # Template replaces "--effort={{effort}}" → "--effort=high" (combined arg)
    assert "--effort=high" in result
    assert "--effort" not in result


def test_build_llm_command_template_both_model_and_effort():
    """Template with both {{model}} and {{effort}} — no prepend for either."""
    provider = {
        "bin": "uv",
        "args": [
            "--directory", "/app", "run", "python", "-m", "agent.cli",
            "--model={{model}}", "--effort={{effort}}", "{{prompt}}"
        ],
    }
    result = build_llm_command(provider, "list files", model="claude-sonnet-4-6", effort="xhigh")
    # Flags rendered as combined form via template replacement
    assert "--model=claude-sonnet-4-6" in result
    assert "--effort=xhigh" in result
    # No separate flag elements (no prepend duplicates)
    assert "--model" not in result
    assert "--effort" not in result
    # Flags are positioned after "run" (template position), not before
    run_idx = result.index("run")
    model_idx = result.index("--model=claude-sonnet-4-6")
    effort_idx = result.index("--effort=xhigh")
    assert model_idx > run_idx, f"--model should be after 'run', got: {result}"
    assert effort_idx > run_idx, f"--effort should be after 'run', got: {result}"


def test_build_llm_command_template_model_absent_when_none():
    """When {{model}} in template but resolved_model is None, arg is skipped."""
    provider = {"bin": "test-llm", "args": ["--model={{model}}", "{{prompt}}"]}
    result = build_llm_command(provider, "hello")
    assert "--model" not in result


def test_build_llm_command_template_effort_absent_when_none():
    """When {{effort}} in template but effort is None, arg is skipped."""
    provider = {"bin": "test-llm", "args": ["--effort={{effort}}", "{{prompt}}"]}
    result = build_llm_command(provider, "hello")
    assert "--effort" not in result


# ============================================================
# build_llm_command — combined scenarios
# ============================================================

def test_build_llm_command_model_only_no_effort():
    """Model without effort — only --model flag."""
    provider = {"bin": "test-llm", "args": ["{{prompt}}"]}
    result = build_llm_command(provider, "hello", model="gpt-5.5")
    assert "--model" in result
    assert "gpt-5.5" in result
    assert "--effort" not in result


def test_build_llm_command_effort_only_no_model():
    """Effort without model — only --effort flag."""
    provider = {"bin": "test-llm", "args": ["{{prompt}}"]}
    result = build_llm_command(provider, "hello", effort="low")
    assert "--effort" in result
    assert "low" in result
    assert "--model" not in result


# ============================================================
# build_llm_command — uv-based provider (skill-pilot style)
# ============================================================

def test_build_llm_command_uv_provider_full():
    """Full skill-pilot style provider with model + effort."""
    provider = {
        "bin": "uv",
        "args": [
            "--directory", "/app",
            "run", "python", "-m", "skill_pilot_agent.cli",
            "--model={{model}}", "--effort={{effort}}", "{{prompt}}"
        ],
    }
    result = build_llm_command(provider, "list files", model="claude-sonnet-4-6", effort="high")
    assert result[0] == "uv"
    assert result[1] == "--directory"
    assert "run" in result
    # flags come after "run" via template
    run_pos = result.index("run")
    assert result.index("--model=claude-sonnet-4-6") > run_pos
    assert result.index("--effort=high") > run_pos
    assert result[-1] == "list files"


def test_build_llm_command_uv_provider_no_selection():
    """Skill-pilot provider with no model/effort — clean command, no flags."""
    provider = {
        "bin": "uv",
        "args": [
            "--directory", "/app",
            "run", "python", "-m", "skill_pilot_agent.cli",
            "--model={{model}}", "--effort={{effort}}", "{{prompt}}"
        ],
    }
    result = build_llm_command(provider, "hello")
    assert "--model" not in result
    assert "--effort" not in result
    assert result == ["uv", "--directory", "/app", "run", "python", "-m", "skill_pilot_agent.cli", "hello"]


# ============================================================
# build_terminal_command — model/effort
# ============================================================

def test_build_terminal_command_model_in_terminal_args():
    """Terminal args with {{model}} template — template replacement, no prepend."""
    provider = {
        "bin": "uv",
        "terminal-args": [
            "--directory", "/app", "run", "python", "-m", "agent.cli",
            "--model={{model}}", "--effort={{effort}}", "{{prompt}}"
        ],
    }
    result = build_terminal_command(provider, "hello", model="opus", effort="high")
    # Template replacement produces combined "--model=opus", "--effort=high"
    assert "--model=opus" in result
    assert "--effort=high" in result
    # No separate flag elements (no prepend duplicates)
    assert "--model" not in result
    assert "--effort" not in result


def test_build_terminal_command_model_prepended_when_no_template():
    """Terminal args without {{model}} — prepend --model flag."""
    provider = {"bin": "test-cli", "terminal-args": ["{{prompt}}"]}
    result = build_terminal_command(provider, "hello", model="gpt-5.5")
    assert "--model" in result
    assert "gpt-5.5" in result


def test_build_terminal_command_effort_prepended_when_no_template():
    """Terminal args without {{effort}} — prepend --effort flag."""
    provider = {"bin": "test-cli", "terminal-args": ["{{prompt}}"]}
    result = build_terminal_command(provider, "hello", effort="xhigh")
    assert "--effort" in result
    assert "xhigh" in result


# ============================================================
# build_terminal_command — codex fallback
# ============================================================

def test_build_terminal_command_codex_with_model_effort():
    """Codex provider terminal command passes model/effort to _build_codex_terminal_args."""
    provider = {"bin": "codex", "args": ["exec", "--json", "-v", "{{prompt}}"]}
    result = build_terminal_command(provider, "test", model="opus", effort="high")
    assert "--model" in result
    assert "opus" in result
    assert "--effort" in result
    assert "high" in result


# ============================================================
# _build_codex_terminal_args
# ============================================================

def test_build_codex_terminal_args_with_model():
    provider = {"bin": "codex", "args": ["exec", "--json", "{{prompt}}"]}
    result = _build_codex_terminal_args(provider, "hello", model="sonnet")
    assert "--model" in result
    assert "sonnet" in result
    assert "exec" not in result
    assert "--json" not in result


def test_build_codex_terminal_args_with_effort():
    provider = {"bin": "codex", "args": ["exec", "--json", "{{prompt}}"]}
    result = _build_codex_terminal_args(provider, "hello", effort="high")
    assert "--effort" in result
    assert "high" in result


def test_build_codex_terminal_args_with_both():
    provider = {"bin": "codex", "args": ["exec", "--json", "{{prompt}}"]}
    result = _build_codex_terminal_args(provider, "hello", model="sonnet", effort="xhigh")
    assert "--model" in result and "sonnet" in result
    assert "--effort" in result and "xhigh" in result


def test_build_codex_terminal_args_without_model_effort():
    provider = {"bin": "codex", "args": ["exec", "--json", "{{prompt}}"]}
    result = _build_codex_terminal_args(provider, "hello")
    assert "--model" not in result
    assert "--effort" not in result


# ============================================================
# format_command_for_log — effort rendering
# ============================================================

def test_format_command_for_log_combines_effort_flag():
    """--effort flag rendered as --effort=value."""
    result = format_command_for_log(["uv", "run", "agent", "--effort", "high", "prompt"])
    assert "--effort=high" in result


def test_format_command_for_log_combines_model_and_effort():
    """Both --model and --effort rendered with =."""
    result = format_command_for_log(["agent", "--model", "sonnet", "--effort", "xhigh", "hello"])
    assert "--model=sonnet" in result
    assert "--effort=xhigh" in result


def test_format_command_for_log_effort_without_value():
    """--effort at end of list without value — rendered as-is."""
    result = format_command_for_log(["agent", "--effort"])
    assert "--effort" in result


# ============================================================
# Edge cases — empty strings treated as not-provided
# ============================================================

def test_build_llm_command_empty_model_string():
    """Empty model string -> no --model flag (treated as not provided)."""
    provider = {"bin": "test-llm", "args": ["{{prompt}}"]}
    result = build_llm_command(provider, "hello", model="")
    # Empty string is falsy, so no --model prepended
    assert "--model" not in result


def test_build_llm_command_empty_effort_string():
    """Empty effort string -> no --effort flag."""
    provider = {"bin": "test-llm", "args": ["{{prompt}}"]}
    result = build_llm_command(provider, "hello", effort="")
    assert "--effort" not in result
