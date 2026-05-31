# Category: Agent Skills — Types

Install, scaffold, and compose Skill Pilot agent skills.

Primary audiences: AI agent builders, platform contributors.

## Types

### AS1. Install a skill
- Add an existing skill from a registry / git URL and run it.

### AS2. Scaffold a new skill
- Use `agent-skill` to generate `SKILL.md`, references, and a starter prompt for a new capability.

### AS3. Refactor an existing skill
- Tighten an existing skill's instructions, references, or trigger description.

### AS4. Compose multiple skills
- Build a showcase whose prompt deliberately chains 2–3 skills (e.g., `markitdown` → `course-creator`).

### AS5. Reverse-engineer a skill
- Remove a feature from a working skill, draft a `requirements.md`, and ask the user to restore it. Requires `git_tag` + `use_worktree: true` + `in_mode: dev`.

### AS6. Test / validate a skill
- Drive a skill through positive and negative cases and produce a report.
