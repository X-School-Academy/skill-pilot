import importlib
from pathlib import Path


def load_guard(monkeypatch, tmp_path):
    engine_path = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(engine_path))
    module = importlib.import_module("hooks.env_guard")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    return module


def test_blocks_env_and_env_star_but_allows_example(monkeypatch, tmp_path):
    guard = load_guard(monkeypatch, tmp_path)
    cwd = str(tmp_path)

    assert guard.find_blocked_env_path({"tool_input": {"file_path": ".env"}, "cwd": cwd}) == str(
        tmp_path / ".env"
    )
    assert guard.find_blocked_env_path({"tool_input": {"file_path": "config/.env.local"}, "cwd": cwd}) == str(
        tmp_path / "config" / ".env.local"
    )
    assert guard.find_blocked_env_path({"tool_input": {"file_path": ".env.example"}, "cwd": cwd}) is None


def test_blocks_shell_command_env_tokens(monkeypatch, tmp_path):
    guard = load_guard(monkeypatch, tmp_path)
    cwd = str(tmp_path)

    assert guard.find_blocked_env_path({"tool_input": {"command": "cat config/.env"}, "cwd": cwd}) == str(
        tmp_path / "config" / ".env"
    )
    assert guard.find_blocked_env_path({"tool_input": {"command": "cat .env.example"}, "cwd": cwd}) is None


def test_allows_keys_safe_guard_as_approved_env_access(monkeypatch, tmp_path):
    guard = load_guard(monkeypatch, tmp_path)
    cwd = str(tmp_path)

    assert (
        guard.find_blocked_env_path(
            {
                "tool_input": {
                    "command": "core/bin/keys-safe-guard --env-file config/.env get_key_value API_KEY"
                },
                "cwd": cwd,
            }
        )
        is None
    )
    assert (
        guard.find_blocked_env_path(
            {
                "tool_input": {
                    "command": "./core/bin/keys-safe-guard --env-file .skillpilot/temp/.env.local get_key_value API_KEY"
                },
                "cwd": cwd,
            }
        )
        is None
    )


def test_still_blocks_non_guard_commands_with_env(monkeypatch, tmp_path):
    guard = load_guard(monkeypatch, tmp_path)
    cwd = str(tmp_path)

    assert guard.find_blocked_env_path({"tool_input": {"command": "python -c 'open(\"config/.env\").read()'"}, "cwd": cwd})


def test_ignores_env_paths_outside_project(monkeypatch, tmp_path):
    guard = load_guard(monkeypatch, tmp_path)

    assert guard.find_blocked_env_path({"tool_input": {"file_path": "/tmp/.env"}}) is None


def test_denial_shape_for_agents(monkeypatch, tmp_path):
    guard = load_guard(monkeypatch, tmp_path)

    claude = guard.deny_response("claude", "/repo/.env")
    assert claude["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert claude["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    gemini = guard.deny_response("gemini", "/repo/.env")
    assert gemini["decision"] == "deny"
    assert "reason" in gemini

    opencode = guard.deny_response("opencode", "/repo/.env")
    assert opencode["decision"] == "deny"
