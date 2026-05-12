# Stage Reference: implement

Implement the project according to `plan.md`.

## When to Use

- The user wants code written from `design-docs/plan.md`
- The plan is approved
- Project is moving from planning into execution

## Steps

### Step 1: Read the Plan

Read `design-docs/plan.md` and identify implementation steps in order.

### Step 2: Implement

Make the required code changes. If a meaningful deviation is needed, explain it before proceeding.

### Step 3: Verify

Run the most relevant tests or static checks for the changed code.

### Step 4: Update the Implementation Record

Write the implementation summary to `design-docs/implementation.md` (overwrite — it is a living doc):

- What was implemented
- What was verified
- Remaining risks

### Step 5: Update Top-Level Project Files

Update the top-level files to reflect the current implementation state:

- `README.md` — update Setup, Usage, and any feature sections that changed.
- `AGENTS.md` — update any project-specific AI agent notes that are now out of date.

(`CHANGELOG.md` is updated by the `update` and `fix-issues` stages, not here.)

### Step 6: Report

Report what was implemented, what was verified, and any remaining risks.
