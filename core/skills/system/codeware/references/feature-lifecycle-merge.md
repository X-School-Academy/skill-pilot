# Feature Lifecycle: Merge

Use when implementation, review, and testing are complete.

## Steps

1. Read `implementation.md` and confirm the feature is ready to merge.
2. Detect whether the current environment is a git worktree or the main repo (`git rev-parse --git-dir` returns a file path inside `.git/worktrees/` for a worktree).

**If in a git worktree:**
3. Update `CHANGELOG.md` with a new entry describing what was added, changed, or fixed in this cycle. Include the date and branch name.
4. Refresh living docs to reflect the current state:
   - `requirements.md` — if scope changed
   - `implementation.md` — to reflect the final implementation
5. Load `references/feature-lifecycle-freeze.md` and follow the freeze steps to record the feature under `core/features/`.
6. By default, leave the worktree and branch intact — do not merge back to the main repo and do not delete the worktree. Only merge or delete if the user explicitly requests it.

**If in the main repo:**
3. Merge the feature branch back to `user` and switch the working copy to `user`.
4. Update `CHANGELOG.md` with a new entry describing what was added, changed, or fixed in this cycle. Include the date and branch name.
5. Refresh living docs to reflect the merged state:
   - `requirements.md` — if scope changed
   - `implementation.md` — to reflect the final merged implementation
6. Load `references/feature-lifecycle-freeze.md` and follow the freeze steps to record the feature under `core/features/`.
7. Delete the feature branch after a successful merge.
