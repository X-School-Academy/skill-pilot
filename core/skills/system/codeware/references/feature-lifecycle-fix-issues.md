# Feature Lifecycle: Fix Issues

Use when a feature has bug reports or issues to resolve.

## Steps

### Phase 1: Prepare

1. Archive any existing `issues.md`, `issues-plan.md`, `issues-impl.md` into `archive/` with timestamps (e.g. `archive/issues.{timestamp}.md`) before starting. Create the `archive/` folder if it does not exist.
2. If `issues.md` does not exist, create it from the user's bug descriptions or issue notes.

### Phase 2: Plan

3. Read `requirements.md` and `implementation.md` for context.
4. Write `issues-plan.md` with the fix steps and files to touch for each issue.

### Phase 3: Fix

5. Implement the fixes following `issues-plan.md`.
6. Write `issues-impl.md` summarizing what was fixed and how.

### Phase 4: Update Persistent Files

7. Update `implementation.md` to reflect the corrected implementation state.
8. Update `CHANGELOG.md` with a brief entry describing the fixes.
