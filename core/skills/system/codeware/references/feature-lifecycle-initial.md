# Feature Lifecycle: Initial

Use when a feature requirement exists and a branch should be created before planning or implementation.

## Steps

1. Read the referenced `requirements.md`.
2. Confirm the working tree is on the `user` branch with no uncommitted changes.
3. If not on `user`, switch to `user` first.
4. If there are uncommitted changes, ask the user whether to commit or stash them before proceeding.
5. Detect the trigger context and create the appropriate branch from `user`:
   - New feature from `requirements.md`: `feature/{feature-name}`
   - Update from `update.md`: `update/{feature-name}`
   - Bug fix from `issues.md`: `fix/{feature-name}`
6. Switch to the new branch and continue working on it.
