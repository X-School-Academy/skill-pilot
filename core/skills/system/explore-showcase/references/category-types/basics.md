# Category: Basics — Types

Beginner-friendly first runs that prove the environment works end-to-end and build user confidence before they try anything ambitious.

Primary audience: AI agent learners and first-time users.

## Types

### B1. Hello-world prompt
- One-shot prompt that returns a visible artifact (a poem, a haiku, a short summary).
- No file inputs, no skills required.

### B2. First file read
- Drop a small `.txt` or `.md` file in `workspace/` and ask the agent to summarise it.
- Teaches the file-attach pattern with `@path/to/file`.

### B3. First skill invocation
- Run one well-defined skill (e.g., `create-image-audio` for a thumbnail, `markitdown` for a doc convert).
- Confirms the skill registry and tool plumbing work locally.

### B4. First terminal command
- Use the `terminal` skill to run a safe shell command (`ls`, `git status`).
- Confirms permissions and sandbox configuration are correct.

### B5. First scheduled run
- Use `schedule` to fire a trivial task once, five minutes from now.
- Confirms the scheduler and notification path.
