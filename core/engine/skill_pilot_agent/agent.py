from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from openai import AsyncOpenAI

from logger import get_logger

from .agents_md import load_agents_md
from .bash_tool import BashToolConfig, build_bash_tool, parse_command_allowlist
from .skills import load_skill_instructions


logger = get_logger("skill-pilot-agent.agent")


@dataclass(frozen=True)
class SkillPilotAgentConfig:
    prompt: str
    agent_dir: Path
    agent_file: Path | None
    skills_dir: Path
    skills: str | None
    model: str
    base_url: str
    api_key: str
    sandbox: bool
    auto: bool
    network: bool
    timeout_seconds: int
    max_retries: int
    bash_commands: str | None


def _compose_instructions(config: SkillPilotAgentConfig) -> str:
    parts = [
        "You are the Skill Pilot background agent.",
        "Use only the available bash tool when a tool is needed.",
        "For any task that asks you to inspect, count, create, edit, or verify local files, you must use the bash tool.",
        "After creating or editing a file, verify it exists before reporting success.",
        "Do not claim a file was created, edited, counted, or verified unless the bash tool output confirms it.",
        "Keep responses concise and return the final answer directly.",
    ]

    if config.agent_file is not None:
        agents_md = load_agents_md(config.agent_dir, config.agent_file)
        if agents_md:
            parts.append(agents_md)

    skill_instructions = load_skill_instructions(config.skills_dir, config.skills)
    if skill_instructions:
        parts.append(skill_instructions)

    return "\n\n".join(parts)


def _prompt_requires_bash(prompt: str) -> bool:
    lowered = prompt.lower()
    filesystem_request_patterns = (
        r"\b(create|write|edit|read|list|inspect|count|verify|delete|remove|move|copy|append|patch|modify|check)\s+"
        r"(a\s+|an\s+|the\s+)?(local\s+)?(file|folder|directory|repo|repository|workspace)s?\b",
        r"\b(file|folder|directory)s?\s+(exists?|is present|is missing)\b",
    )
    if any(re.search(pattern, lowered) for pattern in filesystem_request_patterns):
        return True

    action_terms = (
        "create",
        "write",
        "edit",
        "read",
        "list",
        "inspect",
        "count",
        "verify",
        "delete",
        "remove",
        "move",
        "copy",
        "append",
        "patch",
        "modify",
        "check",
    )
    path_like_pattern = re.compile(
        r"(^|\s)(\.skillpilot/|\.{1,2}/|~/|/[\w.-]|[\w./-]+\."
        r"(py|js|jsx|ts|tsx|json|json5|md|txt|yaml|yml|toml|html|css|csv|svg|png|jpg|jpeg|mp4|wav)\b)"
    )
    return any(term in lowered for term in action_terms) and bool(path_like_pattern.search(lowered))


async def run_agent_async(config: SkillPilotAgentConfig) -> str:
    if not config.base_url:
        raise ValueError("SKILL_PILOT_BASE_URL is required")
    if not config.api_key:
        raise ValueError("SKILL_PILOT_API_KEY is required")
    if not config.model:
        raise ValueError("SKILL_PILOT_MODEL or --model is required")
    if not config.auto:
        raise ValueError("--auto no is parsed but not supported in the first release")

    set_tracing_disabled(True)
    client = AsyncOpenAI(base_url=config.base_url, api_key=config.api_key)
    model = OpenAIChatCompletionsModel(model=config.model, openai_client=client)
    executed_commands: list[str] = []
    bash_config = BashToolConfig(
        agent_dir=config.agent_dir,
        allowed_commands=parse_command_allowlist(config.bash_commands),
        network_allowed=config.network,
        sandbox_enabled=config.sandbox,
        timeout_seconds=config.timeout_seconds,
        executed_commands=executed_commands,
    )
    agent = Agent(
        name="Skill Pilot Agent",
        instructions=_compose_instructions(config),
        model=model,
        tools=[build_bash_tool(bash_config)],
    )

    attempts = max(1, config.max_retries + 1)
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            result = await asyncio.wait_for(
                Runner.run(agent, config.prompt),
                timeout=config.timeout_seconds,
            )
            if _prompt_requires_bash(config.prompt) and not executed_commands:
                final_output = str(result.final_output or "").strip()
                suffix = f": {final_output}" if final_output else ""
                raise RuntimeError(
                    "The model returned a result without executing the required bash tool"
                    f"{suffix}"
                )
            return str(result.final_output or "")
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "skill-pilot-agent attempt %d/%d failed: %s",
                attempt + 1,
                attempts,
                exc,
            )
    assert last_exc is not None
    raise last_exc


def run_agent(config: SkillPilotAgentConfig) -> str:
    return asyncio.run(run_agent_async(config))


def config_from_env(
    *,
    prompt: str,
    agent_dir: Path,
    agent_file: Path | None,
    skills_dir: Path,
    skills: str | None,
    model: str | None,
    sandbox: bool,
    auto: bool,
    network: bool,
    timeout_seconds: int,
    max_retries: int,
    bash_commands: str | None,
) -> SkillPilotAgentConfig:
    return SkillPilotAgentConfig(
        prompt=prompt,
        agent_dir=agent_dir,
        agent_file=agent_file,
        skills_dir=skills_dir,
        skills=skills,
        model=(model or os.environ.get("SKILL_PILOT_MODEL") or "").strip(),
        base_url=(os.environ.get("SKILL_PILOT_BASE_URL") or "").strip(),
        api_key=(os.environ.get("SKILL_PILOT_API_KEY") or "").strip(),
        sandbox=sandbox,
        auto=auto,
        network=network,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        bash_commands=bash_commands,
    )
