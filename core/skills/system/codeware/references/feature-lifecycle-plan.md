# Feature Lifecycle: Plan

Use when a feature requirement needs an implementation plan.

## Steps

1. Read the feature's `requirements.md`.
2. Read `implementation.md` if it exists (provides current implementation context for updates or re-plans).
3. Scan `core/features/` for feature files related by topic or name. Read any that are relevant to understand context and dependencies. Do not read all files — match by topic similarity or explicit references in `requirements.md`.
4. If a `plan.md` already exists, archive it as `archive/plan.{timestamp}.md` before overwriting. Create the `archive/` folder if it does not exist.
5. Write `plan.md` with implementation steps, files to touch, and open questions.
