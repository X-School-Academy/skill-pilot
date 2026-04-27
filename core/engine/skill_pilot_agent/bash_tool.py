from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
import logging
from dataclasses import dataclass
from pathlib import Path

from agents import function_tool


logger = logging.getLogger(__name__)

NETWORK_COMMANDS = {
    "brew",
    "curl",
    "gem",
    "git",
    "go",
    "npm",
    "npx",
    "pip",
    "pip3",
    "pnpm",
    "python",
    "python3",
    "uv",
    "wget",
    "yarn",
}


@dataclass
class BashToolConfig:
    agent_dir: Path
    allowed_commands: set[str] | None = None
    network_allowed: bool = False
    sandbox_enabled: bool = True
    timeout_seconds: int = 60
    executed_commands: list[str] | None = None


def parse_command_allowlist(raw: str | None) -> set[str] | None:
    if raw is None or not raw.strip():
        return None
    commands = {item.strip() for item in raw.split(",") if item.strip()}
    return commands or None


def command_executable(command: str) -> str:
    parts = shlex.split(command, posix=True)
    if not parts:
        raise ValueError("Command is empty")
    return Path(parts[0]).name


def _network_sandbox_prefix() -> list[str] | None:
    if platform.system() == "Darwin" and shutil.which("sandbox-exec"):
        profile = "(version 1)(allow default)(deny network*)"
        return ["sandbox-exec", "-p", profile]
    return None


def _validate_command(command: str, config: BashToolConfig) -> None:
    executable = command_executable(command)
    if config.allowed_commands is not None and executable not in config.allowed_commands:
        allowed = ", ".join(sorted(config.allowed_commands))
        raise PermissionError(f"Command '{executable}' is not allowed. Allowed commands: {allowed}")
    if not config.network_allowed and executable in NETWORK_COMMANDS:
        raise PermissionError(f"Command '{executable}' is blocked because network access is disabled")


def run_bash_command(command: str, config: BashToolConfig) -> str:
    _validate_command(command, config)
    if config.executed_commands is not None:
        config.executed_commands.append(command)
    logger.info("[skill-pilot-agent] bash command: %s", command)

    agent_dir = config.agent_dir.resolve()
    if not agent_dir.exists() or not agent_dir.is_dir():
        raise FileNotFoundError(f"Agent directory does not exist: {agent_dir}")

    argv = ["/bin/bash", "-lc", command]
    if config.sandbox_enabled and not config.network_allowed:
        prefix = _network_sandbox_prefix()
        if prefix is None:
            raise RuntimeError(
                "Network is disabled, but strict local OS-level network enforcement is not available"
            )
        argv = [*prefix, *argv]

    proc = subprocess.run(
        argv,
        cwd=str(agent_dir),
        capture_output=True,
        text=True,
        timeout=config.timeout_seconds,
        shell=False,
        env=dict(os.environ),
    )
    logger.info("[skill-pilot-agent] bash exit_code=%s", proc.returncode)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    return (
        f"exit_code: {proc.returncode}\n"
        f"stdout:\n{stdout.rstrip()}\n"
        f"stderr:\n{stderr.rstrip()}"
    ).rstrip()


def build_bash_tool(config: BashToolConfig):
    @function_tool(name_override="bash", description_override="Run one bash command in the agent directory.")
    def bash(command: str) -> str:
        """Run one bash command in the configured agent directory."""

        return run_bash_command(command, config)

    return bash
