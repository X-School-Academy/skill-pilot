# Subagent Workflows

Use this reference when the user asks to create, update, find, or install a Skill Pilot subagent for coding agents.

## Route by Action

- Create a new subagent: use `references/agent-create.md`.
- Update, rename, reorganize, or fix an existing subagent: use `references/agent-update.md`.
- Find or dynamically use a subagent: use `references/agent-find.md`.

Open only the action-specific reference that matches the user's request. Load additional files only when the action reference requires them.

## Locations

Skill Pilot supports two subagent levels:

- System subagents: `core/subagents/system/`
- User subagents: `core/subagents/user/`

Default to `core/subagents/user/` for personal user-created subagents unless the user specifies `system`.

## First-Stage Format

Subagents use Claude Code style Markdown files with `name` and `description`, plus optional per-agent override blocks:

```markdown
---
name: subagent-name
description: Clear description of when to use this subagent and what it does.
claude:
  tools: [Read, Grep, Bash]
  model: opus
codex:
  model: gpt-5
gemini:
  model: gemini-2.5-pro
opencode:
  permission:
    edit: deny
---

Subagent system prompt body.
```

Supported frontmatter keys:

- `name` (required)
- `description` (required)
- `claude`, `codex`, `gemini`, `opencode` (optional): each is a mapping of agent-level params that the installer flattens into that target's native frontmatter.
- The installer rejects `name`, `description`, and `mode` inside an override block (they are set by the installer itself).
- Only use keys from the per-agent tables below. Unknown keys may be silently ignored by the target agent or break loading — do not invent fields.

The installer converts this source format into each supported code agent's native format, merging the matching agent block into the generated file.

### `claude` overrides (Claude Code, `.claude/agents/*.md`)

| Key | Type / values | Notes |
| --- | --- | --- |
| `tools` | comma-separated string or YAML list | Allowlist of tool names. Omit to inherit all tools. |
| `disallowedTools` | comma-separated string or YAML list | Denylist subtracted from inherited or allowlisted tools. |
| `model` | `sonnet`, `opus`, `haiku`, full model id (e.g. `claude-opus-4-7`), or `inherit` | Defaults to `inherit`. |
| `permissionMode` | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan` | Permission mode override. |
| `maxTurns` | integer | Cap on agentic turns before the subagent stops. |
| `skills` | YAML list of skill names | Skills preloaded into the subagent's context at startup. |
| `mcpServers` | mapping | Either reference an already-configured server by name, or inline a full MCP server config. |
| `hooks` | mapping | Lifecycle hooks scoped to this subagent. |
| `memory` | `user`, `project`, `local` | Enables persistent memory scope. |
| `background` | boolean | Always run as a background task. |
| `effort` | `low`, `medium`, `high`, `xhigh`, `max` | Effort level (model-dependent). |
| `isolation` | `worktree` | Run in a temporary git worktree. |
| `color` | `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan` | Display color. |
| `initialPrompt` | string | Auto-submitted as the first user turn when run as the main session agent. |

### `codex` overrides (Codex CLI, `.codex/agents/*.toml`)

| Key | Type | Notes |
| --- | --- | --- |
| `model` | string | Model id; inherits from the parent session if omitted. |
| `model_reasoning_effort` | string | Reasoning effort level; inherits if omitted. |
| `sandbox_mode` | string | Execution sandbox policy; inherits if omitted. |
| `nickname_candidates` | array of strings | Non-empty, unique display-name pool for spawned agents. |
| `mcp_servers` | table | MCP server configurations. |
| `skills.config` | array | Skill definitions and settings. |

Other standard `config.toml` keys are technically accepted but stick to the table above unless you have a specific need.

### `gemini` overrides (Gemini CLI, `.gemini/agents/*.md`)

| Key | Type / values | Notes |
| --- | --- | --- |
| `kind` | `local` (default) or `remote` | Agent kind. |
| `tools` | YAML list | Tool names this agent can use; supports wildcards such as `*` and `mcp_*`. |
| `mcpServers` | mapping | Inline MCP server configs isolated to this agent. |
| `model` | string | Specific model; defaults to `inherit`. |
| `temperature` | number `0.0`–`2.0` | Defaults to `1`. |
| `max_turns` | integer | Maximum conversation turns before the agent must return. |
| `timeout_mins` | integer | Maximum execution time in minutes; defaults to `10`. |

### `opencode` overrides (OpenCode, `.opencode/agents/*.md`)

| Key | Type / values | Notes |
| --- | --- | --- |
| `model` | string in `provider/model` form (e.g. `anthropic/claude-sonnet-4-20250514`) | Selects model. |
| `temperature` | number `0.0`–`1.0` | Defaults to model-specific value. |
| `top_p` | number `0.0`–`1.0` | Alternative sampling control. |
| `steps` | integer | Max agentic iterations before text-only response. |
| `disable` | boolean | Disable the agent. |
| `hidden` | boolean | Hide from `@` autocomplete (subagents only). |
| `permission` | object (`edit`, `bash`, `read`, ...) | Fine-grained access control. Wildcard patterns supported. |
| `color` | hex color or theme color | Visual appearance. |

`mode` is set to `subagent` by the installer; do not declare it in the override block.

## Install

After creating, updating, deleting, or disabling subagents, run:

```bash
core/bin/subagent-install
```

The installer reconciles the code agent folders for Claude Code, Codex, Gemini CLI, and OpenCode.
