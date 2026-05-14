# Skill Pilot Agent

## Overview

This feature adds a Skill Pilot-owned background agent for non-tmux LLM tasks. It is a CLI provider backed by `openai-agents` and an OpenAI-compatible endpoint.

Use it when background engine code needs an LLM response but does not need a long-running terminal session. It is selected with:

```json5
default: {
  background_llm: 'skill-pilot',
}
```

The normal `default.llm` provider remains responsible for regular LLM selection and terminal/tmux sessions.

## Implemented Components

- `core/bin/skill-pilot-agent` wraps the Python CLI.
- `core/engine/skill_pilot_agent/cli.py` parses CLI arguments and builds runtime config.
- `core/engine/skill_pilot_agent/agent.py` creates and runs the `openai-agents` agent.
- `core/engine/skill_pilot_agent/bash_tool.py` exposes the single bash tool.
- `core/engine/skill_pilot_agent/agents_md.py` loads one root agent instruction file.
- `core/engine/skill_pilot_agent/skills.py` discovers and renders skill instructions.
- `core/engine/skill_pilot_agent/ignore_rules.py` applies conservative ignore-file handling during skill discovery.
- `core/engine/llm_service.py` resolves background LLM providers separately from normal LLM providers.
- `config/ai_providers.json5` registers `skill-pilot` as a `background_only` LLM provider.

## Environment

The provider requires:

```bash
SKILL_PILOT_BASE_URL=http://localhost:8000/v1
SKILL_PILOT_API_KEY=...
SKILL_PILOT_MODEL=...
```

## Example

```bash
core/bin/skill-pilot-agent --skills none "Reply with OK"
```

For local file tasks, the agent is instructed to use its bash tool and verify changes before reporting success.

## Documentation

- `requirements.md` records the reverse-engineered requirements from the current implementation.
- `implementation.md` summarizes the current code design and control flow.
- `AGENTS.md` gives future agents feature-specific maintenance instructions.
- `CHANGELOG.md` tracks lifecycle changes for this feature folder.