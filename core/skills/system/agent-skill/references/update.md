# Update Agent Skill

Use this reference when the user asks to edit, update, rename, reorganize, fix, or improve an existing agent skill.

## Steps

### Step 1: Locate the Existing Skill

If the user gives a skill path, use that path. If the user gives a skill name, look under these folders:

- `core/skills/user/`
- `dev-swarm/skills/`
- `core/skills/system/`
- `core/skills/third-party/`

Read the existing `SKILL.md` to understand the current behavior before editing.

### Step 2: Understand the Requested Change

Clarify only when needed:

- Whether behavior should change or only wording/structure should change.
- Whether the skill name or folder should be renamed.
- Whether detailed instructions should move into references.
- Whether scripts, assets, or validation behavior need updates.

If the update renames the skill, rename the skill folder too.

### Step 3: Update `SKILL.md`

Ensure frontmatter stays valid:

- `name` matches the directory name.
- `name` is lowercase with hyphens only and at most 64 characters.
- Only dev-swarm skills use the `dev-swarm-` prefix.
- `description` is under 1024 characters.
- `description` focuses on capability, trigger phrases, outputs, and task context.

Required sections must remain present:

- Skill title and introduction.
- `When to Use This Skill`.
- `Your Roles in This Skill`.
- `Role Communication`.
- `Instructions`.

Use this role communication text:

```markdown
As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.
```

### Step 4: Move Detail Into References

Always prefer reference files to keep `SKILL.md` concise.

Move detailed content into `references/` when it covers:

- different modes or use cases
- command usage
- platform-specific instructions
- tool usage details
- long examples or validation rules

Keep references focused and user-facing. Document how to use commands, tools, prompts, inputs, outputs, and decision points. Avoid internal transport, payload, protocol, adapter, or backend plumbing details unless they are required for correct use.

### Step 5: Preserve Behavior

When the user asks for a rename or organization change, preserve current behavior unless they explicitly request behavior changes.

Do not add steps to update AGENTS.md, README.md, or other documentation files unless the user explicitly asks.

For workflow skills, preserve this output contract when applicable:

`Output result as plain text. If the user asked to save it to a file, write it there.`

Also preserve enough basic context in the plain-text output so downstream agents can understand what the result represents.

### Step 6: Validate

Check:

- frontmatter name matches directory
- category and prefix are correct
- description is clear and under 1024 characters
- required sections are present
- `SKILL.md` is concise and routes details to references
- references are inside the skill folder unless explicitly required
- scripts remain self-contained if present
- renamed references or folders have no stale internal links

### Step 7: Verify

Run:

```bash
core/bin/skill-verify <path-to-skill-directory>
```

Fix any errors and rerun until verification passes.

## Common Issues

- Skill name does not match directory: update frontmatter or rename the folder.
- Skill is in the wrong category: move it to the correct skill category folder.
- Description is too vague: rewrite around user intent, triggers, capability, and output.
- `SKILL.md` is too long: move mode-specific instructions into references.
- Tool reference leaks internals: rewrite around usage and decision points.
- Documentation files are updated without request: revert those unrelated documentation changes.
