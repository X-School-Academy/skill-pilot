# Feature Lifecycle: Update

Use when an existing feature needs additional changes.

## Steps

### Phase 1: Prepare

1. Archive any existing `update.md`, `update-plan.md`, `update-impl.md` into `archive/` with timestamps (e.g. `archive/update.{timestamp}.md`) before starting. Create the `archive/` folder if it does not exist.
2. If `update.md` does not exist, create it from the user's description of the requested changes.

### Phase 2: Plan

3. Read `requirements.md` and `implementation.md` for context.
4. Scan `core/features/` for feature files related by topic or name and read relevant ones for dependencies.
5. Write `update-plan.md` with the implementation steps and files to touch.

### Phase 3: Implement

6. Implement the changes following `update-plan.md`.
7. Write `update-impl.md` summarizing what was done and what changed.

### Phase 4: Update Persistent Files

8. Update `implementation.md` to reflect the new implementation state.
9. Update `CHANGELOG.md` with a brief entry for this update.
10. Update `README.md` if usage or behavior changed.
