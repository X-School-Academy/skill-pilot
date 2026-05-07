# Stage Reference: plan

Create a development plan from `requirements.md`.

## When to Use

- The user wants a dev plan from `design-docs/requirements.md`
- A file-by-file implementation approach is needed
- Next step is implementation planning, not coding

## Package Management Tools

Use `uv` for Python projects and `pnpm` for Node.js projects unless the user asks otherwise. Mention this in the plan when relevant.

## Steps

### Step 1: Read the Requirement

Read `design-docs/requirements.md`.

### Step 2: Review the Current Codebase

Inspect relevant code and identify implementation gaps.

### Step 3: Write the Plan

Create or update `design-docs/plan.md`. Include:

- Scope
- Current-state analysis
- Implementation phases
- Likely file changes
- Open questions

### Step 4: Ask for Approval

Present the plan as ready for approval before implementation starts.
