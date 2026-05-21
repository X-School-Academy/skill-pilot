from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DENY_REASON = "Security policy: reading .env or .env.* files is not allowed. .env.example is allowed."


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid hook JSON on stdin: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("hook JSON on stdin must be an object")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=("codex", "claude", "gemini", "opencode"), required=True)
    return parser.parse_args()


def is_blocked_env_name(name: str) -> bool:
    return name == ".env" or (name.startswith(".env.") and name != ".env.example")


def resolve_project_path(value: str, cwd: str | None = None) -> Path | None:
    if not value or "\x00" in value:
        return None
    raw = Path(os.path.expanduser(value))
    if raw.is_absolute():
        path = raw
    else:
        base = Path(cwd) if cwd else REPO_ROOT
        path = base / raw
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(REPO_ROOT)
    except (OSError, ValueError):
        return None
    return resolved


def blocked_project_path(value: str, cwd: str | None = None) -> str | None:
    path = resolve_project_path(value, cwd)
    if path and is_blocked_env_name(path.name):
        return str(path)
    return None


def iter_string_values(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, list):
        for item in value:
            strings.extend(iter_string_values(item))
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(iter_string_values(item))
    return strings


def iter_path_inputs(tool_input: Any) -> list[str]:
    if not isinstance(tool_input, dict):
        return []
    path_keys = {
        "file",
        "files",
        "file_path",
        "filePath",
        "path",
        "paths",
        "absolute_path",
        "absolutePath",
        "relative_path",
        "relativePath",
        "target_file",
        "targetFile",
        "pattern",
        "include",
        "includes",
    }
    paths: list[str] = []
    for key, value in tool_input.items():
        if key in path_keys:
            paths.extend(iter_string_values(value))
    return paths


def command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return re.split(r"\s+", command)


def find_blocked_env_path(payload: dict[str, Any]) -> str | None:
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "").lower()
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = payload.get("args") if isinstance(payload.get("args"), dict) else {}
    cwd = str(payload.get("cwd") or tool_input.get("cwd") or REPO_ROOT)

    for candidate in iter_path_inputs(tool_input):
        blocked = blocked_project_path(candidate, cwd)
        if blocked:
            return blocked

    command = tool_input.get("command")
    if isinstance(command, str):
        for token in command_tokens(command):
            token = token.strip("'\"")
            blocked = blocked_project_path(token, cwd)
            if blocked:
                return blocked
        if ".env" in command and ".env.example" not in command:
            return ".env reference in shell command"

    if tool_name in {"read", "readfile", "read_file", "read_many_files", "grep", "glob"}:
        for candidate in iter_string_values(tool_input):
            blocked = blocked_project_path(candidate, cwd)
            if blocked:
                return blocked

    return None


def deny_response(agent: str, blocked_path: str) -> dict[str, Any]:
    reason = f"{DENY_REASON} Blocked path: {blocked_path}"
    if agent in {"codex", "claude"}:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    if agent == "gemini":
        return {"decision": "deny", "reason": reason, "systemMessage": reason}
    return {"decision": "deny", "reason": reason}


def main() -> None:
    args = parse_args()
    payload = read_stdin_json()
    blocked_path = find_blocked_env_path(payload)
    if blocked_path:
        print(json.dumps(deny_response(args.agent, blocked_path), separators=(",", ":")))
        return
    print("{}")


if __name__ == "__main__":
    main()
