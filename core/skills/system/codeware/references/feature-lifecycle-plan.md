# Feature Lifecycle: Plan

Use when a feature needs an implementation plan. Works for all flows: new feature, update, and fix.

## Steps

1. Detect the active flow by checking which trigger doc is present:
   - New feature: no `update.md` or `issues.md` present → read `requirements.md`
   - Update flow: `update.md` present → read `requirements.md`, `implementation.md`, and `update.md`
   - Fix flow: `issues.md` present → read `requirements.md`, `implementation.md`, and `issues.md`
2. Scan `core/features/` for feature files related by topic or name. Read relevant ones for context and dependencies. Do not read all files — match by topic similarity or explicit references in `requirements.md`.
3. If a `plan.md` already exists, archive it as `archive/plan.{timestamp}.md` before overwriting. Create the `archive/` folder if it does not exist.
4. Write `plan.md` with implementation steps, files to touch, and open questions.
