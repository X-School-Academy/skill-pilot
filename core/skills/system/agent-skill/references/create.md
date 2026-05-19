# Create Agent Skill

Use this reference when the user asks to create, add, teach, or build a new reusable agent skill.

## Steps

### Step 1: Understand the Requirements

Ask for clarification only when needed:

- What is the skill name? Use lowercase hyphenated naming.
- What does the skill do?
- When should this skill be used?
- What roles are involved?
- Which category should contain it?

### Step 2: Determine Skill Category and Location

Use these categories:

| Category | Directory | Naming | When to use |
|---|---|---|---|
| user | `core/skills/user/` | `{name}` | User-created personal skills |
| dev-swarm | `dev-swarm/skills/` | `dev-swarm-{name}` | Software-development agent skills |
| system | `core/skills/system/` | `{name}` | Core system skills |
| third-party | `core/skills/third-party/` | `{name}` | Imported or copied skills |

If the user does not specify a category, default to `user`.

Create the skill directory under the correct category folder. Create subdirectories only when useful:

- `references/` for detailed instructions or reference documentation.
- `scripts/` for executable helpers.
- `assets/` for static resources.

### Step 3: Create `SKILL.md`

The file must contain frontmatter:

```yaml
---
name: skill-name
description: A clear description of what this skill does and when to use it.
---
```

Frontmatter rules:

- `name` must match the directory name.
- `name` must be lowercase with hyphens only and at most 64 characters.
- Only dev-swarm skills use the `dev-swarm-` prefix.
- `description` must be under 1024 characters.
- Description should focus on user intent, capability, outputs, triggers, and task context.
- Do not include internal CLI names, transports, file layouts, or implementation details unless required for skill selection.

Required sections:

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

### Step 4: Create Reference Files

Always prefer reference files to keep `SKILL.md` concise.

Use references when the skill includes:

- multiple modes, tools, technologies, or platforms
- detailed command usage
- detailed validation rules
- examples that would make `SKILL.md` long

Keep `SKILL.md` focused on routing and triggers. Put usage details, commands, prompt patterns, flags, inputs, outputs, and decision points in `references/`.

Tool references should describe how to use tools effectively, not internal transport, payload, protocol, adapter, or backend plumbing details unless operationally required.

### Step 5: Add Scripts If Needed

If the skill includes executable scripts:

1. Create `scripts/`.
2. Use `python-package-runtime` whenever Python package installs, Python helper scripts, or package-provided CLIs are needed.
3. Keep scripts self-contained and include helpful errors.
4. Put temp files under `.skillpilot/temp/` with readable unique names.

### Step 6: Validate the Skill

Check:

- `name` matches the directory.
- category and prefix are correct.
- description is clear and under 1024 characters.
- required sections are present.
- `SKILL.md` stays concise and routes details to references.
- references are inside the skill folder unless explicitly required.
- no unsolicited updates to AGENTS.md, README.md, or docs unless the user requested them.

If the user says the skill is for workflow usage, include this sentence in the skill instructions or expected output:

`Output result as plain text. If the user asked to save it to a file, write it there.`

For workflow usage, also include enough basic context in the plain-text output so downstream agents can understand what the result represents.

### Step 7: Verify and install

Run:

```bash
core/bin/skill-verify <path-to-skill-directory>
```

Fix any errors and rerun until verification passes.

Then install the new skill with `core/bin/skill-install`. Pick the mode that matches the situation:

- `core/bin/skill-install` (or `--all`): default. Installs every discovered skill that is not listed in `config/disabled_skills.json5`. Use after refactors that may have affected many skills.
- `core/bin/skill-install --add <skill-name>`: install just the newly created skill. Ignores `config/disabled_skills.json5` (so it works even if the name is disabled) and leaves other installed skills untouched. Use this for a single new skill.
- `core/bin/skill-install --skills s1,s2,...`: install exactly the listed skills, ignoring `config/disabled_skills.json5`. Removes any installed symlink that is not in the list. Use this when you want the active skill set to match an exact list.

## Key Principles

- Follow `dev-swarm/docs/agent-skill-specification.md`.
- Keep `SKILL.md` concise and use progressive disclosure.
- Write descriptions for skill selection, not implementation internals.
- Create reference files proactively.
- Choose roles that match the task.
- Validate before reporting completion.
