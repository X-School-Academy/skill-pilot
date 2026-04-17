# User Preferences

- Record durable user corrections and workflow preferences here as short actionable bullets.
- For skill authoring, write frontmatter descriptions for LLM pickup: focus on capability, outputs, triggers, and task context, not implementation details.
- For skill authoring, keep `SKILL.md` minimal and move tool usage details into `references/` files; document tool usage, not tool internals.
- For skill updates that rename the skill, rename the skill folder too, and split mode-specific instructions into dedicated reference files.
- For scene/video tests, do not mock `capture_image`, `record_screen`, or similar HTML/CSS rendering paths when the goal is to verify the real rendered output.
- For Explore worktree creation, stash local changes before `git worktree add`, apply the stash in both the new worktree and the original repo, drop the stash afterward, and create a `config/.env` symlink in the new worktree that points to the original repo env file.
- Always use the `dev-swarm-draft-commit-message` agent skill when committing — never use a raw `git commit` bash command directly.
