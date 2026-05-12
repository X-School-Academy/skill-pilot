# Feature Lifecycle: Merge

Use when implementation, review, and testing are complete.

## Steps

1. Read `implementation.md` and confirm the feature is ready to merge.
2. Merge the feature branch back to `user` and switch the working copy to `user`.
3. Update `CHANGELOG.md` with a new entry describing what was added, changed, or fixed in this cycle. Include the date and branch name.
4. Refresh living docs to reflect the merged state:
   - `requirements.md` — if scope changed
   - `implementation.md` — to reflect the final merged implementation
5. Load `references/feature-lifecycle-freeze.md` and follow the freeze steps to record the feature under `core/features/`.
6. Delete the feature branch after a successful merge.
