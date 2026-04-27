We need to create a Skill Pilot agent in the folder `core/engine/skill_pilot_agent/`.

Use the package `openai-agents`.

Update `config/ai_providers.json5` to add support for an optional key named `default.background_llm`. If the value is set and is `"skill-pilot"`, then Skill Pilot should use the Skill Pilot agent for any LLM background tasks that do not require a tmux terminal session.

The Skill Pilot agent must be selected only through `default.background_llm: "skill-pilot"`. It should not become the normal default LLM provider unless `default.llm` is also explicitly changed elsewhere.

The Skill Pilot agent will use an OpenAI-compatible API endpoint configured by the following environment variables:

* `SKILL_PILOT_BASE_URL`
* `SKILL_PILOT_API_KEY`
* `SKILL_PILOT_MODEL`

`SKILL_PILOT_MODEL` is the default model name used by the Skill Pilot agent.

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
* `--model <model>`: Overrides the default model from `SKILL_PILOT_MODEL`.

For now, we will only implement the default behavior for the `sandbox`, `auto`, and `network` arguments.

## Other Agent Arguments

* `--agent-dir <path>`: The root directory where the agent operates. The default is the current project root directory.
* `--log-level <level>`: The log level for the agent. The default is `info`.
* `--max-retries <number>`: The maximum number of retries for failed tasks. The default is `3`.
* `--timeout <seconds>`: The timeout for each task. The default is `60` seconds.
* `--bash-commands <command1,command2,...>`: A comma-separated list of bash commands that the agent is allowed to use. The default is all available commands.
* `--skills-dir <path>`: The directory where the agent can find skills. The default is `.agent` under the project root.
* `--skills <skill1,skill2,...>`: A comma-separated list of skills that the agent can use from the skills directory. The default is all available skills.

The first release must support `--skills-dir` and `--skills`, including loading the selected skill instructions for the agent.

## Agent Behavior

The agent should load only the root `AGENTS.md` file found directly in the `agent-dir` directory.

The agent should not load all nested `AGENTS.md` files at once. If subdirectory-specific instructions are needed later, they should be added to the task-specific system prompt or loaded selectively for that task context.

The agent should only use bash commands as tools.

When `--network no` is set, the agent should use strict OS-level network enforcement if `openai-agents` supports it. If `openai-agents` does not support strict network enforcement, the implementation should document that limitation and fail safely or use the strongest available enforcement.
