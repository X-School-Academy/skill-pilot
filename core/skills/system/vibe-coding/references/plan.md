# Stage Reference: plan

Create a development plan from `requirements.md`.

## When to Use

- The user wants a dev plan
- A file-by-file implementation approach is needed
- Works for all flows: new project, update, and fix

## Package Management Tools

Use `uv` for Python projects and `pnpm` for Node.js projects unless the user asks otherwise. Mention this in the plan when relevant.

## Steps

### Step 1: Read the Context

Detect the active flow and read the appropriate docs:
- New project: read `design-docs/requirements.md`
- Update flow (`update.md` present): read `design-docs/requirements.md`, `design-docs/implementation.md`, and `design-docs/update.md`
- Fix flow (`issues.md` present): read `design-docs/requirements.md`, `design-docs/implementation.md`, and `design-docs/issues.md`

### Step 2: Review the Current Codebase

Inspect relevant code and identify implementation gaps.

### Step 3: Interview the User to Co-Design the Plan

After exploring the codebase, only interview the user about genuinely ambiguous decisions — skip anything you can answer clearly from the requirements, the codebase, or established conventions. For the remaining open points, walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time. If there are no real ambiguities, skip this step.

### Step 4: Archive the Existing Plan

If `design-docs/plan.md` already exists, archive it before writing the new one:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/plan.md "design-docs/archive/plan.$timestamp.md"
```

### Step 5: Write the Plan

Create `design-docs/plan.md`. Include:

- Scope
- Current-state analysis
- Implementation phases
- Likely file changes
- Open questions

### Step 6: Ask for Approval

Present the plan as ready for approval before implementation starts.
