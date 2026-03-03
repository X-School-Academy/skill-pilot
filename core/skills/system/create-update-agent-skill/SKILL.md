---
name: create-update-agent-skill
description: Create or update agent skills following the agent skill specification. Use when user asks to create a new skill or update an existing skill.
---

# AI Builder - Create/Update Agent Skill

This skill helps you create new agent skills or update existing ones following the Agent Skills specification.

## When to Use This Skill

- User asks to create a new skill
- User asks to update an existing skill
- User wants to add functionality as a reusable skill
- User wants to modify skill documentation or behavior

## Your Roles in This Skill

- **Project Manager**: Coordinate the skill creation/update process, ensure all required sections are included, and verify adherence to specifications.
- **Backend Developer**: Implement the skill structure, write clear instructions, and ensure proper file organization.
- **Technical Writer**: Document the skill clearly with examples, usage guidelines, and role communication patterns.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps to create or update an agent skill:

### Step 1: Understand the Requirements

  **Ask the user for clarification if needed:**
   - What is the skill name? (lowercase, hyphens only)
   - What does the skill do?
   - When should this skill be used?
   - What roles are involved in this skill?
   - Which category does it belong to? (see Step 2)

### Step 2: Determine Skill Category and Location

There are four skill categories. If the user does not specify a category, default to **user**.

| Category | Directory | Naming | When to use |
|---|---|---|---|
| **user** (default) | `core/skills/user/` | `{name}` (no prefix) | User-created personal skills |
| **dev-swarm** | `dev-swarm/skills/` | `dev-swarm-{name}` | Software-development agent skills |
| **system** | `core/skills/system/` | `{name}` (no prefix) | Core system skills |
| **third-party** | `core/skills/third-party/` | `{name}` (no prefix) | Imported or copied from other projects |

**For new skills:**

1. Create the skill directory under the correct category folder
2. Create any needed subdirectories:
   - `references/` for reference documentation (preferred)
   - `scripts/` for executable scripts (if needed)
   - `assets/` for static resources (if needed)

**For existing skills:**

1. Locate the existing skill directory under its category folder
2. Read the existing `SKILL.md` to understand current structure

### Step 3: Create/Update SKILL.md

The `SKILL.md` file must contain:

#### Required Frontmatter

```yaml
---
name: skill-name
description: A clear description of what this skill does and when to use it.
---
```

**Frontmatter requirements:**
- `name`: Must match directory name, lowercase, hyphens only, max 64 characters. Only dev-swarm skills use the `dev-swarm-` prefix.
- `description`: Max 1024 characters, describe what it does AND when to use it

**Optional frontmatter fields:**
- `metadata`: Additional key-value metadata (author, version, etc.)
- `allowed-tools`: Pre-approved tools (experimental)

#### Required Sections

**1. Skill Title and Introduction**
```markdown
# AI Builder - {Skill Name}

Brief introduction describing what this skill does.
```

**2. When to Use This Skill**
```markdown
## When to Use This Skill

- Bullet point describing use case 1
- Bullet point describing use case 2
- etc.
```

**3. Your Roles in This Skill** (REQUIRED)
```markdown
## Your Roles in This Skill

- **Role Name**: Description of what this role does in this skill
- **Role Name**: Description of what this role does in this skill
```

Choose roles from file `dev-swarm/docs/dev-swarm-roles.md`:

**4. Role Communication** (REQUIRED)
```markdown
## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.
```

**5. Instructions**
```markdown
## Instructions

Follow these steps in order:

### Step 1: {Step Title}

Detailed instructions for this step...

### Step 2: {Step Title}

Detailed instructions for this step...

(Continue with all necessary steps)
```

#### Recommended Sections

- **Expected Output**: Describe what the skill produces (RECOMMENDED)
- **Key Principles**: List important guidelines (RECOMMENDED)
- **Common Issues**: Document known problems and solutions (RECOMMENDED)

**Workflow-specific rule:**
- If the user says the skill is for workflow usage, include this exact sentence in the skill instructions or expected output section:
  `Output result as plain text. If the user asked to save it to a file, write it there.`

#### Optional Sections

- **Examples**: Only include if the user specifically requests examples or if they are truly necessary for understanding. Prefer keeping skills concise.

### Step 4: Create Reference Files (IMPORTANT)

**ALWAYS use reference files to keep SKILL.md concise.** Prefer routing details to `references/` files rather than embedding everything in `SKILL.md`.

**When to use reference files:**
- **Multiple tools/technologies**: Create separate reference files for each tool (e.g., `references/claude-code.md`, `references/gemini-cli.md`)
- **Platform-specific instructions**: Create files for different platforms (e.g., `references/macos.md`, `references/windows.md`, `references/linux.md`)
- **Installation methods**: Create files for different installation approaches (e.g., `references/npm-install.md`, `references/docker-setup.md`)
- **Detailed configurations**: Move lengthy config details to reference files
- **Different frameworks/libraries**: Separate file per framework (e.g., `references/react.md`, `references/vue.md`)

**Use conditional routing format in SKILL.md:**

```markdown
- If installing **tool-a**, refer to `references/tool-a.md`
- If installing **tool-b**, refer to `references/tool-b.md`
- If on **macOS**, refer to `references/macos.md`
- If on **Windows**, refer to `references/windows.md`
```

**Reference file guidance:**
- Create reference files PROACTIVELY - don't wait to be asked
- Keep SKILL.md under 200 lines when possible by using references
- Keep reference files under 500 lines when possible
- Use clear, descriptive filenames
- Link to them from `SKILL.md` using relative paths
- Use a symbolic link for any file under `dev-swarm/` in the project's root if asked to reference an entire file

### Step 5: Add Scripts (if needed)

If your skill includes executable scripts:

1. **Create `scripts/` directory**
2. **Use `core/bin/python`** for all Python helper scripts — this symlink points to `core/engine/.venv/bin/python` and has access to all packages installed in the engine venv.
3. **Install dependencies** with `core/bin/uv-install <package>` from repo root (this runs `uv add` in `core/engine/`). Do not use `pip` for new packages.
4. **Add scripts** that are:
   - Self-contained or clearly document dependencies
   - Include helpful error messages
   - Handle edge cases gracefully
5. **Temp files**: If the skill creates temporary or intermediate files, save them under `.skillpilot/temp/` with readable but unique names using a timestamp suffix. Example: `element-bbox-1739712000.png`, `quadrants-1739712000/`.

### Step 6: Validate the Skill

**Check the following:**

1. **Frontmatter validation:**
   - [ ] `name` matches directory name
   - [ ] `name` is lowercase with hyphens only
   - [ ] Only dev-swarm skills use the `dev-swarm-` prefix
   - [ ] Skill is in the correct category folder
   - [ ] `description` is clear and under 1024 characters

2. **Required sections present:**
   - [ ] Skill title and introduction
   - [ ] "When to Use This Skill"
   - [ ] "Your Roles in This Skill"
   - [ ] "Role Communication"
   - [ ] "Instructions"

3. **Content quality:**
   - [ ] Instructions are clear and step-by-step
   - [ ] Roles are appropriate for the task
   - [ ] File references use relative paths
   - [ ] `SKILL.md` is concise (under 200 lines preferred), defers details to references
   - [ ] Reference files created for different tools/platforms/methods
   - [ ] No steps to update documentation files (AGENTS.md, README.md, etc.) unless explicitly requested by user

4. **File structure:**
   - [ ] No references outside skill folder (unless explicitly required)
   - [ ] Reference files are focused and appropriately sized
   - [ ] Scripts are properly documented

### Step 7: Verify and Install the Skill

After creating or updating the skill, run the CLI tools to verify and install it:

1. **Verify** the skill against the specification:
   ```bash
   core/bin/skill-verify <path-to-skill-directory>
   ```
   Example: `core/bin/skill-verify core/skills/system/my-skill`

   Fix any errors reported and re-run until verification passes.

2. **Install** all skills (re-links verified skills into `.agent/skills/`):
   ```bash
   core/bin/skill-install
   ```
   This discovers skills under `core/skills/` and `dev-swarm/skills/`, verifies each one, and symlinks passing skills into `.agent/skills/`. It also removes broken symlinks and skips disabled skills listed in `config/disabled_skills.json5`.

   Confirm the output shows the new skill was installed successfully.

### Step 8: Ask for User Confirmation

Show the user:
1. The skill name and location
2. Summary of what the skill does
3. List of files created/updated
4. Verify and install results

Ask: "The skill has been created/updated. Would you like me to make any changes?"

## Key Principles

- **Follow the specification**: Always adhere to file `dev-swarm/docs/agent-skill-specification.md`
- **Progressive disclosure**: ALWAYS keep SKILL.md concise (under 200 lines preferred), move detailed content to reference files
- **Use reference files proactively**: Create separate reference files for different tools, platforms, installation methods, frameworks, etc.
- **No unsolicited documentation updates**: NEVER add steps to update AGENTS.md, README.md, or other documentation files unless the user explicitly requests it
- **Clear instructions**: Write step-by-step instructions that are easy to follow
- **Appropriate roles**: Choose roles that match the task from file `dev-swarm/docs/dev-swarm-roles.md`
- **Self-contained**: Don't reference files outside the skill folder unless required
- **Role communication**: Always include the role communication pattern
- **Validate thoroughly**: Check all requirements before considering the skill complete
- **Naming convention**: Only dev-swarm skills use the `dev-swarm-` prefix; system, user, and third-party skills use plain names
- **Minimize examples**: Only include Examples section if truly necessary or explicitly requested
- **Workflow output contract**: If the user says the skill is for workflow usage, the skill must explicitly include `Output result as plain text. If the user asked to save it to a file, write it there.`

## Common Issues

**Issue: Skill name doesn't match directory**
- Solution: Ensure the `name` in frontmatter exactly matches the directory name

**Issue: Skill in wrong category folder**
- Solution: dev-swarm skills go in `dev-swarm/skills/`, system in `core/skills/system/`, user in `core/skills/user/`, third-party in `core/skills/third-party/`

**Issue: Missing required sections**
- Solution: Always include "Your Roles in This Skill" and "Role Communication"

**Issue: Description too vague**
- Solution: Describe both WHAT the skill does and WHEN to use it

**Issue: SKILL.md too long (over 200 lines)**
- Solution: Move detailed content to reference files. Create separate files for different tools, platforms, or methods

**Issue: Including steps to update documentation files without user request**
- Solution: NEVER add steps like "Update AGENTS.md" or "Update README.md" unless the user explicitly asks for it

**Issue: Not using reference files when there are multiple tools/platforms**
- Solution: Always create separate reference files for each tool, platform, or installation method instead of putting everything in SKILL.md
