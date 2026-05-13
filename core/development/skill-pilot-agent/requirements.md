# Skill Pilot Agent Requirements

## Goal

Create a Skill Pilot agent for background LLM tasks that do not require a terminal or tmux session.

The agent should use an OpenAI-compatible API endpoint and should behave like the other AI agent CLIs used by Skill Pilot, so it can be selected by configuration and invoked as a background provider.

## Provider Selection

- Skill Pilot must support an optional default setting named `background_llm` in `config/ai_providers.json5`.
- When `background_llm` is set to `skill-pilot`, background LLM tasks that do not require a terminal session should use the Skill Pilot agent.
- The Skill Pilot agent must be selected only through `default.background_llm: "skill-pilot"`.
- Setting `background_llm` must not change the normal default LLM provider.
- The normal default LLM provider remains controlled by `default.llm`.
- Terminal and tmux agent sessions must continue using the normal LLM provider selection.
- If the Skill Pilot background agent is not selected, unavailable, or not configured, background LLM tasks should continue using the existing default LLM behavior.

## Endpoint Configuration

The Skill Pilot agent must use these environment variables:

- `SKILL_PILOT_BASE_URL`
- `SKILL_PILOT_API_KEY`
- `SKILL_PILOT_MODEL`

`SKILL_PILOT_BASE_URL` is the OpenAI-compatible API base URL.

`SKILL_PILOT_API_KEY` is the API key for that endpoint.

`SKILL_PILOT_MODEL` is the default model name used by the Skill Pilot agent.

The agent should fail clearly when required endpoint configuration is missing.

## Agent CLI

The agent must be available through a command named:

```bash
core/bin/skill-pilot-agent
```

The CLI should accept a user prompt and return the final answer in a format compatible with existing background LLM calls.

The CLI must support these options:

- `--sandbox yes|no`
- `--auto yes|no`
- `--network yes|no`
- `--model <model>`
- `--agent-dir <path>`
- `--agent-file <path|none>`
- `--log-level <level>`
- `--max-retries <number>`
- `--timeout <seconds>`
- `--bash-commands <command1,command2,...>`
- `--skills-dir <path>`
- `--skills <skill1,skill2,...|none>`

Default behavior:

- `--sandbox` defaults to `yes`.
- `--auto` defaults to `yes`.
- `--network` defaults to `no`.
- `--model` defaults to `SKILL_PILOT_MODEL`.
- `--agent-dir` defaults to the configured project root.
- `--agent-file` defaults to `AGENTS.md`.
- `--log-level` defaults to `info`.
- `--max-retries` defaults to `3`.
- `--timeout` defaults to `60` seconds.
- `--bash-commands` defaults to all available commands.
- `--skills-dir` defaults to the agent skill directory under the project root.
- `--skills` defaults to all available skills.

The first release only needs to support the default behavior for `sandbox`, `auto`, and `network`. Unsupported non-default behavior should fail clearly rather than silently pretending to work.

## Agent Instructions

- The agent must load only the root agent instruction file from the configured agent directory.
- The agent must not automatically load nested agent instruction files.
- The agent must allow the caller to skip agent instruction loading.
- If subdirectory-specific instructions are needed later, they should be supplied intentionally for that task rather than loaded automatically.

## Skills

- The first release must support loading skill instructions.
- The caller must be able to specify the skill directory.
- The caller must be able to load all available skills, selected skills, or no skills.
- Skill loading must respect project ignore rules so ignored files are not read or processed.

## Tooling

- The agent should only use bash commands as tools.
- The caller must be able to restrict which bash commands are allowed.
- When network access is disabled, the agent must use the strongest available network restriction.
- If strong network restriction is required but not available, the agent must fail safely.
- The agent should not claim that files were created, edited, counted, or verified unless tool output confirms it.

## Acceptance Criteria

- The Skill Pilot agent can be invoked as a CLI command.
- The Skill Pilot agent can be selected for background LLM tasks through `default.background_llm: "skill-pilot"` in `config/ai_providers.json5`.
- Normal default LLM selection remains unchanged unless configured separately.
- Terminal and tmux sessions are not rerouted to the Skill Pilot background agent.
- The agent uses the configured OpenAI-compatible endpoint and model.
- The CLI supports the required options and defaults.
- The agent loads only the intended root agent instruction file by default.
- The agent supports loading all skills, selected skills, and no skills.
- The agent exposes only bash tooling.
- The agent provides clear failures for missing configuration and unsupported first-release modes.
