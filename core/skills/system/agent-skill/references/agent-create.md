# Create Subagent

Use this reference when the user asks to create, add, or build a reusable Skill Pilot subagent.

## Steps

### Step 1: Understand the Requirements

Ask for clarification only when needed:

- What is the subagent name? Use lowercase hyphenated naming.
- What should the subagent do?
- When should a coding agent delegate work to it?
- Should it be a system subagent or user subagent?

### Step 2: Choose Location

Use these locations:

| Level | Directory | When to use |
|---|---|---|
| user | `core/subagents/user/` | User-created personal or project-specific subagents |
| system | `core/subagents/system/` | Core reusable subagents maintained by Skill Pilot |

If the user does not specify a level, default to `user`.

### Step 3: Create the Markdown Definition

Create one Markdown file under the chosen directory. The filename should normally match the subagent name:

```text
core/subagents/user/<subagent-name>.md
```

The file must use first-stage subagent frontmatter:

```markdown
---
name: subagent-name
description: A clear description of when to use this subagent and what it does.
---

You are a focused subagent. Define the role, scope, output format, and constraints here.
```

Frontmatter rules:

- `name` is required.
- `description` is required.
- `name` should use lowercase letters, numbers, hyphens, and underscores.
- Keep `description` useful for selection: triggers, capability, expected output, and task context.
- Optional per-agent override blocks are supported: `claude`, `codex`, `gemini`, `opencode`. The installer flattens the matching block into that target's native frontmatter. Do not redeclare `name`, `description`, or `mode` inside an override block.
- Only use keys documented in `references/agent.md` for each agent. Inventing keys can break agent loading.

Example with per-agent overrides (every key shown is documented for that agent):

```markdown
---
name: my-subagent
description: When to use and what it does.
claude:
  tools: Read, Grep, Glob
  model: inherit
codex:
  model_reasoning_effort: high
gemini:
  model: inherit
  temperature: 0.2
opencode:
  permission:
    edit: deny
---

Subagent system prompt body.
```

See `references/agent.md` for the full per-agent key tables.

### Step 4: Write the Prompt Body

Keep the body focused on behavior:

- role and responsibility
- inputs the subagent should inspect
- expected output shape
- boundaries and things to avoid
- verification or review criteria when relevant

Avoid tool-specific metadata in the body unless it is necessary for correct behavior.

### Step 5: Install

Run:

```bash
core/bin/subagent-install
```

The installer writes native definitions to:

- `.claude/agents/*.md`
- `.codex/agents/*.toml`
- `.gemini/agents/*.md`
- `.opencode/agents/*.md`

### Step 6: Validate

Check:

- the source file exists under `core/subagents/system/` or `core/subagents/user/`
- the source frontmatter has only `name` and `description`
- generated files exist in each supported code agent folder
- OpenCode output includes `mode: subagent`
- disabling or deleting the subagent and rerunning install removes generated target files when that behavior is part of the task
