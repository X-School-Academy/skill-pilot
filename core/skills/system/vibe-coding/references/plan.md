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

### Step 3: Archive the Existing Plan

If `design-docs/plan.md` already exists, archive it before writing the new one:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/plan.md "design-docs/archive/plan.$timestamp.md"
```

### Step 4: Write the Plan

Create `design-docs/plan.md`. Include:

- Scope
- Current-state analysis
- Implementation phases
- Likely file changes
- Open questions

For the **update or bug fix flow**, also read `design-docs/implementation.md` alongside `requirements.md` to understand the current implementation state before planning changes.

### Step 5: Ask for Approval

Present the plan as ready for approval before implementation starts.
