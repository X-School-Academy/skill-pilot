# Feature Lifecycle: Initial

Use when a feature requirement exists and work should begin before planning or implementation.

## Steps

1. Read the referenced `requirements.md`.
2. Detect whether the current environment is a git worktree or the main repo (`git rev-parse --git-dir` returns a file path inside `.git/worktrees/` for a worktree).

**If in a git worktree:**
3. Use the current branch as-is — do not create a new dev branch.
4. If there are uncommitted changes, ask the user whether to commit or stash them before proceeding.
5. Continue working on the current branch.

**If in the main repo:**
3. Confirm the working tree is on the `user` branch with no uncommitted changes.
4. If not on `user`, switch to `user` first.
5. If there are uncommitted changes, ask the user whether to commit or stash them before proceeding.
6. Detect the trigger context and create the appropriate branch from `user`:
   - New feature from `requirements.md`: `feature/{feature-name}`
   - Update from `update.md`: `update/{feature-name}`
   - Bug fix from `issues.md`: `fix/{feature-name}`
7. Switch to the new branch and continue working on it.
