We need to create a Skill Pilot agent in the folder `core/engine/skill_pilot_agent/`.

Use the package `openai-agents`.

Update `config/ai_providers.json5` to add an optional key named `default.background_llm`. If the value is set and is `"skill-pilot"`, then Skill Pilot should use the Skill Pilot agent for any LLM background tasks that do not require a tmux terminal session.

The Skill Pilot agent will use an OpenAI-compatible API endpoint configured by the following environment variables:

* `SKILL_PILOT_BASE_URL`
* `SKILL_PILOT_API_KEY`

`SKILL_PILOT_BASE_URL` is the OpenAI-compatible API base URL for the Skill Pilot agent, for example:

```bash
http://localhost:8000/v1
```

The agent will be wrapped as:

```bash
core/bin/skill-pilot-agent
```

This CLI should be similar to the other AI agent CLIs, so it remains compatible with the current codebase.

## CLI Arguments

The agent will support the following arguments:

* `--sandbox yes|no`: The default is `yes`. When enabled, the agent runs in a sandbox environment.
* `--auto yes|no`: The default is `yes`. When enabled, the agent can automatically use tools without asking for confirmation.
* `--network yes|no`: The default is `no`. When disabled, network access is not allowed.

For now, we will only implement the default behavior for the `sandbox`, `auto`, and `network` arguments.

## Other Agent Arguments

* `--agent-dir <path>`: The root directory where the agent operates. The default is the current project root directory.
* `--log-level <level>`: The log level for the agent. The default is `info`.
* `--max-retries <number>`: The maximum number of retries for failed tasks. The default is `3`.
* `--timeout <seconds>`: The timeout for each task. The default is `60` seconds.
* `--bash-commands <command1,command2,...>`: A comma-separated list of bash commands that the agent is allowed to use. The default is all available commands.
* `--skills-dir <path>`: The directory where the agent can find skills. The default is `.agent` under the project root.
* `--skills <skill1,skill2,...>`: A comma-separated list of skills that the agent can use from the skills directory. The default is all available skills.

## Agent Behavior

The agent should respect any `AGENTS.md` files found in the `agent-dir` directory or its subdirectories.

The agent should only use bash commands as tools.
