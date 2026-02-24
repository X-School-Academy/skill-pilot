from __future__ import annotations

import json
import os
import re
import shlex

from constants import INTERACTIVE_ALWAYS, INTERACTIVE_WHEN_NO_ARGS, SPECIAL_KEYS, TTY_ERROR_PATTERNS


def resolve_key(key: str) -> str:
    return SPECIAL_KEYS.get(key.lower(), key)


def _normalize_transport(transport: str | None) -> str:
    value = (transport or "auto").strip().lower()
    if value not in {"auto", "pty", "pipe"}:
        raise ValueError("transport must be one of: auto, pty, pipe")
    return value


def _normalize_lifecycle(lifecycle: str | None) -> str:
    value = (lifecycle or "direct").strip().lower()
    if value not in {"direct", "tmux"}:
        raise ValueError("lifecycle must be one of: direct, tmux")
    return value


def _profile_from_target(target: str) -> str:
    t = (target or "").strip()
    if not t.startswith("ssh:"):
        raise ValueError("target must be ssh:<profile>")
    profile = t.split(":", 1)[1].strip()
    if not profile:
        raise ValueError("target must be ssh:<profile>")
    return profile


def _is_interactive_command(command: str, args: list[str] | None) -> bool:
    base = os.path.basename(command).lower()
    if base in INTERACTIVE_ALWAYS:
        return True
    if base in INTERACTIVE_WHEN_NO_ARGS:
        return not args
    return False


def _has_tty_error(text: str) -> bool:
    lower = text.lower()
    return any(re.search(pattern, lower) for pattern in TTY_ERROR_PATTERNS)


def _json(value: dict) -> str:
    return json.dumps(value, indent=2)


def _shell_join(command: str, args: list[str] | None = None) -> str:
    return " ".join([shlex.quote(command), *(shlex.quote(a) for a in (args or []))])


def _shell_wrap(command: str, cwd: str | None, env: dict[str, str] | None) -> str:
    parts = []
    if env:
        exports = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
        parts.append(f"export {exports}")
    if cwd:
        parts.append(f"cd {shlex.quote(cwd)}")
    parts.append(command)
    return " && ".join(parts)


def _build_command(command: str, args: list[str] | None, cwd: str | None, env: dict[str, str] | None) -> str:
    cmd = _shell_join(command, args)
    parts = []
    if env:
        exports = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
        parts.append(f"export {exports}")
    if cwd:
        parts.append(f"cd {shlex.quote(cwd)}")
    parts.append(cmd)
    return " && ".join(parts)


def _sanitize_exec_command(command: str, max_chars: int | None) -> str:
    if not isinstance(command, str):
        raise ValueError("command must be a string")
    text = command.strip()
    if not text:
        raise ValueError("command cannot be empty")
    if max_chars is not None and max_chars > 0 and len(text) > max_chars:
        raise ValueError(f"command is too long (max {max_chars} characters)")
    return text


def _sanitize_description(description: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", description).strip()
