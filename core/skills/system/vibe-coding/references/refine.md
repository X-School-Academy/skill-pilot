# Stage Reference: refine

Refine the trigger document for clarity, grammar, and logic without changing the requested scope. The target file depends on the active flow:

- New project flow: `design-docs/requirements.md`
- Update flow: `design-docs/update.md`
- Fix flow: `design-docs/issues.md`

## When to Use

- The user wants to clean up the trigger document before planning
- The trigger file is rough or inconsistent
- The requirement may reference an existing repo, website, game, app, clone, port, remake, or reimplementation

## Steps

### Step 1: Identify the Active Flow and Read the Trigger File

- New project: read `design-docs/requirements.md`
- Update: read `design-docs/update.md`
- Fix: read `design-docs/issues.md`

Identify wording, grammar, and logic issues.

### Step 2: Check for Reference-Project Work (new project flow only)

If the requirement asks to learn from, clone, port, remake, reimplement, or get inspiration from a source-code repo, live website, game, or app, follow `references/refine-reference-project.md`.

Otherwise continue with the normal refinement steps below.

### Step 3: Refine Only

Fix English, clarity, consistency, and obvious logic issues. Do not add new requirements, features, or constraints — only make the existing content clear and unambiguous.

### Step 4: Save the Refined File

Write the improved content back to the same trigger file (living doc — no archive copy needed).

### Step 5: Summarize

Briefly report what was refined.
