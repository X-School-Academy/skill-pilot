# Feature Lifecycle: Create

Use when the user wants a new feature started and a `requirements.md` should be created.

## Steps

1. Choose a short kebab-case feature folder name.
2. Write `core/development/{feature-name}/requirements.md` from the user's request.
3. Create the three stub persistent files in the same folder:
   - `README.md` — feature name as heading + one-line description derived from requirements
   - `CHANGELOG.md` — stub with `## Unreleased` header only
   - `AGENTS.md` — use `references/agents-template.md` as the template; replace `{Feature Name}` and `{feature-name}` with the actual feature name.
