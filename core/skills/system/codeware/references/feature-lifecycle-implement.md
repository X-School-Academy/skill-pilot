# Feature Lifecycle: Implement

Use when an approved `plan.md` is ready for coding. Works for all flows: new feature, update, and fix.

## Steps

0. **Copy showcase files if needed.** If this feature was launched from an Explore showcase that has a `directory` field, check whether `requirements.md`, `update.md`, and `issues.md` exist in `workspace/showcases/{showcase_slug_id}/`. For each file that exists there but is not already present in the feature `directory`, copy it before starting. Skip if not launched from a showcase.
1. Read `plan.md`.
2. Make the code changes.
3. Verify the implementation with checks appropriate to the touched area.
4. Update `implementation.md` to reflect the current state of what was built.
5. Update `README.md` if usage or behavior changed.
6. Update `CHANGELOG.md` with a brief entry for this change (new feature, update, or fix).
7. Update `AGENTS.md` if AI-agent instructions for this feature changed.
