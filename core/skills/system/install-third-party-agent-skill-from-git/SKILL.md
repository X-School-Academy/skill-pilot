---
name: install-third-party-agent-skill-from-git
description: Import a third-party agent skill from a Git or GitHub repository using sparse checkout, copy it into the target skill directory, normalize SKILL.md to local rules, and handle license files consistently, then verify and install. Use when the user asks to install a skill from a repo URL.
compatibility: Requires git, bash, and local access to this repository workspace.
---

# AI Builder - Install Third-Party Skill From Git

Import and normalize a third-party skill from a remote repository in a controlled, repeatable flow.

## When to Use This Skill

- User gives a Git or GitHub URL and asks to install a skill
- Only a subfolder in the remote repository is needed
- User wants local normalization to this project's skill rules
- User wants verification and installation done at the end

## Your Roles in This Skill

- **Project Manager**: Confirm scope, destination, and change boundaries
- **Backend Developer (Engineer)**: Execute sparse checkout, copy, and normalization steps
- **Technical Writer**: Keep SKILL.md and LICENSE update notes clear and auditable
- **Security Engineer**: Review trust assumptions before pulling third-party code

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Identify source repo and skill folder

Collect and confirm:

1. Remote URL (HTTPS or SSH), for example `https://github.com/org/repo.git`
2. Exact skill folder path in that repo, for example `skills/my-skill`
3. Destination parent folder:
   - Default: `core/skills/third-party/`
   - Or user-provided destination

Before cloning, state that third-party code is untrusted until reviewed.

### Step 2: Sparse checkout only the skill folder into `.skillpilot/temp/`

Run manual commands (no helper scripts):

1. Create a unique temp directory under `.skillpilot/temp/`
2. Clone with `--no-checkout` and `--filter=blob:none`
3. Use sparse checkout to materialize only the requested skill folder
4. Copy the imported folder into destination parent directory

For command details, see `references/sparse-checkout.md`.

### Step 3: Copy to third-party skills folder (or user-requested destination)

Default target is:

- `core/skills/third-party/<skill-name>/`

If user explicitly requests another path, use it and report the final path.
Prefer repository-relative paths in commands and reports.

### Step 4: Normalize SKILL.md to create/update skill rules

After copy, update `SKILL.md` to follow this repository's create/update requirements:

1. Valid frontmatter (`name`, `description`, optional compatibility/license/metadata)
2. Required sections:
   - `When to Use This Skill`
   - `Your Roles in This Skill`
   - `Role Communication`
   - `Instructions`
3. Keep concise; move heavy details to `references/` if needed

Use the checklist in `references/skill-normalization.md`.

### Step 5: Handle license files and attribution

After copy, ensure a license file exists in the imported skill folder using this order:

1. Check for a license file inside the imported skill folder, supporting common names:
   - `LICENSE`, `LICENCE`, `LICENSE.md`, `LICENCE.md`, `COPYING`, `COPYING.md`
2. If none exists in the skill folder, check the cloned repository root for the same names and copy the first match into the imported skill folder as `LICENSE`.
3. If no license file exists anywhere in the cloned project, create `<skill>/LICENSE` with:
   - `unknown licence`
   - `source: <repo-url>`

If an existing license file is found (inside skill folder or from repo root), prepend a one-line update note:

- `Skill-Pilot update note (YYYY-MM-DD): SKILL.md normalized for local agent-skill rules; original license terms remain in effect.`

Do not alter original license text beyond this prepended note.

### Step 6: Verify and install the skill

From repo root:

1. `core/bin/skill-verify <relative-skill-path>`
2. `core/bin/skill-install`

Fix any validation issues and re-run until clean.

### Step 7: Report completion

Return:

1. Source repo URL and imported folder path
2. Destination path
3. Files changed during normalization
4. How license handling was resolved (found in skill folder, copied from repo root, or created as unknown)
5. Verify/install command results

## Expected Output

- Imported skill folder from remote repo via sparse checkout
- Localized, rule-compliant `SKILL.md`
- License resolved consistently (existing, copied from repo root, or created as unknown) with attribution
- Successful verify/install status or actionable failures

## Key Principles

- Pull only required files using sparse checkout
- Treat third-party content as untrusted until reviewed
- Preserve licensing terms while documenting local modifications
- Keep transformation steps reproducible and auditable
