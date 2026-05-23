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

Subagents use Claude Code style Markdown files with only `name` and `description` metadata:

```markdown
---
name: subagent-name
description: Clear description of when to use this subagent and what it does.
---

Subagent system prompt body.
```

Do not add other frontmatter keys in this stage. The installer converts this source format into each supported code agent's native format.

## Install

After creating, updating, deleting, or disabling subagents, run:

```bash
core/bin/subagent-install
```

The installer reconciles the code agent folders for Claude Code, Codex, Gemini CLI, and OpenCode.
