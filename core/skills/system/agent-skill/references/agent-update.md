# Update Subagent

Use this reference when the user asks to edit, rename, reorganize, fix, disable, or remove an existing Skill Pilot subagent.

## Steps

### Step 1: Locate the Existing Subagent

If the user gives a path, use that path. If the user gives a name, search:

- `core/subagents/user/`
- `core/subagents/system/`

Use `rg` first where possible:

```bash
rg --files core/subagents/user core/subagents/system -g '*.md'
rg -n "<subagent-name-or-keyword>" core/subagents/user core/subagents/system -g '*.md'
```

Read the existing Markdown file before editing.

### Step 2: Understand the Requested Change

Clarify only when needed:

- Whether behavior should change or only wording/structure should change.
- Whether the subagent should move between `user` and `system`.
- Whether the subagent name or filename should change.
- Whether the subagent should be disabled or deleted.

If the update renames the subagent, update both frontmatter `name` and filename unless the user asks otherwise.

### Step 3: Preserve Source Format

The source file must remain Claude Code style Markdown with only:

```yaml
name: subagent-name
description: Clear selection description.
```

Do not add fields such as `tools`, `model`, `mode`, or permissions to the source. The installer adds target-specific fields such as OpenCode `mode: subagent`.

### Step 4: Apply the Change

For prompt updates, keep changes focused on the requested behavior.

For disables, add the subagent name to:

```text
config/disabled_subagents.json5
```

For removal, delete the source Markdown file only when the user clearly asked to remove it.

### Step 5: Install and Reconcile

Run:

```bash
core/bin/subagent-install
```

The installer should:

- update generated files for active subagents
- remove generated files for disabled subagents
- remove generated files whose source subagent no longer exists

### Step 6: Validate

Check:

- active subagents generate target files in all supported folders
- disabled or removed subagents are absent from all supported target folders
- OpenCode output includes `mode: subagent`
- no unrelated subagent or skill files were changed
