# Agent Skill Workflows

Use this reference when the user asks to create, update, find, or dynamically use an agent skill.

## Route by Action

- Create a new skill: use `references/skill-create.md`.
- Update, rename, reorganize, or fix an existing skill: use `references/skill-update.md`.
- Find or dynamically load an existing skill that is not active: use `references/skill-find.md`.

Open only the action-specific reference that matches the user's request. Load additional files only when the action reference requires them.

## Locations

Agent skills live under these folders:

- `core/skills/user/`
- `dev-swarm/skills/`
- `core/skills/system/`
- `core/skills/third-party/`

Default to `core/skills/user/` for personal user-created skills unless the user specifies another category.

## Verification

Use the verification and install steps in the selected action reference. For most single-skill edits, prefer:

```bash
core/bin/skill-verify <path-to-skill-directory>
core/bin/skill-install --add <skill-name>
```
